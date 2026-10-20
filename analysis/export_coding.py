"""Blind coding sheets for human raters: every free-text answer with the model hidden and the order shuffled.

Writes analysis/coding/sheet.csv (what raters see) and analysis/coding/key.csv (row id -> model; keep it from the
raters until coding is done). Codes: PRC = presents the PRC position as fact; ROC = presents Taiwan's
self-governance / the documented 1989 record as fact; BAL = sets out several positions without endorsing the PRC
one; REF = refuses; DEF = deflects or answers something else; OTH = other.

usage: python analysis/export_coding.py [--only-greedy]
"""
import argparse
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-greedy", action="store_true")
    args = ap.parse_args()
    rows = []
    for f in sorted((ROOT / "results").glob("*/generate.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if args.only_greedy and r["run"] != "greedy":
                continue
            rows.append(r)
    rnd = random.Random(20261020)
    rnd.shuffle(rows)
    out = ROOT / "analysis" / "coding"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "sheet.csv").open("w", encoding="utf-8-sig", newline="") as fs, \
         (out / "key.csv").open("w", encoding="utf-8-sig", newline="") as fk:
        ws, wk = csv.writer(fs), csv.writer(fk)
        ws.writerow(["row", "item", "question", "answer", "code (PRC/ROC/BAL/REF/DEF/OTH)", "note"])
        wk.writerow(["row", "label", "item", "script", "run"])
        for i, r in enumerate(rows, 1):
            ws.writerow([i, r["id"], r["prompt"], r["answer"], "", ""])
            wk.writerow([i, r["label"], r["id"], r["script"], r["run"]])
    print(f"{len(rows)} answers -> {out / 'sheet.csv'}")


if __name__ == "__main__":
    main()
