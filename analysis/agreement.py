"""How well the 20-sample estimate agrees with the logprob value, per model that has both (validates using sample
mode for engines without logprobs). Appends a section to analysis/tables.md.

usage: python analysis/agreement.py
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(p):
    return {(r["pair"], r["side"], r["script"], r["phrasing"]): r["p_yes"]
            for r in map(json.loads, p.read_text(encoding="utf-8").splitlines()) if r.get("p_yes") is not None}


lines = ["## Agreement: 20-sample estimate vs logprob", "",
         "| model | rows | Pearson r | mean abs. diff | same side of 0.5 |", "|---|---|---|---|---|"]
for d in sorted((ROOT / "results").iterdir()):
    fl, fs = d / "probe_logprob.jsonl", d / "probe_sample.jsonl"
    if not (fl.exists() and fs.exists()):
        continue
    a, b = load(fl), load(fs)
    keys = [k for k in a if k in b]
    x, y = [a[k] for k in keys], [b[k] for k in keys]
    n = len(keys)
    mx, my = sum(x) / n, sum(y) / n
    cov = sum((i - mx) * (j - my) for i, j in zip(x, y))
    r = cov / math.sqrt(sum((i - mx) ** 2 for i in x) * sum((j - my) ** 2 for j in y))
    mad = sum(abs(i - j) for i, j in zip(x, y)) / n
    same = sum((i > 0.5) == (j > 0.5) for i, j in zip(x, y)) / n
    lines.append(f"| {d.name} | {n} | {r:.3f} | {mad:.3f} | {same:.1%} |")
lines.append("")
out = ROOT / "analysis" / "tables.md"
text = out.read_text(encoding="utf-8") if out.exists() else ""
out.write_text(text + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print("\n".join(lines))
