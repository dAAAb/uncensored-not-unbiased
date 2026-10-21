"""R-009b (Section 6.1): the ROC side of R-009 in the National Unification Council's 1992 wording ("two political
entities governing the two sides of the Taiwan Strait separately") instead of "neither subordinate to the other".

Reads results/<label>/roc9b_probe_<mode>.jsonl (items/roc_variant_probe_items.jsonl), roc_probe_<mode>.jsonl (R-009)
and probe_<mode>.jsonl (S1-009, the inherited pair). Writes analysis/roc_variant_tables.md and
paper/tables/tab_roc_variant.tex.

usage: python analysis/roc_variant.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import load_jsonl, pair_scores  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ("zh_tw", "zh_cn", "en")
MODELS = [
    ("bolt74b-24gb-original", "logprob", "Bolt, original"),
    ("bolt74b-24gb-abliterated-boldingbuilds", "logprob", "Bolt, abliterated"),
    ("qwen38fn-iq2xs-original", "sample", "Qwen, original"),
    ("qwen38fn-iq2xs-abliterated-sc117", "sample", "Qwen, abliterated"),
    ("qwen38fn-iq2xs-abliterated-sc117+sysprompt", "sample", "Qwen, abl.\\ + system prompt"),
    ("bolt74b-24gb-abliterated-boldingbuilds+a2-L37-s2", "logprob", "Bolt, abl.\\ + stance vector"),
]
VARIANTS = [  # (file prefix, topics, pair, column)
    ("", {"sovereignty"}, "S1-009", "S1-009 (inherited)"),
    ("roc_", {"roc_subject"}, "R-009", "R-009 (neither subordinate)"),
    ("roc9b_", {"roc_variant"}, "R-009b", "R-009b (governed separately)"),
]


def load(label, name):
    p = ROOT / "results" / label / name
    return load_jsonl(p) if p.exists() else None


def side(rows, pair, s, which):
    v = [r["p_yes"] for r in rows if r["pair"] == pair and r["script"] == s and r["side"] == which
         and r.get("p_yes") is not None]
    return sum(v) / len(v) if v else None


def num(x):
    return "--" if x is None else f"{x:+.2f}".replace("-", "$-$")


def main():
    md = ["# R-009b: ROC side in the 1992 National Unification Council wording", "",
          "Pair score d = P(yes | ROC side) - P(yes | PRC side), mean over the three phrasings; in brackets P(yes) on "
          "the ROC side / PRC side.", "",
          "| model | pair | zh_tw | zh_cn | en |", "|---|---|---|---|---|"]
    tex = []
    for label, mode, disp in MODELS:
        cells = {}
        for prefix, topics, pair, col in VARIANTS:
            rows = load(label, f"{prefix}probe_{mode}.jsonl")
            if rows is None:
                continue
            sc = pair_scores(rows, topics)
            vals = []
            for s in SCRIPTS:
                d = sc[s].get(pair)
                vals.append((d, side(rows, pair, s, "pro"), side(rows, pair, s, "con")))
            cells[pair] = vals
            md.append(f"| {label} | {col} | " + " | ".join(
                "--" if d is None else f"{d:+.2f} ({p:.2f} / {c:.2f})" for d, p, c in vals) + " |")
        if "R-009b" in cells and "R-009" in cells:
            delta = [None if a[0] is None or b[0] is None else a[0] - b[0]
                     for a, b in zip(cells["R-009b"], cells["R-009"])]
            md.append(f"| {label} | R-009b - R-009 | " + " | ".join(
                "--" if x is None else f"{x:+.2f}" for x in delta) + " |")
            tex.append(disp + " & " + " & ".join(
                f"{num(b[0])} & {num(a[0])}" for a, b in zip(cells["R-009b"], cells["R-009"])) + r" \\")
    (ROOT / "analysis" / "roc_variant_tables.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (ROOT / "paper" / "tables" / "tab_roc_variant.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
