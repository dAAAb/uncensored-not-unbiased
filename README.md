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

## What the pilot showed (20 October 2026, one greedy answer per question)

- No model refused anything. The problem is not blocking; it is stating the PRC position as fact.
- The abliterated Qwen3.8-Flash-Next answered all eight sovereignty questions with the PRC position, in every
  script ("台灣不是國家，而是中國的一部分"; "Taiwan is not a country; it is an inalienable part of China").
- NVIDIA's Nemotron 3.5 Bolt answered "Is Taiwan part of the PRC?" with **No** in Traditional Chinese and English
  but **Yes** in Simplified Chinese, reproducing Hsiao's script effect in a chat model.
- After abliteration the same Bolt model answered **Yes** in Traditional Chinese too, while the weight diff shows
  that only the 100 tensors named by the abliteration author changed (by subtracting one direction; no data added).
- On the 1989 crackdown, the abliterated Bolt switched to Simplified characters, cited the official toll of 241 and
  called higher estimates "possibly exaggerated"; the abliterated Qwen used the official term 八九風波.
- A three-sentence system prompt stating Taiwan's constitutional reality turned all eight Qwen answers around.

Working hypothesis: safety tuning partly masks a PRC-leaning prior learned from Chinese-language data; abliteration
removes part of that mask, so it works as a probe. See `pilot/README.md` for the raw answers and caveats.

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
