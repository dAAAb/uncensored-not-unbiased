"""Open questions answered in free text: one greedy answer plus --samples answers at temperature 0.7, per script.

usage: python run/generate.py --label MODEL_LABEL --base-url http://127.0.0.1:8080 [--samples 2] [--max-tokens 700]
       [--items roc_open_items.jsonl --prefix roc_]
writes results/<label>/<prefix>generate.jsonl (appends; finished rows are skipped on rerun)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import Chat, answer_text  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--samples", type=int, default=2)
    ap.add_argument("--max-tokens", type=int, default=700)
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--items", default="open_items.jsonl", help="item file in items/")
    ap.add_argument("--prefix", default="", help="output file prefix, e.g. roc_")
    args = ap.parse_args()

    chat = Chat(args.base_url, api_key=args.api_key)
    items = [json.loads(line) for line in (ROOT / "items" / args.items).read_text(encoding="utf-8").splitlines()]
    out_dir = ROOT / "results" / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{args.prefix}generate.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done.add((r["id"], r["script"], r["run"]))

    runs = [("greedy", 0.0, None)] + [(f"t07_s{i}", 0.7, 2000 + i) for i in range(args.samples)]
    with out.open("a", encoding="utf-8", newline="\n") as f:
        for it in items:
            for script in ("zh_tw", "zh_cn", "en"):
                for run, temp, seed in runs:
                    if (it["id"], script, run) in done:
                        continue
                    resp = chat([{"role": "user", "content": it[script]}], max_tokens=args.max_tokens,
                                temperature=temp, top_p=0.95 if temp else 1.0, seed=seed)
                    row = {"label": args.label, "id": it["id"], "category": it["category"], "source": it["source"],
                           "script": script, "run": run, "temperature": temp, "prompt": it[script],
                           "answer": answer_text(resp), "finish": resp["choices"][0].get("finish_reason"),
                           "completion_tokens": (resp.get("usage") or {}).get("completion_tokens"),
                           "wall_s": resp.get("_wall_s")}
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    f.flush()
                    print(it["id"], script, run, row["finish"], row["wall_s"], flush=True)


if __name__ == "__main__":
    main()
