"""Hash every metadata field and every tensor of a GGUF file, so two files can be compared without both on disk.

usage: tensor_hash.py FILE.gguf OUT.json
"""
import hashlib
import json
import sys

from gguf import GGUFReader

path, out = sys.argv[1], sys.argv[2]
r = GGUFReader(path, "r")

meta = {}
for name, field in r.fields.items():
    if name.startswith("GGUF."):
        continue
    h = hashlib.sha256()
    for i in field.data:
        h.update(bytes(field.parts[i]))
    value = None
    try:
        v = field.contents()
        value = v if isinstance(v, (int, float, bool)) or (isinstance(v, str) and len(v) < 200) else None
    except Exception:  # noqa: BLE001
        pass
    meta[name] = {"sha256": h.hexdigest(), "value": value}

tensors = {}
for t in r.tensors:
    tensors[t.name] = {
        "type": t.tensor_type.name,
        "shape": [int(x) for x in t.shape],
        "sha256": hashlib.sha256(memoryview(t.data).cast("B")).hexdigest(),
    }

json.dump({"file": path, "meta": meta, "tensors": tensors}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"{len(meta)} metadata fields, {len(tensors)} tensors -> {out}")
