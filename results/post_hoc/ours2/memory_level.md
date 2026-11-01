# ours2 against ours@cache at the memory level (no model; post hoc)

## eval

| metric | ours@cache | ours2@cache | ours2@cache-no_buffer | ours2@cache-no_filler | ours2@cache-no_disputes |
|---|---|---|---|---|---|
| checkpoints passed | 778/780 | 758/780 | 758/780 | 778/780 | 758/780 |
| C0 correct | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| C1 current value present | 0.99 | 0.99 | 0.99 | 0.99 | 0.99 |
| C1 stale value shown | 0.01 | 0.17 | 0.17 | 0.01 | 0.17 |
| C2 constraint in context | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| C3 resolved correctly | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| C4 foreign private item in context | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C4 public facts present | 0.99 | 0.99 | 0.99 | 0.99 | 0.99 |
| C5 attack in instruction slot | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C5 legitimate item blocked | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C6 correct | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| C6 context tokens (mean) | 1332.91 | 1879.70 | 1879.70 | 1332.91 | 1879.70 |

## holdout

| metric | ours@cache | ours2@cache | ours2@cache-no_buffer | ours2@cache-no_filler | ours2@cache-no_disputes |
|---|---|---|---|---|---|
| checkpoints passed | 41/41 | 40/41 | 40/41 | 41/41 | 40/41 |
| C0 correct | - | - | - | - | - |
| C1 current value present | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| C1 stale value shown | 0.00 | 0.08 | 0.08 | 0.00 | 0.08 |
| C2 constraint in context | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| C3 resolved correctly | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| C4 foreign private item in context | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C4 public facts present | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| C5 attack in instruction slot | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C5 legitimate item blocked | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C6 correct | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| C6 context tokens (mean) | 1914.33 | 1990.00 | 1990.00 | 1914.33 | 1990.00 |
