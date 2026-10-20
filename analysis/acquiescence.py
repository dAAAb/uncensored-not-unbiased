"""Does abliteration make a model say "yes" more often, whatever the statement? Mean P(yes) by side (pro / con) and
script, original vs abliterated. A rise on both sides is acquiescence (agreeing more), not a change of stance; Index S
(pro - con) cancels it, single yes/no questions do not. Appends a section to analysis/tables.md."""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
pairs = json.loads((ROOT / "configs" / "pairs.json").read_text(encoding="utf-8"))
TOPICS = {"sovereignty", "roc_sovereignty", "prc_jurisdiction", "tiananmen"}


def means(label, mode):
    f = ROOT / "results" / label / f"probe_{mode}.jsonl"
    if not f.exists():
        return None
    acc = defaultdict(list)
    for r in map(json.loads, f.read_text(encoding="utf-8").splitlines()):
        if r.get("p_yes") is not None and r["topic"] in TOPICS:
            acc[(r["script"], r["side"])].append(r["p_yes"])
    return {k: sum(v) / len(v) for k, v in acc.items()}


lines = ["## Acquiescence: mean P(yes) on Taiwan and 1989 statements, original → abliterated", "",
         "| family | mode | script | pro statements | con (PRC) statements |", "|---|---|---|---|---|"]
for fam in pairs:
    for mode in ("logprob", "sample"):
        o, a = means(fam["original"], mode), means(fam["abliterated"], mode)
        if not (o and a):
            continue
        for s in ("zh_tw", "zh_cn", "en"):
            cells = [f"{o[(s, side)]:.2f} → {a[(s, side)]:.2f} ({a[(s, side)] - o[(s, side)]:+.2f})" for side in ("pro", "con")]
            lines.append(f"| {fam['family']} | {mode} | {s} | " + " | ".join(cells) + " |")

yn = ["", "## Direct yes/no questions (run/yesno_first_token.py): P(answer starts with yes)", "",
      "| question | script | Bolt original | Bolt abliterated |", "|---|---|---|---|"]
fo = ROOT / "results" / "bolt74b-24gb-original" / "yesno_first_token.jsonl"
fa = ROOT / "results" / "bolt74b-24gb-abliterated-boldingbuilds" / "yesno_first_token.jsonl"
if fo.exists() and fa.exists():
    A = {(r["question"], r["script"]): r["p_yes"] for r in map(json.loads, fa.read_text(encoding="utf-8").splitlines())}
    for r in map(json.loads, fo.read_text(encoding="utf-8").splitlines()):
        a = A.get((r["question"], r["script"]))
        yn.append(f"| {r['question']} | {r['script']} | {r['p_yes']:.2f} | {a:.2f} ({a - r['p_yes']:+.2f}) |")
lines += yn + [""]
out = ROOT / "analysis" / "tables.md"
out.write_text(out.read_text(encoding="utf-8") + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print("\n".join(lines))
