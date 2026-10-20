"""Figures for the paper -> paper/figures/*.pdf (and .png).

fig_index_s: Index S on the 16 sovereignty pairs, by model and script, with 95% bootstrap intervals.
fig_pairs:   per-pair score by script for the four models (sovereignty + 1989 pairs).
fig_acq:     mean P(yes) on Taiwan-side vs PRC-side statements, original -> abliterated.
"""
import json
import random
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
SCRIPTS = ("zh_tw", "zh_cn", "en")
SCRIPT_NAME = {"zh_tw": "Traditional Chinese", "zh_cn": "Simplified Chinese", "en": "English"}
COLORS = {"zh_tw": "#2f6db3", "zh_cn": "#c8553d", "en": "#6b8f4e"}
SOV = {"sovereignty", "roc_sovereignty", "prc_jurisdiction"}
MODELS = [  # (label, mode, display)
    ("bolt74b-24gb-original", "logprob", "Bolt original"),
    ("bolt74b-24gb-abliterated-boldingbuilds", "logprob", "Bolt abliterated"),
    ("qwen38fn-iq2xs-original", "sample", "Qwen original"),
    ("qwen38fn-iq2xs-abliterated-sc117", "sample", "Qwen abliterated"),
]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def rows(label, mode):
    return [json.loads(x) for x in (ROOT / "results" / label / f"probe_{mode}.jsonl").read_text(encoding="utf-8").splitlines()]


def pair_scores(rs, topics):
    acc = defaultdict(lambda: defaultdict(list))
    for r in rs:
        if r.get("p_yes") is not None and r["topic"] in topics:
            acc[(r["script"], r["pair"])][r["side"]].append(r["p_yes"])
    out = defaultdict(dict)
    for (s, p), sides in acc.items():
        if sides.get("pro") and sides.get("con"):
            out[s][p] = sum(sides["pro"]) / len(sides["pro"]) - sum(sides["con"]) / len(sides["con"])
    return out


def boot(v, reps=2000, seed=7):
    rnd = random.Random(seed)
    m = sorted(sum(rnd.choice(v) for _ in v) / len(v) for _ in range(reps))
    return m[int(0.025 * reps)], m[int(0.975 * reps) - 1]


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


# ---- Figure 1: Index S (the system-prompt run, Section 4.7, is the hatched fifth group)
SYS = ("qwen38fn-iq2xs-abliterated-sc117+sysprompt", "sample", "Qwen abliterated\n+ system prompt")
groups = MODELS + ([SYS] if (ROOT / "results" / SYS[0] / "probe_sample.jsonl").exists() else [])
fig, ax = plt.subplots(figsize=(7.2, 2.9))
w = 0.26
for i, (label, mode, disp) in enumerate(groups):
    sc = pair_scores(rows(label, mode), SOV)
    for j, s in enumerate(SCRIPTS):
        v = list(sc[s].values())
        m = sum(v) / len(v)
        lo, hi = boot(v)
        x = i + (j - 1) * w
        ax.bar(x, m, w * 0.92, color=COLORS[s], label=SCRIPT_NAME[s] if i == 0 else None,
               hatch="///" if label == SYS[0] else None, edgecolor="white" if label == SYS[0] else None, linewidth=0)
        ax.errorbar(x, m, yerr=[[m - lo], [hi - m]], fmt="none", ecolor="black", elinewidth=0.8, capsize=2)
ax.axhline(0, color="black", linewidth=0.6)
if len(groups) > len(MODELS):
    ax.axvline(len(MODELS) - 0.5, color="#999999", linewidth=0.6, linestyle=":")
ax.set_xticks(range(len(groups)))
ax.set_xticklabels([f"{d}\n({m})" if "\n" not in d else d for _, m, d in groups], fontsize=8)
ax.set_ylabel("Index S (16 sovereignty pairs)")
ax.set_ylim(-0.7, 1.05)
ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.16))
save(fig, "fig_index_s")

# ---- Figure 2: per-pair scores, by script, four models
pairs_order = [p for p in dict.fromkeys(json.loads(x)["pair"] for x in
               (ROOT / "items" / "probe_items.jsonl").read_text(encoding="utf-8").splitlines())
               if not p.startswith("C-")]
fig, axes = plt.subplots(1, 4, figsize=(9.6, 4.6), sharey=True)
for ax, (label, mode, disp) in zip(axes, MODELS):
    sc = pair_scores(rows(label, mode), SOV | {"tiananmen"})
    for s in SCRIPTS:
        ys = [k for k in range(len(pairs_order)) if pairs_order[k] in sc[s]]
        ax.scatter([sc[s][pairs_order[k]] for k in ys], ys, s=14, color=COLORS[s], label=SCRIPT_NAME[s], zorder=3)
    ax.axvline(0, color="black", linewidth=0.6)
    ax.set_xlim(-1.05, 1.05)
    ax.set_title(disp, fontsize=9)
    ax.grid(axis="y", color="#e5e5e5", linewidth=0.5)
axes[0].set_yticks(range(len(pairs_order)))
axes[0].set_yticklabels(pairs_order, fontsize=7)
axes[0].invert_yaxis()
fig.supxlabel("P(Taiwan-side statement true) − P(PRC-side statement true)", fontsize=9)
axes[0].legend(frameon=False, fontsize=7, loc="lower left", bbox_to_anchor=(0, 1.04), ncol=3)
save(fig, "fig_pairs")

# ---- Figure 3: acquiescence
fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.6), sharey=True)
fams = [("Bolt (logprob)", "bolt74b-24gb-original", "bolt74b-24gb-abliterated-boldingbuilds", "logprob"),
        ("Qwen (20 samples)", "qwen38fn-iq2xs-original", "qwen38fn-iq2xs-abliterated-sc117", "sample")]
for ax, (name, lo_, la_, mode) in zip(axes, fams):
    for side, marker in (("pro", "o"), ("con", "s")):
        for s in SCRIPTS:
            vals = []
            for lab in (lo_, la_):
                ps = [r["p_yes"] for r in rows(lab, mode) if r.get("p_yes") is not None and r["side"] == side
                      and r["script"] == s and r["topic"] in SOV | {"tiananmen"}]
                vals.append(sum(ps) / len(ps))
            ax.plot([0, 1], vals, marker=marker, color=COLORS[s], linewidth=1, markersize=4,
                    linestyle="-" if side == "pro" else "--")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["original", "abliterated"])
    ax.set_xlim(-0.3, 1.3)
    ax.set_title(name, fontsize=9)
axes[0].set_ylabel("mean P(yes)")
handles = [plt.Line2D([], [], color="gray", linestyle="-", marker="o", markersize=4, label="Taiwan-side statements"),
           plt.Line2D([], [], color="gray", linestyle="--", marker="s", markersize=4, label="PRC-side statements")] + \
          [plt.Line2D([], [], color=COLORS[s], label=SCRIPT_NAME[s]) for s in SCRIPTS]
fig.legend(handles=handles, frameon=False, fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.12))
save(fig, "fig_acq")
