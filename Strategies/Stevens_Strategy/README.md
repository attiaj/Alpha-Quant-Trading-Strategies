# Stevens_Strategy

Systematic rule search and validation for the Alpha Quant project.
Steven Ghabyous, Fall 2026.

**Everything in this folder is new. Nothing outside it was modified.**
`Quantreo/` and the existing `Launching*/`, `Strategies/` and `Data/` files are
untouched. The scripts read `../Data/FixTimeBars/*.csv` and `../Quantreo/`, and
write only into `Stevens_Strategy/results/`.

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

Four things found in the shared code while building this. Not fixed here, since
nothing outside this folder was modified.

1. `Quantreo/DataPreprocessing.py`, `previous_ret` computes
   `(close.shift(n) - close) / close`. The sign is inverted, so a positive value
   means price **fell**. Anyone using this feature has its direction backwards.
2. `Quantreo/LiveTradingSignal.py` line 92, the sell condition in
   `li_2023_02_Ichimoku_1` reads `(BASE < CONVERSION)`, the same geometry as its
   buy condition. It should be `CONVERSION < BASE`.
3. The optimisation criterion `return + 2 * drawdown` is not scale-invariant and
   penalises short test windows. It inverted rankings during this project.
4. The walk-forward recomputes features inside each slice, so every indicator
   burns its full lookback at the start of every window. At 4H with 857-bar test
   windows, a candidate using a 500-period moving average keeps about 357 usable
   bars. Long-lookback candidates in the screen were handicapped by this.

Two unit traps worth knowing:

- `Backtest.get_ret_dd()` returns **percent**; `Backtest.data["returns"].sum()`
  returns a **fraction**. Comparing them needs a division by 100.
- `WFO.df_results["criterion"]` is raw out-of-sample. `WFO.smooth_result["criterion"]`
  is smoothed **training** data. They are not interchangeable.
