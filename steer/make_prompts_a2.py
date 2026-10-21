"""Prompts for A2 (contrastive activation addition, Panickssery et al. 2023): each probe prompt twice, once followed by
the answer token that takes the ROC side and once by the token that takes the PRC side.

For a ROC-side statement the ROC-side answer is yes; for a PRC-side statement it is no. Because both statement
sides are included, "yes" and "no" appear equally often on each side of the contrast, so a plain yes-bias cancels.

usage: python steer/make_prompts_a2.py -> steer/work/prompts_a2.txt, steer/work/index_a2.jsonl (train + test pairs)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "run"))
sys.path.insert(0, str(ROOT / "steer"))
from directions import TEST, TRAIN  # noqa: E402
from probe import prompt_for  # noqa: E402

YES = {"zh_tw": "是", "zh_cn": "是", "en": "Yes"}
NO = {"zh_tw": "否", "zh_cn": "否", "en": "No"}
out = ROOT / "steer" / "work"
items = [json.loads(x) for x in (ROOT / "items" / "probe_items.jsonl").read_text(encoding="utf-8").splitlines()]
lines, index = [], []
for it in items:
    if it["pair"] not in TRAIN + TEST:
        continue
    for script in ("zh_tw", "zh_cn", "en"):
        for k in range(3):
            text = prompt_for(it, script, k).replace("\\", "\\\\").replace("\n", "\\n")
            tw_ans = YES[script] if it["side"] == "pro" else NO[script]
            prc_ans = NO[script] if it["side"] == "pro" else YES[script]
            for answer, stance in ((tw_ans, "taiwan"), (prc_ans, "prc")):
                lines.append(f"{text}\t{answer}")
                index.append({"pair": it["pair"], "side": it["side"], "script": script, "phrasing": k,
                              "answer": answer, "stance": stance, "split": "train" if it["pair"] in TRAIN else "test"})
(out / "prompts_a2.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
(out / "index_a2.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in index) + "\n",
                                    encoding="utf-8", newline="\n")
print(len(lines), "prompts")
