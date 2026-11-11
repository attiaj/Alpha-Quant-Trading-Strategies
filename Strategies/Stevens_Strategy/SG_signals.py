"""
SG_signals.py
-------------
Live signal functions for the SG rule search. Kept in its own file so nothing in
Quantreo/ has to be edited: everything here is additive to the shared repo.

Mirrors Quantreo/LiveTradingSignal.py in shape, so it is used the same way.
"""

from Quantreo.DataPreprocessing import *
from Quantreo.MetaTrader5 import *


def sg_ichimoku_cross(symbol, timeframe, ichi_window_1=9, ichi_window_2=26):
    """
    Candidate 18 from the SG rule search: Conversion crossing Base, nothing else.

    NOT the same as Quantreo's li_2023_02_Ichimoku_1, which also requires
    SPAN_A > SPAN_B (and whose sell condition has a bug: it reads BASE < CONVERSION,
    the same geometry as its buy).

    Bar indexing, which is the part that is easy to get wrong:
    get_rates() returns the currently FORMING bar as iloc[-1]. The backtest builds
    its signal from the last CLOSED bar and fills at the next bar's open. This
    launcher runs at the bar boundary, so the last closed bar is iloc[-2] and the
    one before it is iloc[-3]. Using iloc[-1] here would read a bar that has barely
    started and would not match the backtest.
    """
    df = get_rates(symbol=symbol, number_of_data=500, timeframe=timeframe)
    df = ichimoku(df, ichi_window_1, ichi_window_2)

    conv_now,  base_now  = df["CONVERSION"].iloc[-2], df["BASE"].iloc[-2]
    conv_prev, base_prev = df["CONVERSION"].iloc[-3], df["BASE"].iloc[-3]

    # A cross is a CHANGE of state, not simply being above or below.
    buy  = (conv_prev <= base_prev) and (conv_now > base_now)
    sell = (conv_prev >= base_prev) and (conv_now < base_now)

    return bool(buy), bool(sell)
