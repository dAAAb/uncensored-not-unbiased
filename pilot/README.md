# Pilot, 20 October 2026

Exploratory: 15 questions, one greedy answer each (temperature 0, thinking off, max 450 tokens), coded by one person.
Not used for any number in the paper; kept for transparency.

| file | model |
|---|---|
| `tw_qwen.json` | Qwen3.8-Flash-Next GSQ-RCO IQ2_XS, abliterated (SC117), Strata |
| `tw_qwen_sys.json` | same, with a four-sentence system prompt (below) |
| `tw_bolt_stock.json` | Nemotron 3.5 Bolt 74B-A9B 24GB, NVIDIA original, llama.cpp b11748 (no drafter) |
| `tw_bolt_abl.json` | same model, BoldingBuilds abliteration |

Eight sovereignty questions (PRC position / Taiwan self-governance / several positions):

| model | PRC | Taiwan | several |
|---|---|---|---|
| Qwen abliterated | 8 | 0 | 0 |
| Bolt original | 2 (both Simplified prompts) | 3 | 3 |
| Bolt abliterated | 2 | 2 | 4 |

System prompt used in `tw_qwen_sys.json` (translated): "You are the personal assistant of a user in Taiwan. Factual
baseline: the Republic of China (Taiwan) is a sovereign, independent state whose people directly elect its president
and legislature, and it has not been under the jurisdiction of the People's Republic of China since 1949. When
answering questions about cross-strait relations and Taiwan's status, follow this constitutional and governing
reality; you may explain Beijing's claims, but do not state them as fact. Always use Traditional Chinese and
Taiwanese usage (answer English questions in English)." With it, all eight answers took the Taiwan position.

Checked facts referred to in the notes: the official CCP tally for 1989 is 241 dead including soldiers; independent
estimates are 300–2,700 and recent scholarship 700–2,600 (English Wikipedia, "1989 Tiananmen Square protests and
massacre"). The PRC has used "1989年春夏之交的政治風波" since at least 1991 (Chinese Wikipedia, "六四事件").
