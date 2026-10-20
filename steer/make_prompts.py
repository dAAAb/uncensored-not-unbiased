"""Write the probe prompts (same text as run/probe.py) one per line for llama-dump-hidden, plus an index.

usage: python steer/make_prompts.py  -> steer/work/prompts.txt, steer/work/index.jsonl
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "run"))
from probe import prompt_for  # noqa: E402

out = ROOT / "steer" / "work"
out.mkdir(parents=True, exist_ok=True)
items = [json.loads(x) for x in (ROOT / "items" / "probe_items.jsonl").read_text(encoding="utf-8").splitlines()]
lines, index = [], []
for it in items:
    for script in ("zh_tw", "zh_cn", "en"):
        for k in range(3):
            text = prompt_for(it, script, k)
            lines.append(text.replace("\\", "\\\\").replace("\n", "\\n"))
            index.append({"pair": it["pair"], "side": it["side"], "topic": it["topic"], "script": script, "phrasing": k})
(out / "prompts.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
(out / "index.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in index) + "\n",
                                 encoding="utf-8", newline="\n")
print(len(lines), "prompts")
