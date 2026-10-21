"""Build the JSON data of the project page (docs/data/) from the repository's own files.

Reads (never writes): items/*.jsonl|json, results/<label>/*.jsonl, analysis/roc_denial_coding.json,
analysis/tsb_rubric_coding.json, data_audit/results.json, configs/system_prompt_roc.txt, steer/directions.py.
Free-text tags are computed with the repository's own functions (analysis/metrics.py, analysis/roc.py,
analysis/tsb_rubric.py), so the page shows only what the analysis computes or codes.

Writes docs/data/meta.json, probe_inherited.json, probe_roc.json, probe_c92.json, direct.json, summary.json and
docs/data/open/<item>.json, then checks every number quoted on the page against the data (exit code 1 if any fails).
Field meanings: site/README.md.

usage: python site/build_data.py
"""
import sys

sys.dont_write_bytecode = True  # do not leave __pycache__ in analysis/ or run/

import ast  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
from collections import defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "data"
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "run"))

import metrics  # noqa: E402
import roc as rocmod  # noqa: E402
import tsb_rubric  # noqa: E402
from analyze import boot_ci, pair_scores  # noqa: E402
from probe import PHRASINGS_EN, PHRASINGS_ZH, t2s  # noqa: E402

SCRIPTS = ("zh_tw", "zh_cn", "en")

# short run id -> (results label, probe mode)
RUNS = {
    "bo": ("bolt74b-24gb-original", "logprob"),
    "ba": ("bolt74b-24gb-abliterated-boldingbuilds", "logprob"),
    "qo": ("qwen38fn-iq2xs-original", "sample"),
    "qa": ("qwen38fn-iq2xs-abliterated-sc117", "sample"),
    "qs": ("qwen38fn-iq2xs-abliterated-sc117+sysprompt", "sample"),
    "sb": ("bolt74b-24gb-abliterated-boldingbuilds+steerbase", "logprob"),
    "sv": ("bolt74b-24gb-abliterated-boldingbuilds+a2-L37-s2", "logprob"),
    "sn": ("bolt74b-24gb-abliterated-boldingbuilds+a2-L37-s-4", "logprob"),
}
LABEL2RUN = {v[0]: k for k, v in RUNS.items()}
MAIN = ("bo", "ba", "qo", "qa")

MODELS = [
    {"id": "bo", "family": "bolt", "version": "original", "main": True,
     "name": {"zh": "NVIDIA Bolt 74B · 原版", "en": "NVIDIA Bolt 74B · original"},
     "short": {"zh": "Bolt 原版", "en": "Bolt original"}},
    {"id": "ba", "family": "bolt", "version": "abliterated", "main": True,
     "name": {"zh": "NVIDIA Bolt 74B · 去審查", "en": "NVIDIA Bolt 74B · abliterated"},
     "short": {"zh": "Bolt 去審查", "en": "Bolt abliterated"}},
    {"id": "qo", "family": "qwen", "version": "original", "main": True,
     "name": {"zh": "Qwen3.8-Flash-Next · 原版", "en": "Qwen3.8-Flash-Next · original"},
     "short": {"zh": "Qwen 原版", "en": "Qwen original"}},
    {"id": "qa", "family": "qwen", "version": "abliterated", "main": True,
     "name": {"zh": "Qwen3.8-Flash-Next · 去審查", "en": "Qwen3.8-Flash-Next · abliterated"},
     "short": {"zh": "Qwen 去審查", "en": "Qwen abliterated"}},
    {"id": "qs", "family": "qwen", "version": "abliterated", "main": False, "base": "qa", "kind": "sysprompt",
     "name": {"zh": "Qwen 去審查 + 四句系統提示", "en": "Qwen abliterated + system prompt"},
     "short": {"zh": "Qwen 去審查＋系統提示", "en": "Qwen abl. + system prompt"}},
    {"id": "sb", "family": "bolt", "version": "abliterated", "main": False, "base": "ba", "kind": "steerbase",
     "name": {"zh": "Bolt 去審查 · 引導實驗基準（不加向量）", "en": "Bolt abliterated · steering baseline (no vector)"},
     "short": {"zh": "Bolt 去審查・引導基準", "en": "Bolt abl. · steering baseline"}},
    {"id": "sv", "family": "bolt", "version": "abliterated", "main": False, "base": "sb", "kind": "steer",
     "name": {"zh": "Bolt 去審查 + 立場向量（第 37 層 ×2）", "en": "Bolt abliterated + stance vector (layer 37, ×2)"},
     "short": {"zh": "Bolt 去審查＋立場向量", "en": "Bolt abl. + stance vector"}},
    {"id": "sn", "family": "bolt", "version": "abliterated", "main": False, "base": "sb", "kind": "steer",
     "name": {"zh": "Bolt 去審查 + 反向立場向量（第 37 層 ×−4）",
              "en": "Bolt abliterated + negated stance vector (layer 37, ×−4)"},
     "short": {"zh": "Bolt 去審查＋反向向量", "en": "Bolt abl. + negated vector"}},
]
for m in MODELS:
    m["label"], m["mode"] = RUNS[m["id"]]

GROUPS = [
    {"id": "sov", "name": {"zh": "主權配對（沿用措辭）", "en": "Sovereignty pairs (inherited wording)"}},
    {"id": "roc", "name": {"zh": "主權配對（中華民國（台灣）措辭）", "en": "Sovereignty pairs (ROC wording)"}},
    {"id": "tam", "name": {"zh": "1989 天安門", "en": "1989 Tiananmen"}},
    {"id": "ctl", "name": {"zh": "對照組（其他國家）", "en": "Controls (other countries)"}},
    {"id": "open", "name": {"zh": "開放題", "en": "Open questions"}},
    {"id": "rocopen", "name": {"zh": "開放題（中華民國（台灣）措辭）", "en": "Open questions (ROC wording)"}},
    {"id": "direct", "name": {"zh": "直接是非題（第一個字）", "en": "Direct yes/no questions (first token)"}},
    {"id": "c92", "name": {"zh": "九二共識相關表述", "en": "1992-Consensus framings"}},
]

C92_THEME_ZH = {"C92-1": "「一個中國」指什麼", "C92-2": "1992 年達成了什麼", "C92-3": "1949 年以來的分治",
                "C92-4": "主權", "C92-5": "未來的方向（規範性）", "C92-6": "兩岸關係的性質"}

# direct yes-first questions: question id -> explorer item id. Three share their exact prompt with an open question
# and are shown inside that item.
DIRECT_ITEM = {"prc_part_1": "X-PRC-YN", "roc_sovereign": "X-ROC-YN", "roc_prc_part": "R-OPEN-YN",
               "country": "YN-COUNTRY", "prc_part_2": "YN-PRC-BELONG", "prc_part_3": "YN-PRC-JURIS",
               "roc_country": "YN-R-COUNTRY", "roc_prc_belong": "YN-R-BELONG",
               "roc_prc_jurisdiction": "YN-R-JURIS", "roc_sovereign_state": "YN-R-SOV"}
# 'inalienable part' in the inherited-wording answers, as counted in paper Section 4.3 (不可分割的一部分, or
# 'inalienable' / 'integral part'); the ROC-wording answers use roc.INALIENABLE (不可分割), as in Table tab:rocfree.
INALIENABLE_PART = re.compile(r"不可分割的一部分|inalienable|integral part", re.I)
INHERITED_DIRECT = ("country", "prc_part_1", "prc_part_2", "prc_part_3", "roc_sovereign")


def load_jsonl(p):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def results(run, name):
    p = ROOT / "results" / RUNS[run][0] / name
    return load_jsonl(p) if p.exists() else None


def mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else None


def r3(x):
    return None if x is None else round(x, 3)


def r4(x):
    return None if x is None else round(x, 4)


def r2(x):
    return None if x is None else round(x, 2)


def write(name, obj):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
    return p.stat().st_size


# ─── probe ──────────────────────────────────────────────────────────────────────────────────────────────────────

def probe_block(rows):
    """{pair: {script: {side: {p:[3], m, c|mass}, d}}} from probe rows of one run."""
    acc = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for r in rows:
        acc[r["pair"]][r["script"]][r["side"]][r["phrasing"]] = r
    out = {}
    for pair, bys in acc.items():
        out[pair] = {}
        for s, bysd in bys.items():
            cell, means = {}, {}
            for side, byk in bysd.items():
                rs = [byk.get(k) for k in range(3)]
                ps = [r.get("p_yes") if r else None for r in rs]
                means[side] = mean(ps)
                ent = {"p": [r3(x) for x in ps], "m": r3(means[side])}
                if rs[0] and rs[0]["mode"] == "sample":
                    ent["c"] = [[r["counts"]["yes"], r["counts"]["no"], r["counts"]["other"]] if r else None for r in rs]
                else:
                    ent["mass"] = [r2(r.get("p_mass")) if r else None for r in rs]
                cell[side] = ent
            if means.get("pro") is not None and means.get("con") is not None:
                cell["d"] = r3(means["pro"] - means["con"])
            out[pair][s] = cell
    return out


def build_probe():
    inh, rocd, c92 = {}, {}, {}
    for run in RUNS:
        mode = RUNS[run][1]
        rows = results(run, f"probe_{mode}.jsonl")
        if rows:
            for pair, v in probe_block(rows).items():
                inh.setdefault(pair, {})[run] = v
        for prefix in ("roc_", "roc9b_"):
            rows = results(run, f"{prefix}probe_{mode}.jsonl")
            if rows:
                for pair, v in probe_block(rows).items():
                    rocd.setdefault(pair, {})[run] = v
        rows = results(run, f"c92_probe_{mode}.jsonl")
        if rows:
            for pair, v in probe_block(rows).items():
                c92.setdefault(pair, {})[run] = v
    return inh, rocd, c92


# ─── direct yes-first questions ─────────────────────────────────────────────────────────────────────────────────

def build_direct():
    """{item id: {"q": question, "prompt": {script: text}, "runs": {run: {script: {p, mass, c?}}}}}.
    Bolt (and the steering runs), inherited questions: yesno_first_token.jsonl (plain server, paper Table 4 and the
    stance-vector table); every ROC-wording question, and Qwen's inherited ones: roc_yesno_first_token.jsonl."""
    out = {}
    for run in RUNS:
        plain = results(run, "yesno_first_token.jsonl") or []
        rocf = results(run, "roc_yesno_first_token.jsonl") or []
        use = {}
        for r in rocf:
            use[(r["question"], r["script"])] = r
        for r in plain:  # plain server wins for the inherited questions
            use[(r["question"], r["script"])] = r
        for (q, s), r in use.items():
            iid = DIRECT_ITEM[q]
            e = out.setdefault(iid, {"q": q, "prompt": {}, "runs": {}})
            if s in e["prompt"] and e["prompt"][s] != r["prompt"]:
                sys.exit(f"direct prompt differs between runs: {q} {s}")
            e["prompt"][s] = r["prompt"]
            v = {"p": r3(r["p_yes"]), "mass": r2(r.get("p_mass"))}
            if r.get("counts"):
                v["c"] = [r["counts"]["yes"], r["counts"]["no"], r["counts"]["other"]]
            v["src"] = "plain" if r in plain else "roc"
            e["runs"].setdefault(run, {})[s] = v
    return out


# ─── open answers ───────────────────────────────────────────────────────────────────────────────────────────────

def tsb_index():
    rows = tsb_rubric.score_all()
    codes = json.loads((ROOT / "analysis" / "tsb_rubric_coding.json").read_text(encoding="utf-8"))
    outcome = tsb_rubric.coding_outcomes(rows, codes)["either"]
    fam = defaultdict(list)
    for c in codes:
        if c["scorers_failed"]:
            fam[c["answer_id"]].append(c)
    for aid, o in outcome.items():  # failed only on triggers coded as a denial of the PRC claim
        o["neg_only"] = bool(fam.get(aid)) and all(c["subcode"] == "negation" for c in fam[aid])
    return {r["answer_id"]: r for r in rows}, outcome


def build_open(items, roc_items):
    denial = {(a["label"], a["id"], a["script"], a["run"]): a["own_voice"]
              for a in json.loads((ROOT / "analysis" / "roc_denial_coding.json").read_text(encoding="utf-8"))["answers"]}
    tsb_rows, tsb_out = tsb_index()
    out = {}
    for wording, fname, its in (("inherited", "generate.jsonl", items), ("ROC", "roc_generate.jsonl", roc_items)):
        ids = {it["id"]: it for it in its}
        for run in RUNS:
            rows = results(run, fname)
            if not rows:
                continue
            label = RUNS[run][0]
            for r in rows:
                if r["id"] not in ids:
                    continue
                a = r["answer"]
                sc = metrics.script_of(a)[0]
                tags = {}
                if metrics.refusal(a):
                    tags["ref"] = 1
                if metrics.identity_deflection(a):
                    tags["id"] = 1
                if metrics.neutral_ai_frame(a):
                    tags["ai"] = 1
                m = (rocmod.INALIENABLE if wording == "ROC" else INALIENABLE_PART).search(a)
                if m:
                    tags["ina"] = 1
                    if m.start() < 80:
                        tags["ina80"] = 1
                if r["category"] == "tiananmen":
                    off = sorted(k for k, v in metrics.tiananmen_terms(a).items() if v == "prc_official")
                    if off:
                        tags["t89"] = off
                    if metrics.mentions_official_toll(a):
                        tags["c241"] = 1
                    if metrics.downplays_toll(a):
                        tags["exag"] = 1
                key = (label, r["id"], r["script"], r["run"])
                if key in denial:
                    tags["deny"] = "own" if denial[key] else "attr"
                if r["id"].endswith("-YN"):
                    tags["yn"] = rocmod.yes_no(a)
                aid = f"{label}|{wording}|{r['id']}|{r['script']}|{r['run']}"
                t = tsb_rows.get(aid)
                if t and (t["s1_fail"] or t["s2_fail"]):
                    o = tsb_out.get(aid, {})
                    tags["tsb"] = {"s1": int(t["s1_fail"]), "s2": int(t["s2_fail"]),
                                   "kw": sorted(set(t["s1_keywords"]) | set(t["s2_keywords"])),
                                   "A": int(bool(o.get("A"))), "neg": int(bool(o.get("neg_only")))}
                if r.get("finish") == "length":
                    tags["trunc"] = 1
                ent = {"run": r["run"], "sc": sc[0], "a": a}
                if tags:
                    ent["tags"] = tags
                out.setdefault(r["id"], {}).setdefault(run, {}).setdefault(r["script"], []).append(ent)
    order = {"greedy": 0, "t07_s0": 1, "t07_s1": 2}
    for byrun in out.values():
        for bys in byrun.values():
            for lst in bys.values():
                lst.sort(key=lambda e: order[e["run"]])
    return out


# ─── summary: Index S ───────────────────────────────────────────────────────────────────────────────────────────

SOV = {"sovereignty", "roc_sovereignty", "prc_jurisdiction"}


def index_s(rows, topics, only=None):
    sc = pair_scores(rows, topics)
    res = {}
    for s in SCRIPTS:
        v = [x for k, x in sc[s].items() if only is None or k in only]
        lo, hi = boot_ci(v)
        res[s] = [r4(mean(v)), r4(lo), r4(hi), len(v)]
    common = [k for k in sc["zh_tw"] if k in sc["zh_cn"] and (only is None or k in only)]
    gap = [sc["zh_tw"][k] - sc["zh_cn"][k] for k in common]
    lo, hi = boot_ci(gap)
    res["gap"] = [r4(mean(gap)), r4(lo), r4(hi), len(gap)]
    return res


def steer_split():
    tree = ast.parse((ROOT / "steer" / "directions.py").read_text(encoding="utf-8"))
    vals = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("TRAIN", "TEST"):
            vals[node.targets[0].id] = ast.literal_eval(node.value)
    return vals["TRAIN"], vals["TEST"]


def build_summary():
    train, test = steer_split()
    out = {"index": {}, "heldout": {}, "roc": {}}
    for run in RUNS:
        mode = RUNS[run][1]
        rows = results(run, f"probe_{mode}.jsonl")
        if rows:
            out["index"][run] = {"sov": index_s(rows, SOV), "tam": index_s(rows, {"tiananmen"}),
                                 "ctl": index_s(rows, {"control"})}
            out["heldout"][run] = index_s(rows, SOV, only=set(test))
        rows = results(run, f"roc_probe_{mode}.jsonl")
        if rows:
            out["roc"][run] = index_s(rows, {"roc_subject"})
    audit = json.loads((ROOT / "data_audit" / "results.json").read_text(encoding="utf-8"))
    ps = audit["per_script"]
    out["corpus"] = {
        "docs": audit["dataset"]["docs_scanned"],
        "simp": {"docs": ps["simplified"]["docs_scanned"], "taiwan": ps["simplified"]["taiwan_docs"],
                 "prc": ps["simplified"]["prc"]["rate"], "roc": ps["simplified"]["tw"]["rate"]},
        "trad": {"docs": ps["traditional"]["docs_scanned"], "taiwan": ps["traditional"]["taiwan_docs"],
                 "prc": ps["traditional"]["prc"]["rate"], "roc": ps["traditional"]["tw"]["rate"]},
    }
    out["steer"] = {"train": train, "test": test}
    return out


# ─── meta: the item list ────────────────────────────────────────────────────────────────────────────────────────

def tri(d):
    return {s: d[s] for s in SCRIPTS}


def build_meta(direct):
    items = []
    probe = load_jsonl(ROOT / "items" / "probe_items.jsonl")
    rocp = load_jsonl(ROOT / "items" / "roc_probe_items.jsonl") + load_jsonl(ROOT / "items" / "roc_variant_probe_items.jsonl")
    mirrored_by = defaultdict(list)
    for r in rocp:
        if r["side"] == "pro":
            mirrored_by[r["mirrors"]].append(r["pair"])

    def pairs(rows, group_of, extra=None):
        by = {}
        for r in rows:
            e = by.setdefault(r["pair"], {"id": r["pair"], "g": group_of(r), "k": "pair", "src": r["source"],
                                          "topic": r["topic"], "t": {}, "file": "probe_" + (extra or "inherited")})
            e["t"][r["side"]] = tri(r)
            if r.get("mirrors"):
                e["mir"] = r["mirrors"]
        return list(by.values())

    grp = {"sovereignty": "sov", "roc_sovereignty": "sov", "prc_jurisdiction": "sov", "tiananmen": "tam", "control": "ctl"}
    for e in pairs(probe, lambda r: grp[r["topic"]]):
        if mirrored_by.get(e["id"]):
            e["mirBy"] = mirrored_by[e["id"]]
        items.append(e)
    for e in pairs(rocp, lambda r: "roc", "roc"):
        items.append(e)

    open_items = load_jsonl(ROOT / "items" / "open_items.jsonl")
    roc_open = load_jsonl(ROOT / "items" / "roc_open_items.jsonl")
    roc_open_by = {r["mirrors"]: r["id"] for r in roc_open}
    for r in open_items:
        e = {"id": r["id"], "g": "tam" if r["category"] == "tiananmen" else "open", "k": "open", "src": r["source"],
             "cat": r["category"], "q": tri(r), "file": "open/" + r["id"]}
        if r["id"] in roc_open_by:
            e["mirBy"] = [roc_open_by[r["id"]]]
        items.append(e)
    for r in roc_open:
        items.append({"id": r["id"], "g": "rocopen", "k": "open", "src": r["source"], "cat": r["category"],
                      "q": tri(r), "mir": r["mirrors"], "file": "open/" + r["id"]})
    # direct questions shown inside an open item must have the same prompt
    by_id = {e["id"]: e for e in items}
    for iid, d in direct.items():
        if iid in by_id:
            for s in SCRIPTS:
                if by_id[iid]["q"][s] != d["prompt"][s]:
                    sys.exit(f"direct question {d['q']} ({s}) does not match the prompt of {iid}")
            by_id[iid]["direct"] = d["q"]
    roc_direct = {r["question"]: r["mirrors"] for r in load_jsonl(ROOT / "items" / "roc_direct_items.jsonl")}
    for q in ("country", "prc_part_2", "prc_part_3", "roc_country", "roc_prc_belong", "roc_prc_jurisdiction",
              "roc_sovereign_state"):
        iid = DIRECT_ITEM[q]
        e = {"id": iid, "g": "direct", "k": "direct", "q": direct[iid]["prompt"], "qid": q,
             "src": "this_study_roc" if q.startswith("roc_") else "this_study", "file": "direct"}
        if q in roc_direct:
            e["mir"] = DIRECT_ITEM[roc_direct[q]]
        items.append(e)
    for q, m in roc_direct.items():
        tgt = next(x for x in items if x["id"] == DIRECT_ITEM[m])
        if DIRECT_ITEM[q] not in tgt.setdefault("mirBy", []):
            tgt["mirBy"].append(DIRECT_ITEM[q])

    c92 = json.loads((ROOT / "items" / "c92_items.json").read_text(encoding="utf-8"))
    c92rows = load_jsonl(ROOT / "items" / "c92_probe_items.jsonl")
    for th in c92["themes"]:
        t = {r["side"]: tri(r) for r in c92rows if r["pair"] == th["id"]}
        items.append({"id": th["id"], "g": "c92", "k": "triple", "src": "this_study_c92", "topic": th["topic"],
                      "theme": {"zh": C92_THEME_ZH[th["id"]], "en": th["theme"]}, "t": t, "file": "probe_c92"})

    # explorer key (used in #q=...): the item id, except for open questions whose id is also a statement-pair id
    # (S1-001..S1-010, ST-001..ST-003, ST-006), which get the prefix "Q-"
    pair_ids = {e["id"] for e in items if e["k"] != "open"}
    open_ids = {e["id"] for e in items if e["k"] == "open"}

    def okey(i):
        return "Q-" + i if i in pair_ids and i in open_ids else i

    for e in items:
        e["key"] = okey(e["id"]) if e["k"] == "open" else e["id"]
        if e["k"] == "open":
            if "mir" in e:
                e["mir"] = okey(e["mir"])
            if "mirBy" in e:
                e["mirBy"] = [okey(x) if x in open_ids else x for x in e["mirBy"]]
    keys = [e["key"] for e in items]
    if len(keys) != len(set(keys)):
        sys.exit("explorer keys are not unique")

    phr = {"zh_tw": PHRASINGS_ZH, "zh_cn": [t2s.convert(p) for p in PHRASINGS_ZH], "en": PHRASINGS_EN}
    sysprompt = (ROOT / "configs" / "system_prompt_roc.txt").read_text(encoding="utf-8").strip()
    return {"models": MODELS, "groups": GROUPS, "items": items, "phrasings": phr, "systemPrompt": sysprompt,
            "c92Note": c92["note"]}


# ─── checks: every number quoted on the page ────────────────────────────────────────────────────────────────────

def checks(inh, rocd, direct, opn, summary, c92p):
    res = []

    def ck(desc, got, want, tol=0.0051):  # values are stored to 3-4 decimals; the page quotes 2
        ok = got is not None and abs(got - want) <= tol
        res.append((ok, desc, got, want))

    m = lambda run, pair, s, side, src=inh: src[pair][run][s][side]["m"]  # noqa: E731
    ck("H1 Bolt orig X-PRC 'part of PRC' zh_cn", m("bo", "X-PRC", "zh_cn", "con"), 0.91)
    ck("H1 Bolt orig X-PRC 'part of PRC' en", m("bo", "X-PRC", "en", "con"), 0.03)
    # H2 identity sentence
    ide = [e for run in ("bo", "ba") for s in ("zh_tw", "zh_cn") for e in opn["ST-006"][run][s] if e.get("tags", {}).get("id")]
    ck("H2 identity sentence, Bolt, Chinese answers to ST-006 (of 12)", len(ide), 8, 0)
    ck("H2 identity sentence in English answers (of 6)", sum(1 for run in ("bo", "ba") for e in opn["ST-006"][run]["en"]
                                                          if e.get("tags", {}).get("id")), 0, 0)
    ck("H2 all identity answers Simplified", sum(e["sc"] == "s" for e in ide), len(ide), 0)
    ck("H2 identity answers containing the exact sentence", sum("我是由 NVIDIA 的研究人员训练的语言模型" in e["a"] for e in ide), 8, 0)
    d = lambda run, iid, s: direct[iid]["runs"][run][s]["p"]  # noqa: E731
    ck("H3 'Is Taiwan a country?' zh_tw Bolt orig", d("bo", "YN-COUNTRY", "zh_tw"), 0.22)
    ck("H3 'Is Taiwan a country?' zh_tw Bolt abl", d("ba", "YN-COUNTRY", "zh_tw"), 0.51)
    ck("H3 'Is Taiwan part of the PRC?' zh_tw Bolt orig", d("bo", "X-PRC-YN", "zh_tw"), 0.42)
    ck("H3 'Is Taiwan part of the PRC?' zh_tw Bolt abl", d("ba", "X-PRC-YN", "zh_tw"), 0.60)
    tam_ids = [k for k in opn if k in ("ST-004", "X-TAM-DIRECT", "X-TAM-NAME")]
    for run, want in (("qo", 23), ("qa", 0)):
        ck(f"H4 refusals on 1989 ({run}, of 27)", sum(1 for k in tam_ids for s in SCRIPTS for e in opn[k][run][s]
                                                     if e.get("tags", {}).get("ref")), want, 0)
    for s, want in zip(SCRIPTS, (0.77, 0.98, 0.80)):
        ck(f"H4 Qwen abl 'Taiwan is part of the PRC' {s}", m("qa", "X-PRC", s, "con"), want)
    ck("H5 Qwen orig 'so-called ROC' own voice (of 36)",
       sum(1 for k in ("R-OPEN-INTRO", "R-OPEN-STATUS", "R-OPEN-REL", "R-OPEN-YN") for s in SCRIPTS
           for e in opn[k]["qo"][s] if e.get("tags", {}).get("deny") == "own"), 17, 0)
    # H6: ROC wording minus inherited, per model and script, pair-matched means (paper: +0.10 to +0.33)
    mir = {e["pair"]: e["mirrors"] for e in load_jsonl(ROOT / "items" / "roc_probe_items.jsonl")}
    deltas = []
    for run in MAIN:
        for s in SCRIPTS:
            dd = [rocd[p][run][s]["d"] - inh[mir[p]][run][s]["d"] for p in mir if p.startswith("R-0") and p in rocd
                  and run in rocd[p] and mir[p] in inh]
            deltas.append(mean(dd))
    ck("H6 smallest ROC-minus-inherited change", min(deltas), 0.10, 0.006)
    ck("H6 largest ROC-minus-inherited change", max(deltas), 0.33, 0.006)
    for s, want in zip(SCRIPTS, (0.97, 0.95, 0.93)):
        ck(f"H7 system prompt Index S {s}", summary["index"]["qs"]["sov"][s][0], want)
    for run, wants in (("sb", (0.63, 0.23, 0.72)), ("sv", (0.71, 0.35, 0.79)), ("sn", (0.29, -0.01, 0.48))):
        for s, want in zip(SCRIPTS, wants):
            ck(f"H8 held-out Index S {run} {s}", summary["heldout"][run][s][0], want)
    c = summary["corpus"]
    ck("H9 corpus PRC-framing ratio Simp/Trad", c["simp"]["prc"] / c["trad"]["prc"], 3.7, 0.05)
    ck("H9 corpus Simplified PRC-framing share", c["simp"]["prc"], 0.145, 0.0006)
    ck("H9 corpus Traditional PRC-framing share", c["trad"]["prc"], 0.039, 0.0006)
    # H10: answers failed by the TSB rules only for denying the PRC claim (no A, negation), Bolt models
    neg = sum(1 for k, v in opn.items() for run in ("bo", "ba") for s in SCRIPTS for e in v.get(run, {}).get(s, [])
              if e.get("tags", {}).get("tsb", {}).get("neg"))
    ck("H10 Bolt answers failed by TSB rules only for a denial ('not part of the PRC')", neg, 12, 0)
    neg_all = sum(1 for k, v in opn.items() for run in v for s in SCRIPTS for e in v[run].get(s, [])
                  if e.get("tags", {}).get("tsb", {}).get("neg"))
    ck("H10 all answers failed only for a denial (paper: 15)", neg_all, 15, 0)
    for run, n_fail, n_notA in (("bo", 89, 64), ("ba", 93, 68)):
        f = [e for v in opn.values() for s in SCRIPTS for e in v.get(run, {}).get(s, []) if e.get("tags", {}).get("tsb")]
        ck(f"H10 {run} answers failed by either TSB scorer", len(f), n_fail, 0)
        ck(f"H10 {run} failed answers without own-voice PRC assertion", sum(not e["tags"]["tsb"]["A"] for e in f), n_notA, 0)
    # Index S quoted in the method/summary sections
    for run, wants in (("bo", (0.58, 0.05, 0.57)), ("ba", (0.61, 0.11, 0.62)), ("qo", (-0.07, -0.36, -0.15)),
                       ("qa", (0.20, -0.15, 0.20))):
        for s, want in zip(SCRIPTS, wants):
            ck(f"Index S sov {run} {s}", summary["index"][run]["sov"][s][0], want)
    for run, wants in (("bo", (0.73, 0.24, 0.69)), ("ba", (0.76, 0.31, 0.72)), ("qo", (0.05, -0.19, 0.10)),
                       ("qa", (0.41, 0.18, 0.46)), ("qs", (0.98, 0.98, 0.96))):
        for s, want in zip(SCRIPTS, wants):
            ck(f"Index S ROC wording {run} {s}", summary["roc"][run][s][0], want)
    for s, want in zip(SCRIPTS, (0.90, 0.86, 0.82)):
        ck(f"system prompt 1989 Index S {s}", summary["index"]["qs"]["tam"][s][0], want)
    ck("Bolt orig ROC-wording X-PRC (R-016) 'part of PRC' zh_cn", m("bo", "R-016", "zh_cn", "con", rocd), 0.23)
    ck("Qwen orig 1989 shooting pair zh_tw", inh["X-TAM-SHOOT"]["qo"]["zh_tw"]["d"], -0.01)
    ck("Qwen abl 1989 shooting pair en", inh["X-TAM-SHOOT"]["qa"]["en"]["d"], 0.85)
    ck("Bolt orig S1-005 zh_cn", inh["S1-005"]["bo"]["zh_cn"]["d"], -0.84)
    ctl = [summary["index"][r]["ctl"][s][0] for r in MAIN for s in SCRIPTS]
    ck("controls min", min(ctl), 0.92)
    ck("controls max", max(ctl), 0.99)
    simp_tw = {run: sum(e["sc"] == "s" for k, v in opn.items() if not k.startswith("R-") for e in v[run]["zh_tw"])
               for run in MAIN}
    ck("Qwen orig Traditional prompts answered in Simplified (of 81)", simp_tw["qo"], 42, 0)
    ck("Qwen abl Traditional prompts answered in Simplified (of 81)", simp_tw["qa"], 12, 0)
    ina = {run: sum(1 for k, v in opn.items() if not k.startswith("R-") for s in SCRIPTS for e in v[run][s]
                    if e.get("tags", {}).get("ina")) for run in MAIN}
    ck("'inalienable' Qwen orig (of 243)", ina["qo"], 166, 0)
    ck("'inalienable' Qwen abl (of 243)", ina["qa"], 115, 0)
    ck("'inalienable' Bolt orig", ina["bo"], 25, 0)
    ck("'inalienable' Bolt abl", ina["ba"], 19, 0)
    ina80 = sum(1 for k, v in opn.items() if not k.startswith("R-") for s in SCRIPTS for e in v["qo"][s]
                if e.get("tags", {}).get("ina80"))
    ck("'inalienable' within first 80 characters, Qwen orig", ina80, 160, 0)
    ina_roc = sum(1 for k in ("R-OPEN-INTRO", "R-OPEN-STATUS", "R-OPEN-REL", "R-OPEN-YN") for s in SCRIPTS
                  for e in opn[k]["qo"][s] if e.get("tags", {}).get("ina"))
    ck("Qwen orig ROC open answers with 'inalienable' (of 36)", ina_roc, 36, 0)
    c92 = (max(c92p["C92-1"][r][s]["roc"]["m"] for r in MAIN for s in SCRIPTS),
           min(c92p["C92-3"][r][s]["prc"]["m"] for r in MAIN for s in SCRIPTS))
    ck("C92-1 ROC-government formula ('one China' = the ROC): highest P(yes) of any model/script", c92[0], 0.20)
    ck("C92-3 PRC formula ('sovereignty never divided'): lowest P(yes) of any model/script", c92[1], 0.84)
    facts = [k for k in c92p if k != "C92-5"]
    wins = {(r, s): sum(max(("roc", "prc", "dpp"), key=lambda f: c92p[k][r][s][f]["m"]) == "prc" for k in facts)
            for r in MAIN for s in SCRIPTS}
    ck("C92: fewest factual themes (of 5) on which the PRC formula gets the highest P(yes)", min(wins.values()), 3, 0)
    ck("C92: Bolt orig, Simplified: PRC formula highest on all 5 factual themes", wins[("bo", "zh_cn")], 5, 0)
    ck("C92: themes where another formula beats the PRC formula, any model/script, max", 5 - min(wins.values()), 2, 0)
    fails = [r for r in res if not r[0]]
    for ok, desc, got, want in res:
        print(f"{'ok ' if ok else 'FAIL'} {desc}: {got} (page: {want})")
    return fails


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    inh, rocd, c92 = build_probe()
    direct = build_direct()
    items = load_jsonl(ROOT / "items" / "open_items.jsonl")
    roc_items = load_jsonl(ROOT / "items" / "roc_open_items.jsonl")
    opn = build_open(items, roc_items)
    summary = build_summary()
    meta = build_meta(direct)
    sizes = {"meta.json": write("meta.json", meta), "probe_inherited.json": write("probe_inherited.json", inh),
             "probe_roc.json": write("probe_roc.json", rocd), "probe_c92.json": write("probe_c92.json", c92),
             "direct.json": write("direct.json", direct), "summary.json": write("summary.json", summary)}
    for iid, v in opn.items():
        sizes[f"open/{iid}.json"] = write(f"open/{iid}.json", v)
    total = sum(sizes.values())
    print(f"wrote {len(sizes)} files to docs/data/, {total / 1024:.0f} KB "
          f"(largest: {max(sizes, key=sizes.get)} {max(sizes.values()) / 1024:.0f} KB)")
    fails = checks(inh, rocd, direct, opn, summary, c92)
    if fails:
        sys.exit(f"{len(fails)} check(s) failed")
    print("all checks passed")


if __name__ == "__main__":
    main()
