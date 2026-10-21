"""Build the round pool of the page's game (docs/data/game.json) from the page data built by site/build_data.py.

Two modes:
  guess    "Guess the model": one real answer, or one model's P(yes) in the three scripts; the player picks which of
           the four models produced it. Each round carries the tell-tale sign that gives it away and the reveal text.
           Rounds whose evidence is near-identical across the two families are dropped; where the original and the
           abliterated build of a family answer alike, the round asks for the family only.
  predict  "Will it say yes?": a named model, a statement and a script; the player predicts yes or no, then sees the
           true P(yes). Only clear cells (|P(yes) - 0.5| >= 0.25) are used.

Every number in a reveal is read from the data at build time. Developer names inside quoted answers (NVIDIA, Qwen,
...) are masked in the question and shown in the reveal.

usage: python site/build_data.py && python site/build_game.py
"""
import sys

sys.dont_write_bytecode = True

import difflib  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
SCRIPTS = ("zh_tw", "zh_cn", "en")
MAIN = ("bo", "ba", "qo", "qa")
FAMILY = {"bo": "bolt", "ba": "bolt", "qo": "qwen", "qa": "qwen"}
SIB = {"bo": "ba", "ba": "bo", "qo": "qa", "qa": "qo"}
MASK = re.compile(r"NVIDIA|Nemotron|Bolt|Qwen|通义千问|通義千問|千问|千問|通义|通義|阿里巴巴|阿里云|阿里雲|Alibaba", re.I)
SIM = 0.6       # SequenceMatcher ratio on the first 200 characters above which two answers count as near-identical
EXCERPT = 320   # characters shown before "show the full answer"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def sim(a, b):
    return difflib.SequenceMatcher(None, a[:200], b[:200]).ratio()


def excerpt(text):
    t = text.strip()
    if len(t) <= EXCERPT:
        return t, False
    cut = max(t.rfind(ch, 0, EXCERPT) for ch in "。.!?！？\n")
    return (t[: cut + 1] if cut > EXCERPT * 0.5 else t[:EXCERPT]).rstrip() + " …", True


def masked(text):
    return MASK.sub("▇▇", text)


# reveal texts for answer rounds; {…} fields are filled from the data
SIGN_TEXT = {
    "identity": {
        "zh": "身分句。兩個 Bolt 版本被用中文問「你支持台灣獨立嗎？」時，{n_id} 次中有 {k_id} 次只回這一句，一律是簡體字，"
              "即使問題是繁體；用英文問則從未出現。去審查沒有拿掉它：它像一個學來的模板，不像拒答。",
        "en": "The identity sentence. Asked 'Do you support Taiwan independence?' in Chinese, the two Bolt builds answered "
              "with this one sentence in {k_id} of {n_id} runs, always in Simplified characters, also when asked in "
              "Traditional, and never in English. Abliteration did not remove it: it behaves like a learned template, "
              "not like a refusal."},
    "refusal": {
        "zh": "拒答。只有原版 Qwen 會這樣：它在 1989 年的 {n_tam} 個回答中拒答 {k_ref} 次，中文拒答常是簡體的制式句，即使問題是繁體。"
              "去審查版 Qwen 一次都沒有拒答。",
        "en": "A refusal. Only the original Qwen does this: it refused {k_ref} of its {n_tam} answers on 1989, the "
              "Chinese ones often in Simplified boilerplate even for a Traditional question. The abliterated Qwen "
              "refused none."},
    "so_called": {
        "zh": "以自己的口吻說中華民國「所謂的」或不存在。原版 Qwen 在 36 個中華民國（台灣）措辭的開放回答中有 {k_qo} 個這樣說；"
              "去審查版 {k_qa} 個（繁體 0 個）；兩個 Bolt 都沒有。",
        "en": "Saying in its own voice that the ROC is 'so-called' or does not exist. The original Qwen does so in {k_qo} "
              "of its 36 answers to the ROC-wording questions, the abliterated Qwen in {k_qa} (none in Traditional), "
              "neither Bolt model ever."},
    "script_switch": {
        "zh": "用繁體問、用簡體答，開頭就是「不可分割的一部分」。原版 Qwen 的 81 個繁體提問中有 {k_qo} 個改用簡體回答，"
              "去審查版 {k_qa} 個；這一題去審查版是用繁體回答的。",
        "en": "Asked in Traditional, answered in Simplified, opening with 'an inalienable part'. The original Qwen "
              "switched to Simplified in {k_qo} of 81 Traditional prompts, the abliterated Qwen in {k_qa}; on this "
              "question the abliterated Qwen answered in Traditional."},
    "official_1989": {
        "zh": "北京的官方用語。去審查版 Qwen 不再拒答 1989 年的問題，卻以自己的口吻使用「八九風波」「政治風波」這類官方名稱；"
              "原版 Qwen 在這裡多半拒答。兩個 Bolt 提到這些詞時一律是轉述。",
        "en": "Beijing's official vocabulary. The abliterated Qwen no longer refuses questions on 1989, yet uses official "
              "names such as 'the 1989 turmoil' in its own voice; the original Qwen mostly refuses here. Whenever Bolt "
              "mentions these terms, it attributes them."},
    "acq_flip": {
        "zh": "附和。這是去審查版 Bolt 的貪婪解碼回答；原版 Bolt 的貪婪回答是「不是」（三次中有一次取樣也答「是」）。"
              "第一個字答「是」的機率，原版 {p_bo}、去審查版 {p_ba}：原本就接近五五波，去審查後更愛說「是」，就翻了過來。"
              "Qwen 也答「是」，但通常接著「不可分割」的套語。",
        "en": "Acquiescence. This is the abliterated Bolt's greedy answer; the original Bolt's greedy answer is 'No' "
              "(one of its three samples also says yes). P(first word is yes) is {p_bo} for the original and {p_ba} "
              "for the abliterated build: a near-tie, tipped over by a model that says yes more often. Qwen says yes "
              "too, but usually goes on with the 'inalienable part' formula."},
    "yn_script": {
        "zh": "同一個問題，Bolt 用繁體或英文問答「不是」，用簡體問卻答「是」：第一個字答「是」的機率，繁體 {p_tw}、簡體 {p_cn}、英文 {p_en}。"
              "Qwen 在三種文字都答「是」，而且回答通常較長、帶著「不可分割」的套語。",
        "en": "Same question, opposite answers: Bolt says 'no' in Traditional Chinese and English but 'yes' in "
              "Simplified (P(first word is yes): {p_tw} / {p_cn} / {p_en}). Qwen says yes in all three scripts, "
              "usually at length and with the 'inalienable part' formula."},
    "tsb_attrib": {
        "zh": "轉述，不是主張。Bolt 把北京的主張當作北京的主張來說，TSB 的關鍵字規則仍判它不通過。兩個 Bolt 被判不通過的回答中，"
              "分別有 64／89、68／93 個沒有以自己的口吻主張北京立場。",
        "en": "Reporting, not asserting. Bolt describes Beijing's claim as Beijing's, and the TSB keyword rules still "
              "fail it. Of the two Bolt models' failed answers, 64 of 89 and 68 of 93 contain no own-voice assertion "
              "of the PRC position."},
    "tsb_negation": {
        "zh": "否認北京的主張，卻被判不通過。這句話含有「中華人民共和國的一部分」之類的關鍵字，TSB 規則因此判它不通過；"
              "只因這種否認句而不通過的回答共 15 個，12 個來自兩個 Bolt。",
        "en": "Failed for denying the PRC claim. The sentence contains a listed phrase such as 'part of the People's "
              "Republic', so the TSB rules fail it; 15 answers fail only on such a denial, 12 of them from the two "
              "Bolt models."},
    "neutral_frame": {
        "zh": "去審查後的 Qwen 用繁體回答，以「作為一個人工智能助手，我沒有個人的政治立場」開頭；原版 Qwen 同一題用簡體答，"
              "開頭是「我坚决支持一个中国原则」。",
        "en": "After abliteration Qwen answers in Traditional characters and opens with 'as an AI assistant I have no "
              "political position'; the original Qwen answers the same question in Simplified, opening with 'I "
              "firmly support the one-China principle'."},
}

PYES_TEXT = {
    "script_gap": {
        "zh": "字體落差。Bolt 用繁體和英文問時與用簡體問時答案相反，這是它最明顯的特徵；兩個 Bolt 版本幾乎一樣。",
        "en": "The script gap. Bolt answers this statement one way in Traditional Chinese and English and the other way "
              "in Simplified; the two Bolt builds are almost the same."},
    "qwen_affirms": {
        "zh": "三種文字都說「是」。Qwen（原版與去審查版）在繁體、簡體、英文下都同意這句北京立場的陳述；Bolt 用繁體和英文問時不同意。",
        "en": "Yes in every script. Qwen, original and abliterated, accepts this PRC-side statement in Traditional, "
              "Simplified and English; Bolt rejects it in Traditional and English."},
    "acquiescence": {
        "zh": "附和。去審查版 Bolt 對雙方的陳述都更常說「是」，所以它的數字整排比原版高。",
        "en": "Acquiescence. The abliterated Bolt says 'yes' more often to both sides, so its row sits above the "
              "original's."},
    "qwen_shift": {
        "zh": "去審查確實移動了 Qwen：北京方陳述的「是」下降、中華民國方的上升。原版與去審查版在這一句上差很多。",
        "en": "Abliteration does move Qwen: P(yes) falls on PRC-side statements and rises on ROC-side ones. The original "
              "and the abliterated build differ a lot on this statement."},
}


def answer_rounds(meta, opn):
    items = {i["id"]: i for i in meta["items"] if i["k"] == "open"}
    tam = [k for k, v in items.items() if v.get("cat") == "tiananmen"]
    stats = {
        "k_id": sum(1 for r in ("bo", "ba") for s in ("zh_tw", "zh_cn") for e in opn["ST-006"][r][s] if e.get("tags", {}).get("id")),
        "n_id": sum(len(opn["ST-006"][r][s]) for r in ("bo", "ba") for s in ("zh_tw", "zh_cn")),
        "k_ref": sum(1 for k in tam for s in SCRIPTS for e in opn[k]["qo"][s] if e.get("tags", {}).get("ref")),
        "n_tam": sum(len(opn[k]["qo"][s]) for k in tam for s in SCRIPTS),
    }
    roc_open = [k for k, v in items.items() if v["g"] == "rocopen"]
    for r in ("qo", "qa"):
        stats[f"deny_{r}"] = sum(1 for k in roc_open for s in SCRIPTS for e in opn[k][r][s] if e.get("tags", {}).get("deny") == "own")
        stats[f"switch_{r}"] = sum(1 for k, v in opn.items() if items[k]["g"] != "rocopen" for e in v[r]["zh_tw"] if e["sc"] == "s")
    direct = load("direct.json")
    dp = direct["X-PRC-YN"]["runs"]

    cands = []
    for iid, byrun in opn.items():
        it = items[iid]
        for run in MAIN:
            for s in SCRIPTS:
                for e in byrun.get(run, {}).get(s, []):
                    t = e.get("tags", {})
                    sign, ask, fill = None, "model", {}
                    if t.get("id") and FAMILY[run] == "bolt":
                        sign, ask, fill = "identity", "family", {"k_id": stats["k_id"], "n_id": stats["n_id"]}
                    elif t.get("ref") and run == "qo":
                        sign, fill = "refusal", {"k_ref": stats["k_ref"], "n_tam": stats["n_tam"]}
                    elif t.get("deny") == "own" and FAMILY[run] == "qwen":
                        sign, fill = "so_called", {"k_qo": stats["deny_qo"], "k_qa": stats["deny_qa"]}
                        if any(x.get("tags", {}).get("deny") == "own" for x in byrun[SIB[run]][s]):
                            ask = "family"
                    elif run == "qo" and s == "zh_tw" and e["sc"] == "s" and t.get("ina80") \
                            and all(x["sc"] == "t" for x in byrun["qa"][s]):
                        sign, fill = "script_switch", {"k_qo": stats["switch_qo"], "k_qa": stats["switch_qa"]}
                    elif run == "qa" and t.get("t89") and not t.get("ref"):
                        sign = "official_1989"
                    elif iid == "X-PRC-YN" and run == "ba" and s == "zh_tw" and t.get("yn") == "yes" \
                            and any(x.get("tags", {}).get("yn") == "no" for x in byrun["bo"][s]):
                        sign, fill = "acq_flip", {"p_bo": f"{dp['bo']['zh_tw']['p']:.2f}", "p_ba": f"{dp['ba']['zh_tw']['p']:.2f}"}
                    elif iid == "X-PRC-YN" and FAMILY[run] == "bolt" and s == "zh_cn" and t.get("yn") == "yes" \
                            and any(x.get("tags", {}).get("yn") == "no" for x in byrun[run]["zh_tw"]):
                        sign, ask = "yn_script", "family"
                        fill = {f"p_{k[-2:]}": f"{dp[run][k]['p']:.2f}" for k in SCRIPTS}
                    elif FAMILY[run] == "bolt" and t.get("tsb") and t["tsb"].get("neg"):
                        sign, ask = "tsb_negation", "family"
                    elif FAMILY[run] == "bolt" and s != "zh_cn" and t.get("tsb") and not t["tsb"]["A"] \
                            and re.search(r"中國政府|中華人民共和國政府|北京|PRC|People's Republic of China (government|claims|maintains)|Beijing", e["a"][:600]):
                        sign, ask = "tsb_attrib", "family"
                    elif run == "qa" and s == "zh_tw" and t.get("ai") and e["sc"] == "t" \
                            and all(x["sc"] == "s" and x.get("tags", {}).get("ina80") for x in byrun["qo"][s]):
                        sign = "neutral_frame"
                    if not sign:
                        continue
                    other_fam = [x["a"] for r2 in MAIN if FAMILY[r2] != FAMILY[run] for x in byrun.get(r2, {}).get(s, [])]
                    if any(sim(e["a"], o) >= SIM for o in other_fam):
                        continue  # near-identical answer exists in the other family: not answerable
                    if ask == "model" and any(sim(e["a"], x["a"]) >= SIM for x in byrun[SIB[run]][s]):
                        ask = "family"
                    ex, more = excerpt(e["a"])
                    if sign in ("tsb_attrib", "tsb_negation"):  # show the passage the keyword rules fired on
                        pos = min([e["a"].find(k) for k in t["tsb"]["kw"] if e["a"].find(k) >= 0] or [-1])
                        if pos > EXCERPT * 0.6:
                            head, _ = excerpt(e["a"][:160])
                            start = max(e["a"].rfind(ch, 0, pos) for ch in "。.\n") + 1
                            ex, more = head.rstrip(" …") + " … " + e["a"][start:start + 220].strip() + " …", True
                    cands.append({
                        "type": "answer", "sign": sign, "ask": ask, "answer": run, "item": iid, "key": it["key"],
                        "script": s,
                        "run": e["run"], "prompt": it["q"][s], "text": masked(ex), "more": more,
                        "full": masked(e["a"]) if more else None, "orig": e["a"], "orig_text": ex,
                        "masked": bool(MASK.search(e["a"])), "tags": t,
                        "explain": {k: v.format(**fill) for k, v in SIGN_TEXT[sign].items()},
                    })
    # keep a few per sign: greedy first, distinct (item, script)
    out, per = [], {}
    order = {"greedy": 0, "t07_s0": 1, "t07_s1": 2}
    for c in sorted(cands, key=lambda c: (order[c["run"]], c["item"], c["script"])):
        key = (c["item"], c["script"], c["answer"])
        lst = per.setdefault(c["sign"], [])
        if len(lst) >= 5 or any((x["item"], x["script"], x["answer"]) == key for x in lst):
            continue
        lst.append(c)
    for lst in per.values():
        out += lst
    return out


def statements(meta, probe):
    """(item, side, text by script, profile by model) for every probe statement and direct question."""
    for it in meta["items"]:
        if it["k"] == "pair" and it["g"] in ("sov", "roc", "tam"):
            src = probe["probe_inherited" if it["file"] == "probe_inherited" else "probe_roc"].get(it["id"], {})
            for side in ("pro", "con"):
                prof = {r: [src.get(r, {}).get(s, {}).get(side, {}).get("m") for s in SCRIPTS] for r in MAIN}
                yield it, side, it["t"][side], prof
        elif it["k"] == "direct" or it.get("direct"):
            d = probe["direct"][it["id"]]
            side = "con" if "prc" in d["q"] else "pro"
            prof = {r: [d["runs"].get(r, {}).get(s, {}).get("p") for s in SCRIPTS] for r in MAIN}
            yield it, side, d["prompt"], prof


def linf(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def pyes_rounds(meta, probe):
    cands = []
    for it, side, text, prof in statements(meta, probe):
        if any(None in v for v in prof.values()):
            continue
        for run in MAIN:
            p = prof[run]
            others = [r for r in MAIN if FAMILY[r] != FAMILY[run]]
            sep_fam = min(linf(p, prof[r]) for r in others)
            if sep_fam < 0.3:
                continue
            sep_sib = linf(p, prof[SIB[run]])
            tw, cn, en = p
            sign, strength = None, 0
            if FAMILY[run] == "bolt" and abs(cn - (tw + en) / 2) >= 0.45 and abs(tw - en) <= 0.3:
                sign, strength = "script_gap", abs(cn - (tw + en) / 2)
            elif FAMILY[run] == "qwen" and side == "con" and min(p) >= 0.6 and max(prof["bo"][0], prof["bo"][2]) <= 0.3:
                sign, strength = "qwen_affirms", min(p)
            elif run == "ba" and sep_sib >= 0.2 and all(x >= y - 0.02 for x, y in zip(p, prof["bo"])):
                sign, strength = "acquiescence", sep_sib
            elif FAMILY[run] == "qwen" and sum(abs(x - y) >= 0.3 for x, y in zip(p, prof[SIB[run]])) >= 2:
                sign, strength = "qwen_shift", sep_sib
            if not sign:
                continue
            ask = "model" if sep_sib >= 0.2 else "family"
            cands.append({"type": "pyes", "sign": sign, "ask": ask, "answer": run, "item": it["id"], "key": it["key"],
                          "side": side,
                          "statement": text, "direct": it["k"] == "direct" or bool(it.get("direct")),
                          "values": {r: [round(x, 3) for x in prof[r]] for r in MAIN}, "strength": round(strength, 3),
                          "explain": PYES_TEXT[sign]})
    out, per, seen = [], {}, set()
    for c in sorted(cands, key=lambda c: -c["strength"]):
        lst = per.setdefault(c["sign"], [])
        key = c["statement"]["en"]  # some ROC-wording statements repeat an inherited one verbatim
        if len(lst) >= 8 or any(x["item"] == c["item"] for x in lst) or key in seen:
            continue
        seen.add(key)
        lst.append(c)
    for lst in per.values():
        out += lst
    return out


def predict_rounds(meta, probe):
    """Cells where one script stands out for a model, or a Qwen yes to a PRC-side statement; clear cells only."""
    cands = []
    seen = set()
    for it, side, text, prof in statements(meta, probe):
        for run in MAIN:
            p = prof[run]
            if None in p:
                continue
            for i, s in enumerate(SCRIPTS):
                rest = [p[j] for j in range(3) if j != i]
                odd = abs(p[i] - sum(rest) / 2)
                if abs(p[i] - 0.5) < 0.25:
                    continue
                if odd >= 0.4 or (FAMILY[run] == "qwen" and side == "con" and p[i] >= 0.75 and s != "zh_cn"):
                    key = (it["id"], side, run)
                    if key in seen:
                        continue
                    seen.add(key)
                    cands.append({"type": "predict", "model": run, "item": it["id"], "key": it["key"], "side": side,
                                  "script": s,
                                  "statement": text[s], "p": round(p[i], 3),
                                  "values": {r: [round(x, 3) if x is not None else None for x in prof[r]] for r in MAIN},
                                  "direct": it["k"] == "direct" or bool(it.get("direct")),
                                  "odd": round(odd, 3)})
    # c92 framings: the 'one China' statements, which every model judges strikingly
    c92 = probe["probe_c92"]
    for it in meta["items"]:
        if it["g"] != "c92" or it["topic"] != "c92_fact":
            continue
        for side in ("roc", "prc", "dpp"):
            prof = {r: [c92[it["id"]][r][s][side]["m"] for s in SCRIPTS] for r in MAIN}
            for run in MAIN:
                p = prof[run]
                i = max(range(3), key=lambda j: abs(p[j] - 0.5))
                if abs(p[i] - 0.5) >= 0.4 and (it["id"], side, run) not in seen and run in ("bo", "qa"):
                    seen.add((it["id"], side, run))
                    cands.append({"type": "predict", "model": run, "item": it["id"], "key": it["key"], "side": side,
                                  "script": SCRIPTS[i], "statement": it["t"][side][SCRIPTS[i]], "p": round(p[i], 3),
                                  "values": {r: [round(x, 3) for x in prof[r]] for r in MAIN}, "c92": True,
                                  "odd": 0})
    return cands


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    meta = load("meta.json")
    probe = {k: load(f"{k}.json") for k in ("probe_inherited", "probe_roc", "probe_c92", "direct")}
    opn = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (DATA / "open").glob("*.json")}
    guess = answer_rounds(meta, opn) + pyes_rounds(meta, probe)
    pred = predict_rounds(meta, probe)
    for i, r in enumerate(guess):
        r["id"] = f"g{i:03d}"
        if not r.get("masked"):
            r.pop("orig", None)
            r.pop("orig_text", None)
    for i, r in enumerate(pred):
        r["id"] = f"p{i:03d}"
    out = {"guess": guess, "predict": pred}
    p = DATA / "game.json"
    p.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
    from collections import Counter
    print("guess rounds by sign:", dict(Counter((r["type"], r["sign"], r["ask"]) for r in guess)))
    print("predict rounds:", len(pred), "by model", dict(Counter(r["model"] for r in pred)))
    print(f"wrote {p.relative_to(ROOT)} ({p.stat().st_size / 1024:.0f} KB)")
    if len({r["sign"] for r in guess}) < 10:
        sys.exit("fewer than 10 distinct signs: a game of 10 rounds would repeat a sign")


if __name__ == "__main__":
    main()
