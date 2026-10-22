# Steering vectors (version 2 of the paper, Section 5)

- `cvec_bolt_abl_a3.gguf`: the stance vector of Section 5.3, built from the Republic of China (Taiwan) wording
  (`items/roc_steer_items.json`) on the abliterated Bolt (BoldingBuilds 24 GB GGUF). Apply it at layer 45, scale 2:
  `--control-vector-scaled cvec_bolt_abl_a3.gguf:2 --control-vector-layer-range 45 45`. The same file is released,
  with a model card, at https://huggingface.co/dAAAb/roc-stance-vector-bolt-74b (OpenMDW-1.1, as the model it was
  computed from).
- `layers_bolt_abl_a3.json`: per-layer statistics of that direction (held-out separation, cosine between the
  Traditional, Simplified and English estimates).
- `layers_bolt_abl_a1roc.json`, `layers_bolt_abl_a1rocmean.json`: the same for the script direction of Section 5.2
  (last token and token mean). The script-direction vectors are not included; `steer/directions.py` rebuilds them from
  a `llama-dump-hidden` run.

How the A3 layer and scale were chosen: `steer/a3_selection_rule.txt`.
