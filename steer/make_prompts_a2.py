"""Prompts for contrastive activation addition (Panickssery et al. 2023): each probe prompt twice, once followed by
the answer token that takes the ROC side and once by the token that takes the PRC side.

For a ROC-side statement the ROC-side answer is yes; for a PRC-side statement it is no. Because both statement
sides are included, "yes" and "no" appear equally often on each side of the contrast, so a plain yes-bias cancels.

usage: python steer/make_prompts_a2.py
         A2, inherited wording: probe_items.jsonl, TRAIN/TEST of directions.py
           -> steer/work/prompts_a2.txt, steer/work/index_a2.jsonl
       python steer/make_prompts_a2.py --items roc_steer_probe_items.jsonl --splits roc_steer_items.json --tag a3
         A3, ROC wording (Section 5.3): train/select lists of items/roc_steer_items.json
           -> steer/work/prompts_a3.txt, steer/work/index_a3.jsonl
"""
import argparse
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

ap = argparse.ArgumentParser()
ap.add_argument("--items", default="probe_items.jsonl", help="item file in items/")
ap.add_argument("--splits", default="", help="json in items/ with 'train' and 'select' pair lists")
ap.add_argument("--tag", default="a2")
args = ap.parse_args()
train, test = TRAIN, TEST
if args.splits:
    sp = json.loads((ROOT / "items" / args.splits).read_text(encoding="utf-8"))
    train, test = sp["train"], sp["select"]

out = ROOT / "steer" / "work"
items = [json.loads(x) for x in (ROOT / "items" / args.items).read_text(encoding="utf-8").splitlines()]
lines, index = [], []
for it in items:
    if it["pair"] not in train + test:
        continue
    for script in ("zh_tw", "zh_cn", "en"):
        for k in range(3):
            text = prompt_for(it, script, k).replace("\\", "\\\\").replace("\n", "\\n")
            tw_ans = YES[script] if it["side"] == "pro" else NO[script]
            prc_ans = NO[script] if it["side"] == "pro" else YES[script]
            for answer, stance in ((tw_ans, "taiwan"), (prc_ans, "prc")):
                lines.append(f"{text}\t{answer}")
                index.append({"pair": it["pair"], "side": it["side"], "script": script, "phrasing": k,
                              "answer": answer, "stance": stance, "split": "train" if it["pair"] in train else "test"})
(out / f"prompts_{args.tag}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
(out / f"index_{args.tag}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in index) + "\n",
                                           encoding="utf-8", newline="\n")
print(len(lines), "prompts")
