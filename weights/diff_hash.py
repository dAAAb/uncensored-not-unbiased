"""Compare two tensor_hash.py outputs: which metadata fields and tensors differ, grouped by kind and layer.

usage: python weights/diff_hash.py ORIGINAL.json MODIFIED.json
"""
import json
import re
import sys
from collections import Counter

s = json.load(open(sys.argv[1], encoding="utf-8"))
a = json.load(open(sys.argv[2], encoding="utf-8"))
meta_diff = sorted(k for k in set(s["meta"]) | set(a["meta"])
                   if s["meta"].get(k, {}).get("sha256") != a["meta"].get(k, {}).get("sha256"))
print("metadata fields:", len(s["meta"]), "/", len(a["meta"]), "differing:", meta_diff)
print("tensors:", len(s["tensors"]), "/", len(a["tensors"]),
      "only in first:", len(set(s["tensors"]) - set(a["tensors"])), "only in second:", len(set(a["tensors"]) - set(s["tensors"])))
retyped = [n for n in s["tensors"] if n in a["tensors"] and
           (s["tensors"][n]["type"], s["tensors"][n]["shape"]) != (a["tensors"][n]["type"], a["tensors"][n]["shape"])]
print("type/shape changes:", len(retyped), retyped[:5])
changed = [n for n in s["tensors"] if n in a["tensors"] and s["tensors"][n]["sha256"] != a["tensors"][n]["sha256"]]
print("changed tensors:", len(changed))
print("by kind:", dict(Counter(re.sub(r"^blk\.\d+\.", "", n) for n in changed)))
blocks = sorted({int(m.group(1)) for n in changed if (m := re.match(r"blk\.(\d+)\.", n))})
print("blocks:", (blocks[0], blocks[-1], len(blocks)) if blocks else None)
print("chat template identical:", s["meta"].get("tokenizer.chat_template", {}).get("sha256") ==
      a["meta"].get("tokenizer.chat_template", {}).get("sha256"))
