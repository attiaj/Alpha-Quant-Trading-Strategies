"""
SG_pull_jpy.py
--------------
Pulls the four JPY pairs from MT5 and writes 4H files with high_time / low_time,
ready for the rule engine. Run this with MT5 open and logged in.

Why not the existing pipeline
-----------------------------
create_databases.py + HighLowTime.py needs two MT5 pulls per pair and then a
Python loop over every bar. This does one pull and gets high_time / low_time from
a groupby, which is the same answer: a 4H bar's high IS the high of whichever 30M
bar inside it was highest, so that 30M bar's timestamp is the 4H bar's high_time.

PRE-REGISTERED 2026-11-11, before any JPY data was seen:
    instruments : USDJPY, EURJPY, GBPJPY, AUDJPY
    parameters  : identical to EURUSD 4H, no tuning
    prediction  : if the edge is partly reflexive (Ichimoku is far more widely
                  watched on yen pairs), JPY pairs beat the +6.0 / +6.9 bp per
                  trade seen on GBPUSD and the second EURUSD dataset
    reporting   : all four reported, failures included

Usage (from the Data folder, with the AlphaQuant env active):
    python SG_pull_jpy.py
"""

from datetime import datetime
from pathlib import Path
import pandas as pd
import MetaTrader5 as mt5

OUT = Path(__file__).resolve().parent.parent / "Data" / "FixTimeBars"

# MetaQuotes-Demo uses bare names. If your broker appends a suffix (EURUSD.a,
# USDJPY-Z), set SUFFIX and the script will find them.
SUFFIX = ""
SYMBOLS = ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY"]

# 99,999 is the per-request cap. At 30M bars that is roughly 8 years.
N_BARS = 99999


def pull(symbol):
    rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M30, datetime.now(), N_BARS)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"no data for {symbol}: {mt5.last_error()}")
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df.set_index("time").sort_index()


def to_4h(df30):
    """Resample to 4H, carrying the timestamp of the 30M bar that set each extreme."""
    # groupby on a floored timestamp, not .resample(): forex has weekend gaps and
    # .resample() emits empty buckets, which makes idxmax raise on an empty sequence.
    g = df30.groupby(df30.index.floor("4h"))

    out = pd.DataFrame({
        "open":  g["open"].first(),
        "high":  g["high"].max(),
        "low":   g["low"].min(),
        "close": g["close"].last(),
        "tick_volume": g["tick_volume"].sum(),
        "spread": g["spread"].mean(),
        "real_volume": g["real_volume"].sum(),
    })
    # idxmax gives the timestamp of the 30M bar that set the high, which IS the
    # high_time. This matches find_timestamp_extremum in HighLowTime.py exactly,
    # which also stores the lower-timeframe bar's own index.
    out["high_time"] = g["high"].idxmax()
    out["low_time"]  = g["low"].idxmin()

    out = out.dropna(subset=["open", "high", "low", "close", "high_time", "low_time"])
    out.index.name = "time"
    return out


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")

    acct = mt5.account_info()
    print(f"connected: login {acct.login} on {acct.server}\n")

    for base in SYMBOLS:
        sym = base + SUFFIX
        if not mt5.symbol_select(sym, True):
            print(f"{base:<8} SKIPPED - could not select '{sym}' in Market Watch")
            continue
        try:
            df30 = pull(sym)
            out = to_4h(df30)
        except Exception as exc:
            print(f"{base:<8} FAILED - {type(exc).__name__}: {exc}")
            continue

        path = OUT / f"{base}_4H_Demo_Ready.csv"
        out.to_csv(path)

        # Sanity checks worth printing rather than trusting silently.
        bad = ((out["high"] < out[["open", "close"]].max(axis=1)).sum()
               + (out["low"] > out[["open", "close"]].min(axis=1)).sum())
        med_bp = ((out["high"] - out["low"]) / out["close"] * 10000).median()

        print(f"{base:<8} {len(out):>6,} bars  "
              f"{out.index[0].date()} to {out.index[-1].date()}  "
              f"median bar {med_bp:>5.1f} bp  violations={bad}")
        print(f"         -> {path.name}")

    mt5.shutdown()
    print("\nDone. Send me the four CSVs and I'll run the test.")


if __name__ == "__main__":
    main()
