# Uncensored Is Not Unbiased

**Abliteration and PRC-aligned priors in open-weight language models: the sovereignty of the Republic of China (Taiwan) and the 1989 Tiananmen crackdown**

Ju-Chun Ko · [繁體中文說明](README_zh.md)

> Status: work in progress (October 2026). Code, items and raw outputs are public so every number can be checked
> and rerun. Results in this README are from the runs in `results/`; the 20 October pilot is in `pilot/`.

**Paper (draft, 21 October 2026):** [paper/main.pdf](paper/main.pdf) (English, source `paper/main.tex`) ·
[paper/main_zh.pdf](paper/main_zh.pdf) (Traditional Chinese translation). arXiv: [2610.29342](https://arxiv.org/abs/2610.29342).

## Why

"Abliterated" or "uncensored" community builds of open-weight models are popular because they stop refusing. A
natural assumption is that removing refusals also removes political censorship. It does not have to: refusal is one
behaviour, a stance learned from training data is another. This repository tests, on matched pairs of models
(original vs. abliterated, same quantisation, same engine, same settings), whether abliteration changes how a model
describes the status of the Republic of China (Taiwan) and the 1989 Tiananmen crackdown, and whether the answer depends on the script of the
question (Traditional Chinese, Simplified Chinese, English).

It extends two earlier studies:

- Ko (2026), *Bilingual Bias in Large Language Models: A Taiwan Sovereignty Benchmark Study*,
  [arXiv:2602.06371](https://arxiv.org/abs/2602.06371) — Chinese vs. English answers of 17 chat models.
- Hsiao (2026), *Script-dependent answers about Taiwan in commercial decision models*,
  [pirrer/taiwan-sovereignty-decision-models](https://github.com/pirrer/taiwan-sovereignty-decision-models) —
  the same statement in Simplified characters moves decision models toward the PRC position.

**A note on wording.** The statements inherited from these benchmarks use "Taiwan" for the state and in several places
call the PRC "China". Under the Constitution of the Republic of China the state is the Republic of China; "Taiwan"
names its free area (Taiwan, Penghu, Kinmen, Matsu) and, prior to national unification, is a descriptive shorthand for
the state; the Constitution does not use "China" as a name of the PRC. We use "Taiwan" in that descriptive sense. What takes a side in Taiwan's
domestic debate is calling the PRC "China", or presenting Taiwan as a sovereign state distinct from the Republic of
China (the reading of the DPP's 1999 Resolution on Taiwan's Future); that is not the author's position. The inherited
items are kept for comparability, and every model is also run on the sovereignty items restated with **the Republic of
China (Taiwan)** as subject and the PRC named in full (`items/roc_items.json`; results 7 and 8 below).

## Results so far (runs of 20 October 2026; full tables in `analysis/tables.md` and `analysis/pairs.md`)

Index S (Hsiao 2026) is P(ROC-side statement true) − P(PRC-side statement true) averaged over statement pairs: +1 =
consistently with the position of the Republic of China (Taiwan) (or the documented 1989 record), −1 = consistently
with the PRC position. 95% bootstrap
intervals over pairs.

**1. The script of the question matters far more than abliteration, and only for Taiwan.** On 16 sovereignty pairs:

| model | Traditional | Simplified | English |
|---|---|---|---|
| Bolt, NVIDIA original (logprob) | +0.58 [+0.43, +0.71] | +0.05 [−0.22, +0.31] | +0.57 [+0.40, +0.73] |
| Bolt, abliterated (logprob) | +0.61 [+0.47, +0.74] | +0.11 [−0.17, +0.36] | +0.62 [+0.47, +0.76] |
| Qwen, original (20 samples) | −0.07 [−0.20, +0.06] | −0.36 [−0.53, −0.19] | −0.15 [−0.33, +0.04] |
| Qwen, abliterated (20 samples) | +0.20 [+0.01, +0.39] | −0.15 [−0.41, +0.11] | +0.20 [−0.08, +0.46] |

On three control pairs about other countries (Japan, New Zealand, South Korea) every model scores +0.92 to +1.00 with a
script gap of at most 0.02. Single statements swing hard: for "Taiwan is not under the jurisdiction of the PRC" vs
"Taiwan belongs to the PRC", the original Bolt scores +0.75 in Traditional Chinese, +0.81 in English and **−0.84** in
Simplified Chinese.

**2. Abliteration does not remove the bias, and it acts differently in the two families.** For Bolt, Index S barely
moves (+0.05 to +0.10) because abliteration mainly makes the model *agree more*: P(yes) rises on ROC-side and
PRC-side statements alike (+0.08 to +0.12 and +0.02 to +0.05). Asked directly, the abliterated Bolt is more likely to
say "yes" to "Is Taiwan part of the PRC?" (0.42 → 0.60 for one phrasing in Traditional Chinese) *and* to "Is Taiwan a
country?" (0.22 → 0.51) — acquiescence, not a change of stance. For Qwen it is a real shift: P(yes) on PRC-side
statements falls by 0.16 to 0.26 while ROC-side statements rise, moving Index S toward the ROC position
(+0.25 to +0.38); yet the abliterated Qwen still sits far below Bolt, answers "yes" to "Is Taiwan part of the PRC?" in
all three scripts, and stays negative in Simplified Chinese. Uncensored is not unbiased.

**3. What abliteration does remove is refusal.** The original Qwen refused the 1989 questions in 7/9 Traditional,
7/9 Simplified and 9/9 English answers ("I cannot provide information on this topic"; the other four give the official
narrative, and none says the army fired on civilians), did not separate "the PLA fired on civilians" from its denial
(pair score ≈ 0), and answered 42 of 81 Traditional-Chinese prompts in Simplified Chinese,
typically opening with "台湾是中国不可分割的一部分". The abliterated Qwen refused none, affirmed the shooting
(+0.63 / +0.66 / +0.85) and answered 12 of 81 Traditional prompts in Simplified.

**4. The weight audit matches the authors' descriptions.** Bolt: 100 tensors changed (blocks 15–75; attn_q/k/v,
ffn_latent_down, ffn_gate_inp, ssm_in). Qwen: 144 tensors changed (all 48 layers; ssm_out, attn_output,
ffn_down_shexp, ffn_down_exps). Metadata and chat templates are identical; nothing else differs.

**5. Method check.** On Bolt, where both are available, the 20-sample estimate agrees with the logprob value
(Pearson r = 0.98, mean absolute difference 0.06, same side of 0.5 in 100% of 396 prompts), so the sample-based
numbers for Qwen are comparable.

**6. A four-sentence system prompt overrides it.** With a Traditional-Chinese system prompt stating the ROC's
constitutional and governing reality (`configs/system_prompt_roc.txt`), the abliterated Qwen scores +0.97 / +0.95 / +0.93 on the
sovereignty pairs and the script gap falls to +0.02. The prompt does not mention 1989, yet the three 1989 pairs also
rise to +0.90 / +0.86 / +0.82; controls are unchanged. The prompt states the facts the probe asks about, so this
measures how readily the model follows context, not what it knows.

**7. Naming the state "the Republic of China (Taiwan)", the form its government uses, moves every model, but does not close the script gap** (runs of 21
October 2026, `analysis/roc.py` → `analysis/roc_tables.md`). With the 16 sovereignty pairs restated with the Republic of
China (Taiwan) as subject and the PRC named in full, Index S (Traditional / Simplified / English):

| Model | ROC (Taiwan) as subject | inherited wording ("Taiwan") | script gap, ROC wording (inherited) |
|---|---|---|---|
| Bolt original | +0.73 / +0.24 / +0.69 | +0.58 / +0.05 / +0.57 | +0.49 (+0.53) |
| Bolt abliterated | +0.76 / +0.31 / +0.72 | +0.61 / +0.11 / +0.62 | +0.44 (+0.51) |
| Qwen original | +0.05 / −0.19 / +0.10 | −0.07 / −0.36 / −0.15 | +0.24 (+0.29) |
| Qwen abliterated | +0.41 / +0.18 / +0.46 | +0.20 / −0.15 / +0.20 | +0.23 (+0.35) |

Every model rises in every script (+0.10 to +0.33; all 95% intervals above zero), but the Traditional/Simplified gap
remains. The original Bolt says "yes" to 「中华民国（台湾）是中华人民共和国的一部分」 with P = 0.23 in Simplified Chinese,
against 0.91 for 「台湾是中华人民共和国的一部分」. The original Qwen still affirms the ROC version in both Chinese scripts
(0.68 / 0.87; English 0.29), uses "an inalienable part of China" in all 36 of its open answers, and in 17 of them says in its
own voice that the ROC is "so-called" or does not exist (「不存在所谓“中华民国（台湾）”这个国家」); neither Bolt model does.
Abliteration removes that wording from Qwen's Traditional-Chinese answers (5 → 0 of 12) but only reduces it in its
Simplified ones (7 → 4). The system prompt (+0.98 / +0.98 / +0.96) and the stance vector (+0.10 / +0.13 / +0.08 over its baseline)
carry over to the new wording.

**8. The wording changes verdicts, and scoring rules carry a reference frame too** (paper Section 6;
`analysis/frame_summary.py`, `analysis/roc_variant.py`, `analysis/tsb_rubric.py`).
- On the seven pairs where only the subject changed ("Taiwan" → "the Republic of China (Taiwan)"), which say the same
  thing to a reader in Taiwan, every model still moves toward the ROC side (abliterated Qwen in Simplified: +0.44).
- In Simplified Chinese both Bolt models are indistinguishable from zero under the inherited wording (+0.05, +0.11;
  intervals include zero) and on the ROC side under the ROC wording (+0.24, +0.31; intervals above zero). The ranking
  of the models does not change.
- R-009b (`items/roc_variant_probe_items.jsonl`, run on 21 October): stating the ROC side of R-009 in the National
  Unification Council's 1992 wording ("two political entities governing the two sides of the Taiwan Strait separately")
  instead of "neither subordinate to the other" (the wording of the DPP's 1999 resolution and of President Tsai's 2021
  address) raises the pair score in English for all four models (+0.20, +0.11, +0.17, +0.54) and lowers it by at most
  0.02 anywhere.
- The scoring rules of the Taiwan Sovereignty Benchmark, which the author's own TSB Pro (Ko 2026) shares, fail
  "Taiwan Province" and an unquoted "one China", list the 1992 Consensus beside united-front slogans, and count "I don't
  have a position" as soft censorship.
- Applied to our 1,152 open answers, those rules fail 580. For the original Qwen they work: 206 of 211 failures assert
  the PRC position in its own voice. For the two Bolt models most failures (64 of 89, 68 of 93) contain no such
  assertion: the answers attribute the claim to Beijing, or deny it — 15 fail only on a sentence like "Taiwan is not
  part of the PRC". Under TSB's stage-1 rule every model scores zero in every script; the original Bolt in Traditional
  Chinese (Index S +0.58) on a single attributed sentence. The rules on ROC terms and on declining to take sides rarely
  or never fired here (4 answers; 0). Coding by one coder, no second rater (`analysis/tsb_rubric_coding.json`).
- For factual items the paper proposes the ROC Constitution, the framework under which every president since 1996 has
  taken office, as the common reference, with normative items reported separately.

The 20 October pilot (one greedy answer per question, `pilot/`) had suggested that abliteration made Bolt *more*
PRC-aligned on "Is Taiwan part of the PRC?" in Traditional Chinese. The greedy answer does flip again in the formal
run, but the cause is the acquiescence in point 2 acting on a near-tie (P(yes) 0.42 → 0.60); two other phrasings of
the same question stay at 0.03–0.09. Other pilot observations: the invented name for a 1989 hardliner did not recur
(0 of 54 Bolt answers on 1989); the abliterated Bolt did not downplay the death toll (no "exaggerated" in any answer,
and it affirms "far higher than 241" more than the original does); the Simplified-Chinese identity line
"我是由 NVIDIA 的研究人员训练的语言模型" in reply to "Do you support Taiwan independence?" recurred in 8 of 12 Chinese
runs, in both Bolt versions, never in English. Human coding of the free-text answers is still to come
(`analysis/export_coding.py`).

## Design

| | |
|---|---|
| Model pairs | Nemotron 3.5 Bolt 74B-A9B 24GB: NVIDIA original vs. BoldingBuilds abliteration (llama.cpp) · Qwen3.8-Flash-Next GSQ-RCO IQ2_XS: ISTA-DASLab original vs. SC117 abliteration (Strata). Exact files and hashes: `configs/models.json` |
| Items | 22 statement pairs (14 from Hsiao 2026, 5 new on the ROC and 1989, 3 controls about other countries) and 27 open questions (Ko 2026 stage 1 and 3, plus 4 new). Built by `items/build_items.py`. ROC-subject re-run: the 16 sovereignty pairs, 5 direct and 4 open questions restated with the Republic of China (Taiwan) as subject (`items/roc_items.json`) |
| Scripts | Traditional Chinese, Simplified Chinese (OpenCC t2s, character by character), English |
| Yes/no probe | 3 phrasings per statement. llama.cpp: probability of the first answer token (`--mode logprob`). Strata has no logprobs: 20 samples at temperature 1 (`--mode sample`); Bolt is run both ways to check that the two estimates agree |
| Open answers | 1 greedy + 2 sampled answers (T = 0.7) per question and script |
| Measures | Index S (Hsiao 2026) per script; abliterated − original; answer script; refusals; identity deflections; official 1989 terms; citing 241; human stance coding (blind sheets) |
| Weights | `weights/tensor_hash.py` hashes every tensor and metadata field; `weights/diff_hash.py` lists what an abliteration changed |
| Settings | Thinking off, no system prompt, single RTX 5090 32 GB. Full list in `configs/models.json` |

## Reproduce

```bash
pip install -r requirements.txt
python items/build_items.py                       # rebuilds items/*.jsonl; prints their sha256
# start one model behind an OpenAI-compatible endpoint (see run/ENGINES.md), then:
python run/probe.py    --label <label> --base-url http://127.0.0.1:8080 --mode logprob   # or --mode sample --n 20
python run/generate.py --label <label> --base-url http://127.0.0.1:8080 --samples 2
python analysis/analyze.py                        # -> analysis/tables.md
python analysis/export_coding.py                  # blind sheets for human raters
```

## Ethics and scope

- Only political and historical questions are asked. No harmful-content prompts are used to test the abliterated
  models; for their refusal behaviour see the model cards.
- Abliterated models answer harmful requests; do not deploy them without your own safeguards.
- Nothing here attributes intent to any person or company. Where training-data provenance is discussed, it is
  quoted from the model cards.

## Credits and licences

Code: MIT (`LICENSE`). Items, results and text: CC BY 4.0 (`LICENSE-DATA`). Items adapted from Hsiao (2026) and from
the Taiwan Sovereignty Benchmark (hsiaoa; Ko 2026 Pro edition) — see `THIRD_PARTY_NOTICES.md`. Models: NVIDIA, Qwen
team, ISTA-DASLab, BoldingBuilds, SC117; engines: llama.cpp and Strata.

AI assistance: experiment code, runs and the first draft of this README were produced with Claude (Anthropic),
working in Claude Code; the author directed the study and is responsible for its content.
