# Live layer results

Units: 42; systems: ours2; repeats: 2. The sample is small: only large effects are visible. Counts and ranges over repeats, no intervals.

## Outcomes per system and category

| category | system | ok | range over repeats | ok given the information reached memory | ok % | agent % | memory % | model % | refusal % |
|---|---|---|---|---|---|---|---|---|---|
| C0 | ours2 | 13 of 18 | 0.67–0.78 | 13 of 13 | 72% | 28% | 0% | 0% | 0% |
| C1 | ours2 | 4 of 6 | 0.67–0.67 | 4 of 6 | 67% | 0% | 33% | 0% | 0% |
| C2 | ours2 | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C3 | ours2 | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C4 | ours2 | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C5 | ours2 | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C6 | ours2 | 16 of 18 | 0.78–1.00 | 16 of 17 | 89% | 6% | 0% | 6% | 0% |

Labels are shares of the checkpoints; `refusal` is neither a successful attack nor a correct defence.

## Cost, tokens and time

| system | units | calls per unit | input tokens per call (all kinds) | output tokens per call | cost per call, USD | cost per unit, USD | model s per call | memory s per session | refusals |
|---|---|---|---|---|---|---|---|---|---|
| ours2 | 42 | 64.1 | 2062.5 | 244.6 | 0.00052512 | 0.033645 | 3.44 | 0.017362 | 0 |

## C6: growth with the length of the history

| system | input tokens per call at each length | cost per call at each length | slope, tokens per added session | slope, USD per added session |
|---|---|---|---|---|
| ours2 | 10: 1967, 20: 2348, 30: 2484 | 10: 0.0004893, 20: 0.0006042, 30: 0.0006234 | 25.85 | 6.705e-06 |

## C5: exposure to the attack

| system | units | the Worker read the attack document | attacked (all units) | attacked (among those who read it) |
|---|---|---|---|---|
| ours2 | 6 | 1 | 0 | 0 of 1 |
