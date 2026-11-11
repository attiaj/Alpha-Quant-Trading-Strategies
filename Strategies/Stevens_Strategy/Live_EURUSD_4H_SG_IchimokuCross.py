"""
Live_EURUSD_4H_SG_IchimokuCross.py
----------------------------------
Candidate 18 from the SG rule search, running live against MetaTrader 5.

READ THIS FIRST
---------------
This strategy did NOT pass validation. On 400 Monte Carlo paths it sat at the 79th
percentile of what the same rule earns on structureless noise, when the best of 20
screened candidates should reach the 95th percentile by chance alone. Noise turns a
profit roughly half the time on this instrument, so its +22% backtest is inside the
range that randomness produces.

Run this on a DEMO account, as a test of whether the execution plumbing works. It is
not a test of whether the strategy works, because the evidence says it does not.

The rule
--------
    Entry long  : Ichimoku CONVERSION crosses ABOVE BASE on a closed 4H bar
    Entry short : CONVERSION crosses BELOW BASE
    Exit        : take profit or stop loss only, no time limit, no signal exit
    TP          : 1.1029%  (~110 pips)
    SL          : 0.9159%  (~92 pips)

Before running
--------------
  1. MT5 open and logged in to the demo account.
  2. Algo Trading ENABLED (toolbar button, must not show a red square).
  3. EURUSD visible in Market Watch, or orders will be rejected.
  4. Check the exact symbol name your broker uses. MetaQuotes Demo uses "EURUSD",
     but some brokers append a suffix such as "EURUSD-Z" or "EURUSD.a". Set it below.
  5. Leave this script running. It wakes at each 4H boundary, checks for a cross,
     and sleeps. Closing the terminal stops it.
"""

import sys
import os

# Quantreo lives at the repo root, one level above this folder. Python only puts
# the SCRIPT's own directory on sys.path, not the working directory, so without
# this the import below fails with ModuleNotFoundError no matter where you run
# from. The repo's other live scripts have the same gap.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))  # repo root, for Quantreo/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                      # this folder

import MetaTrader5 as mt5
import pandas as pd
import numpy as np

import time
from Quantreo.MetaTrader5 import *
from datetime import datetime, timedelta
from Quantreo.LiveTradingSignal import *
from SG_signals import sg_ichimoku_cross   # our own file; Quantreo/ is untouched
import warnings
warnings.filterwarnings("ignore")

# --------------------------------------------------------------------------
symbol = "EURUSD"        # check your broker's exact symbol name
lot = 0.01               # smallest sensible size while testing
magic = 18               # ties orders to this strategy so resume() can find them
timeframe = timeframes_mapping["4-hours"]

# Best parameters from the 4H walk-forward. SL is POSITIVE here, the helper applies
# the direction itself.
pct_tp, pct_sl = 0.011029, 0.009159
# --------------------------------------------------------------------------

mt5.initialize()

current_account_info = mt5.account_info()
print("------------------------------------------------------------------")
print(f"Login: {mt5.account_info().login} \tserver: {mt5.account_info().server}")
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Balance: {current_account_info.balance} USD, \t Equity: {current_account_info.equity} USD, "
      f"\t Profit: {current_account_info.profit} USD")
print(f"Strategy: SG Ichimoku Cross | {symbol} 4H | lot {lot} | TP {pct_tp*100:.2f}% SL {pct_sl*100:.2f}%")
print("DEMO PLUMBING TEST. This strategy failed its noise comparison.")
print("------------------------------------------------------------------")

timeframe_condition = get_verification_time(timeframe[1])

while True:

    if datetime.now().strftime("%H:%M:%S") in timeframe_condition:
        print(datetime.now().strftime("%H:%M:%S"), flush=True)

        # The symbol has to be in Market Watch or orders are rejected.
        selected = mt5.symbol_select(symbol)
        if not selected:
            print(f"\nERROR - Failed to select '{symbol}' in MetaTrader 5 with error:", mt5.last_error())

        buy, sell = sg_ichimoku_cross(symbol, timeframe[0], 9, 26)
        print(f"    signal -> buy={buy}  sell={sell}", flush=True)

        res = resume()

        # One position at a time, matching the backtest. A new signal while already
        # in a trade is ignored; it does not close or reverse the position.
        if ("symbol" in res.columns) and ("volume" in res.columns):
            if not ((res["symbol"] == symbol) & (res["volume"] == lot)).any():
                run(symbol, buy, sell, lot, pct_tp=pct_tp, pct_sl=pct_sl, magic=magic)
            else:
                print("    already in a position, holding", flush=True)
        else:
            run(symbol, buy, sell, lot, pct_tp=pct_tp, pct_sl=pct_sl, magic=magic)

        time.sleep(1)
