"""Script-invariance direction (A1) from llama-dump-hidden output, and control-vector GGUFs for llama.cpp.

d_TW[l]  = mean over train Taiwan pairs (both sides, 3 phrasings) of h_l(Traditional prompt) - h_l(Simplified prompt)
d_CTL[l] = the same over the three control pairs (Japan, New Zealand, South Korea)
d[l]     = d_TW[l] with its component along d_CTL[l] removed (keep the Taiwan-specific part of the script shift)
h_l is the residual stream after layer l at the last prompt token (the position that produces the answer).

The 16 sovereignty pairs are split in two; only the train half is used here. Held-out separation is reported per
layer to choose where to apply the vector. Writes steer/work/cvec_<name>.gguf with direction.<l> = d[l] (unnormalised,
so scale 1.0 adds the full average Traditional-minus-Simplified shift at the chosen layer).

usage: python steer/directions.py steer/work/hidden_<model>.bin --name <name>
"""
import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
W = ROOT / "steer" / "work"
TRAIN = ["S1-001", "S1-003", "S1-005", "S1-007", "S1-009", "ST-001", "ST-003", "X-ROC"]
TEST = ["S1-002", "S1-004", "S1-006", "S1-008", "S1-010", "ST-002", "ST-006", "X-PRC"]
CTRL = ["C-JP", "C-NZ", "C-KR"]


def load(path):
    with open(path, "rb") as f:
        n, L, E = (int(x) for x in np.frombuffer(f.read(12), dtype=np.int32))
        data = np.fromfile(f, dtype=np.float32)
    return data.reshape(n, 2, L, E)


def script_pairs(idx, pairs):
    tw = {(r["pair"], r["side"], r["phrasing"]): i for i, r in enumerate(idx) if r["script"] == "zh_tw" and r["pair"] in pairs}
    cn = {(r["pair"], r["side"], r["phrasing"]): i for i, r in enumerate(idx) if r["script"] == "zh_cn" and r["pair"] in pairs}
    keys = sorted(tw.keys() & cn.keys())
    return [tw[k] for k in keys], [cn[k] for k in keys]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hidden")
    ap.add_argument("--name", required=True)
    ap.add_argument("--pos", type=int, default=0, help="0 = last prompt token, 1 = mean over prompt tokens")
    args = ap.parse_args()

    idx = [json.loads(x) for x in (W / "index.jsonl").read_text(encoding="utf-8").splitlines()]
    H = load(args.hidden)[:, args.pos]  # [n, L, E]
    n, L, E = H.shape
    assert n == len(idx), (n, len(idx))

    tw_i, cn_i = script_pairs(idx, TRAIN)
    d_tw = (H[tw_i] - H[cn_i]).mean(0)
    ct_i, cc_i = script_pairs(idx, CTRL)
    d_ctl = (H[ct_i] - H[cc_i]).mean(0)
    denom = np.maximum((d_ctl * d_ctl).sum(-1, keepdims=True), 1e-12)
    d = d_tw - (d_tw * d_ctl).sum(-1, keepdims=True) / denom * d_ctl

    # held-out check: projection of test-pair activations on the unit direction, Traditional vs Simplified
    te_tw, te_cn = script_pairs(idx, TEST)
    rows = []
    for l in range(L):
        nrm = np.linalg.norm(d[l])
        if nrm == 0:
            rows.append(None)
            continue
        u = d[l] / nrm
        a, b = H[te_tw, l] @ u, H[te_cn, l] @ u
        pooled = np.sqrt((a.var() + b.var()) / 2) + 1e-9
        ca, cb = H[ct_i, l] @ u, H[cc_i, l] @ u
        rows.append({
            "layer": l,
            "resid_norm": float(np.linalg.norm(H[:, l], axis=-1).mean()),
            "d_tw_norm": float(np.linalg.norm(d_tw[l])),
            "d_norm": float(nrm),
            "cos_tw_ctl": float((d_tw[l] @ d_ctl[l]) / (np.linalg.norm(d_tw[l]) * np.linalg.norm(d_ctl[l]) + 1e-12)),
            "heldout_effect": float((a.mean() - b.mean()) / pooled),
            "heldout_shift_ratio": float((a.mean() - b.mean()) / nrm),
            "control_effect": float((ca.mean() - cb.mean()) / (np.sqrt((ca.var() + cb.var()) / 2) + 1e-9)),
        })
    good = [r for r in rows if r]
    (W / f"layers_{args.name}.json").write_text(json.dumps(good, indent=1), encoding="utf-8")
    print("layer resid |d_tw| |d| cos(tw,ctl) heldout_d ratio ctl_d")
    for r in good:
        if r["layer"] % 4 == 0 or r["layer"] == L - 2:
            print(f"{r['layer']:3d} {r['resid_norm']:8.1f} {r['d_tw_norm']:7.2f} {r['d_norm']:7.2f} {r['cos_tw_ctl']:+.2f} "
                  f"{r['heldout_effect']:+6.2f} {r['heldout_shift_ratio']:+.2f} {r['control_effect']:+6.2f}")

    import gguf  # Strata's vendored gguf-py (knows all quant types); only used for writing F32 here
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
