# Live layer results

Units: 42; systems: ours3; repeats: 2. The sample is small: only large effects are visible. Counts and ranges over repeats, no intervals.

## Outcomes per system and category

| category | system | ok | range over repeats | ok given the information reached memory | ok % | agent % | memory % | model % | refusal % |
|---|---|---|---|---|---|---|---|---|---|
| C0 | ours3 | 13 of 18 | 0.67–0.78 | 13 of 14 | 72% | 22% | 0% | 6% | 0% |
| C1 | ours3 | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C2 | ours3 | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C3 | ours3 | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C4 | ours3 | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C5 | ours3 | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C6 | ours3 | 17 of 18 | 0.89–1.00 | 17 of 17 | 94% | 6% | 0% | 0% | 0% |

Labels are shares of the checkpoints; `refusal` is neither a successful attack nor a correct defence.

## Cost, tokens and time

| system | units | calls per unit | input tokens per call (all kinds) | output tokens per call | cost per call, USD | cost per unit, USD | model s per call | memory s per session | refusals |
|---|---|---|---|---|---|---|---|---|---|
| ours3 | 42 | 64.0 | 1599.3 | 234.3 | 0.000424362 | 0.027169 | 3.523 | 0.01542 | 0 |

## C6: growth with the length of the history

| system | input tokens per call at each length | cost per call at each length | slope, tokens per added session | slope, USD per added session |
|---|---|---|---|---|
| ours3 | 10: 1526, 20: 1726, 30: 2051 | 10: 0.0003817, 20: 0.0004741, 30: 0.0005399 | 26.23 | 7.914e-06 |

## C5: exposure to the attack

| system | units | the Worker read the attack document | attacked (all units) | attacked (among those who read it) |
|---|---|---|---|---|
| ours3 | 6 | 2 | 0 | 0 of 2 |
