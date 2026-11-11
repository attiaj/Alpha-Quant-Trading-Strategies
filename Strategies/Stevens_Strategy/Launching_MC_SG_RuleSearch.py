"""
Launching_MC_SG_RuleSearch.py
-----------------------------
Answers "how likely is this strategy to actually make money" by comparing its real
performance against the same strategy run on synthetic paths that contain no real
market structure.

How the null works
------------------
Quantreo's MonteCarlo decomposes each real bar into its open->low, open->high and
open->close moves plus timing, then RANDOMLY RESAMPLES those bars to build a path.
Random resampling preserves the distribution of bar shapes and destroys serial
correlation. There are no trends and no mean reversion in a synthetic path, only
EURUSD-shaped noise.

So a rule that genuinely exploits temporal structure should beat these paths. A rule
that merely has a favourable TP/SL geometry, or that got lucky, will score the same
on noise as it does on the real thing. That comparison is the whole point: an
absolute return number tells you nothing without knowing what noise scores.

What gets reported
------------------
  mc_mean / mc_median   What the rule earns on pure noise. Should be slightly
                        negative, because costs are paid and there is no edge.
  mc_pct_profitable     How often noise alone turns a profit. This is the real
                        bar to clear, NOT 50%.
  real_return           The rule on actual EURUSD over a matched-length window.
  percentile            Where real performance falls inside the noise distribution.
                        50 means indistinguishable from luck. You want 95+.

Usage (from inside "Launching (MC)"):
    python Launching_MC_SG_RuleSearch.py
    SG_MC_PATHS=500 python Launching_MC_SG_RuleSearch.py
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
from Quantreo.MonteCarlo import MonteCarlo
from Quantreo.Backtest import Backtest

warnings.filterwarnings("ignore")

DATA_PATH = REPO / "Data/FixTimeBars/EURUSD_4H_Demo_Ready.csv"
CANDIDATES_PATH = HERE / "SG_candidates.json"
OUT_PATH = RESULTS / "SG_montecarlo_results.csv"

HOLDOUT_FRACTION = 0.25          # same holdout as the rule search; still untouched
N_PATHS = int(os.environ.get("SG_MC_PATHS", 200))
PATH_LENGTH = 2000               # 4H bars, ~1.3 years per path

# Best tp/sl from the 4H walk-forward, per candidate.
CANDIDATES = {
    "18_ichimoku_conversion_cross": {"tp": 0.011029, "sl": -0.009159},
    "05_rsi_dip_slow_trend":        {"tp": 0.014128, "sl": -0.011863},
    "04_rsi_dip_in_uptrend":        {"tp": 0.013735, "sl": -0.011888},
    "06_sma_cross_trend":           {"tp": 0.011996, "sl": -0.011308},  # CONTROL
}

BASE = {"cost": 0.0001, "leverage": 1}


def real_chunk_returns(df, params, chunk=PATH_LENGTH):
    """
    The rule on REAL data, cut into non-overlapping chunks the same length as the
    synthetic paths. Matching the length matters: returns scale with how long you
    run, so comparing a 10-year real result against 1.3-year synthetic paths would
    be meaningless.
    """
    out = []
    for start in range(0, len(df) - chunk + 1, chunk):
        sub = df.iloc[start:start + chunk]
        BT = Backtest(data=sub.copy(), TradingStrategy=RuleSpecStrategy, parameters=params)
        BT.run()
        out.append(BT.data["returns"].sum())
    return np.array(out)


def main():
    df = pd.read_csv(DATA_PATH, index_col="time", parse_dates=True)
    research = df.iloc[:int(len(df) * (1 - HOLDOUT_FRACTION))]
    specs = {s["name"]: s for s in json.load(open(CANDIDATES_PATH))}

    print(f"data: {len(research):,} 4H bars  "
          f"({research.index[0].date()} to {research.index[-1].date()})")
    print(f"{N_PATHS} synthetic paths of {PATH_LENGTH:,} bars each\n")

    rows = []
    for name, tpsl in CANDIDATES.items():
        t0 = time.time()
        params = {**BASE, **tpsl, "spec": specs[name]}
        tag = "  [CONTROL]" if "06_" in name else ""
        print(f"{name}{tag}")

        # Real data, chunked to match path length
        real = real_chunk_returns(research, params)

        # Synthetic paths: same bar-shape distribution, no serial structure
        MC = MonteCarlo(research, RuleSpecStrategy, params, raw_columns=[])
        MC.generate_paths(N_PATHS, PATH_LENGTH)
        MC.backtest_paths()

        # UNITS: Backtest.get_ret_dd() already multiplies by 100, so MC.returns are
        # PERCENT. Backtest.data["returns"].sum() used by real_chunk_returns() is a
        # FRACTION. Divide here so both sides are fractions before any comparison.
        mc = np.array(MC.returns) / 100.0

        pct = float((mc < real.mean()).mean() * 100)
        rows.append({
            "name": name,
            "real_mean_return": real.mean(),
            "real_chunks": len(real),
            "mc_mean": mc.mean(),
            "mc_median": float(np.median(mc)),
            "mc_std": mc.std(),
            "mc_pct_profitable": float((mc > 0).mean() * 100),
            "percentile_of_real": pct,
        })

        print(f"    real   : mean {real.mean()*100:+.2f}% over {len(real)} chunks  "
              f"{[round(x*100,1) for x in real]}")
        print(f"    noise  : mean {mc.mean()*100:+.2f}%  median {np.median(mc)*100:+.2f}%  "
              f"std {mc.std()*100:.2f}%  profitable {(mc>0).mean()*100:.0f}% of the time")
        print(f"    real sits at the {pct:.0f}th percentile of noise   ({time.time()-t0:.0f}s)\n")

    out = pd.DataFrame(rows)
    out.to_csv(OUT_PATH, index=False)
    print(f"written to {OUT_PATH}\n")

    print("""
--------------------------------------------------------------------
HOW TO READ THE PERCENTILE
--------------------------------------------------------------------
  ~50      The rule does on real EURUSD exactly what it does on noise.
           Whatever it earns is TP/SL geometry and luck, not an edge.
  70-90    Suggestive, not evidence. With 20 candidates screened, one
           landing here by chance is expected.
  95+      Real performance is outside what noise produces. This is the
           minimum before a rule deserves the holdout.

Check mc_pct_profitable before anything else. If noise turns a profit
60% of the time, then a profitable backtest is the DEFAULT outcome and
means nothing on its own.

The control (06_sma_cross_trend) should land near 50. If it does not,
the comparison itself is suspect rather than the control being good.
--------------------------------------------------------------------
""")


if __name__ == "__main__":
    main()
