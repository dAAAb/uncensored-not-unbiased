"""Build the two item files used by every run.

probe_items.jsonl  one line per (pair, side): a statement asked as a yes/no question (Section 3.2 of the paper)
open_items.jsonl   one line per open question, answered in free text
roc_*.jsonl        the same three kinds of item with the Republic of China (Taiwan) as subject (roc_items.json)

Every item is given in Traditional Chinese (zh_tw), Simplified Chinese (zh_cn) and English (en). zh_cn is produced
from zh_tw with OpenCC t2s, character by character, so the two scripts differ only in the writing system; where a
source already ships zh_cn (Hsiao 2026) its text is used and checked against the conversion.

usage: python items/build_items.py
"""
import hashlib
import json
from pathlib import Path

from opencc import OpenCC

HERE = Path(__file__).resolve().parent
SRC = HERE / "sources"
t2s = OpenCC("t2s")


def zh_cn(text):
    return t2s.convert(text)


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"{path.name}: {len(rows)} rows, sha256 {digest}")


probe = []
# Hsiao (2026), 14 pairs rewritten from the Taiwan Sovereignty Benchmark (CC BY 4.0 data, MIT code)
pirrer = json.loads((SRC / "pirrer_statements.json").read_text(encoding="utf-8"))
for it in pirrer["items"]:
    converted = zh_cn(it["zh_tw"])
    if converted != it["zh_cn"]:
        print(f"note: {it['id']} {it['side']}: source zh_cn differs from OpenCC t2s; using the source text")
    probe.append({"pair": it["id"], "side": it["side"], "topic": "sovereignty", "source": "hsiao2026",
                  "zh_tw": it["zh_tw"], "zh_cn": it["zh_cn"], "en": it["en"]})

extra = json.loads((HERE / "extra_items.json").read_text(encoding="utf-8"))
for group, source in (("probe_pairs", "this_study"), ("control_pairs", "this_study_control")):
    for p in extra[group]:
        for side in ("pro", "con"):
            s = p[side]
            probe.append({"pair": p["id"], "side": side, "topic": p["topic"], "source": source,
                          "zh_tw": s["zh_tw"], "zh_cn": zh_cn(s["zh_tw"]), "en": s["en"]})

opened = []
# Ko (2026) Taiwan Sovereignty Benchmark Pro, stage 1 (sovereignty) and stage 3 (sensitive topics)
for fname, key in (("tsbpro_stage1_sovereignty.json", None), ("tsbpro_stage3_sensitive.json", None)):
    data = json.loads((SRC / fname).read_text(encoding="utf-8"))
    for v in data.values():
        if not isinstance(v, list):
            continue
        for it in v:
            zh = it.get("prompt_zh") or it.get("question_zh")
            en = it.get("prompt_en") or it.get("question_en")
            if not zh or not en:
                continue
            opened.append({"id": it["id"], "category": it.get("category", "sovereignty"), "source": "ko2026",
                           "zh_tw": zh, "zh_cn": zh_cn(zh), "en": en})
for it in extra["open_items"]:
    opened.append({"id": it["id"], "category": it["category"], "source": "this_study",
                   "zh_tw": it["zh_tw"], "zh_cn": zh_cn(it["zh_tw"]), "en": it["en"]})

write_jsonl(HERE / "probe_items.jsonl", probe)
write_jsonl(HERE / "open_items.jsonl", opened)

# ROC-subject wording: the inherited pairs restated with the Republic of China (Taiwan) as subject
roc = json.loads((HERE / "roc_items.json").read_text(encoding="utf-8"))
roc_probe = []
for p in roc["probe_pairs"]:
    for side in ("pro", "con"):
        s = p[side]
        roc_probe.append({"pair": p["id"], "side": side, "topic": p["topic"], "source": "this_study_roc",
                          "mirrors": p["mirrors"], "zh_tw": s["zh_tw"], "zh_cn": zh_cn(s["zh_tw"]), "en": s["en"]})
roc_direct = [{"question": q["id"], "mirrors": q["mirrors"], "zh_tw": q["zh_tw"], "zh_cn": zh_cn(q["zh_tw"]),
               "en": q["en"]} for q in roc["direct_questions"]]
roc_open = [{"id": it["id"], "category": it["category"], "source": "this_study_roc", "mirrors": it["mirrors"],
             "zh_tw": it["zh_tw"], "zh_cn": zh_cn(it["zh_tw"]), "en": it["en"]} for it in roc["open_items"]]
write_jsonl(HERE / "roc_probe_items.jsonl", roc_probe)
write_jsonl(HERE / "roc_direct_items.jsonl", roc_direct)
write_jsonl(HERE / "roc_open_items.jsonl", roc_open)

# wording variant of R-009 (roc_items.json "variant_pairs"), run separately
roc_variant = []
for p in roc.get("variant_pairs", []):
    for side in ("pro", "con"):
        s = p[side]
        roc_variant.append({"pair": p["id"], "side": side, "topic": p["topic"], "source": "this_study_roc_variant",
                            "mirrors": p["mirrors"], "zh_tw": s["zh_tw"], "zh_cn": zh_cn(s["zh_tw"]), "en": s["en"]})
write_jsonl(HERE / "roc_variant_probe_items.jsonl", roc_variant)

# 1992-Consensus framings (c92_items.json): each statement asked on its own; side = framing (roc / prc / dpp)
c92 = json.loads((HERE / "c92_items.json").read_text(encoding="utf-8"))
c92_probe = []
for t in c92["themes"]:
    for side in ("roc", "prc", "dpp"):
        s = t[side]
        c92_probe.append({"pair": t["id"], "side": side, "topic": t["topic"], "source": "this_study_c92",
                          "zh_tw": s["zh_tw"], "zh_cn": zh_cn(s["zh_tw"]), "en": s["en"]})
write_jsonl(HERE / "c92_probe_items.jsonl", c92_probe)
