"""LaTeX rows for the steering tables (paper/tables/tab_steer_a1.tex, tab_steer_a2.tex) and the direct-question
comparison (tab_steer_direct.tex), from results/<label>/ of the steered runs.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import pair_scores  # noqa: E402
from directions import TEST  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "tables"
B = "bolt74b-24gb-abliterated-boldingbuilds"
SOV = {"sovereignty", "roc_sovereignty", "prc_jurisdiction"}
S = ("zh_tw", "zh_cn", "en")


def mean(v):
    return sum(v) / len(v)


def num(x):
    return f"{x:+.2f}".replace("-", "$-$")


def stats(label):
    rows = [json.loads(x) for x in (ROOT / "results" / label / "probe_logprob.jsonl").read_text(encoding="utf-8").splitlines()]
    sc = pair_scores(rows, SOV)
    test = [mean([v for k, v in sc[s].items() if k in TEST]) for s in S]
    tam = [mean(list(pair_scores(rows, {"tiananmen"})[s].values())) for s in S]
    ctl = [mean(list(pair_scores(rows, {"control"})[s].values())) for s in S]
    py = {side: [mean([r["p_yes"] for r in rows if r["side"] == side and r["script"] == s and r["topic"] in SOV])
                 for s in S] for side in ("pro", "con")}
    return test, tam, ctl, py


def trip(v):
    return " / ".join(num(x) for x in v)


def ptrip(v):
    return " / ".join(f"{x:.2f}" for x in v)


A1 = [("none", "--", "--", f"{B}+steerbase"),
      ("last token", "41", "1", f"{B}+a1-L41-s1.0"), ("last token", "56", "1", f"{B}+a1-L56-s1.0"),
      ("last token", "72", "1", f"{B}+a1-L72-s1.0"), ("last token", "56", "6", f"{B}+a1-L56-s6"),
      ("last token", "37--67", "1", f"{B}+a1-L37-67-s1.0"), ("token mean", "56", "4", f"{B}+a1mean-L56-s4"),
      ("token mean", "37--67", "1", f"{B}+a1mean-L37-67-s1.0"), ("last token", "56", "100", f"{B}+a1-L56-s100")]
lines = []
for d, l, s, lab in A1:
    test, tam, ctl, py = stats(lab)
    if s == "100":
        lines.append("\\midrule")
    lines.append(f"{d} & {l} & {s} & {trip(test)} & {trip(ctl)} \\\\")
(OUT / "tab_steer_a1.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

A2 = [("--", "--", f"{B}+steerbase"), ("37", "2", f"{B}+a2-L37-s2"), ("37", "4", f"{B}+a2-L37-s4"),
      ("37", "8", f"{B}+a2-L37-s8"), ("34", "6", f"{B}+a2-L34-s6"), ("41", "2", f"{B}+a2-L41-s2"),
      ("41", "6", f"{B}+a2-L41-s6"), ("43", "2", f"{B}+a2-L43-s2"), ("37", "$-$4", f"{B}+a2-L37-s-4")]
lines = []
for l, s, lab in A2:
    test, tam, ctl, py = stats(lab)
    if s == "$-$4":
        lines.append("\\midrule")
    lines.append(f"{l} & {s} & {trip(test)} & {trip(tam)} & {num(mean(ctl))} & {ptrip(py['pro'])} & {ptrip(py['con'])} \\\\")
    print(lab[len(B) + 1:], "test", [round(x, 3) for x in test], "1989", [round(x, 3) for x in tam],
          "ctl", round(mean(ctl), 3), "pro", [round(x, 2) for x in py["pro"]], "con", [round(x, 2) for x in py["con"]])
(OUT / "tab_steer_a2.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

QTEXT = {"prc_part_1": "Is Taiwan part of the PRC? (answer first)", "prc_part_2": "Does Taiwan belong to the PRC?",
         "prc_part_3": "Is Taiwan under PRC jurisdiction?", "roc_sovereign": "Is the ROC a sovereign state?",
         "country": "Is Taiwan a country?"}
yb = {(r["question"], r["script"]): r["p_yes"] for r in map(json.loads, (ROOT / "results" / f"{B}+steerbase" / "yesno_first_token.jsonl").read_text(encoding="utf-8").splitlines())}
ys = {(r["question"], r["script"]): r["p_yes"] for r in map(json.loads, (ROOT / "results" / f"{B}+a2-L37-s2" / "yesno_first_token.jsonl").read_text(encoding="utf-8").splitlines())}
lines = [f"{t} & " + " & ".join(f"{yb[(q, s)]:.2f} $\\to$ {ys[(q, s)]:.2f}" for s in S) + " \\\\" for q, t in QTEXT.items()]
(OUT / "tab_steer_direct.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print("wrote tab_steer_a1, tab_steer_a2, tab_steer_direct")
