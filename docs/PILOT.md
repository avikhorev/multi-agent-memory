# Pilot: calling Claude as a transport

Goal of the pilot: find out what a call of `claude -p` costs and how fast it runs when used as a stateless transport for the agents, and recalculate the forecast of the runs. All numbers below are taken from `results/pilot/*.jsonl` (medians over calls without refusals; the file is indicated for each table).

## Measurement conditions

| Parameter | Value |
|---|---|
| Date | 2026-10-31 |
| Model | `claude-haiku-5-5` |
| CLI version | 2.1.316 (pinned, auto-update disabled) |
| Threads | 1, 4, 8 (see below) |
| `api_key_set` | `false` (`ANTHROPIC_API_KEY` and `CLAUDE_CODE_OAUTH_TOKEN` are not set; the call is authorized by the launch environment, the payment source is not confirmed) |
| Cores, memory | 4 cores, 16 GB |
| Measurement scripts | `step0.py`, `calibrate.py` are not included in the repository; the conditions of each measurement are described below |

## Final set of flags

```text
claude -p --model claude-haiku-5-5 --output-format json
       --system-prompt <role text> --tools "" --strict-mcp-config --mcp-config '{"mcpServers":{}}'
       --setting-sources "" --disable-slash-commands --no-session-persistence --effort low
       <prompt>
```

Each call runs in a new process, with a closed stdin, in an empty temporary folder, with an environment from a whitelist. Undocumented flags and variables are not used.

Whitelist of environment variables (everything else is not passed): `PATH`, `HOME`, `LANG`, `LC_ALL`, `TMPDIR`, `HTTPS_PROXY`, `https_proxy`, `HTTP_PROXY`, `http_proxy`, `NO_PROXY`, `no_proxy`, `NODE_EXTRA_CA_CERTS`, `SSL_CERT_FILE`, `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_BASE_URL`; plus `DISABLE_AUTOUPDATER=1`.

The list has 16 names, but in the measurement the child process has 10 variables. The difference is explained as follows: the measurement environment had 9 of the 16 allowed names set (not set: `LANG`, `LC_ALL`, `TMPDIR`, `HTTP_PROXY`, `http_proxy`, `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`), and the tenth variable, `DISABLE_AUTOUPDATER=1`, is added by the code. The number 10 is the field `env_vars` in `results/pilot/env.jsonl`.

## Results

### Overhead tokens and environment (`env.jsonl`, `claudemd.jsonl`)

| Environment | Service input tokens | Call time | Cost |
|---|---|---|---|
| Whitelist (9 of the 16 allowed names set, plus `DISABLE_AUTOUPDATER`, 10 in total) | 556–558 | 2.3 s | $0.000113 |
| Full environment of the parent process (169 variables) | 1,326 | 6.1 s | $0.000267 |

- The whitelist reduces the overhead tokens 2.4 times, and the call is 2.6 times faster. The whitelist is chosen.
- Without `--bare` the project instructions file in the working folder is not picked up (557.5 against 557 tokens), but the calls still go out from an empty temporary folder.
- The measurement in each row is single (`env.jsonl`), so the difference is estimated roughly; the direction is confirmed by the other measurements of the pilot.

### History on disk

After all measurements there are no new files in `~/.claude/projects/`: with `--no-session-persistence` the history is not written.

### Effort and thinking (`effort.jsonl`, `thinking.jsonl`, `realistic.jsonl`)

| Setting | Output tokens | Of which thinking | Time | Cost |
|---|---|---|---|---|
| `--effort low` (context 8,000 characters) | 658 | 330 | 5.5 s | $0.000462 |
| `--effort medium` | 1,067 | 688 | 7.0 s | $0.000640 |
| without `--effort` | 1,186 | 763 | 7.7 s | $0.000700 |
| `--effort low` and context 2,000 tokens | 962 | 529 | 6.8 s | $0.000628 |

- The lowest documented setting is `low`. Disabling thinking did not succeed: the hidden flag `--thinking disabled` and the variable `CLAUDE_CODE_DISABLE_THINKING` do not change the number of thinking tokens (331 and 365 against 319 by default). They are not used in the final flags.
- The output depends on the prompt: from 660 to 970 tokens per call. The plan assumed 150. The forecast below includes the measured values.

### Parallelism (`parallel.jsonl`, 24 realistic calls per level)

| Threads | Errors | Median call | Calls per minute |
|---|---|---|---|
| 1 | 0 | 6.2 s | 9.0 |
| 4 | 0 | 6.3 s | 35.1 |
| 8 | 0 | 7.0 s | 64.0 |

There are no limit errors. The scaling is close to linear. The default working level is 8 threads, with a fallback on limit errors. More than 8 threads was not tested.

### Provider refusals (`tokens*.jsonl`)

Of the 49 calls of the calibration measurements on synthetic "word porridge" (random words from one list), 12 ended with the answer `API Error: Haiku 5.5 can't help with this`, with output 0 tokens. Such an answer comes as an error, and the CLI itself repeats the request, so the input tokens in `usage` are counted twice (this explains the suspicious prose points: 1,598 and 4,566 tokens instead of 488 and 1,971). The other calls of the pilot (130 in the measurements of environment, effort, thinking and parallelism, and 67 in the calibration on natural text) gave no refusals. The number of requests in `iterations` for refusals is 1, that is, the CLI repeat is not visible in this field.

Consequence: in the benchmark a refusal is a separate outcome, not an infrastructure error. It is especially likely in C5 (injected instructions). The runner counts it as a separate category (see `DECISIONS.md`).

### Token counter (`calibration_samples.jsonl`, `token_counter_fit.json`, `tokens*.jsonl`)

The estimate "characters ÷ 4" does not work. Characters per token (median over `calibration_samples.jsonl`): facts 2.1, JSON 1.9, mixed context 2.5, prose 3.3. On the "word porridge" of the pilot it was 4.1, but that is an atypical text.

| Text type | Error of "characters ÷ 4" (mean / max) | Error of the offline counter (mean / max) |
|---|---|---|
| facts | 47% / 47% | 0.4% / 1.3% |
| prose | 17% / 18% | 2.4% / 6.3% |
| JSON | 52% / 52% | 0.5% / 1.8% |
| mixed | 38% / 39% | 1.6% / 6.3% |

The values are on the verification sample (8 texts of each type; the seeds did not take part in the fitting). The counter is a linear model over the features of regular expressions; the features and weights are recorded in `token_counter_fit.json` and in `DECISIONS.md`. Check on a realistic call (`realistic.jsonl`): the context counted as 1,999 tokens, and the whole call took 2,678 input tokens. The same call with an empty context gives 665–667 tokens (556 service and about 110 for the role and the task). The actual size of the context is 2,678 − 666 = 2,012 tokens; the discrepancy with the counter is 13 tokens (0.6%).

### Compact answer format (`compact.jsonl`, 12 calls per variant, the same context)

| Agent answer format | Output tokens | Of which thinking | Visible answer | Time | Cost |
|---|---|---|---|---|---|
| Detailed (with a `rationale` explanation) | 904 | 459 | 445 | 6.5 s | $0.000542 |
| Strict JSON with short fields, no explanations | 629 | 517 | 112 | 5.0 s | $0.000465 |

The compact format shortens the visible answer by 75%, the total output by 30%, the time by 23% and the cost by 14%. The thinking tokens do not decrease. The answer format is recorded in `SCENARIO_FORMAT.md`.

## Forecast of section 6 (preliminary)

The cost of a call with a compact answer and a 2,000-token context: $0.00047 (`compact.jsonl`). For comparison, with a detailed answer it is $0.00054–0.00066. Speed: 64 calls per minute at 8 threads, 35 at 4 (measured with the detailed answer; with the compact one the call is faster, so the estimate is cautious). The cost of an extraction call is not yet measured: the extractor's prompt does not exist yet, so the same price is used in the calculation. The growth of `full_history` (up to $1.2 for A and $0.9 for B) is taken from the plan and is not measured.

| Level | Calls | Time at 8 threads | Time at 4 threads | Cost |
|---|---|---|---|---|
| Trial extraction pass | ~700 | 11 min | 20 min | $0.33 |
| Full extraction pass | ~6,000 | 94 min | 171 min | $2.8 |
| Smoke | ~630 | 10 min | 18 min | $0.30 |
| Main A | ~10,800 | 169 min | 308 min | $5.1 |
| Main B | ~8,100 | 127 min | 231 min | $3.8 |

Total together with the full extraction pass and the growth of `full_history`: A — $9.1, B — $7.5. With the detailed answer at the upper estimate of the call cost ($0.00066) it would be $12.3 and $10.2. The margin to the $10 limit for variant A is small.

**The choice of A or B is not made.** It is made after the trial extraction pass and Smoke, by the measured price of the extraction call and by the actual growth of `full_history`. The price of the extraction call is measured on the trial pass, after which section 6 is recalculated.

## Not verified

| Item | Status |
|---|---|
| `--bare` with `ANTHROPIC_API_KEY` | NOT RUN: there is no key. Without a key `--bare` does not authorize (verified). The final set of flags does not use it |
| Priority if both the key and `CLAUDE_CODE_OAUTH_TOKEN` are set | NOT RUN: no credentials |
| Payment by key and by subscription | Key: NOT RUN. The run with a subscription token in Docker works (`results/live/docker_check`); how the spending is counted under the subscription was not verified |
| Agent SDK instead of `claude -p` | not tried: the overhead tokens are small (556) |
| More than 8 threads | not verified |
| Work of the counter on the texts of the future generator | verified on Smoke by the actual `usage` |
| Work in a Docker container | not verified |
