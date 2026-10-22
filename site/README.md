# Project page: build scripts

The page is static: `docs/index.html`, `docs/assets/` (CSS, vanilla JS, no dependencies) and `docs/data/*.json`.
GitHub Pages can serve `docs/` from `main` as is; no build server is needed. The JSON is generated from the
repository's own files by two scripts, which only read `items/`, `results/`, `analysis/`, `data_audit/` and
`configs/`:

```bash
python site/build_data.py   # docs/data/meta.json, probe_*.json, direct.json, summary.json, open/*.json; checks the quoted numbers
python site/build_game.py   # docs/data/game.json (reads the files written by build_data.py)
python -m http.server 8000 --directory docs   # then open http://localhost:8000/
```

`build_data.py` imports `analysis/metrics.py`, `analysis/roc.py`, `analysis/tsb_rubric.py`, `analysis/analyze.py`
and `run/probe.py` (for the prompt templates), so it needs the analysis requirements (`opencc`). It writes no
`__pycache__`. At the end it recomputes every number quoted on the page (highlights, method, "more results") from the
data and exits with code 1 if any differs from the text; update the text and the check together.

Things to change in one place:

- links, arXiv id and the teaser video URLs: `docs/assets/js/config.js` (`arxiv.id` empty = "coming soon"; set it
  and the button and the BibTeX pick it up);
- UI strings in both languages: `docs/assets/js/i18n.js`; long text is in `docs/index.html` as
  `data-lang="zh"` / `data-lang="en"` pairs.

Language: Traditional Chinese by default; `?lang=en` or the toggle switches and the choice is kept in
`localStorage` (`unu-lang`). Deep links: `#q=<key>`, optionally `&m=<run>` (model), `&s=zh_tw|zh_cn|en`,
`&v=models` (compare models in an open question), `&x=1` (show the intervention runs).

## Runs (short ids)

| id | results label | probe |
|---|---|---|
| `bo` | `bolt74b-24gb-original` | logprob |
| `ba` | `bolt74b-24gb-abliterated-boldingbuilds` | logprob |
| `qo` | `qwen38fn-iq2xs-original` | 20 samples |
| `qa` | `qwen38fn-iq2xs-abliterated-sc117` | 20 samples |
| `qs` | `qwen38fn-iq2xs-abliterated-sc117+sysprompt` (four-sentence system prompt) | 20 samples |
| `sb` | `bolt74b-24gb-abliterated-boldingbuilds+steerbase-a3` (steering server, no vector) | logprob |
| `sv` | `bolt74b-24gb-abliterated-boldingbuilds+a3-L45-s2` (stance vector, layer 45, ×2) | logprob |
| `sn` | `bolt74b-24gb-abliterated-boldingbuilds+a3-L45-s-4` (negated stance vector, layer 45, ×−4; `a3_probe_logprob.jsonl` only) | logprob |

The stance vector is that of version 2 of the paper (ROC wording, split in `items/roc_steer_items.json`). The other
steering runs (`+a1roc-*`, `+a1rocmean-*`, `+a3-*` at other layers/scales; version 1: `+steerbase`, `+a1-*`, `+a2-*`)
and Bolt's 20-sample probe are not on the page. The open answers of `sb` are left out (not scored by
`analysis/tsb_rubric.py`).

## Files and fields

All probabilities are rounded to 3 decimals (summary values to 4); scripts are `zh_tw`, `zh_cn`, `en`.

### `meta.json`

- `models[]`: `id`, `family` (`bolt`/`qwen`), `version` (`original`/`abliterated`), `main` (one of the four),
  `base` (the run an intervention is compared with), `name` / `short` (`zh`, `en` display names), `label`, `mode`.
- `groups[]`: `id`, `name` — `sov` inherited sovereignty pairs, `roc` ROC-wording pairs (incl. R-TAM-TOLL, R-009b and
  R-014c), `fresh` the stance vector's fresh test pairs F-01…F-08 (steering runs only), `tam` 1989 pairs and open questions, `ctl` controls, `open` open questions, `rocopen` ROC-wording open questions,
  `direct` direct yes-first questions, `c92` 1992-Consensus framings.
- `items[]`: `key` (unique, used in `#q=`), `id` (item id in the repository), `g` (group), `k` (`pair`, `triple`,
  `open`, `direct`), `src` (item source), `file` (data file without `.json`), and
  - pairs: `t.pro` / `t.con` = statement per script (`pro` = ROC side, `con` = PRC side), `topic`, `mir` (the inherited
    pair an ROC-wording pair restates), `mirBy` (the reverse);
  - triples (C92): `t.roc` / `t.prc` / `t.dpp` (ROC government formula under the KMT / PRC formula / DPP formula),
    `theme` (`zh`, `en`), `topic` (`c92_fact` or `c92_norm`);
  - open questions: `q` (prompt per script), `cat`, `direct` (the direct question that has exactly this prompt, if
    any), `mir` / `mirBy`;
  - direct questions: `q` (prompt per script), `qid` (question id in `*yesno_first_token.jsonl`), `mir` / `mirBy`.
  Open questions whose id is also a pair id (S1-001…S1-010, ST-001, ST-002, ST-003, ST-006) get the key `Q-<id>`.
- `phrasings`: the three probe templates per script (`{s}` = statement), exactly as `run/probe.py` builds them (the
  `zh_cn` ones are its OpenCC t2s conversion). Prompt = template with `{s}` replaced by the statement in that script.
- `systemPrompt`: `configs/system_prompt_roc.txt`; `c92Note`: the note of `items/c92_items.json`.

### `probe_inherited.json`, `probe_roc.json`, `probe_c92.json`

`{item id: {run: {script: cell}}}` from `results/<label>/probe_<mode>.jsonl`, `roc_probe_*` + `roc9b_probe_*`, and
`c92_probe_*`; for the steering runs also `a3_probe_*` (`items/roc_steer_probe_items.jsonl`: R-009b, R-014c and the fresh
pairs go to `probe_roc.json`, 1989 and controls to `probe_inherited.json`; values shared with the other files are checked
to agree, and fill in where a run lacks them, as for `sn`). A cell has one entry per side (`pro`/`con`, or `roc`/`prc`/`dpp`):

| field | meaning |
|---|---|
| `p` | P(yes) for phrasings 0, 1, 2 (`null` if no yes/no answer) |
| `m` | mean of `p` (the per-statement value used in Index S) |
| `mass` | logprob runs: probability that fell on a yes or no answer, per phrasing |
| `c` | sample runs: `[yes, no, other]` counts of the 20 samples, per phrasing |

and, for pairs, `d` = `pro.m − con.m`, the pair score (+1 ROC position, −1 PRC position).

### `direct.json`

`{item key: {q, prompt: {script}, runs: {run: {script: {p, mass, c?, src}}}}}`: probability that the first answer
token is yes for the yes-first questions. Bolt, inherited questions: `yesno_first_token.jsonl` (plain server,
`src: "plain"`, paper Table 4); all ROC-wording questions and Qwen's inherited ones: `roc_yesno_first_token.jsonl`
(`src: "roc"`); the steering runs: both question sets from their `yesno_first_token.jsonl` (`src: "steer"`, the
stance-vector table). `prc_part_1`, `roc_sovereign` and `roc_prc_part` have
the same prompt as the open questions X-PRC-YN, X-ROC-YN and R-OPEN-YN and are shown inside them (checked at build).

### `open/<id>.json`

`{run: {script: [answer, answer, answer]}}` from `generate.jsonl` / `roc_generate.jsonl` (runs `bo`, `ba`, `qo`, `qa`;
`sv` for the ROC-wording questions). Each answer: `run` (`greedy`, `t07_s0`, `t07_s1`), `a` (text, verbatim), `sc`
(script of the answer by `metrics.script_of`: `s` Simplified, `t` Traditional, `n` no script-specific characters),
and `tags`, present only when they fire:

| tag | computed by | meaning |
|---|---|---|
| `ref` | `metrics.refusal` | refusal phrase in the first 300 characters |
| `id` | `metrics.identity_deflection` | "I am a language model trained by …" in the first 200 characters |
| `ai` | `metrics.neutral_ai_frame` | "As an AI …" frame in the first 200 characters |
| `ina`, `ina80` | regex | "inalienable part": `不可分割的一部分`/inalienable/integral part (inherited wording, as counted in paper §4.3) or `roc.INALIENABLE` (ROC wording, Table tab:rocfree); `ina80` = within the first 80 characters |
| `t89` | `metrics.tiananmen_terms` | 1989 items only: PRC official names used (quoted or adopted) |
| `c241`, `exag` | `metrics.mentions_official_toll`, `metrics.downplays_toll` | 1989 items only |
| `deny` | `analysis/roc_denial_coding.json` | hand-coded: `own` = the model itself calls the ROC "so-called" / non-existent; `attr` = reports it as the PRC's view |
| `yn` | `roc.yes_no` | `*-YN` items: first word yes / no / other |
| `tsb` | `tsb_rubric.score_all` + `tsb_rubric_coding.json` | answer failed by TSB (`s1`) or TSB Pro (`s2`) keyword rules; `kw` = failing keywords; `A` = a failing trigger was coded as the PRC position in the model's own voice; `neg` = every failing trigger was coded as a denial of the PRC claim |
| `trunc` | `finish == "length"` | stopped at the 700-token limit |

### `summary.json`

`index[run].sov|tam|ctl[script|gap] = [mean, lo, hi, n]` (Index S with the 95% bootstrap interval of
`analysis/analyze.py`), `roc[run]` (ROC-wording sovereignty pairs), `stance[run].train|select|fresh|tam|ctl` (steering
runs, from `a3_probe_logprob.jsonl`: the stance vector's 8 training, 8 selection and 8 fresh pairs, 1989, controls;
paper tables tab:steerA2 and tab:steerfresh), `corpus` (from `data_audit/results.json`), `steer.train` / `steer.select`
/ `steer.fresh` (from `items/roc_steer_items.json`) and `steer.replaced` (R-009 → R-009b, R-014 → R-014c).

### `game.json`

`guess[]` and `predict[]` rounds (`site/build_game.py` explains the selection rules). Guess rounds: `type`
(`answer` = one real answer, `pyes` = one model's mean P(yes) in the three scripts), `sign` (the tell-tale sign),
`ask` (`model` = pick one of four, `family` = the two builds answer alike, so only Bolt vs Qwen is asked), `answer`
(run id), `item`/`key`, `script`, `run`, `prompt`, `text` (excerpt; developer names masked when `masked`), `full`,
`orig`/`orig_text` (unmasked, for the reveal), `values` (pyes: P(yes) of all four models), `explain` (`zh`, `en`; every
number in it is read from the data at build time). Predict rounds: `model`, `item`/`key`, `side`, `script`,
`statement`, `p` (true P(yes)), `values`.

Data licence: CC BY 4.0, as for the rest of the repository's data (`LICENSE-DATA`).
