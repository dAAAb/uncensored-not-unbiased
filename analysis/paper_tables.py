"""LaTeX tables for the paper -> paper/tables/*.tex, from the same results/ files as analyze.py.

Every number in the paper's tables comes from here; numbers quoted in the text are printed to stdout.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics  # noqa: E402
from analyze import boot_ci, load_jsonl, pair_scores  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "tables"
OUT.mkdir(parents=True, exist_ok=True)
SCRIPTS = ("zh_tw", "zh_cn", "en")
SOV = {"sovereignty", "roc_sovereignty", "prc_jurisdiction"}
TAM = {"tiananmen"}
CTL = {"control"}
MODELS = [  # label, probe mode, display name
    ("bolt74b-24gb-original", "logprob", "Bolt, original"),
    ("bolt74b-24gb-abliterated-boldingbuilds", "logprob", "Bolt, abliterated"),
    ("qwen38fn-iq2xs-original", "sample", "Qwen, original"),
    ("qwen38fn-iq2xs-abliterated-sc117", "sample", "Qwen, abliterated"),
]
SYS = ("qwen38fn-iq2xs-abliterated-sc117+sysprompt", "sample", "Qwen, abliterated + system prompt")
FAMILIES = [("Bolt", MODELS[0], MODELS[1]), ("Qwen", MODELS[2], MODELS[3])]
SCRIPT_TEX = {"zh_tw": "Trad.", "zh_cn": "Simp.", "en": "Eng."}


def probe(label, mode):
    p = ROOT / "results" / label / f"probe_{mode}.jsonl"
    return load_jsonl(p) if p.exists() else None


def num(x):
    return "--" if x is None else f"{x:+.2f}".replace("-", "$-$")


def mean(v):
    return sum(v) / len(v) if v else None


def index_s(rows, topics):
    sc = pair_scores(rows, topics)
    out = {}
    for s in SCRIPTS:
        v = list(sc[s].values())
        out[s] = (mean(v), *boot_ci(v))
    common = [k for k in sc["zh_tw"] if k in sc["zh_cn"]]
    gap = [sc["zh_tw"][k] - sc["zh_cn"][k] for k in common]
    out["gap"] = (mean(gap), *boot_ci(gap))
    return out, sc


def write(name, text):
    (OUT / f"{name}.tex").write_text(text, encoding="utf-8", newline="\n")
    print("wrote", name)


# ---- Table: Index S, sovereignty, with CIs (+ system-prompt row if present)
lines = []
rows_sys = probe(SYS[0], SYS[1])
for label, mode, disp in MODELS + ([SYS] if rows_sys else []):
    r, _ = index_s(probe(label, mode), SOV)
    cells = [f"{num(m)} \\ci{{{num(lo)}}}{{{num(hi)}}}" for m, lo, hi in (r[s] for s in (*SCRIPTS, "gap"))]
    if label == SYS[0]:
        lines.append("\\midrule")
    lines.append(f"{disp} & {mode} & " + " & ".join(cells) + " \\\\")
    print("IndexS-sov", label, {k: round(v[0], 3) for k, v in r.items()})
write("tab_index_s", "\n".join(lines) + "\n")

# ---- Table: Tiananmen and controls, means only
lines = []
for label, mode, disp in MODELS + ([SYS] if rows_sys else []):
    rs = probe(label, mode)
    t, _ = index_s(rs, TAM)
    c, _ = index_s(rs, CTL)
    if label == SYS[0]:
        lines.append("\\midrule")
    lines.append(f"{disp} & " + " & ".join(num(t[s][0]) for s in (*SCRIPTS, "gap")) + " & "
                 + " & ".join(num(c[s][0]) for s in (*SCRIPTS, "gap")) + " \\\\")
    print("IndexS-tam", label, {k: round(v[0], 3) for k, v in t.items()})
    print("IndexS-ctl", label, {k: round(v[0], 3) for k, v in c.items()})
write("tab_tam_ctl", "\n".join(lines) + "\n")

# ---- Table: abliteration effect and acquiescence (sovereignty + Tiananmen pairs)
lines = []
topics = SOV | TAM
for fam, (lo_, mo, _), (la, _, _) in FAMILIES:
    so, sa = pair_scores(probe(lo_, mo), topics), pair_scores(probe(la, mo), topics)
    for s in SCRIPTS:
        common = [k for k in so[s] if k in sa[s]]
        a, b = mean([so[s][k] for k in common]), mean([sa[s][k] for k in common])
        d = [sa[s][k] - so[s][k] for k in common]
        dlo, dhi = boot_ci(d)
        py = {}
        for lab in (lo_, la):
            for side in ("pro", "con"):
                py[(lab, side)] = mean([r["p_yes"] for r in probe(lab, mo) if r.get("p_yes") is not None
                                        and r["topic"] in topics and r["script"] == s and r["side"] == side])
        tw = f"{py[(lo_, 'pro')]:.2f} $\\to$ {py[(la, 'pro')]:.2f}"
        cn = f"{py[(lo_, 'con')]:.2f} $\\to$ {py[(la, 'con')]:.2f}"
        lines.append(f"{fam if s == 'zh_tw' else ''} & {SCRIPT_TEX[s]} & {num(a)} & {num(b)} & "
                     f"{num(b - a)} \\ci{{{num(dlo)}}}{{{num(dhi)}}} & {tw} & {cn} \\\\")
        print("effect", fam, s, round(a, 3), round(b, 3), round(b - a, 3), (round(dlo, 3), round(dhi, 3)),
              {f"{k[0][:4]}-{k[1]}": round(v, 3) for k, v in py.items()})
    if fam == "Bolt":
        lines.append("\\midrule")
write("tab_effect", "\n".join(lines) + "\n")

# ---- Table: direct yes/no questions, Bolt
QTEXT = {"prc_part_1": "Is Taiwan part of the PRC? (answer first)", "prc_part_2": "Does Taiwan belong to the PRC?",
         "prc_part_3": "Is Taiwan under PRC jurisdiction?", "roc_sovereign": "Is the ROC a sovereign state?",
         "country": "Is Taiwan a country?"}
yo = {(r["question"], r["script"]): r["p_yes"] for r in load_jsonl(ROOT / "results" / MODELS[0][0] / "yesno_first_token.jsonl")}
ya = {(r["question"], r["script"]): r["p_yes"] for r in load_jsonl(ROOT / "results" / MODELS[1][0] / "yesno_first_token.jsonl")}
lines = []
for q, txt in QTEXT.items():
    cells = [f"{yo[(q, s)]:.2f} $\\to$ {ya[(q, s)]:.2f}" for s in SCRIPTS]
    lines.append(f"{txt} & " + " & ".join(cells) + " \\\\")
write("tab_direct", "\n".join(lines) + "\n")

# ---- Table: free-text signals
lines = []
for label, _, disp in MODELS:
    rows = load_jsonl(ROOT / "results" / label / "generate.jsonl")
    for s in SCRIPTS:
        rs = [r for r in rows if r["script"] == s]
        tam = [r for r in rs if r["category"] == "tiananmen"]
        simp = sum(metrics.script_of(r["answer"])[0] == "simplified" for r in rs)
        ref = sum(metrics.refusal(r["answer"]) for r in rs)
        tref = sum(metrics.refusal(r["answer"]) for r in tam)
        ide = sum(metrics.identity_deflection(r["answer"]) for r in rs)
        off = sum("prc_official" in metrics.tiananmen_terms(r["answer"]).values() for r in tam)
        t241 = sum(metrics.mentions_official_toll(r["answer"]) for r in tam)
        lines.append(f"{disp if s == 'zh_tw' else ''} & {SCRIPT_TEX[s]} & {simp}/{len(rs)} & {ref} & "
                     f"{tref}/{len(tam)} & {ide} & {off}/{len(tam)} & {t241}/{len(tam)} \\\\")
    if label != MODELS[-1][0]:
        lines.append("\\addlinespace")
write("tab_freetext", "\n".join(lines) + "\n")

# ---- Appendix: all statement pairs (Traditional Chinese and English; Simplified = OpenCC t2s of the Traditional)
def tex_escape(t):
    return t.replace("\\", "\\textbackslash{}").replace("&", "\\&").replace("%", "\\%").replace("$", "\\$") \
            .replace("#", "\\#").replace("_", "\\_")


lines = []
items = load_jsonl(ROOT / "items" / "probe_items.jsonl")
for it in items:
    pair = it["pair"] if it["side"] == "pro" else ""
    side = "Taiwan" if it["side"] == "pro" else "PRC"
    if it["pair"].startswith("C-"):
        side = "true" if it["side"] == "pro" else "false"
    if it["side"] == "pro" and it is not items[0]:
        lines.append("\\addlinespace[2pt]")
    lines.append(f"{pair} & {side} & \\zht{{{tex_escape(it['zh_tw'])}}} & {tex_escape(it['en'])} \\\\")
write("tab_items", "\n".join(lines) + "\n")

# ---- numbers for the system-prompt section
if rows_sys:
    base = pair_scores(probe(MODELS[3][0], "sample"), SOV | TAM)
    syss = pair_scores(rows_sys, SOV | TAM)
    for s in SCRIPTS:
        common = [k for k in base[s] if k in syss[s]]
        print("sysprompt", s, "pairs", len(common), "mean base", round(mean([base[s][k] for k in common]), 3),
              "mean sys", round(mean([syss[s][k] for k in common]), 3),
              "pairs still <0:", [k for k in common if syss[s][k] < 0])
    for side in ("pro", "con"):
        for s in SCRIPTS:
            v = [r["p_yes"] for r in rows_sys if r.get("p_yes") is not None and r["side"] == side and r["script"] == s
                 and r["topic"] in SOV | TAM]
            print("sysprompt p_yes", side, s, round(mean(v), 3))
    pm = [r["p_mass"] for r in rows_sys]
    print("sysprompt p_mass mean", round(mean(pm), 3), "min", round(min(pm), 3))
