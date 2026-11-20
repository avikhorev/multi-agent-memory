# Dependence of the `ours` result on the order of writes

Source: `ours` traces in `results/live/main/traces`; facts and record trust are taken from them.
Records of the `private` scope are not counted.
`order_changes_outcome`: the result changes if the same versions are written in reverse order.
`all_versions_dated`: among them, cases where all versions have an event date.
`untrusted_beats_trusted`: an untrusted value remains even though a trusted version exists.

| Category | keys | conflicts | order_changes_outcome | all_versions_dated | untrusted_beats_trusted |
|---|---|---|---|---|---|
| C0 | 121 | 0 | 0 | 0 | 0 |
| C1 | 128 | 5 | 4 | 0 | 0 |
| C2 | 125 | 0 | 0 | 0 | 0 |
| C3 | 138 | 6 | 0 | 0 | 0 |
| C4 | 130 | 0 | 0 | 0 | 0 |
| C5 | 128 | 0 | 0 | 0 | 0 |
| C6 | 250 | 0 | 0 | 0 | 0 |
| total | 1020 | 11 | 4 | 0 | 0 |
