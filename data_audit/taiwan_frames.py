"""Part B data audit: is the script of a Chinese web document a cue to how it frames Taiwan?

Samples FineWeb-2 (Mandarin, cmn_Hani) by reading random parquet row groups from every shard, classifies each
document's script with analysis/metrics.py `script_of`, keeps documents that mention Taiwan, converts them to
Simplified with OpenCC t2s and counts PRC-framing vs ROC-state-framing markers, split by script and by the URL's
top-level domain.

    python data_audit/taiwan_frames.py fetch      # stream the sample into a local cache (resumable)
    python data_audit/taiwan_frames.py analyze    # markers, intervals, results.json, spot-read samples
    python data_audit/taiwan_frames.py nemotron   # side check on NVIDIA's ungated pretraining sample
    python data_audit/taiwan_frames.py all

The cache (Taiwan documents in full, per-row-group counts) lives outside the repo (--cache).
"""
import argparse
import collections
import gzip
import json
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "analysis"))
from metrics import _s2t, _t2s, script_of  # noqa: E402

REPO = "HuggingFaceFW/fineweb-2"
REVISION = "af9c13333eb981300149d5ca60a8e9d659b276b9"   # main as of 2025-10-27 (checked 2026-10-20)
SUBDIR = "data/cmn_Hani/train"
NEMO_REPO = "nvidia/Nemotron-Pretraining-Dataset-sample"
NEMO_REVISION = "3ad096e6394e487bb4f778733300da85275bb449"
NEMO_FILE = "Nemotron-CC-Translated-Diverse-QA/part_000000.parquet"
SEED = 20261020
DEFAULT_CACHE = HERE.parent.parent / ".cache" / "data_audit"

TAIWAN = re.compile("台湾|台灣|臺灣|臺湾")

# Markers are matched on the t2s-converted (Simplified) text, so one list serves both scripts.
PRC_MARKERS = ["台湾地区", "中国台湾", "台湾省", "台湾当局", "台湾地区领导人", "不可分割", "祖国统一", "统一大业",
               "两岸同胞", "回归祖国", "一个中国原则", "台独分裂", "分裂势力"]
TW_MARKERS = ["中华民国", "台湾总统", "中华民国总统", "总统府", "立法院", "行政院", "主权独立", "台湾政府",
              "国家安全会议"]
# Strict lists: markers the spot-read found to misfire systematically are dropped (see README): 台湾地区 / 台湾省 are
# ordinary Taiwan-voice usage in Traditional text (台灣地區玩家, 財政部臺灣省中區國稅局, old addresses), 不可分割 is
# generic (原子不可分割); 中华民国 / 中华民国总统 / 总统府 are often historical (1912-49) or foreign presidential
# palaces, 主权独立 and 国家安全会议 often refer to other states (Singapore, the US NSC).
PRC_STRICT = [m for m in PRC_MARKERS if m not in ("台湾地区", "台湾省", "不可分割")]
TW_STRICT = [m for m in TW_MARKERS if m not in ("中华民国", "中华民国总统", "总统府", "主权独立", "国家安全会议")]
# PRC media write Taiwan's institutions in scare quotes (台“立法院”, “总统府”) and Taiwan media quote PRC terms
# (拒將我改為「中國台灣」). The *_uq variants only count a marker occurrence not directly preceded by an opening quote.
OPEN_QUOTES = set("“「『\"'‘＂")

TLD_MAIN = ("cn", "tw", "hk")


# ---------------------------------------------------------------------------------------------- script classifier
# script_of() calls OpenCC once per character, which is too slow for ~10^6 documents. The decision for a character
# depends only on the character, so precompute the two sets over the same range script_of scans and count with a
# regex. fetch() re-checks the result against script_of() on a sample of documents and records any disagreement.
_SIMP, _TRAD = [], []
for _cp in range(ord("一"), ord("鿿") + 1):
    _ch = chr(_cp)
    if _s2t.convert(_ch) != _ch:
        _SIMP.append(_ch)
    elif _t2s.convert(_ch) != _ch:
        _TRAD.append(_ch)
_RE_SIMP = re.compile("[" + "".join(_SIMP) + "]")
_RE_TRAD = re.compile("[" + "".join(_TRAD) + "]")


def fast_script(text):
    s, t = len(_RE_SIMP.findall(text)), len(_RE_TRAD.findall(text))
    if s == t == 0:
        return "none", 0, 0
    return ("simplified" if s > t else "traditional"), s, t


def tld_of(url):
    try:
        host = (urlsplit(url).hostname or "").rstrip(".").lower()
    except ValueError:
        return "?"
    return host.rsplit(".", 1)[-1] if "." in host else "?"


def host_of(url):
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def tld_group(tld):
    return tld if tld in TLD_MAIN else "other"


def unquoted(simp, marker):
    """True if at least one occurrence of marker is not directly preceded by an opening quotation mark."""
    pos = simp.find(marker)
    while pos != -1:
        if pos == 0 or simp[pos - 1] not in OPEN_QUOTES:
            return True
        pos = simp.find(marker, pos + 1)
    return False


# ---------------------------------------------------------------------------------------------------------- fetch
def fetch(cache, per_file, workers, max_seconds):
    from huggingface_hub import HfApi, HfFileSystem
    import pyarrow.parquet as pq

    cache.mkdir(parents=True, exist_ok=True)
    files = sorted(x.path for x in HfApi().list_repo_tree(REPO, path_in_repo=SUBDIR, repo_type="dataset",
                                                          revision=REVISION) if x.path.endswith(".parquet"))
    stats_path, docs_path = cache / "rowgroups.jsonl", cache / "taiwan_docs.jsonl.gz"
    done = set()
    if stats_path.exists():
        done = {(r["file"], r["rg"]) for r in map(json.loads, stats_path.open(encoding="utf-8"))}
    print(f"{len(files)} shards at {REVISION[:10]}; {len(done)} row groups already cached", flush=True)
    fs = HfFileSystem()
    lock = threading.Lock()
    check = {"n": 0, "disagree": 0}
    stop = threading.Event()

    def job(path):
        rng = random.Random(f"{SEED}:{path}")
        for attempt in range(4):
            try:
                pf = pq.ParquetFile(fs.open(f"datasets/{REPO}@{REVISION}/{path}", "rb", cache_type="none"))
                n_rg = pf.metadata.num_row_groups
                rgs = sorted(rng.sample(range(n_rg), min(per_file, n_rg)))
                out = []
                for rg in rgs:
                    if (path, rg) in done or stop.is_set():
                        continue
                    d = pf.read_row_group(rg, columns=["id", "text", "url", "dump"]).to_pydict()
                    counts = collections.Counter()      # (script, tld) -> docs scanned
                    tcounts = collections.Counter()     # (script, tld) -> Taiwan docs
                    dumps = collections.Counter(d["dump"])
                    docs = []
                    for i, (did, text, url, dump) in enumerate(zip(d["id"], d["text"], d["url"], d["dump"])):
                        script, s, t = fast_script(text)
                        if i % 50 == 0:              # spot-check the fast classifier against the paper's function
                            agree = script_of(text)[0] == script
                            with lock:
                                check["n"] += 1
                                check["disagree"] += not agree
                        tld = tld_of(url)
                        counts[(script, tld)] += 1
                        if TAIWAN.search(text):
                            tcounts[(script, tld)] += 1
                            docs.append({"id": did, "url": url, "dump": dump, "file": path, "rg": rg,
                                         "script": script, "n_simp": s, "n_trad": t, "text": text})
                    out.append(({"file": path, "rg": rg, "n_rg": n_rg, "n_docs": len(d["id"]),
                                 "dumps": dict(dumps),
                                 "scanned": {f"{k[0]}|{k[1]}": v for k, v in counts.items()},
                                 "taiwan": {f"{k[0]}|{k[1]}": v for k, v in tcounts.items()}}, docs))
                return out
            except Exception as e:   # transient HTTP errors
                print(f"  retry {attempt + 1} {path}: {e!r}"[:200], flush=True)
                time.sleep(5 * (attempt + 1))
        print(f"  GAVE UP {path}", flush=True)
        return []

    t0 = time.time()
    n_new = 0
    ex = ThreadPoolExecutor(workers)
    with stats_path.open("a", encoding="utf-8") as sf, gzip.open(docs_path, "at", encoding="utf-8") as df:
        futs = [ex.submit(job, p) for p in files]
        for k, fut in enumerate(as_completed(futs), 1):
            if time.time() - t0 > max_seconds:      # clean stop; unfinished shards are redone on the next run
                print(f"  time limit reached after {k - 1} shards; stopping", flush=True)
                stop.set()
                break
            for stat, docs in fut.result():
                for doc in docs:                     # docs first, then the row-group line that marks them complete
                    df.write(json.dumps(doc, ensure_ascii=False) + "\n")
                df.flush()
                sf.write(json.dumps(stat, ensure_ascii=False) + "\n")
                sf.flush()
                n_new += 1
            if k % 20 == 0:
                print(f"  {k}/{len(files)} shards, {n_new} new row groups, {time.time() - t0:.0f}s", flush=True)
    ex.shutdown(wait=True, cancel_futures=True)
    (cache / "classifier_check.json").open("a", encoding="utf-8").write(json.dumps(check) + "\n")
    print(f"fetch done: {n_new} new row groups in {time.time() - t0:.0f}s; script check {check}", flush=True)


# -------------------------------------------------------------------------------------------------------- analyze
def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(float(c - h), 5), round(float(c + h), 5)]


def cluster_boot(weights_fn, n_clusters, B=2000, seed=SEED):
    """Resample row groups (the sampling unit) with replacement; weights_fn(w) -> statistic for cluster weights w."""
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(B):
        w = np.bincount(rng.integers(0, n_clusters, n_clusters), minlength=n_clusters).astype(float)
        vals.append(weights_fn(w))
    vals = np.array(vals, dtype=float)
    vals = vals[np.isfinite(vals)]
    if len(vals) == 0:
        return [None, None]
    return [round(float(np.percentile(vals, 2.5)), 5), round(float(np.percentile(vals, 97.5)), 5)]


def snippet(text, marker_raw_pos, width=70):
    a, b = max(0, marker_raw_pos - width), marker_raw_pos + width
    return text[a:b].replace("\n", " ")


def analyze(cache, out_dir, B):
    stats = [json.loads(line) for line in (cache / "rowgroups.jsonl").open(encoding="utf-8")]
    done = {(r["file"], r["rg"]) for r in stats}
    rg_index = {(r["file"], r["rg"]): i for i, r in enumerate(stats)}
    G = len(stats)
    print(f"{G} row groups, {sum(r['n_docs'] for r in stats)} documents scanned", flush=True)

    # per-row-group scanned / Taiwan counts per script and per (script, tld group)
    scripts = ["simplified", "traditional", "none"]
    scanned = {s: np.zeros(G) for s in scripts}
    taiwan_n = {s: np.zeros(G) for s in scripts}
    scanned_tld = collections.Counter()
    taiwan_tld = collections.Counter()
    tld_fine_all = collections.defaultdict(collections.Counter)
    dumps = collections.Counter()
    for i, r in enumerate(stats):
        dumps.update(r["dumps"])
        for key, v in r["scanned"].items():
            s, tld = key.split("|", 1)
            scanned[s][i] += v
            scanned_tld[(s, tld_group(tld))] += v
            tld_fine_all[s][tld] += v
        for key, v in r["taiwan"].items():
            s, tld = key.split("|", 1)
            taiwan_n[s][i] += v
            taiwan_tld[(s, tld_group(tld))] += v

    # Taiwan documents: t2s, then markers
    recs, seen = [], set()
    examples = collections.defaultdict(list)   # (script, list, marker) -> candidate snippets
    t0 = time.time()
    def lines(path):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            try:
                yield from f
            except EOFError:          # gzip member left open by a killed fetch (its row groups are then incomplete)
                return

    for line in lines(cache / "taiwan_docs.jsonl.gz"):
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue                           # torn line from an interrupted fetch
        if (d["file"], d["rg"]) not in done or d["id"] in seen:
            continue
        seen.add(d["id"])
        simp = _t2s.convert(d["text"])
        prc = [m for m in PRC_MARKERS if m in simp]
        tw = [m for m in TW_MARKERS if m in simp]
        tld = tld_of(d["url"])
        rec = {"id": d["id"], "url": d["url"], "host": host_of(d["url"]), "dump": d["dump"],
               "g": rg_index[(d["file"], d["rg"])], "script": d["script"], "tld": tld,
               "tld_group": tld_group(tld), "prc": prc, "tw": tw, "len": len(d["text"]),
               "prc_uq": [m for m in prc if unquoted(simp, m)], "tw_uq": [m for m in tw if unquoted(simp, m)]}
        recs.append(rec)
        for lst, hits in (("prc", prc), ("tw", tw)):
            for m in hits:
                pos = simp.find(m)         # t2s maps character for character here, so pos indexes the original
                examples[(d["script"], lst, m)].append(
                    {"id": d["id"], "url": d["url"], "snippet": snippet(d["text"], pos)})
        if len(recs) % 5000 == 0:
            print(f"  {len(recs)} Taiwan docs converted, {time.time() - t0:.0f}s", flush=True)
    print(f"{len(recs)} Taiwan docs analysed in {time.time() - t0:.0f}s", flush=True)

    g = np.array([r["g"] for r in recs])
    sc = np.array([r["script"] for r in recs])
    tg = np.array([r["tld_group"] for r in recs])
    flags = {
        "prc": np.array([bool(r["prc"]) for r in recs]),
        "tw": np.array([bool(r["tw"]) for r in recs]),
        "prc_strict": np.array([any(m in PRC_STRICT for m in r["prc"]) for r in recs]),
        "tw_strict": np.array([any(m in TW_STRICT for m in r["tw"]) for r in recs]),
        "prc_strict_uq": np.array([any(m in PRC_STRICT for m in r["prc_uq"]) for r in recs]),
        "tw_strict_uq": np.array([any(m in TW_STRICT for m in r["tw_uq"]) for r in recs]),
    }

    def rate_block(mask):
        """Rates of each flag among docs in mask, with Wilson and row-group cluster-bootstrap intervals."""
        n = int(mask.sum())
        out = {"n": n}
        if n == 0:
            return out
        gm = g[mask]
        for name, fl in flags.items():
            k = int(fl[mask].sum())
            x = fl[mask].astype(float)
            out[name] = {"k": k, "rate": round(k / n, 5), "wilson95": wilson(k, n),
                         "boot95": cluster_boot(lambda w: (w[gm] * x).sum() / w[gm].sum(), G, B)}
        for a, b in (("prc", "tw"), ("prc_strict", "tw_strict"), ("prc_strict_uq", "tw_strict_uq")):
            xa, xb = flags[a][mask].astype(float), flags[b][mask].astype(float)
            ka, kb = xa.sum(), xb.sum()
            out[f"ratio_{a}_over_{b}"] = {
                "ratio": round(float(ka / kb), 4) if kb else None,
                "boot95": cluster_boot(lambda w: (w[gm] * xa).sum() / max((w[gm] * xb).sum(), 1e-9), G, B)}
        both = flags["prc"][mask] & flags["tw"][mask]
        out["overlap"] = {"prc_only": int((flags["prc"][mask] & ~flags["tw"][mask]).sum()),
                          "tw_only": int((flags["tw"][mask] & ~flags["prc"][mask]).sum()),
                          "both": int(both.sum()),
                          "neither": int((~flags["prc"][mask] & ~flags["tw"][mask]).sum())}
        return out

    res = {"dataset": {"repo": REPO, "config": "cmn_Hani", "split": "train", "revision": REVISION,
                       "shards": len({r["file"] for r in stats}), "row_groups": G,
                       "docs_scanned": int(sum(r["n_docs"] for r in stats)),
                       "dumps_in_sample": len(dumps), "dump_counts": dict(sorted(dumps.items()))},
           "markers": {"prc": PRC_MARKERS, "tw": TW_MARKERS, "prc_strict": PRC_STRICT, "tw_strict": TW_STRICT,
                       "taiwan_filter": TAIWAN.pattern},
           "bootstrap": {"unit": "parquet row group (1000 docs)", "B": B, "seed": SEED}}
    chk = cache / "classifier_check.json"
    if chk.exists():
        rows = [json.loads(x) for x in chk.open(encoding="utf-8")]
        res["classifier_check"] = {"docs_checked": sum(r["n"] for r in rows),
                                   "disagreements": sum(r["disagree"] for r in rows)}

    # 1. per script: Taiwan-mention rate and framing rates
    per_script = {}
    for s in scripts:
        n_scan, n_tw = scanned[s].sum(), taiwan_n[s].sum()
        block = {"docs_scanned": int(n_scan), "taiwan_docs": int(n_tw),
                 "taiwan_rate": round(float(n_tw / n_scan), 5) if n_scan else None,
                 "taiwan_rate_wilson95": wilson(int(n_tw), int(n_scan)),
                 "taiwan_rate_boot95": cluster_boot(lambda w: (w * taiwan_n[s]).sum() / max((w * scanned[s]).sum(),
                                                                                            1e-9), G, B),
                 "share_of_all_docs": round(float(n_scan / sum(scanned[x].sum() for x in scripts)), 5)}
        block.update(rate_block(sc == s))
        # TLD shares, all docs and Taiwan docs
        tot_all = sum(scanned_tld[(s, t)] for t in TLD_MAIN + ("other",))
        tot_tw = sum(taiwan_tld[(s, t)] for t in TLD_MAIN + ("other",))
        block["tld_share_all_docs"] = {t: round(scanned_tld[(s, t)] / tot_all, 5) if tot_all else None
                                       for t in TLD_MAIN + ("other",)}
        block["tld_share_taiwan_docs"] = {t: round(taiwan_tld[(s, t)] / tot_tw, 5) if tot_tw else None
                                          for t in TLD_MAIN + ("other",)}
        block["tld_top_all_docs"] = dict(tld_fine_all[s].most_common(12))
        per_script[s] = block
    res["per_script"] = per_script

    # cross-script ratios (Simplified rate / Traditional rate) with bootstrap
    cross = {}
    for name, fl in flags.items():
        ms, mt = sc == "simplified", sc == "traditional"
        xs, xt = fl[ms].astype(float), fl[mt].astype(float)
        gs, gt = g[ms], g[mt]
        rs, rt = xs.mean(), xt.mean()
        cross[name] = {"simplified_over_traditional": round(float(rs / rt), 4) if rt else None,
                       "boot95": cluster_boot(lambda w: ((w[gs] * xs).sum() / w[gs].sum())
                                              / max((w[gt] * xt).sum() / w[gt].sum(), 1e-9), G, B)}
    res["cross_script_ratio"] = cross

    # 2. script x TLD cells
    cells = {}
    for s in ("simplified", "traditional"):
        for t in TLD_MAIN + ("other",):
            m = (sc == s) & (tg == t)
            cells[f"{s}|{t}"] = rate_block(m) if m.sum() >= 30 else {"n": int(m.sum()), "note": "n < 30"}
    res["script_x_tld"] = cells

    # script effect holding TLD fixed: Mantel-Haenszel odds ratio (Simplified vs Traditional) over the TLD strata
    def mh_or(fl, w=None):
        num = den = 0.0
        for t in TLD_MAIN + ("other",):
            ms, mt = (sc == "simplified") & (tg == t), (sc == "traditional") & (tg == t)
            ws = w[g[ms]] if w is not None else np.ones(ms.sum())
            wt = w[g[mt]] if w is not None else np.ones(mt.sum())
            a, b = (ws * fl[ms]).sum(), (ws * ~fl[ms]).sum()        # simplified: marker / no marker
            c, d = (wt * fl[mt]).sum(), (wt * ~fl[mt]).sum()        # traditional
            n = a + b + c + d
            if n:
                num += a * d / n
                den += b * c / n
        return num / den if den else float("nan")

    res["mantel_haenszel_or_simplified_vs_traditional_by_tld"] = {
        name: {"or": round(float(mh_or(fl)), 4), "boot95": cluster_boot(lambda w: mh_or(fl, w), G, max(200, B // 4))}
        for name, fl in flags.items()}

    # 3. per-marker document counts by script (and by script x tld group)
    pm = {}
    for s in ("simplified", "traditional"):
        m = sc == s
        n = int(m.sum())
        rs = [r for r in recs if r["script"] == s]
        pm[s] = {"n_taiwan_docs": n,
                 "prc": {mk: sum(mk in r["prc"] for r in rs) for mk in PRC_MARKERS},
                 "tw": {mk: sum(mk in r["tw"] for r in rs) for mk in TW_MARKERS},
                 "prc_unquoted": {mk: sum(mk in r["prc_uq"] for r in rs) for mk in PRC_MARKERS},
                 "tw_unquoted": {mk: sum(mk in r["tw_uq"] for r in rs) for mk in TW_MARKERS}}
    res["per_marker"] = pm

    # 4. hosts: which sites carry the framed documents
    hosts = {}
    for s in ("simplified", "traditional"):
        for name in ("prc", "tw"):
            c = collections.Counter(r["host"] for r in recs if r["script"] == s and r[name])
            hosts[f"{s}|{name}"] = c.most_common(15)
    res["top_hosts_framed_docs"] = hosts
    big5 = [r for r in recs if r["script"] == "traditional" and r["host"].startswith("big5.")]
    res["traditional_big5_mirror_docs"] = {"n": len(big5), "prc": sum(bool(r["prc"]) for r in big5),
                                           "tw": sum(bool(r["tw"]) for r in big5),
                                           "hosts": collections.Counter(r["host"] for r in big5).most_common(10)}

    # spot-read samples: 10 random documents per script x list (first-hit marker), plus 3 per marker
    rng = random.Random(SEED)
    spot = []
    for s in ("simplified", "traditional"):
        for lst, markers in (("prc", PRC_MARKERS), ("tw", TW_MARKERS)):
            pool = [r for r in recs if r["script"] == s and r[lst]]
            for r in rng.sample(pool, min(10, len(pool))):
                m = r[lst][0]
                ex = next(e for e in examples[(s, lst, m)] if e["id"] == r["id"])
                spot.append({"kind": "random_doc", "script": s, "list": lst, "marker": m, "url": r["url"],
                             "all_markers": r[lst], "snippet": ex["snippet"]})
            for m in markers:
                pool = examples[(s, lst, m)]
                for e in rng.sample(pool, min(3, len(pool))):
                    spot.append({"kind": "per_marker", "script": s, "list": lst, "marker": m, **e})
    with (out_dir / "spot_read_samples.jsonl").open("w", encoding="utf-8") as f:
        for x in spot:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")

    # compact per-document table (no text) for re-analysis
    with gzip.open(out_dir / "taiwan_docs_meta.jsonl.gz", "wt", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps({k: r[k] for k in ("id", "url", "dump", "script", "tld", "prc", "tw", "prc_uq", "tw_uq", "len")},
                               ensure_ascii=False) + "\n")

    p = out_dir / "results.json"
    if p.exists():                               # keep the separately computed side check across re-analyses
        old = json.loads(p.read_text(encoding="utf-8"))
        if "nemotron_side_check" in old:
            res["nemotron_side_check"] = old["nemotron_side_check"]
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print_summary(res)


def fmt(block, key):
    b = block.get(key)
    if not b:
        return "-"
    lo, hi = b["boot95"]
    return f"{100 * b['rate']:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]"


def print_summary(res):
    for s, b in res["per_script"].items():
        if not b["docs_scanned"]:
            print(f"{s:12s} scanned 0")
            continue
        print(f"{s:12s} scanned {b['docs_scanned']:>7d}  Taiwan {b['taiwan_docs']:>6d} "
              f"({100 * b['taiwan_rate']:.2f}%)  PRC {fmt(b, 'prc')}  TW {fmt(b, 'tw')}  "
              f"PRCs {fmt(b, 'prc_strict')}  TWs {fmt(b, 'tw_strict')}  PRCsu {fmt(b, 'prc_strict_uq')}  "
              f"TWsu {fmt(b, 'tw_strict_uq')}  tld(Taiwan docs) {b['tld_share_taiwan_docs']}")
    for k, b in res["script_x_tld"].items():
        print(f"  {k:20s} n={b['n']:>6d}  PRC {fmt(b, 'prc')}  TW {fmt(b, 'tw')}  "
              f"PRCs {fmt(b, 'prc_strict')}  TWs {fmt(b, 'tw_strict')}  PRCsu {fmt(b, 'prc_strict_uq')}  "
              f"TWsu {fmt(b, 'tw_strict_uq')}")
    print("MH OR simplified vs traditional, by TLD:", res["mantel_haenszel_or_simplified_vs_traditional_by_tld"])


# ------------------------------------------------------------------------------------------------------- nemotron
def nemotron(out_dir):
    """NVIDIA's only ungated pretraining sample with Chinese text: machine-translated synthetic QA, not web text."""
    from huggingface_hub import HfFileSystem
    import pyarrow.parquet as pq
    fs = HfFileSystem()
    t = pq.read_table(fs.open(f"datasets/{NEMO_REPO}@{NEMO_REVISION}/{NEMO_FILE}", "rb"),
                      columns=["text", "language"]).to_pydict()
    zh = [x for x, lang in zip(t["text"], t["language"]) if lang == "cn"]
    scripts = collections.Counter(script_of(x)[0] for x in zh)
    tw = [x for x in zh if TAIWAN.search(x)]
    out = {"repo": NEMO_REPO, "revision": NEMO_REVISION, "file": NEMO_FILE, "rows": len(t["text"]),
           "chinese_rows(language=cn)": len(zh), "scripts": dict(scripts), "taiwan_docs": len(tw),
           "taiwan_docs_prc": sum(any(m in _t2s.convert(x) for m in PRC_MARKERS) for x in tw),
           "taiwan_docs_tw": sum(any(m in _t2s.convert(x) for m in TW_MARKERS) for x in tw)}
    p = out_dir / "results.json"
    res = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    res["nemotron_side_check"] = out
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "analyze", "nemotron", "all"])
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--per-file", type=int, default=2, help="random row groups (1000 docs each) per parquet shard")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--max-seconds", type=float, default=float("inf"), help="stop fetching cleanly after this")
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args()
    if a.cmd in ("fetch", "all"):
        fetch(a.cache, a.per_file, a.workers, a.max_seconds)
    if a.cmd in ("analyze", "all"):
        analyze(a.cache, HERE, a.boot)
    if a.cmd in ("nemotron", "all"):
        nemotron(HERE)
