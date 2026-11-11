"""
Launching_SG_ExitVariant.py
---------------------------
Two experiments in one run.

EXPERIMENT 1 - does a signal exit help?
    Current rules exit on TP or SL only. On the 4H Ichimoku cross that means
    ~69 crosses a year produce only ~30 trades: the rest fire while a position is
    already open and get discarded. Which crosses get traded therefore depends on
    unrelated history rather than on the signal itself.

    The variant closes the position when the opposite signal appears. Same entry,
    different exit. If it performs about the same, the discarded crosses were
    noise. If it is much worse, the accidental filtering was doing real work,
    which would be a strange and informative result.

EXPERIMENT 2 - does a longer holding period beat the cost drag?
    The one robust finding across everything tested is that losses rank by how
    often a rule trades. Median bar range is ~5 pips on 15M, 21.3 on 4H and 61.6
    on 1D, so a 1 pip round trip is 20%, 4.7% and 1.6% of a typical bar. Daily is
    the direct test.

REPORTED ON RETURN, NOT CRITERION
    WFO.df_results["criterion"] is return + 2*drawdown, which penalises short test
    windows and inverted the rankings earlier in this project. Everything here is
    raw out-of-sample return per window.

Usage (from inside "Launching (WFO)"):
    python Launching_SG_ExitVariant.py
"""

import sys
import os
import json
import time
import warnings
import numpy as np
import pandas as pd

from pathlib import Path

# This folder is self-contained. Paths come from the file's own location, so the
# scripts run from anywhere and nothing outside Stevens_Strategy/ is written to.
HERE = Path(__file__).resolve().parent          # Stevens_Strategy/
REPO = HERE.parent                              # repo root, for Quantreo/ and Data/
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from SG_RuleSpec import RuleSpecStrategy
from Quantreo.WalkForwardOptimization import WalkForwardOptimization
from Quantreo.Backtest import Backtest

warnings.filterwarnings("ignore")

CANDIDATES_PATH = HERE / "SG_candidates.json"
OUT_PATH = RESULTS / "SG_exit_variant_results.csv"
HOLDOUT_FRACTION = 0.25

# tp/sl scale with bar size, train window scales inversely with bar count.
TIMEFRAMES = {
    "4H": {
        "data": REPO / "Data/FixTimeBars/EURUSD_4H_Demo_Ready.csv",
        "tp": [0.006, 0.010, 0.017],
        "sl": [-0.008, -0.014],
        "length_train_set": 2000,
    },
    "1D": {
        "data": REPO / "Data/FixTimeBars/EURUSD_1D_Demo_Ready.csv",
        "tp": [0.018, 0.030, 0.050],
        "sl": [-0.024, -0.042],
        "length_train_set": 400,
    },
}

# 06 is the direction CONTROL. It tests the opposite hypothesis to the reversion
# family, so it should NOT come out well. If it does, suspect the harness.
TEST_CANDIDATES = [
    "18_ichimoku_conversion_cross",
    "05_rsi_dip_slow_trend",
    "04_rsi_dip_in_uptrend",
    "06_sma_cross_trend",
]

BASE = {"cost": 0.0001, "leverage": 1}


def run_one(df, spec, cfg):
    """Walk-forward, then re-run each test window to collect RAW returns."""
    W = WalkForwardOptimization(
        df, RuleSpecStrategy,
        {**BASE, "spec": spec},
        {"tp": cfg["tp"], "sl": cfg["sl"]},
        length_train_set=cfg["length_train_set"],
        pct_train_set=0.70,
        anchored=False,
        randomness=1.0,
    )
    W.run_optimization()

    per_window, trades = [], []
    for i, p in enumerate(W.best_params_smoothed):
        BT = Backtest(data=W.test_samples[i].copy(), TradingStrategy=RuleSpecStrategy, parameters=p)
        BT.run()
        r = BT.data["returns"]
        per_window.append(r.sum())
        trades.append(r[r != 0])

    tr = pd.concat(trades) if trades else pd.Series(dtype=float)
    pw = np.array(per_window)

    t_stat = (tr.mean() / (tr.std() / np.sqrt(len(tr)))) if len(tr) > 1 and tr.std() > 0 else np.nan
    best = max(per_window) if per_window else 0.0

    return {
        "n_windows": len(pw),
        "windows_positive": int((pw > 0).sum()),
        "total_return": float(pw.sum()),
        "total_ex_best_window": float(pw.sum() - best),
        "trades": len(tr),
        "win_rate": float((tr > 0).mean()) if len(tr) else np.nan,
        "pips_per_trade": float(tr.mean() * 10000) if len(tr) else np.nan,
        "t_stat": float(t_stat),
    }


def main():
    specs = {s["name"]: s for s in json.load(open(CANDIDATES_PATH))}
    rows = []

    for tf, cfg in TIMEFRAMES.items():
        df = pd.read_csv(cfg["data"], index_col="time", parse_dates=True)
        research = df.iloc[:int(len(df) * (1 - HOLDOUT_FRACTION))]
        print(f"\n=== {tf} | {len(research):,} research bars "
              f"({research.index[0].date()} to {research.index[-1].date()}) ===", flush=True)

        for name in TEST_CANDIDATES:
            for exit_mode in (False, True):
                spec = dict(specs[name])
                spec["exit_on_opposite"] = exit_mode
                label = "signal-exit" if exit_mode else "tp/sl only "

                t0 = time.time()
                try:
                    res = run_one(research, spec, cfg)
                except Exception as exc:
                    print(f"  {name:<30} {label}  FAILED: {type(exc).__name__}: {exc}", flush=True)
                    continue

                rows.append({"timeframe": tf, "name": name, "exit": label.strip(), **res})
                print(f"  {name:<30} {label} | ret {res['total_return']*100:+7.2f}%  "
                      f"{res['windows_positive']}/{res['n_windows']} win  "
                      f"{res['trades']:>4} trades  {res['pips_per_trade']:+6.1f} pips  "
                      f"t={res['t_stat']:+5.2f}  ({time.time()-t0:.0f}s)", flush=True)
                pd.DataFrame(rows).to_csv(OUT_PATH, index=False)

    out = pd.DataFrame(rows)
    out.to_csv(OUT_PATH, index=False)
    print(f"\nwritten to {OUT_PATH}")

    print("""
--------------------------------------------------------------------
HOW TO READ THIS
--------------------------------------------------------------------
Compare the two rows of each candidate within a timeframe. The entry is
identical; only the exit differs. A large gap either way is the finding.

total_ex_best_window matters as much as total_return. If dropping the single
best window wipes out the result, performance came from one period rather
than from the rule.

Check 06_sma_cross_trend. It is the direction CONTROL and should look bad.
If it looks good, doubt the harness before believing the strategy.

t_stat is per trade, uncorrected. The Bonferroni bar for the original 20
candidates is 0.0025, so a t around 2 is nowhere near significance. Treat
anything here as a lead, not a result.
--------------------------------------------------------------------
""")


if __name__ == "__main__":
    main()
