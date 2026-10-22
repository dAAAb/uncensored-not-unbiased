"""Section 6.1: what the change of wording changed, per model, in one table.

For each model: the change in Index S from the inherited wording to the ROC (Taiwan) wording on the 16 sovereignty
pairs (mean over pairs of ROC pair score minus the score of the inherited pair it restates), the same on the seven
pairs where only the subject changed, the script gap under both wordings, and whether each Index S interval excludes
zero under each wording. Reads the same files as analysis/roc.py. Writes paper/tables/tab_frame_sum.tex; prints the
numbers quoted in the text.

usage: python analysis/frame_summary.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import boot_ci, pair_scores  # noqa: E402
from roc import MODELS, ROC, ROOT, SCRIPTS, SOV, change_groups, index_s, load, mean, mirrors, num  # noqa: E402

EXTRA = [("qwen38fn-iq2xs-abliterated-sc117+sysprompt", "sample", "Qwen, abl.\\ + system prompt")]


def num0(x):
    return num(0.0 if x is not None and abs(x) < 0.005 else x)


def side_of_zero(lo, hi):
    return "ROC" if lo > 0 else "PRC" if hi < 0 else "0"


def main():
    mir, grp = mirrors(), change_groups()
    tex = []
    for label, mode, disp in list(MODELS) + EXTRA:
        roc, old = load(label, f"roc_probe_{mode}.jsonl"), load(label, f"probe_{mode}.jsonl")
        if roc is None or old is None:
            continue
        r, rsc = index_s(roc, ROC)
        o, _ = index_s(old, SOV)
        osc = pair_scores(old, SOV)
        all_d, subj_d = [], []
        for s in SCRIPTS:
            d = {p: rsc[s][p] - osc[s][mir[p]] for p in rsc[s] if mir.get(p) in osc[s]}
            all_d.append(mean(list(d.values())))
            subj_d.append(mean([v for p, v in d.items() if grp[p] == "subject"]))
            lo, hi = boot_ci(list(d.values()))
            print(f"{label} {s}: inherited {o[s][0]:+.3f} [{o[s][1]:+.3f},{o[s][2]:+.3f}] {side_of_zero(o[s][1], o[s][2])}"
                  f" -> ROC {r[s][0]:+.3f} [{r[s][1]:+.3f},{r[s][2]:+.3f}] {side_of_zero(r[s][1], r[s][2])};"
                  f" change {all_d[-1]:+.3f} [{lo:+.3f},{hi:+.3f}], subject-only {subj_d[-1]:+.3f}")
        print(f"{label} gap: inherited {o['gap'][0]:+.3f} -> ROC {r['gap'][0]:+.3f}")
        tex.append(f"{disp} & " + " & ".join(num0(x) for x in all_d) + " & " + " & ".join(num0(x) for x in subj_d)
                   + f" & {num0(o['gap'][0])} $\\to$ {num0(r['gap'][0])} \\\\")
    (ROOT / "paper" / "tables" / "tab_frame_sum.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
