"""Index S for the ROC-framed stance vector (A3, Section 5.3), from <prefix>probe_logprob.jsonl runs on
items/roc_steer_probe_items.jsonl: train / select pairs (items/roc_steer_items.json), the fresh test pairs, 1989,
controls, and mean P(yes) per side on the select and fresh pairs. --json writes the numbers for the paper tables.

usage: python steer/score_roc.py <label> [<label> ...] [--prefix a3_] [--json steer/work/a3_scores.json]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from analyze import pair_scores  # noqa: E402

S = ("zh_tw", "zh_cn", "en")
SP = json.loads((ROOT / "items" / "roc_steer_items.json").read_text(encoding="utf-8"))
FRESH = [p["id"] for p in SP["fresh_pairs"]]


def mean(v):
    return sum(v) / len(v) if v else float("nan")


def score(rows):
    out = {}
    for name, topics, pairs in (("train", {"roc_subject"}, SP["train"]), ("select", {"roc_subject"}, SP["select"]),
                                ("fresh", {"roc_fresh"}, FRESH), ("1989", {"tiananmen"}, None),
                                ("ctrl", {"control"}, None)):
        sc = pair_scores(rows, topics)
        out[name] = [mean([v for k, v in sc[s].items() if pairs is None or k in pairs]) for s in S]
    for name, pairs in (("select", SP["select"]), ("fresh", FRESH)):
        for side in ("pro", "con"):
            out[f"pyes_{name}_{side}"] = [mean([r["p_yes"] for r in rows if r["side"] == side and r["script"] == s
                                                and r["pair"] in pairs and r.get("p_yes") is not None]) for s in S]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("labels", nargs="+")
    ap.add_argument("--prefix", default="a3_")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    fmt = lambda v: "/".join(f"{x:+.2f}" for x in v)  # noqa: E731
    allout = {}
    for label in args.labels:
        p = ROOT / "results" / label / f"{args.prefix}probe_logprob.jsonl"
        if not p.exists():
            print(label, "missing")
            continue
        o = score([json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()])
        allout[label] = o
        print(f"{label[39:] or label:16s} train {fmt(o['train'])}  SELECT {fmt(o['select'])}  FRESH {fmt(o['fresh'])}  "
              f"1989 {fmt(o['1989'])}  ctrl {fmt(o['ctrl'])}  P(yes) sel pro {fmt(o['pyes_select_pro'])} "
              f"con {fmt(o['pyes_select_con'])}  fresh pro {fmt(o['pyes_fresh_pro'])} con {fmt(o['pyes_fresh_con'])}")
    if args.json:
        Path(args.json).write_text(json.dumps(allout, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
