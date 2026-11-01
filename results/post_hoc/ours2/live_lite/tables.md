# Live layer results

Units: 42; systems: ours2_lite; repeats: 2. The sample is small: only large effects are visible. Counts and ranges over repeats, no intervals.

## Outcomes per system and category

| category | system | ok | range over repeats | ok given the information reached memory | ok % | agent % | memory % | model % | refusal % |
|---|---|---|---|---|---|---|---|---|---|
| C0 | ours2_lite | 11 of 18 | 0.56–0.67 | 11 of 13 | 61% | 28% | 0% | 11% | 0% |
| C1 | ours2_lite | 5 of 6 | 0.67–1.00 | 5 of 6 | 83% | 0% | 17% | 0% | 0% |
| C2 | ours2_lite | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C3 | ours2_lite | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C4 | ours2_lite | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C5 | ours2_lite | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C6 | ours2_lite | 14 of 18 | 0.67–0.89 | 14 of 14 | 78% | 22% | 0% | 0% | 0% |

Labels are shares of the checkpoints; `refusal` is neither a successful attack nor a correct defence.

## Cost, tokens and time

| system | units | calls per unit | input tokens per call (all kinds) | output tokens per call | cost per call, USD | cost per unit, USD | model s per call | memory s per session | refusals |
|---|---|---|---|---|---|---|---|---|---|
| ours2_lite | 42 | 64.0 | 1400.3 | 246.8 | 0.000370962 | 0.023724 | 3.368 | 0.009919 | 0 |

## C6: growth with the length of the history

| system | input tokens per call at each length | cost per call at each length | slope, tokens per added session | slope, USD per added session |
|---|---|---|---|---|
| ours2_lite | 10: 1261, 20: 1611, 30: 1848 | 10: 0.0003521, 20: 0.0004265, 30: 0.0004936 | 29.37 | 7.074e-06 |

## C5: exposure to the attack

| system | units | the Worker read the attack document | attacked (all units) | attacked (among those who read it) |
|---|---|---|---|---|
| ours2_lite | 6 | 3 | 0 | 0 of 3 |
