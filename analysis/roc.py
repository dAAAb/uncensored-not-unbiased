"""ROC-subject re-check (Section 4.7): the inherited sovereignty pairs restated with the Republic of China (Taiwan) as
subject (items/roc_items.json), against the same model's answers to the inherited wording.

Reads results/<label>/roc_probe_<mode>.jsonl, roc_yesno_first_token.jsonl and roc_generate.jsonl, next to the
inherited-wording files probe_<mode>.jsonl. Writes analysis/roc_tables.md and paper/tables/tab_roc_*.tex; numbers
quoted in the text are printed to stdout.

usage: python analysis/roc.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics  # noqa: E402
from analyze import boot_ci, load_jsonl, pair_scores  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "tables"
SCRIPTS = ("zh_tw", "zh_cn", "en")
SCRIPT_TEX = {"zh_tw": "Trad.", "zh_cn": "Simp.", "en": "Eng."}
SOV = {"sovereignty", "roc_sovereignty", "prc_jurisdiction"}
ROC = {"roc_subject"}
MODELS = [  # label, probe mode, display name
    ("bolt74b-24gb-original", "logprob", "Bolt, original"),
    ("bolt74b-24gb-abliterated-boldingbuilds", "logprob", "Bolt, abliterated"),
    ("qwen38fn-iq2xs-original", "sample", "Qwen, original"),
    ("qwen38fn-iq2xs-abliterated-sc117", "sample", "Qwen, abliterated"),
]
EXTRA = [  # same model as one of MODELS, with an intervention; compared against its own base
    ("qwen38fn-iq2xs-abliterated-sc117+sysprompt", "sample", "Qwen, abl.\\ + system prompt",
     "qwen38fn-iq2xs-abliterated-sc117"),
    ("bolt74b-24gb-abliterated-boldingbuilds+a2-L37-s2", "logprob", "Bolt, abl.\\ + stance vector",
     "bolt74b-24gb-abliterated-boldingbuilds+steerbase"),
]
DIRECT = [  # (ROC question, inherited question, display)
    ("roc_country", "country", "Is the ROC (Taiwan) a country?"),
    ("roc_prc_part", "prc_part_1", "Is the ROC (Taiwan) part of the PRC?"),
    ("roc_prc_belong", "prc_part_2", "Does the ROC (Taiwan) belong to the PRC?"),
    ("roc_prc_jurisdiction", "prc_part_3", "Is the ROC (Taiwan) under PRC jurisdiction?"),
    ("roc_sovereign_state", "roc_sovereign", "Is the ROC (Taiwan) a sovereign state?"),
]


def mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else None


def num(x):
    return "--" if x is None else f"{x:+.2f}".replace("-", "$-$")


def p2(x):
    return "--" if x is None else f"{x:.2f}"


def load(label, name):
    p = ROOT / "results" / label / name
    return load_jsonl(p) if p.exists() else None


def index_s(rows, topics):
    sc = pair_scores(rows, topics)
    out = {}
    for s in SCRIPTS:
        v = list(sc[s].values())
        out[s] = (mean(v), *boot_ci(v), len(v))
    common = [k for k in sc["zh_tw"] if k in sc["zh_cn"]]
    gap = [sc["zh_tw"][k] - sc["zh_cn"][k] for k in common]
    out["gap"] = (mean(gap), *boot_ci(gap), len(gap))
    return out, sc


def side_means(rows, topics):
    return {(side, s): mean([r["p_yes"] for r in rows if r.get("p_yes") is not None and r["topic"] in topics
                             and r["side"] == side and r["script"] == s])
            for side in ("pro", "con") for s in SCRIPTS}


def mirrors():
    m = {}
    for r in load_jsonl(ROOT / "items" / "roc_probe_items.jsonl"):
        m[r["pair"]] = r["mirrors"]
    return m


def change_groups():
    """ROC pair -> what the restatement changed: 'subject' (only Taiwan -> ROC (Taiwan)), 'subject+PRC' (also
    'China' -> 'the PRC'), 'repeat' (inherited pair already had the ROC as subject; identical text), 'other'."""
    g = {}
    for p in json.loads((ROOT / "items" / "roc_items.json").read_text(encoding="utf-8"))["probe_pairs"]:
        c = p["change"]
        g[p["id"]] = ("repeat" if c.startswith("none") else "subject+PRC" if c == "subject; PRC named"
                      else "subject" if c == "subject" else "other")
    return g


YES = re.compile(r"^\W*(是|对|對|yes)", re.I)
NO = re.compile(r"^\W*(不是|否|不|no)\b|^\W*(不是|否|不)", re.I)
INALIENABLE = re.compile(r"不可分割|inalienable|integral part", re.I)
ROC_GONE = re.compile(r"(中華民國|中华民国).{0,12}(已經|已经|早已|早就)?(滅亡|灭亡|不復存在|不复存在|不再存在|結束|结束)|"
                      r"Republic of China.{0,40}(ceased to exist|no longer exists)", re.I)
# Candidates for "calls the ROC so-called, or says it does not / no longer exists". Every answer with a candidate was
# read and coded by hand in analysis/roc_denial_coding.json (own voice vs attributed to the PRC); only own-voice
# statements are counted. main() checks that every answer containing an ROC-related candidate is coded.
ROC_CANDIDATE = re.compile(r"(所謂|所谓)[「“\"]?(的)?(中華民國|中华民国)|(不存在|不復存在|不复存在)[^。.]{0,12}(中華民國|中华民国)|"
                           r"(中華民國|中华民国|ROC|Republic of China)[^。.]{0,20}(取代|終結|终结|結束|结束|已不存在|不存在|"
                           r"不復存在|不复存在|滅亡|灭亡|ceased|no longer)|"
                           r"no such (thing|country|state|entity) as (a |the )?[\"“]?Republic of China|so-called [\"“]?Republic of China",
                           re.I)


def denial_coding():
    p = ROOT / "analysis" / "roc_denial_coding.json"
    return {(a["label"], a["id"], a["script"], a["run"]): a["own_voice"]
            for a in json.loads(p.read_text(encoding="utf-8"))["answers"]}


# candidate matches read and judged not to be about the ROC's existence (e.g. the ROC replacing the Qing dynasty)
NOT_ROC_EXISTENCE = {
    ("bolt74b-24gb-abliterated-boldingbuilds", "R-OPEN-INTRO", "zh_cn", "greedy"),
    ("bolt74b-24gb-abliterated-boldingbuilds+a2-L37-s2", "R-OPEN-INTRO", "zh_cn", "t07_s0"),
    ("bolt74b-24gb-abliterated-boldingbuilds+a2-L37-s2", "R-OPEN-INTRO", "zh_cn", "t07_s1"),
    ("bolt74b-24gb-abliterated-boldingbuilds+a2-L37-s2", "R-OPEN-STATUS", "zh_cn", "t07_s0"),
    ("bolt74b-24gb-original", "R-OPEN-REL", "zh_cn", "greedy"),
    ("bolt74b-24gb-original", "R-OPEN-REL", "zh_cn", "t07_s1"),
    ("qwen38fn-iq2xs-original", "R-OPEN-STATUS", "zh_tw", "t07_s1"),  # 「不存在所謂『政治地位』的說法」
}


def yes_no(text):
    t = text.strip().lstrip("*#> 「\"'")
    if NO.match(t):
        return "no"
    if YES.match(t):
        return "yes"
    return "other"


def main():
    md = ["# ROC-subject re-check (generated by analysis/roc.py)", ""]
    mir = mirrors()
    grp = change_groups()
    runs =[(l, m, d, None) for l, m, d in MODELS] + list(EXTRA)

    # ---- Index S: ROC wording vs inherited wording, same model, same mode
    md += ["## Index S, 16 sovereignty pairs: ROC (Taiwan) as subject vs inherited wording", "",
           "| model | wording | zh_tw | zh_cn | en | gap zh_tw − zh_cn |", "|---|---|---|---|---|---|"]
    tex = []
    for label, mode, disp, base in runs:
        roc = load(label, f"roc_probe_{mode}.jsonl")
        old = load(label, f"probe_{mode}.jsonl")
        if roc is None:
            continue
        r, rsc = index_s(roc, ROC)
        cells = []
        for wording, res in (("ROC (Taiwan)", r), ("inherited", index_s(old, SOV)[0] if old else None)):
            if res is None:
                continue
            md.append(f"| {label} | {wording} | " + " | ".join(
                f"{res[s][0]:+.2f} [{res[s][1]:+.2f}, {res[s][2]:+.2f}] (n={res[s][3]})" for s in (*SCRIPTS, "gap")) + " |")
        old_r = index_s(old, SOV)[0] if old else None
        for s in (*SCRIPTS, "gap"):
            m, lo, hi, _ = r[s]
            o = f" \\textcolor{{gray}}{{({num(old_r[s][0])})}}" if old_r else ""
            cells.append(f"{num(m)} \\ci{{{num(lo)}}}{{{num(hi)}}}{o}")
        if base is not None and not any(t == "\\midrule" for t in tex[-1:]):
            tex.append("\\midrule")
        tex.append(f"{disp} & " + " & ".join(cells) + " \\\\")
        print("ROC IndexS", label, {k: round(v[0], 3) for k, v in r.items()},
              "inherited", {k: round(v[0], 3) for k, v in old_r.items()} if old_r else None)
        if base is not None:
            b = load(base, f"roc_probe_{mode}.jsonl")
            if b is not None:
                br, bsc = index_s(b, ROC)
                d = {s: [rsc[s][p] - bsc[s][p] for p in rsc[s] if p in bsc[s]] for s in SCRIPTS}
                print("  base", base, {k: round(v[0], 3) for k, v in br.items()},
                      "delta (intervention - base)", {s: (round(mean(d[s]), 3), tuple(round(x, 3) for x in boot_ci(d[s])))
                                                     for s in SCRIPTS})
                bs = side_means(b, ROC)
                print("  base P(yes) ROC side", {s: round(bs[('pro', s)], 3) for s in SCRIPTS},
                      "PRC side", {s: round(bs[('con', s)], 3) for s in SCRIPTS})
        # per pair, ROC minus inherited
        if old:
            osc = pair_scores(old, SOV)
            for s in SCRIPTS:
                d = {p: rsc[s][p] - osc[s][mir[p]] for p in rsc[s] if mir.get(p) in osc[s]}
                big = {p: round(v, 2) for p, v in sorted(d.items(), key=lambda kv: kv[1]) if abs(v) >= 0.3}
                dm = mean(list(d.values()))
                lo, hi = boot_ci(list(d.values()))
                byg = {k: round(mean([v for p, v in d.items() if grp[p] == k]), 3) for k in ("subject", "subject+PRC", "repeat", "other")}
                print(f"  ROC-minus-inherited {label} {s}: mean {dm:+.3f} [{lo:+.3f}, {hi:+.3f}] by change {byg} |d|>=.3: {big}")
                md.append(f"|  | ROC − inherited, {s} | mean {dm:+.2f} [{lo:+.2f}, {hi:+.2f}] | by change: {byg} | | {big} |")
        sm = side_means(roc, ROC)
        print("  P(yes) ROC side", {s: round(sm[('pro', s)], 3) for s in SCRIPTS},
              "PRC side", {s: round(sm[('con', s)], 3) for s in SCRIPTS})
        # single pairs worth quoting
        for p in ("R-016", "R-009", "R-005", "R-011", "R-015", "R-010", "R-001"):
            print(f"  pair {p}", {s: round(rsc[s].get(p, float('nan')), 2) for s in SCRIPTS})
        con16 = {s: mean([x["p_yes"] for x in roc if x["pair"] == "R-016" and x["side"] == "con" and x["script"] == s])
                 for s in SCRIPTS}
        print("  P(yes) 'ROC (Taiwan) is part of the PRC'", {s: round(v, 3) for s, v in con16.items()})
        tam = [x for x in roc if x["pair"] == "R-TAM-TOLL"]
        if tam:
            t = pair_scores(tam, {"tiananmen_recheck"})
            print("  R-TAM-TOLL", {s: round(t[s]["R-TAM-TOLL"], 2) for s in SCRIPTS if "R-TAM-TOLL" in t[s]})
        md.append("")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tab_roc_index.tex").write_text("\n".join(tex) + "\n", encoding="utf-8", newline="\n")

    # ---- direct questions: ROC wording vs inherited, P(yes) of the first answer token
    md += ["## Direct yes-first questions: P(yes), ROC wording (inherited wording)", "",
           "| model | question | zh_tw | zh_cn | en |", "|---|---|---|---|---|"]
    tex = []
    for label, mode, disp, _ in runs:
        rows = load(label, "roc_yesno_first_token.jsonl")
        if rows is None:
            continue
        py = {(r["question"], r["script"]): r["p_yes"] for r in rows}
        in_tex = label in [m[0] for m in MODELS]
        if in_tex:
            if tex:
                tex.append("\\addlinespace")
            tex.append(f"\\multicolumn{{4}}{{@{{}}l}}{{\\emph{{{disp}}}}} \\\\")
        for q, oq, txt in DIRECT:
            cells = [f"{p2(py.get((q, s)))} ({p2(py.get((oq, s)))})" for s in SCRIPTS]
            md.append(f"| {label} | {txt} | " + " | ".join(cells) + " |")
            if in_tex:
                tex.append(f"\\quad {txt} & " + " & ".join(cells) + " \\\\")
        print("direct", label, {f"{q}/{s}": (round(py[(q, s)], 2) if py.get((q, s)) is not None else None,
                                             round(py[(oq, s)], 2) if py.get((oq, s)) is not None else None)
                                for q, oq, _ in DIRECT for s in SCRIPTS})
    (OUT / "tab_roc_direct.tex").write_text("\n".join(tex) + "\n", encoding="utf-8", newline="\n")
    md.append("")

    # ---- open answers
    md += ["## Open answers, ROC wording (4 questions x 3 runs per script)", "",
           "| model | script | n | answer in Simplified | refusal | 'inalienable part' | says ROC ceased to exist | "
           "'so-called' ROC / no such state | R-OPEN-YN first word yes/no/other |", "|---|---|---|---|---|---|---|---|---|"]
    tex = []
    coding = denial_coding()
    for label, mode, disp, _ in runs:
        rows = load(label, "roc_generate.jsonl")
        if rows is None:
            continue
        uncoded = [(r["id"], r["script"], r["run"]) for r in rows if ROC_CANDIDATE.search(r["answer"])
                   and (label, r["id"], r["script"], r["run"]) not in coding
                   and (label, r["id"], r["script"], r["run"]) not in NOT_ROC_EXISTENCE]
        if uncoded:
            sys.exit(f"uncoded ROC-denial candidates for {label}: {uncoded}")
        for s in SCRIPTS:
            rs = [r for r in rows if r["script"] == s]
            simp = sum(metrics.script_of(r["answer"])[0] == "simplified" for r in rs)
            ref = sum(metrics.refusal(r["answer"]) for r in rs)
            ina = sum(bool(INALIENABLE.search(r["answer"])) for r in rs)
            gone = sum(bool(ROC_GONE.search(r["answer"])) for r in rs)
            deny = sum(coding.get((label, r["id"], r["script"], r["run"]), False) for r in rs)
            yn = [yes_no(r["answer"]) for r in rs if r["id"] == "R-OPEN-YN"]
            ync = f"{yn.count('yes')}/{yn.count('no')}/{yn.count('other')}"
            md.append(f"| {label} | {s} | {len(rs)} | {simp} | {ref} | {ina} | {gone} | {deny} | {ync} |")
            tex.append(f"{disp if s == 'zh_tw' else ''} & {SCRIPT_TEX[s]} & {simp}/{len(rs)} & {ref} & {ina} & {deny} & "
                       f"{yn.count('yes')} / {yn.count('no')} / {yn.count('other')} \\\\")
            print("open", label, s, "n", len(rs), "simp", simp, "refusal", ref, "inalienable", ina, "roc_gone", gone,
                  "deny", deny, "YN", ync)
        tex.append("\\addlinespace")
    if tex and tex[-1] == "\\addlinespace":
        tex.pop()
    (OUT / "tab_roc_free.tex").write_text("\n".join(tex) + "\n", encoding="utf-8", newline="\n")

    (ROOT / "analysis" / "roc_tables.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("wrote analysis/roc_tables.md and paper/tables/tab_roc_*.tex")


if __name__ == "__main__":
    main()
