# Stevens_Strategy

Systematic rule search and validation for the Alpha Quant project.
Steven Ghabyous, Fall 2026.

**Everything in this folder was new when it was added, and nothing outside it
was modified at that point.** The scripts read `../Data/FixTimeBars/*.csv` and
`../Quantreo/`, and write only into `Stevens_Strategy/results/`. Two bugs found
during the work have since been fixed in `Quantreo/` and `Strategies/`; see
Notes for the team.

---

## Headline result

**Candidate 18, the Ichimoku TK Cross on EURUSD 4H.** Best of 20 pre-registered
candidates. Entry on Tenkan-sen crossing Kijun-sen, exit on take profit, stop
loss, or the opposite cross.

| | Targets only | Signal exit |
| --- | --- | --- |
| Total return, 10 years | 26.42% | 29.81% |
| CAGR | 2.54% | 2.91% |
| Sharpe (annualised) | 0.49 | 0.63 |
| Max drawdown | -10.27% | -8.69% |
| Trades | 268 | 417 |
| Win rate | 50.7% | 43.9% |
| t-statistic per trade | 1.60 | 2.03 |

**Verdict: best candidate found, edge not demonstrated.**

It passes a 400-path Monte Carlo noise comparison, a one-shot holdout, and a fine
parameter sweep. It fails the cross-market test. Applied unchanged to four new
markets the edge drops to roughly zero:

| Market | Return | bp/trade | t |
| --- | --- | --- | --- |
| EURUSD 4H | 26.42% | +9.9 | 1.60 |
| GBPUSD 4H | 27.42% | +9.8 | 1.62 |
| USDJPY 4H | 16.34% | +6.7 | 1.03 |
| EURJPY 4H | 9.52% | +3.9 | 0.60 |
| GBPJPY 4H | 0.99% | +0.3 | 0.06 |
| AUDUSD 4H | -12.32% | -3.7 | -0.67 |
| AUDJPY 4H | -23.60% | -6.8 | -1.27 |

The two markets it was found and first confirmed on average +9.8 bp per trade.
The five checked afterwards average **+0.1 bp**. Pooled over all seven markets
and 2,023 trades: +2.2 bp per trade at t = 0.99.

Suitable for paper trading on a demo account. Not for capital.

---

## Method

The search was **pre-registered**. All 20 candidates were written down with a
stated mechanism in `SG_candidates.json` before any was run, so no hypothesis
could be reverse-engineered from a result. Two are controls:

- `06_sma_cross_trend` tests the opposite hypothesis to the reversion family and
  should look bad. It does. If it ever looks good, suspect the harness.
- `08_rsi_sma_divergence_control` reproduces the repo's existing hardcoded
  `RsiSma`, to confirm the harness is correct.

Picking the best of 20 moves the significance bar. The expected maximum of 20
draws from pure noise sits at the 95th percentile; this candidate reached the
80.2nd on its noise comparison (84.5th with the signal exit). The Bonferroni
threshold for 20 tests is 0.05 / 20 = 0.0025, about t = 3.0. Observed t-statistics
run 1.60 to 2.14.

Searching does not destroy an edge, it destroys the ability to detect one. The
edge may be real. This evidence cannot show it.

---

## Files

| File | What it does |
| --- | --- |
| `SG_RuleSpec.py` | The rule engine. Reads a declarative spec rather than hardcoding a rule, so candidates are proposed as data. Holds entry, exit and intrabar tie-break logic. |
| `SG_candidates.json` | The 20 pre-registered candidates, each with its stated mechanism. |
| `Launching_SG_RuleSearch.py` | Walk-forward across the candidate set. Timeframe via the `SG_TIMEFRAME` env var (15M / 1H / 4H). |
| `Launching_SG_ExitVariant.py` | The two exit versions side by side, reported on raw return. |
| `Launching_MC_SG_RuleSearch.py` | Monte Carlo comparison against structureless noise. |
| `SG_resample.py` | Builds 1H / 4H / 1D bars from the shared 15M file, carrying `high_time` / `low_time` correctly. |
| `SG_pull_jpy.py` | Pulls the JPY pairs from MT5 and builds 4H files. Needs MT5 open. |
| `SG_signals.py` | Live signal function. Separate from `Quantreo/LiveTradingSignal.py` so that file stays untouched. |
| `Live_EURUSD_4H_SG_IchimokuCross.py` | Python live runner. Needs MT5 open on the machine. |
| `SG_IchimokuCross.mq5` | Native MT5 expert advisor. Runs without Python, hostable on the MT5 VPS. |
| `results/` | Output CSVs for every run reported above. |

## Running it

From this folder, with the `AlphaQuant` environment active:

```
python Launching_SG_RuleSearch.py 0 20      # full 20-candidate walk-forward
python Launching_SG_ExitVariant.py          # exit comparison
python Launching_MC_SG_RuleSearch.py        # noise comparison
```

Paths are derived from each file's own location, so the working directory does
not matter. Results land in `results/`.

The 4H and higher bar files are not committed, since they regenerate in seconds:

```
python SG_resample.py                       # 1H / 4H / 1D from the shared 15M file
python SG_pull_jpy.py                       # the JPY pairs, needs MT5
```

---

## Notes for the team

Four things found in the shared code while building this. They were not fixed at
the time, since nothing outside this folder was modified. Items 1 and 2 were
genuine bugs and have since been fixed in `Quantreo/` and `Strategies/`. Items 3
and 4 are design choices and are unchanged.

### Fixed

1. `Quantreo/DataPreprocessing.py`, `previous_ret` computed
   `(close.shift(n) - close) / close`. The sign was inverted, so a positive value
   meant price **fell**, and the denominator was the current price rather than
   the base, making the result `-r / (1 + r)` instead of `r`. It now computes
   `(close - close.shift(n)) / close.shift(n)`.

   This changes one candidate in this folder. `20_return_reversion_raw` was
   written against the old flipped convention, as its `mechanism` note records,
   so under the corrected feature its long side buys strength rather than
   weakness and the rule now tests momentum rather than reversion. Re-running the
   search will not reproduce the published row for that candidate until its two
   comparison operators are swapped. The other 19 candidates do not use
   `previous_ret` and are unaffected.
2. The sell condition in `li_2023_02_Ichimoku_1` read `(BASE < CONVERSION)`, the
   same geometry as its buy condition, and should have been `CONVERSION < BASE`.
   The bug was in two places rather than one, `Quantreo/LiveTradingSignal.py`
   line 92 and `Strategies/LI_2023_02_Ichimoku_1.py` line 41, so it affected
   backtests as well as live signals. Both are fixed.

   The effect was larger than a short leg that never fires. The old condition
   describes a bullish-continuation state that holds on most bars, so on the
   12,516-bar AUDUSD 4H file it produced 2,788 short entries against 64 longs.
   The corrected version produces 64 of each. Any previously published
   `LI_2023_02_Ichimoku_1` result was generated with roughly 44 times too many
   shorts and should be regenerated.

### Unchanged

3. The optimisation criterion `return + 2 * drawdown` is not scale-invariant and
   penalises short test windows. It inverted rankings during this project. Left
   alone because it is a metric choice rather than an error, and changing it
   would rescore every strategy in the repo.
4. The walk-forward recomputes features inside each slice, so every indicator
   burns its full lookback at the start of every window. At 4H with 857-bar test
   windows, a candidate using a 500-period moving average keeps about 357 usable
   bars. Long-lookback candidates in the screen were handicapped by this. Left
   alone for the same reason.

Two unit traps worth knowing, both still present:

- `Backtest.get_ret_dd()` returns **percent**; `Backtest.data["returns"].sum()`
  returns a **fraction**. Comparing them needs a division by 100. The same method
  also returns drawdown as a negative number, while `display_metrics` prints it
  positive.
- `WFO.df_results["criterion"]` is raw out-of-sample. `WFO.smooth_result["criterion"]`
  is not: `get_smoother_result` runs before the out-of-sample value is written
  back, so that column is an exponentially weighted mix of earlier folds'
  out-of-sample criteria with the current fold's **training** criterion. They are
  not interchangeable.
