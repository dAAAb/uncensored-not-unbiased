"""A2 direction: mean over train items of h_l(prompt + Taiwan-side answer) - h_l(prompt + PRC-side answer), at the
answer token. Reports held-out separation on the test pairs and writes a control-vector GGUF.

usage: python steer/directions_a2.py steer/work/hidden_a2_<model>.bin --name <name>
"""
import argparse
import json
from pathlib import Path

import numpy as np

from directions import load

ROOT = Path(__file__).resolve().parents[1]
W = ROOT / "steer" / "work"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hidden")
    ap.add_argument("--name", required=True)
    args = ap.parse_args()
    idx = [json.loads(x) for x in (W / "index_a2.jsonl").read_text(encoding="utf-8").splitlines()]
    H = load(args.hidden)[:, 0]  # last token = the answer token
    n, L, E = H.shape
    assert n == len(idx)
    key = lambda r: (r["pair"], r["side"], r["script"], r["phrasing"])  # noqa: E731
    tw = {key(r): i for i, r in enumerate(idx) if r["stance"] == "taiwan"}
    prc = {key(r): i for i, r in enumerate(idx) if r["stance"] == "prc"}
    tr = [k for k in tw if idx[tw[k]]["split"] == "train"]
    te = [k for k in tw if idx[tw[k]]["split"] == "test"]
    d = (H[[tw[k] for k in tr]] - H[[prc[k] for k in tr]]).mean(0)  # [L, E]

    rows = []
    for l in range(L):
        nrm = float(np.linalg.norm(d[l]))
        if nrm == 0:
            continue
        u = d[l] / nrm
        a = H[[tw[k] for k in te], l] @ u
        b = H[[prc[k] for k in te], l] @ u
        # also: does the direction agree across scripts? cosine of per-script train means
        per = {}
        for s in ("zh_tw", "zh_cn", "en"):
            ks = [k for k in tr if k[2] == s]
            per[s] = (H[[tw[k] for k in ks], l] - H[[prc[k] for k in ks], l]).mean(0)
        cos = lambda x, y: float(x @ y / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-12))  # noqa: E731
        rows.append({"layer": l, "resid_norm": float(np.linalg.norm(H[:, l], axis=-1).mean()), "d_norm": nrm,
                     "heldout_effect": float((a.mean() - b.mean()) / (np.sqrt((a.var() + b.var()) / 2) + 1e-9)),
                     "cos_tw_cn": cos(per["zh_tw"], per["zh_cn"]), "cos_tw_en": cos(per["zh_tw"], per["en"])})
    (W / f"layers_{args.name}.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print("layer resid |d| heldout_d cos(tw,cn) cos(tw,en)")
    for r in rows:
        print(f"{r['layer']:3d} {r['resid_norm']:8.1f} {r['d_norm']:7.2f} {r['heldout_effect']:+6.2f} "
              f"{r['cos_tw_cn']:+.2f} {r['cos_tw_en']:+.2f}")

    import gguf
    out = W / f"cvec_{args.name}.gguf"
    w = gguf.GGUFWriter(str(out), arch="controlvector")
    w.add_string("controlvector.model_hint", "nemotron_h_moe")
    w.add_int32("controlvector.layer_count", L - 1)
    for l in range(1, L):
        w.add_tensor(f"direction.{l}", d[l].astype(np.float32))
    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_tensors_to_file()
    w.close()
    print("wrote", out)


if __name__ == "__main__":
    main()
