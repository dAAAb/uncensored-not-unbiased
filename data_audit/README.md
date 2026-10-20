# Data audit (part B): script as a cue to how web text frames Taiwan

Question: in open web pretraining text, does the script of a Chinese document (Simplified vs Traditional) predict
whether it talks about Taiwan in PRC terms or in Taiwan-state terms? If it does, a model can learn "Simplified ->
PRC framing" from pretraining data alone, which would explain script-dependent answers.

Run of 20 October 2026. Code: `taiwan_frames.py`; numbers: `results.json`.

## Data

- **FineWeb-2**, `HuggingFaceFW/fineweb-2`, config `cmn_Hani` (Mandarin, Han script), split `train`, revision
  `af9c13333eb981300149d5ca60a8e9d659b276b9` (main, last modified 2025-10-27). 370 parquet shards, 1.62 TB.
- Sample: 2 random row groups (1,000 documents each) from **every one of the 370 shards**, chosen with a seeded RNG
  (seed 20261020) per shard: 740 row groups, **740,000 documents**, 79 Common Crawl dumps (CC-MAIN-2013-20 to
  CC-MAIN-2024-18). Only the `id`, `text`, `url` and `dump` columns were read, via HTTP range requests (about 2 GB).
  FineWeb-2 is already deduplicated (MinHash) and quality-filtered; no further filtering was applied.
- **NVIDIA** (checked via `https://huggingface.co/api/datasets?author=nvidia&search=...` for Nemotron-CC,
  Nemotron-Pretraining, multilingual, Nemotron): the web-text corpora that would contain Chinese, `nvidia/Nemotron-CC-v2`
  and `nvidia/Nemotron-CC-v2.1`, are **gated (manual approval)**, so not used. Ungated sets are English
  (`Nemotron-ClimbMix`, `Nemotron-Pretraining-Specialized-v1.x`, ...), code, math or SFT/RL data. The only ungated
  Chinese pretraining text found is `nvidia/Nemotron-Pretraining-Dataset-sample` (revision
  `3ad096e6394e487bb4f778733300da85275bb449`), subset `Nemotron-CC-Translated-Diverse-QA`: 1,031 Chinese rows
  (`language=cn`), machine-translated synthetic QA, not web text. All 1,030 classifiable rows are Simplified; none
  mentions Taiwan. Recorded under `nemotron_side_check` in `results.json`; no framing analysis is possible.

## Method

1. **Script**: `script_of` from `analysis/metrics.py` (counts characters that change under OpenCC s2t vs t2s). For
   speed the script precomputes the same per-character decision over the range `script_of` scans and counts with a
   regex; it is checked against `script_of` itself on every 50th document: 14,800 checked, **0 disagreements**.
   No document came out as `none`.
2. **Taiwan filter** on the raw text: `台湾|台灣|臺灣|臺湾`.
3. Each Taiwan document is converted to Simplified with OpenCC `t2s`, then matched against two marker lists
   (substring, document-level: does it contain at least one marker).
4. **TLD**: last label of the URL host, grouped `.cn` / `.tw` / `.hk` / other (other is mostly `.com`, `.net`).
5. **Intervals**: 95% cluster bootstrap over row groups (the sampling unit; 2,000 draws), shown below; Wilson
   intervals are also in `results.json` and are slightly narrower. Script effect net of TLD: Mantel-Haenszel odds
   ratio over the four TLD strata (bootstrap 500 draws).

### Markers (matched after t2s)

| list | markers |
|---|---|
| PRC framing | 台湾地区, 中国台湾, 台湾省, 台湾当局, 台湾地区领导人, 不可分割, 祖国统一, 统一大业, 两岸同胞, 回归祖国, 一个中国原则, 台独分裂, 分裂势力 |
| Taiwan-state framing | 中华民国, 台湾总统, 中华民国总统, 总统府, 立法院, 行政院, 主权独立, 台湾政府, 国家安全会议 |
| PRC strict | PRC list without 台湾地区, 台湾省, 不可分割 |
| Taiwan-state strict | 台湾总统, 立法院, 行政院, 台湾政府 |

Strict lists drop the markers the spot-read showed misfiring systematically (below). The **unquoted** variant
additionally counts a marker only if at least one occurrence is not directly preceded by an opening quotation mark
(“ 「 『 " ' ‘ ＂), because PRC outlets write Taiwan's institutions in scare quotes (台“立法院”) and Taiwanese outlets
quote PRC terms (拒將我改為「中國台灣」).

## Results

Sample: 626,143 Simplified documents (84.6%) and 113,857 Traditional (15.4%); **35,050 Simplified and 17,781
Traditional documents mention Taiwan**.

| | Simplified | Traditional | S / T |
|---|---|---|---|
| Taiwan-mention rate | 5.60% [5.32, 5.90] | 15.62% [15.06, 16.27] | |
| P(PRC marker \| Taiwan doc) | **14.5%** [13.7, 15.2] | 3.9% [3.6, 4.2] | 3.69 [3.37, 4.05] |
| P(Taiwan-state marker \| Taiwan doc) | 4.5% [4.2, 4.7] | **11.4%** [10.8, 11.9] | 0.39 [0.37, 0.42] |
| PRC / Taiwan-state, within script | 3.22 [3.00, 3.46] | 0.34 [0.32, 0.38] | |
| PRC strict | 9.9% [9.3, 10.5] | 1.7% [1.5, 1.9] | 5.85 [5.14, 6.69] |
| Taiwan-state strict | 2.8% [2.6, 2.9] | 7.4% [6.9, 7.8] | 0.37 [0.34, 0.41] |
| PRC strict, unquoted | 9.7% [9.1, 10.3] | 1.5% [1.3, 1.7] | 6.37 [5.57, 7.35] |
| Taiwan-state strict, unquoted | 1.2% [1.1, 1.3] | 7.1% [6.7, 7.6] | 0.17 [0.15, 0.19] |
| PRC / Taiwan-state, strict unquoted | 8.06 [6.96, 9.37] | 0.21 [0.19, 0.24] | |

Both markers in one document: 406 Simplified (1.2%), 158 Traditional (0.9%).

**TLD shares** (all documents / Taiwan documents):

| | .cn | .tw | .hk | other |
|---|---|---|---|---|
| Simplified | 21.6% / 15.8% | 0.3% / 0.3% | 0.1% / 0.05% | 78.0% / 83.8% |
| Traditional | 4.1% / 1.0% | 16.7% / 29.8% | 3.0% / 1.0% | 76.2% / 68.2% |

**Script × TLD** (Taiwan documents; PRC / Taiwan-state rate, full lists, then strict unquoted):

| cell | n | PRC | Taiwan-state | PRC strict-uq | Taiwan-state strict-uq |
|---|---|---|---|---|---|
| Simplified .cn | 5,530 | 17.2% [16.1, 18.3] | 3.3% [2.8, 3.9] | 11.7% | 0.6% |
| Simplified .tw | 117 | 8.5% [3.8, 13.8] | 7.7% [3.1, 12.8] | 3.4% | 5.1% |
| Simplified other | 29,386 | 13.9% [13.1, 14.8] | 4.7% [4.4, 5.0] | 9.3% | 1.3% |
| Traditional .cn | 179 | 27.4% [21.0, 33.7] | 5.6% [2.5, 9.3] | 20.1% | 0.6% |
| Traditional .tw | 5,302 | 3.3% [2.8, 3.8] | 12.4% [11.5, 13.4] | 0.5% | 8.3% |
| Traditional .hk | 177 | 6.8% [3.5, 10.3] | 4.5% [1.7, 7.9] | 4.0% | 1.7% |
| Traditional other | 12,123 | 3.8% [3.5, 4.2] | 11.1% [10.4, 11.8] | 1.6% | 6.8% |

(Simplified .hk: n = 17, not reported.) Mantel-Haenszel odds ratio, Simplified vs Traditional, within TLD:
PRC marker **3.65** [3.29, 4.11], Taiwan-state marker **0.40** [0.37, 0.44]; strict unquoted 5.08 [4.40, 5.91] and
0.19 [0.16, 0.22].

Reading: most documents in both scripts sit on generic TLDs (.com etc.), and within that stratum the script alone
separates the framings almost as sharply as overall (13.9% vs 3.8% PRC; 4.7% vs 11.1% Taiwan-state). The script is
therefore a cue to framing beyond what the site's country domain says. The TLD carries information too: the small
group of Traditional pages on .cn is the most PRC-framed cell of all (it includes Big5 mirrors of PRC outlets,
big5.taiwan.cn, big5.china.com.cn, big5.news.cn: 32 of 179, the rest mostly .cn spam and commercial sites), and
Simplified pages on .tw are about balanced. Across all TLDs, 68 Traditional Taiwan documents come from `big5.*`
mirror hosts, both PRC state media (big5.taiwan.cn, big5.huaxia.com, big5.gwytb.gov.cn) and Falun Gong sites
(big5.minghui.org, big5.zhengjian.org). So the script
is a proxy for where the text comes from, not a property of the characters themselves.

## Spot-read (`spot_read_samples.jsonl`: 10 random matched documents per script × list, plus 3 per marker)

- PRC markers in Simplified documents are PRC voice in almost every case read (国台办/外交部 statements, 中国台湾网
  copy, 台湾地区领导人选举, 台湾省 in weather reports). Many matches sit in SEO spam pages that splice in sentences
  from PRC news. They are still pretraining text.
- **Misfires dropped in the strict lists**: 台湾地区 is ordinary Taiwan-voice usage in Traditional text (台灣地區玩家,
  台灣地區大型企業排名, the ROC 臺灣地區與大陸地區人民關係條例); 台湾省 appears in ROC agency names and old addresses
  (財政部臺灣省中區國稅局, 台灣省桃園市, 臺灣省立…中學); 不可分割 is generic (原子不可分割). 中华民国 and 中华民国总统 are
  often historical (1912–49) in Simplified text; 总统府 is often a foreign presidential palace (Peru, Iraq) or historical;
  主权独立 refers to other states (Singapore); 国家安全会议 is usually the US NSC.
- **Scare quotes**: in Simplified Taiwan documents 72% of documents with 立法院 have it only in quotation marks
  (485 → 137 unquoted), 53% for 行政院, 30% for 总统府: these are PRC-voice reports, which is why the unquoted
  Taiwan-state rate for Simplified falls from 2.8% to 1.2%. Traditional documents barely change (7.4% → 7.1%).
- Remaining known noise: 行政院 in Simplified still catches pre-1949 and Wang Jingwei-regime history (it inflates
  the Simplified Taiwan-state rate, i.e. works against the hypothesis); Traditional 中国台湾 / 一个中国原则 / 两岸同胞
  hits include Taiwanese or Hong Kong media quoting PRC officials (reported speech is not fully removed by the quote
  filter); some Traditional PRC-voice text is PRC content republished in Traditional characters.

## Caveats

- Markers are a crude, lexical proxy for framing: most Taiwan documents (82% Simplified, 86% Traditional) contain
  neither list. The rates describe the presence of overtly political vocabulary, not stance.
- "Mentions Taiwan" includes trivial uses (product origin, place names, spam keyword lists).
- The unit of sampling is a row group; documents in a row group mostly come from one dump, hence the cluster
  bootstrap.
  Shards were sampled uniformly, not weighted by size (row groups within a shard are uniform).
- The TLD is a weak proxy for origin: most Chinese web text, PRC or not, sits on .com.
- Only FineWeb-2 was analysed; NVIDIA's Chinese web text (Nemotron-CC-v2/v2.1) is gated and not checked.

## Reproduce

```
python data_audit/taiwan_frames.py fetch      # about 3 min, ~2 GB over HTTP; cache in ../.cache/data_audit (resumable)
python data_audit/taiwan_frames.py analyze    # about 4 min
python data_audit/taiwan_frames.py nemotron
```

Files: `results.json` (all numbers, per-marker counts with and without the quote filter, top hosts of framed
documents, dump counts), `spot_read_samples.jsonl` (snippets read for the checks above), `taiwan_docs_meta.jsonl.gz`
(one line per Taiwan document: id, url, dump, script, TLD, markers hit; no text).
