"""Index S for steered runs: train / held-out sovereignty pairs, 1989, controls, mean P(yes) per side.

usage: python steer/score.py <label> [<label> ...]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
from analyze import pair_scores  # noqa: E402

from directions import TEST, TRAIN  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOV = {"sovereignty", "roc_sovereignty", "prc_jurisdiction"}
S = ("zh_tw", "zh_cn", "en")


def mean(v):
    return sum(v) / len(v) if v else float("nan")


for label in sys.argv[1:]:
    p = ROOT / "results" / label / "probe_logprob.jsonl"
    if not p.exists():
        print(label, "missing")
        continue
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]
    out = {}
    for name, topics, pairs in (("train", SOV, TRAIN), ("test", SOV, TEST), ("1989", {"tiananmen"}, None),
                                ("ctrl", {"control"}, None)):
        sc = pair_scores(rows, topics)
        out[name] = [mean([v for k, v in sc[s].items() if pairs is None or k in pairs]) for s in S]
    py = {side: [mean([r["p_yes"] for r in rows if r["side"] == side and r["script"] == s and r["topic"] in SOV])
                 for s in S] for side in ("pro", "con")}
    fmt = lambda v: "/".join(f"{x:+.2f}" for x in v)  # noqa: E731
    print(f"{label[39:] or label:24s} train {fmt(out['train'])}  TEST {fmt(out['test'])}  1989 {fmt(out['1989'])}  "
          f"ctrl {fmt(out['ctrl'])}  P(yes) pro {fmt(py['pro'])} con {fmt(py['con'])}")
