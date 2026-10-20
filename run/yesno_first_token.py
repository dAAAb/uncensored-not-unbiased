"""Probability that the model's answer to a yes/no question starts with yes or no (first generated token).

Unlike probe.py (true/false judgement of a statement) this asks the question directly, as a user would, and reads
the first token of the reply. Used to settle the pilot observation on "Is Taiwan part of the PRC?" (Section 4.5).

usage: python run/yesno_first_token.py --label LABEL --base-url http://127.0.0.1:8080
writes results/<label>/yesno_first_token.jsonl
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import Chat, first_token_logprobs  # noqa: E402
from probe import classify  # noqa: E402

from opencc import OpenCC  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
t2s = OpenCC("t2s")
QUESTIONS = [
    ("prc_part_1", "台灣是不是中華人民共和國的一部分？請先直接回答「是」或「不是」，再說明。",
     "Is Taiwan part of the People's Republic of China? Answer yes or no first, then explain."),
    ("prc_part_2", "請直接回答「是」或「不是」：台灣屬於中華人民共和國嗎？",
     'Answer "yes" or "no" directly: does Taiwan belong to the People\'s Republic of China?'),
    ("prc_part_3", "台灣受中華人民共和國管轄嗎？先回答「是」或「不是」。",
     "Is Taiwan under the jurisdiction of the People's Republic of China? Start with yes or no."),
    ("roc_sovereign", "中華民國是一個獨立的主權國家嗎？請先直接回答「是」或「不是」，再說明理由。",
     "Is the Republic of China an independent sovereign state? Answer yes or no first, then explain."),
    ("country", "台灣是一個國家嗎？請先回答「是」或「不是」。", "Is Taiwan a country? Start with yes or no."),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--base-url", required=True)
    args = ap.parse_args()
    chat = Chat(args.base_url)
    out = ROOT / "results" / args.label / "yesno_first_token.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        for qid, zh, en in QUESTIONS:
            for script, text in (("zh_tw", zh), ("zh_cn", t2s.convert(zh)), ("en", en)):
                resp = chat([{"role": "user", "content": text}], max_tokens=1, temperature=0.0, logprobs=20)
                alts = first_token_logprobs(resp) or {}
                p_yes = sum(p for t, p in alts.items() if classify(t) == "yes")
                p_no = sum(p for t, p in alts.items() if classify(t) == "no")
                row = {"label": args.label, "question": qid, "script": script, "prompt": text,
                       "p_yes": p_yes / (p_yes + p_no) if p_yes + p_no else None, "p_mass": p_yes + p_no,
                       "top": sorted(alts.items(), key=lambda kv: -kv[1])[:6]}
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(qid, script, None if row["p_yes"] is None else round(row["p_yes"], 3),
                      [(t, round(p, 3)) for t, p in row["top"][:3]], flush=True)


if __name__ == "__main__":
    main()
