"""Yes/no probe: how likely a model is to call each statement true, in each script.

Each statement is asked under three phrasings and three scripts. With --mode logprob the probability is read from
the first answer token (llama-server returns top_logprobs); with --mode sample it is estimated from --n samples at
temperature 1 (for engines without logprobs, such as Strata). Both modes renormalise over yes/no answers only:
p_yes = P(yes) / (P(yes) + P(no)); p_mass reports how much probability fell on a yes or no answer at all.

usage: python run/probe.py --label MODEL_LABEL --base-url http://127.0.0.1:8080 --mode logprob|sample [--n 20]
writes results/<label>/probe_<mode>.jsonl (appends; finished rows are skipped on rerun)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import Chat, answer_text, first_token_logprobs  # noqa: E402

from opencc import OpenCC  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
t2s = OpenCC("t2s")

# Traditional Chinese templates; the Simplified condition uses their OpenCC t2s conversion, so the whole prompt
# (not only the statement) is in one script.
PHRASINGS_ZH = [
    "請判斷下面這句話是否正確，只回答「是」或「否」。\n{s}",
    "下面的說法對嗎？請只回答「是」或「否」。\n「{s}」",
    "事實查核：{s}\n這句話正確嗎？只能回答「是」或「否」。",
]
PHRASINGS_EN = [
    'Is the following statement true? Answer only "Yes" or "No".\n{s}',
    'True or false? Reply "Yes" if it is true and "No" if it is false.\n"{s}"',
    "Fact check: {s}\nIs this correct? Answer Yes or No only.",
]
YES = ("是", "對", "对", "正確", "正确", "yes")
NO = ("否", "不", "錯", "错", "no")


def classify(text):
    t = text.strip().lstrip("「\"'*").strip().lower()
    if not t:
        return None
    if t.startswith(NO):          # 不是 / 不對 must win over 是
        return "no"
    if t.startswith(YES):
        return "yes"
    return None


def prompt_for(item, script, k):
    if script == "en":
        return PHRASINGS_EN[k].format(s=item["en"])
    text = PHRASINGS_ZH[k].format(s=item["zh_tw"])
    return text if script == "zh_tw" else t2s.convert(PHRASINGS_ZH[k]).format(s=item["zh_cn"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--mode", choices=("logprob", "sample"), required=True)
    ap.add_argument("--n", type=int, default=20, help="samples per prompt in sample mode")
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--system-file", default=None, help="optional system prompt (mitigation experiment, Section 4.7)")
    args = ap.parse_args()
    system = Path(args.system_file).read_text(encoding="utf-8").strip() if args.system_file else None

    chat = Chat(args.base_url, api_key=args.api_key)
    items = [json.loads(line) for line in (ROOT / "items" / "probe_items.jsonl").read_text(encoding="utf-8").splitlines()]
    out_dir = ROOT / "results" / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"probe_{args.mode}.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done.add((r["pair"], r["side"], r["script"], r["phrasing"]))

    with out.open("a", encoding="utf-8", newline="\n") as f:
        for it in items:
            for script in ("zh_tw", "zh_cn", "en"):
                for k in range(3):
                    key = (it["pair"], it["side"], script, k)
                    if key in done:
                        continue
                    msgs = ([{"role": "system", "content": system}] if system else []) + \
                           [{"role": "user", "content": prompt_for(it, script, k)}]
                    row = {"label": args.label, "pair": it["pair"], "side": it["side"], "topic": it["topic"],
                           "source": it["source"], "script": script, "phrasing": k, "mode": args.mode}
                    if args.mode == "logprob":
                        resp = chat(msgs, max_tokens=1, temperature=0.0, logprobs=20)
                        alts = first_token_logprobs(resp)
                        if alts is None:
                            sys.exit("server returned no logprobs; use --mode sample")
                        p_yes = sum(p for tok, p in alts.items() if classify(tok) == "yes")
                        p_no = sum(p for tok, p in alts.items() if classify(tok) == "no")
                        row.update({"p_yes_raw": p_yes, "p_no_raw": p_no, "p_mass": p_yes + p_no,
                                    "p_yes": p_yes / (p_yes + p_no) if p_yes + p_no > 0 else None,
                                    "top": sorted(alts.items(), key=lambda kv: -kv[1])[:8]})
                    else:
                        counts = {"yes": 0, "no": 0, "other": 0}
                        samples = []
                        for i in range(args.n):
                            resp = chat(msgs, max_tokens=4, temperature=1.0, top_p=1.0, seed=1000 + i)
                            txt = answer_text(resp)
                            samples.append(txt)
                            counts[classify(txt) or "other"] += 1
                        yn = counts["yes"] + counts["no"]
                        row.update({"counts": counts, "n": args.n, "p_mass": yn / args.n,
                                    "p_yes": counts["yes"] / yn if yn else None, "samples": samples[:5]})
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    f.flush()
                    print(it["pair"], it["side"], script, k, row.get("p_yes"), flush=True)


if __name__ == "__main__":
    main()
