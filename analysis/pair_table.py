"""Per-pair scores (pro - con, mean over phrasings) for every model, mode and script -> analysis/pairs.md.
Shows which statements carry the script gap and which move under abliteration."""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ("zh_tw", "zh_cn", "en")
items = {}
for line in (ROOT / "items" / "probe_items.jsonl").read_text(encoding="utf-8").splitlines():
    it = json.loads(line)
    items.setdefault(it["pair"], {})[it["side"]] = it["en"]

cols, data = [], defaultdict(dict)
for d in sorted((ROOT / "results").iterdir()):
    for f in sorted(d.glob("probe_*.jsonl")):
        col = f"{d.name} ({f.stem.split('_')[1]})"
        cols.append(col)
        acc = defaultdict(lambda: defaultdict(list))
        for r in map(json.loads, f.read_text(encoding="utf-8").splitlines()):
            if r.get("p_yes") is not None:
                acc[(r["pair"], r["script"])][r["side"]].append(r["p_yes"])
        for (pair, script), sides in acc.items():
            if sides.get("pro") and sides.get("con"):
                data[(pair, script)][col] = (sum(sides["pro"]) / len(sides["pro"]) - sum(sides["con"]) / len(sides["con"]))

lines = ["# Per-pair scores (P(pro true) − P(con true), mean of 3 phrasings)", "",
         "| pair | script | " + " | ".join(cols) + " |", "|---|---|" + "---|" * len(cols)]
for pair in items:
    for s in SCRIPTS:
        row = data.get((pair, s), {})
        lines.append(f"| {pair} | {s} | " + " | ".join(f"{row[c]:+.2f}" if c in row else "–" for c in cols) + " |")
lines += ["", "## Statements", ""] + [f"- **{p}** pro: {v.get('pro')} / con: {v.get('con')}" for p, v in items.items()]
(ROOT / "analysis" / "pairs.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print("\n".join(lines[:4 + 3 * len(items)]))
