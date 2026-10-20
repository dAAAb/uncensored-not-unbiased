# Uncensored Is Not Unbiased

**Abliteration and PRC-aligned priors in open-weight language models: Taiwan's sovereignty and the 1989 Tiananmen crackdown**

Ju-Chun Ko · [繁體中文說明](README_zh.md)

> Status: work in progress (October 2026). Code, items and raw outputs are public so every number can be checked
> and rerun. Results in this README are from the runs in `results/`; the 20 October pilot is in `pilot/`.

## Why

"Abliterated" or "uncensored" community builds of open-weight models are popular because they stop refusing. A
natural assumption is that removing refusals also removes political censorship. It does not have to: refusal is one
behaviour, a stance learned from training data is another. This repository tests, on matched pairs of models
(original vs. abliterated, same quantisation, same engine, same settings), whether abliteration changes how a model
describes Taiwan's status and the 1989 Tiananmen crackdown, and whether the answer depends on the script of the
question (Traditional Chinese, Simplified Chinese, English).

It extends two earlier studies:

- Ko (2026), *Bilingual Bias in Large Language Models: A Taiwan Sovereignty Benchmark Study*,
  [arXiv:2602.06371](https://arxiv.org/abs/2602.06371) — Chinese vs. English answers of 17 chat models.
- Hsiao (2026), *Script-dependent answers about Taiwan in commercial decision models*,
  [pirrer/taiwan-sovereignty-decision-models](https://github.com/pirrer/taiwan-sovereignty-decision-models) —
  the same statement in Simplified characters moves decision models toward the PRC position.

## Results so far (runs of 20 October 2026; full tables in `analysis/tables.md` and `analysis/pairs.md`)

Index S (Hsiao 2026) is P(pro statement true) − P(con statement true) averaged over statement pairs: +1 = consistently
with Taiwan's self-governance (or the documented 1989 record), −1 = consistently with the PRC position. 95% bootstrap
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

**2. Abliteration does not remove the bias.** For Bolt it barely moves anything (+0.05 to +0.10). For Qwen it moves
answers *toward* Taiwan's self-governance (+0.25 to +0.38), yet the abliterated Qwen still sits far below Bolt and
stays negative in Simplified Chinese. Uncensored is not unbiased.

**3. What abliteration does remove is refusal.** The original Qwen refused the 1989 questions in 4/9 Traditional,
4/9 Simplified and 7/9 English answers ("I cannot provide information on this topic"), would not affirm that the PLA
fired on civilians (statement score ≈ 0), and answered 42 of 81 Traditional-Chinese prompts in Simplified Chinese,
typically opening with "台湾是中国不可分割的一部分". The abliterated Qwen refused none, affirmed the shooting
(+0.63 / +0.66 / +0.85) and answered 12 of 81 Traditional prompts in Simplified.

**4. The weight audit matches the authors' descriptions.** Bolt: 100 tensors changed (blocks 15–75; attn_q/k/v,
ffn_latent_down, ffn_gate_inp, ssm_in). Qwen: 144 tensors changed (all 48 layers; ssm_out, attn_output,
ffn_down_shexp, ffn_down_exps). Metadata and chat templates are identical; nothing else differs.

**5. Method check.** On Bolt, where both are available, the 20-sample estimate agrees with the logprob value
(Pearson r = 0.98, mean absolute difference 0.06, same side of 0.5 in 100% of 396 prompts), so the sample-based
numbers for Qwen are comparable.

The 20 October pilot (one greedy answer per question, `pilot/`) had suggested that abliteration made Bolt *more*
PRC-aligned on "Is Taiwan part of the PRC?" in Traditional Chinese. The probe shows why that was fragile: both Bolt
versions sit near a tie on that statement in Traditional Chinese (+0.06 / +0.09), so a single greedy run can land on
either side. Human coding of the free-text answers is still to come (`analysis/export_coding.py`).

## Design

| | |
|---|---|
| Model pairs | Nemotron 3.5 Bolt 74B-A9B 24GB: NVIDIA original vs. BoldingBuilds abliteration (llama.cpp) · Qwen3.8-Flash-Next GSQ-RCO IQ2_XS: ISTA-DASLab original vs. SC117 abliteration (Strata). Exact files and hashes: `configs/models.json` |
| Items | 22 statement pairs (14 from Hsiao 2026, 5 new on the ROC and 1989, 3 controls about other countries) and 27 open questions (Ko 2026 stage 1 and 3, plus 4 new). Built by `items/build_items.py` |
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
