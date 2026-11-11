"""
Launching_SG_RuleSearch.py
--------------------------
Runs EVERY pre-registered candidate rule through walk-forward optimization and
reports EVERY result, not just the winners.

Protocol this enforces:
  1. Candidates are read from a frozen JSON file. Nothing is generated at runtime.
  2. Each candidate gets the identical walk-forward treatment.
  3. All results are written out, including the bad ones.
  4. The number of candidates is known, so the multiple-testing bar is computable.

Step 4 is the whole point. If you add candidates after seeing results, delete the
results file and start over, or the correction is meaningless.

Usage (from inside the "Launching (WFO)" folder):
    python Launching_SG_RuleSearch.py                 # all candidates
    python Launching_SG_RuleSearch.py 0 10            # candidates [0, 10)
    python Launching_SG_RuleSearch.py 10 20           # candidates [10, 20)

The index range exists so you can split the work across two terminals on a
2-core machine. Merge the output CSVs afterwards.
"""

import sys
import os
import json
import time
import warnings
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
from Quantreo.WalkForwardOptimization import *

warnings.filterwarnings("ignore")


# ==========================================================================
# CONFIG
# ==========================================================================
CANDIDATES_PATH = HERE / "SG_candidates.json"
RESULTS_DIR = RESULTS

# Held back entirely. Not touched by this script. See the note at the bottom.
HOLDOUT_FRACTION = 0.25

# --------------------------------------------------------------------------
# TIMEFRAME CONFIGS
#
# tp/sl must scale with the size of a bar, or the test is not comparable across
# timeframes: a 25 pip target is 5 bars of travel on 15M and barely 1 bar on 4H.
# Median bar range is ~5 pips on 15M, 9.9 on 1H, 21.3 on 4H, so the targets below
# are scaled to keep "bars of travel to target" roughly constant.
#
# length_train_set scales the other way, since higher timeframes have fewer bars.
# --------------------------------------------------------------------------
TIMEFRAMES = {
    "15M": {
        "data": REPO / "Data/FixTimeBars/EURUSD_15M_Demo_Ready.csv",
        "tp": [0.0015, 0.0025, 0.0040],
        "sl": [-0.0020, -0.0035],
        "length_train_set": 20_000,
    },
    "1H": {
        "data": REPO / "Data/FixTimeBars/EURUSD_1H_Demo_Ready.csv",
        "tp": [0.0030, 0.0050, 0.0080],
        "sl": [-0.0040, -0.0070],
        "length_train_set": 6_000,
    },
    "4H": {
        "data": REPO / "Data/FixTimeBars/EURUSD_4H_Demo_Ready.csv",
        "tp": [0.0060, 0.0100, 0.0170],
        "sl": [-0.0080, -0.0140],
        "length_train_set": 2_000,
    },
}

TIMEFRAME = os.environ.get("SG_TIMEFRAME", "15M")
if TIMEFRAME not in TIMEFRAMES:
    raise SystemExit(f"SG_TIMEFRAME must be one of {list(TIMEFRAMES)}, got {TIMEFRAME!r}")

_CFG = TIMEFRAMES[TIMEFRAME]
DATA_PATH = _CFG["data"]
PARAMS_RANGE = {"tp": _CFG["tp"], "sl": _CFG["sl"]}

PARAMS_FIXED_BASE = {
    "cost": 0.0001,     # ~1 pip round trip on EURUSD. Raise it if your broker is worse.
    "leverage": 1,      # Keep at 1 while researching. Leverage scales the noise too.
}

# anchored=False gives a ROLLING training window instead of an expanding one.
# Two reasons: an expanding window makes the last folds 9x more expensive than the
# first (tens of hours per candidate), and a fixed-length window asks the more
# honest question, which is whether the rule works on recent data rather than
# whether it works on average over everything since 2016.
LENGTH_TRAIN_SET = _CFG["length_train_set"]
PCT_TRAIN_SET = 0.70        # -> test windows of ~8,500 bars (~3.5 months)
ANCHORED = False
RANDOMNESS = 1.00           # Test the full tp/sl grid, no sampling


# ==========================================================================
def load_data():
    df = pd.read_csv(DATA_PATH, index_col="time", parse_dates=True)

    # Carve off the holdout and never look at it here.
    split = int(len(df) * (1 - HOLDOUT_FRACTION))
    research = df.iloc[:split]
    print(f"Loaded {len(df):,} bars  |  research {len(research):,} "
          f"({research.index[0].date()} to {research.index[-1].date()})")
    print(f"Holdout withheld: {len(df) - split:,} bars from {df.index[split].date()} onward\n")
    return research


def run_candidate(df, spec):
    """One candidate -> one walk-forward run -> one row of results."""
    params_fixed = dict(PARAMS_FIXED_BASE)
    params_fixed["spec"] = spec

    WFO = WalkForwardOptimization(
        df,
        RuleSpecStrategy,
        params_fixed,
        PARAMS_RANGE,
        length_train_set=LENGTH_TRAIN_SET,
        pct_train_set=PCT_TRAIN_SET,
        anchored=ANCHORED,
        randomness=RANDOMNESS,
    )
    WFO.run_optimization()

    best = WFO.best_params_smoothed[-1]

    # ------------------------------------------------------------------
    # WHICH ATTRIBUTE TO READ. This matters and is easy to get wrong.
    #
    # WFO.df_results["criterion"] is the RAW per-window criterion. For each window
    # the training criterion is written first and then OVERWRITTEN with the test-set
    # criterion in test_best_params(). So this column is genuinely out-of-sample.
    #
    # WFO.smooth_result["criterion"] is an exponentially smoothed version, and
    # get_smoother_result() runs BEFORE the overwrite, so it smooths TRAINING
    # criteria. Reading it makes rules look different from how they actually did
    # out of sample. Use df_results.
    # ------------------------------------------------------------------
    crit = pd.to_numeric(WFO.df_results["criterion"], errors="coerce").dropna()

    # Signal starts across the research set. This is an UPPER BOUND on trades (you
    # can only hold one position at a time), but it is what separates "this rule
    # never fires" from "this rule broke even", which otherwise look identical at 0.0.
    probe = RuleSpecStrategy(df.copy(), {**params_fixed, "tp": PARAMS_RANGE["tp"][0],
                                         "sl": PARAMS_RANGE["sl"][0]})
    sig = probe.data["signal"]
    signal_starts = int(((sig != 0) & (sig.shift(1) != sig)).sum())

    return {
        "name": spec["name"],
        "signal_starts": signal_starts,
        "n_windows": len(crit),
        "criterion_mean": crit.mean() if len(crit) else float("nan"),
        "criterion_median": crit.median() if len(crit) else float("nan"),
        "criterion_std": crit.std() if len(crit) else float("nan"),
        "windows_positive": int((crit > 0).sum()) if len(crit) else 0,
        "pct_windows_positive": float((crit > 0).mean()) if len(crit) else float("nan"),
        "best_tp": best.get("tp"),
        "best_sl": best.get("sl"),
        "mechanism": spec["mechanism"],
    }


def main(argv):
    with open(CANDIDATES_PATH) as fh:
        candidates = json.load(fh)

    total = len(candidates)
    start = int(argv[0]) if len(argv) > 0 else 0
    end = int(argv[1]) if len(argv) > 1 else total
    subset = candidates[start:end]

    results_path = os.path.join(
        RESULTS_DIR,
        f"SG_rule_search_results_{TIMEFRAME}_{start}_{end}.csv" if (start, end) != (0, total)
        else f"SG_rule_search_results_{TIMEFRAME}.csv"
    )

    print(f"TIMEFRAME: {TIMEFRAME}   data: {DATA_PATH}")
    print(f"tp grid {PARAMS_RANGE['tp']}  sl grid {PARAMS_RANGE['sl']}  train window {LENGTH_TRAIN_SET:,} bars")
    print(f"{total} pre-registered candidates in total")
    print(f"Bonferroni bar for {total} tests: {0.05 / total:.5f}")
    print(f"Running indices [{start}, {end}) -> {results_path}\n")

    df = load_data()

    rows = []
    for i, spec in enumerate(subset, start + 1):
        t0 = time.time()
        print(f"[{i}/{total}] {spec['name']} ...", flush=True)
        try:
            row = run_candidate(df, spec)
            print(f"    done in {time.time()-t0:.0f}s  "
                  f"signals={row['signal_starts']:,}  windows={row['n_windows']}  "
                  f"median={row['criterion_median']:.4f}  "
                  f"pct_pos={row['pct_windows_positive']:.2f}", flush=True)
        except Exception as exc:
            print(f"    FAILED after {time.time()-t0:.0f}s: {type(exc).__name__}: {exc}", flush=True)
            row = {"name": spec["name"], "signal_starts": 0, "n_windows": 0,
                   "criterion_mean": float("nan"), "criterion_median": float("nan"),
                   "criterion_std": float("nan"), "windows_positive": 0,
                   "pct_windows_positive": float("nan"), "best_tp": None, "best_sl": None,
                   "mechanism": spec["mechanism"], "error": f"{type(exc).__name__}: {exc}"}
        rows.append(row)
        pd.DataFrame(rows).to_csv(results_path, index=False)   # checkpoint every candidate

    out = pd.DataFrame(rows).sort_values("criterion_median", ascending=False)
    out.to_csv(results_path, index=False)

    print(f"\n{len(rows)} results written to {results_path}\n")
    cols = ["name", "signal_starts", "n_windows", "criterion_median", "criterion_mean",
            "criterion_std", "pct_windows_positive", "best_tp", "best_sl"]
    print(out[cols].to_string(index=False))

    print("""
--------------------------------------------------------------------
READ THIS BEFORE INTERPRETING ANYTHING ABOVE
--------------------------------------------------------------------
The top row is the best of N candidates, which is not the same as good.
With this many candidates something will look strong by luck alone.

What to actually look at:
  pct_windows_positive   Consistency. A rule winning 55% of windows with a
                         modest median beats one winning 35% of windows with
                         a big median driven by a single era.
  criterion_std          Spread across windows. A large std means the median
                         is not telling you much.
  n_windows              Fewer windows means less evidence.

Also check candidate 06 (sma_cross_trend). It is a DIRECTION CONTROL and
tests the opposite hypothesis to the reversion family. If the reversion
rules AND the trend rule both make money, suspect the backtest rather than
celebrate the strategies.

Candidate 08 is a CORRECTNESS CONTROL: it reproduces the repo's hardcoded
RsiSma rule. Its returns have been verified identical to that class.

The holdout is still untouched. Spend it ONCE, on ONE candidate, after you
have chosen that candidate for reasons visible above. If you test the
holdout, get a bad answer, and come back for the next candidate, it is no
longer a holdout and you have no clean test left.
--------------------------------------------------------------------
""")


if __name__ == "__main__":
    main(sys.argv[1:])
