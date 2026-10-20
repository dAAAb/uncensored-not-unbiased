# Raw outputs

One folder per model label (see `configs/models.json`).

`probe_logprob.jsonl` / `probe_sample.jsonl` — one line per statement × script × phrasing:

| field | meaning |
|---|---|
| `pair`, `side`, `topic`, `source` | item (`side`: `pro` = Taiwan self-governance or the documented 1989 record; `con` = PRC position; controls use the same sides) |
| `script`, `phrasing` | `zh_tw` / `zh_cn` / `en`; phrasing 0–2 (templates in `run/probe.py`) |
| `p_yes` | P(the model answers yes), renormalised over yes and no answers |
| `p_mass` | probability (logprob) or share of samples (sample) that was a yes or no answer at all |
| `top` | logprob mode: the 8 most likely first tokens with probabilities |
| `counts`, `n`, `samples` | sample mode: yes/no/other counts over `n` samples at temperature 1, first 5 samples |

`generate.jsonl` — one line per open question × script × run (`greedy`, `t07_s0`, `t07_s1`): prompt, answer,
finish reason, token count, wall time.
