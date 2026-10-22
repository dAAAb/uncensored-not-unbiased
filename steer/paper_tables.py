"""LaTeX rows for the steering tables of Section 5 (version 2: both experiments on the Republic of China (Taiwan)
wording of items/roc_steer_items.json): tab_steer_a1.tex (script direction), tab_steer_a3.tex (stance vector, layer and
scale), tab_steer_fresh.tex (the 8 fresh test pairs) and tab_steer_direct.tex (direct questions), from results/<label>/
of the steered runs (a3_probe_logprob.jsonl, yesno_first_token.jsonl). Version 1 used the inherited wording
(results/<B>+a1-*, +a1mean-*, +a2-*); those runs stay in results/ but no longer feed a table.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import pair_scores  # noqa: E402
from score_roc import score as roc_score  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "tables"
B = "bolt74b-24gb-abliterated-boldingbuilds"
S = ("zh_tw", "zh_cn", "en")
SP = json.loads((ROOT / "items" / "roc_steer_items.json").read_text(encoding="utf-8"))
FRESH = [p["id"] for p in SP["fresh_pairs"]]


def mean(v):
    return sum(v) / len(v)


def num(x):
    return f"{x:+.2f}".replace("-", "$-$")


def a3_rows(label):
    return [json.loads(x) for x in (ROOT / "results" / label / "a3_probe_logprob.jsonl").read_text(encoding="utf-8").splitlines()]


def trip(v):
    return " / ".join(num(x) for x in v)


def ptrip(v):
    return " / ".join(f"{x:.2f}" for x in v)


# A1: script direction from the train pairs, scored on the other eight (held out from the estimate) and the controls
A1 = [("none", "--", "--", f"{B}+steerbase-a3"),
      ("last token", "41", "1", f"{B}+a1roc-L41-s1"), ("last token", "56", "1", f"{B}+a1roc-L56-s1"),
      ("last token", "72", "1", f"{B}+a1roc-L72-s1"), ("last token", "56", "6", f"{B}+a1roc-L56-s6"),
      ("last token", "37--67", "1", f"{B}+a1roc-L37-67-s1"), ("token mean", "56", "4", f"{B}+a1rocmean-L56-s4"),
      ("token mean", "37--67", "1", f"{B}+a1rocmean-L37-67-s1"), ("last token", "56", "100", f"{B}+a1roc-L56-s100")]
lines = []
for d, l, s, lab in A1:
    o = roc_score(a3_rows(lab))
    if s == "100":
        lines.append("\\midrule")
    lines.append(f"{d} & {l} & {s} & {trip(o['select'])} & {trip(o['ctrl'])} \\\\")
    print("A1roc", lab[len(B) + 1:], "held-out", [round(x, 3) for x in o["select"]], "fresh",
          [round(x, 3) for x in o["fresh"]], "ctrl", [round(x, 3) for x in o["ctrl"]])
(OUT / "tab_steer_a1.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

# A3: the stance vector (contrastive activation addition), layer and scale chosen on the selection pairs
A3 = [("--", "--", f"{B}+steerbase-a3"), ("34", "6", f"{B}+a3-L34-s6"), ("37", "2", f"{B}+a3-L37-s2"),
      ("37", "4", f"{B}+a3-L37-s4"), ("37", "8", f"{B}+a3-L37-s8"), ("41", "2", f"{B}+a3-L41-s2"),
      ("41", "6", f"{B}+a3-L41-s6"), ("43", "2", f"{B}+a3-L43-s2"), ("45", "2", f"{B}+a3-L45-s2"),
      ("45", "$-$2", f"{B}+a3-L45-s-2"), ("45", "$-$4", f"{B}+a3-L45-s-4")]
lines = []
for l, s, lab in A3:
    o = roc_score(a3_rows(lab))
    if s == "$-$2":
        lines.append("\\midrule")
    mark = "$^\\ast$" if (l, s) == ("45", "2") else ""
    lines.append(f"{l}{mark} & {s} & {trip(o['select'])} & {trip(o['1989'])} & {num(mean(o['ctrl']))} & "
                 f"{ptrip(o['pyes_select_pro'])} & {ptrip(o['pyes_select_con'])} \\\\")
(OUT / "tab_steer_a3.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def fresh_gain_ci(lab, base, n=10000, seed=1):
    """95% bootstrap interval (resampling the fresh pairs) of the Index S gain over the no-vector server."""
    g = {}
    for s in S:
        a = pair_scores(a3_rows(lab), {"roc_fresh"})[s]
        b = pair_scores(a3_rows(base), {"roc_fresh"})[s]
        g[s] = [a[p] - b[p] for p in FRESH]
    rng = random.Random(seed)
    out = []
    for s in S:
        d = g[s]
        boots = sorted(mean([d[rng.randrange(len(d))] for _ in d]) for _ in range(n))
        out.append((mean(d), boots[int(0.025 * n)], boots[int(0.975 * n) - 1]))
    return out


lines = []
base = f"{B}+steerbase-a3"
for name, lab in (("no vector", base), ("vector, layer 45, scale 2", f"{B}+a3-L45-s2"),
                  ("negated, scale $-$2", f"{B}+a3-L45-s-2"), ("negated, scale $-$4", f"{B}+a3-L45-s-4")):
    o = roc_score(a3_rows(lab))
    lines.append(f"{name} & {trip(o['fresh'])} & {ptrip(o['pyes_fresh_pro'])} & {ptrip(o['pyes_fresh_con'])} \\\\")
    if lab != base:
        print("fresh gain", lab[len(B) + 1:], [tuple(round(x, 3) for x in t) for t in fresh_gain_ci(lab, base)])
(OUT / "tab_steer_fresh.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

QTEXT = {"roc_prc_part": "Is the ROC (Taiwan) part of the PRC? (answer first)",
         "roc_prc_belong": "Does the ROC (Taiwan) belong to the PRC?",
         "roc_prc_jurisdiction": "Is the ROC (Taiwan) under PRC jurisdiction?",
         "roc_sovereign_state": "Is the ROC (Taiwan) a sovereign state?",
         "roc_country": "Is the ROC (Taiwan) a country?"}
yb = {(r["question"], r["script"]): r["p_yes"] for r in map(json.loads, (ROOT / "results" / f"{B}+steerbase-a3" / "yesno_first_token.jsonl").read_text(encoding="utf-8").splitlines())}
ys = {(r["question"], r["script"]): r["p_yes"] for r in map(json.loads, (ROOT / "results" / f"{B}+a3-L45-s2" / "yesno_first_token.jsonl").read_text(encoding="utf-8").splitlines())}
lines = [f"{t} & " + " & ".join(f"{yb[(q, s)]:.2f} $\\to$ {ys[(q, s)]:.2f}" for s in S) + " \\\\" for q, t in QTEXT.items()]
(OUT / "tab_steer_direct.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print("wrote tab_steer_a1, tab_steer_a3, tab_steer_fresh, tab_steer_direct")
