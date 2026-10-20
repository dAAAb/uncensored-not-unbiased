# Serving the models

Every run talks to an OpenAI-compatible `/v1/chat/completions` endpoint. Thinking is switched off per request through
`chat_template_kwargs.enable_thinking = false`; no system prompt is sent.

## Nemotron 3.5 Bolt (llama.cpp)

llama.cpp b11748 or newer (older builds cannot load the per-layer pruned experts). Same flags for both files:

```bash
llama-server -m <NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB.gguf | NVIDIA-Nemotron-3.5-Bolt-74B-A9B-Abliterated-24GB.gguf> \
  --mmproj mmproj-NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB.gguf \
  -ngl 999 -c 262144 -np 1 -b 2048 -ub 512 -fa on --cache-type-k q8_0 --cache-type-v q8_0 --jinja \
  --spec-type draft-dflash --spec-draft-n-max 6 --spec-draft-ngl 999 \
  --spec-draft-model NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-LiLiCorr.gguf \
  --host 127.0.0.1 --port 8080
```

The LiLiCorr drafter is NVIDIA's (sha256 `080e1ea4…0194`). Speculative decoding does not change the probability of
the first answer token, which is all `probe.py --mode logprob` reads; for free text it can change wording after a few
dozen tokens (verified in the pilot: plain decoding is bit-identical across reruns, drafted decoding is not).

## Qwen3.8-Flash-Next GSQ-RCO (Strata)

Strata v0.1.41 (<https://github.com/Niko1221/Strata>). Each GGUF needs its own native pack:

```bash
python tools/iq_pack.py --gguf <...-IQ2_XS-00001-of-00002.gguf> --out <packs/name>
```

then point `--pack`, `--native`, `--ple-gguf` and the tokenizer at that model, keeping all other flags identical
between the original and the abliterated run (`--expert-cache auto --prefill auto --spec 4 --spec-min-p 0.5
--max-context 262144 --kv int8`). Shard 2 of both repositories is byte-identical (sha256 `316b46f3…e113`).

Strata ignores `logprobs`, so the Qwen pair is probed with `--mode sample --n 20`.
