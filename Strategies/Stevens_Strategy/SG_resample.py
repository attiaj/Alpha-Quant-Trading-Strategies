"""
SG_resample.py
--------------
Resamples the shared EURUSD 15M dataset up to higher timeframes, correctly
carrying the high_time / low_time columns that HighLowTime.py produced.

Why this exists
---------------
Every rule tested on 15M bars loses in every out-of-sample window, and the losses
rank almost perfectly by how often the rule trades. That is the signature of cost
drag, not of bad signals: a 1 pip round trip is a large fraction of a 15-minute
move. If that diagnosis is right, the fix is a longer holding period, because the
move being captured grows while the spread stays the same.

Why resample instead of using EURUSD_4H_Admiral_READY.csv
---------------------------------------------------------
That file is a different broker over a different period. Resampling the shared
15M file keeps the whole team on one dataset, so results stay comparable.

The high_time / low_time problem
--------------------------------
Those two columns are what let the backtester decide whether a stop or a target
was hit first inside a bar. A naive resample would destroy them. But they survive
exactly: an hourly bar's high IS the high of whichever 15M bar inside it was
highest, so that 15M bar's high_time is the hourly bar's high_time. Same for the
low. No information is invented and none is lost.

Usage (from the Data folder):
    python SG_resample.py
"""

from pathlib import Path
import pandas as pd

REPO = Path(__file__).resolve().parent.parent      # repo root
BARS = REPO / "Data" / "FixTimeBars"
SRC = BARS / "EURUSD_15M_Demo_Ready.csv"

# label/closed="left" means a bar stamped 09:00 covers 09:00 up to (not including)
# the next bar, matching how the 15M file is stamped.
TARGETS = {
    "1H": BARS / "EURUSD_1H_Demo_Ready.csv",
    "4H": BARS / "EURUSD_4H_Demo_Ready.csv",
    "1D": BARS / "EURUSD_1D_Demo_Ready.csv",
}


def resample(df, rule):
    # groupby on a floored timestamp instead of .resample(): forex has weekend and
    # holiday gaps, and .resample() emits empty buckets for them, which makes
    # idxmax/idxmin raise on an empty sequence. A groupby key only produces groups
    # that actually contain bars.
    bucket = df.index.floor(rule)
    g = df.groupby(bucket)

    out = pd.DataFrame({
        "open":  g["open"].first(),
        "high":  g["high"].max(),
        "low":   g["low"].min(),
        "close": g["close"].last(),
        "tick_volume": g["tick_volume"].sum(),
        "spread": g["spread"].mean(),
        "real_volume": g["real_volume"].sum(),
    })

    # Carry high_time / low_time from the constituent 15M bar that set the extreme.
    # idxmax/idxmin give that 15M bar's timestamp; .map pulls its stored time.
    out["high_time"] = g["high"].idxmax().map(df["high_time"])
    out["low_time"] = g["low"].idxmin().map(df["low_time"])

    out = out.dropna(subset=["open", "high", "low", "close", "high_time", "low_time"])
    out.index.name = "time"
    return out


def main():
    df = pd.read_csv(SRC, index_col="time", parse_dates=True).sort_index()
    print(f"source: {len(df):,} bars  {df.index[0]} -> {df.index[-1]}\n")

    for rule, path in TARGETS.items():
        out = resample(df, rule)
        out.to_csv(path)

        # Sanity checks worth printing rather than trusting silently.
        bad_hi = (out["high"] < out[["open", "close"]].max(axis=1)).sum()
        bad_lo = (out["low"] > out[["open", "close"]].min(axis=1)).sum()
        same = (out["high_time"] == out["low_time"]).sum()

        print(f"{rule}: {len(out):,} bars -> {path}")
        print(f"    range {out.index[0]} -> {out.index[-1]}")
        print(f"    high < max(open,close): {bad_hi}   low > min(open,close): {bad_lo}  (both must be 0)")
        print(f"    bars where high_time == low_time: {same:,} ({same/len(out)*100:.2f}%)")
        print(f"    median bar range: {((out['high']-out['low'])/out['close']*10000).median():.1f} pips")
        print()


if __name__ == "__main__":
    main()
