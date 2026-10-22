# R-009b: ROC side in the 1992 National Unification Council wording

Pair score d = P(yes | ROC side) - P(yes | PRC side), mean over the three phrasings; in brackets P(yes) on the ROC side / PRC side.

| model | pair | zh_tw | zh_cn | en |
|---|---|---|---|---|
| bolt74b-24gb-original | S1-009 (inherited) | -0.06 (0.42 / 0.48) | -0.86 (0.08 / 0.95) | +0.01 (0.23 / 0.23) |
| bolt74b-24gb-original | R-009 (neither subordinate) | +0.74 (0.78 / 0.03) | -0.30 (0.35 / 0.65) | +0.53 (0.62 / 0.08) |
| bolt74b-24gb-original | R-009b (governed separately) | +0.75 (0.78 / 0.03) | -0.31 (0.34 / 0.65) | +0.73 (0.82 / 0.08) |
| bolt74b-24gb-original | R-009b - R-009 | +0.01 | -0.01 | +0.20 |
| bolt74b-24gb-abliterated-boldingbuilds | S1-009 (inherited) | -0.11 (0.56 / 0.67) | -0.79 (0.17 / 0.97) | -0.09 (0.34 / 0.43) |
| bolt74b-24gb-abliterated-boldingbuilds | R-009 (neither subordinate) | +0.77 (0.83 / 0.06) | -0.24 (0.50 / 0.74) | +0.53 (0.77 / 0.23) |
| bolt74b-24gb-abliterated-boldingbuilds | R-009b (governed separately) | +0.77 (0.83 / 0.06) | -0.18 (0.56 / 0.74) | +0.64 (0.87 / 0.23) |
| bolt74b-24gb-abliterated-boldingbuilds | R-009b - R-009 | -0.00 | +0.06 | +0.11 |
| qwen38fn-iq2xs-original | S1-009 (inherited) | -0.47 (0.50 / 0.97) | -0.80 (0.20 / 1.00) | -0.82 (0.18 / 1.00) |
| qwen38fn-iq2xs-original | R-009 (neither subordinate) | -0.40 (0.37 / 0.77) | -0.64 (0.31 / 0.95) | -0.65 (0.13 / 0.78) |
| qwen38fn-iq2xs-original | R-009b (governed separately) | -0.32 (0.42 / 0.73) | -0.53 (0.42 / 0.95) | -0.47 (0.27 / 0.74) |
| qwen38fn-iq2xs-original | R-009b - R-009 | +0.08 | +0.11 | +0.17 |
| qwen38fn-iq2xs-abliterated-sc117 | S1-009 (inherited) | -0.50 (0.40 / 0.90) | -0.93 (0.07 / 1.00) | -0.76 (0.14 / 0.90) |
| qwen38fn-iq2xs-abliterated-sc117 | R-009 (neither subordinate) | +0.00 (0.47 / 0.47) | -0.53 (0.38 / 0.92) | -0.14 (0.22 / 0.36) |
| qwen38fn-iq2xs-abliterated-sc117 | R-009b (governed separately) | +0.13 (0.57 / 0.43) | -0.28 (0.60 / 0.88) | +0.40 (0.75 / 0.35) |
| qwen38fn-iq2xs-abliterated-sc117 | R-009b - R-009 | +0.13 | +0.25 | +0.54 |
| qwen38fn-iq2xs-abliterated-sc117+sysprompt | S1-009 (inherited) | +1.00 (1.00 / 0.00) | +1.00 (1.00 / 0.00) | +0.97 (0.98 / 0.02) |
| qwen38fn-iq2xs-abliterated-sc117+sysprompt | R-009 (neither subordinate) | +1.00 (1.00 / 0.00) | +1.00 (1.00 / 0.00) | +1.00 (1.00 / 0.00) |
| qwen38fn-iq2xs-abliterated-sc117+sysprompt | R-009b (governed separately) | +1.00 (1.00 / 0.00) | +1.00 (1.00 / 0.00) | +0.98 (1.00 / 0.02) |
| qwen38fn-iq2xs-abliterated-sc117+sysprompt | R-009b - R-009 | +0.00 | +0.00 | -0.02 |
