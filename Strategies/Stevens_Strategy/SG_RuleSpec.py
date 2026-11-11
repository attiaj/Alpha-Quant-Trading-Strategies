"""
RuleSpecStrategy
----------------
A Quantreo-compatible strategy class that reads a DECLARATIVE rule spec instead of
having one rule hardcoded. This is what lets a hypothesis generator (an LLM agent,
a human, or a grid) propose candidate strategies as data, without writing Python.

The spec format (passed in as parameters["spec"]):

    {
      "name": "rsi_extreme_meanrev_trendfilter",
      "mechanism": "Plain-English reason this rule should work. Recorded, never used
                    by the code. Required so every candidate is pre-registered with a
                    stated hypothesis rather than being a blind grid point.",
      "features": [
          {"fn": "rsi", "n": 14},
          {"fn": "sma", "n": 50}
      ],
      "long":  [{"left": "RSI", "op": "<", "right": 25},
                {"left": "close", "op": ">", "right": "SMA_50"}],
      "short": [{"left": "RSI", "op": ">", "right": 75},
                {"left": "close", "op": "<", "right": "SMA_50"}]
    }

Every condition in "long" must be true for a long signal. Same for "short".
If "short" is omitted or empty, the rule is long-only.

Condition fields:
    left   column name produced by the feature functions, or a raw OHLCV column
    op     "<" ">" "<=" ">=" "cross_above" "cross_below"
    right  a number, or a column name, or "COLNAME@k" for that column shifted k bars

Look-ahead protection: get_entry_signal reads signal[-2], i.e. the signal computed
from the PREVIOUS bar's close, and enters at the CURRENT bar's open. Identical to
the reference RsiSma implementation. Do not change this without understanding why
it is there.

Exit logic (TP/SL with high_time/low_time ordering) is taken from the reference
implementation so results are directly comparable with the rest of the repo.
"""

from Quantreo.DataPreprocessing import *
import pandas as pd
import numpy as np


# --------------------------------------------------------------------------
# Feature dispatch: maps a spec "fn" name to the DataPreprocessing call.
# Only these features exist. An agent may not invent new ones.
# --------------------------------------------------------------------------
def roll_mean(df, col, n):
    """Rolling mean of any column. Lets a spec say 'above its own recent average'."""
    df[f"RMEAN_{col}_{n}"] = df[col].rolling(int(n)).mean()
    return df


def roll_z(df, col, n):
    """
    Rolling z-score of any column: (value - rolling mean) / rolling std.

    This is the generic version of the lesson from the feature screen: a raw level
    drifts over ten years and is not comparable across eras, a position is. Use this
    for volume, ATR, spread, or anything else measured in instrument units.
    """
    m = df[col].rolling(int(n)).mean()
    s = df[col].rolling(int(n)).std()
    df[f"RZ_{col}_{n}"] = (df[col] - m) / s
    return df


def _apply_feature(df, f):
    fn = f["fn"]

    if fn == "roll_mean":
        return roll_mean(df, f["col"], f["n"])
    if fn == "roll_z":
        return roll_z(df, f["col"], f["n"])

    if fn == "sma":
        return sma(df, f.get("col", "close"), f["n"])
    if fn == "sma_diff":
        return sma_diff(df, f.get("col", "close"), f["n"], f["m"])
    if fn == "rsi":
        return rsi(df, f.get("col", "close"), f["n"])
    if fn == "atr":
        return atr(df, f["n"])
    if fn == "sto_rsi":
        return sto_rsi(df, f.get("col", "close"), f["n"])
    if fn == "ichimoku":
        return ichimoku(df, f["n1"], f["n2"])
    if fn == "previous_ret":
        return previous_ret(df, f.get("col", "close"), f["n"])
    if fn == "k_enveloppe":
        return k_enveloppe(df, f.get("n", 10))
    if fn == "candle_information":
        return candle_information(df)

    raise ValueError(f"Unknown feature function in spec: {fn}")


class RuleSpecStrategy:

    def __init__(self, data, parameters):
        self.data = data
        self.spec = parameters["spec"]
        self.tp = parameters["tp"]
        self.sl = parameters["sl"]
        self.cost = parameters["cost"]
        self.leverage = parameters["leverage"]
        self.get_features()
        self.start_date_backtest = self.data.index[0]

        # ------------------------------------------------------------------
        # Speed: the reference implementation does self.data.loc[:time]["signal"][-2]
        # on every bar, which re-slices the entire history each time and makes a full
        # walk-forward take tens of hours. These precomputed arrays give the identical
        # value in O(1).
        #
        # signal[-2] of the data up to and including `time` IS signal.shift(1) at
        # `time`: the signal computed from the previous bar's close. Same number,
        # same look-ahead protection.
        # ------------------------------------------------------------------
        self._pos = {ts: i for i, ts in enumerate(self.data.index)}
        self._sig_prev = self.data["signal"].shift(1).to_numpy()
        self._open = self.data["open"].to_numpy()
        self._high = self.data["high"].to_numpy()
        self._low = self.data["low"].to_numpy()
        self._high_time = self.data["high_time"].to_numpy()
        self._low_time = self.data["low_time"].to_numpy()

        # Entry state
        self.buy, self.sell = False, False
        self.open_buy_price, self.open_sell_price = None, None
        self.entry_time, self.exit_time = None, None

        # Exit state
        self.var_buy_high, self.var_sell_high = None, None
        self.var_buy_low, self.var_sell_low = None, None

        self.output_dictionary = parameters.copy()

    # ----------------------------------------------------------------------
    # Condition evaluation
    # ----------------------------------------------------------------------
    def _resolve(self, ref):
        """A condition's 'right' side: a number, a column, or 'COLNAME@k' (shifted)."""
        if isinstance(ref, (int, float, np.integer, np.floating)):
            return float(ref)
        if isinstance(ref, str):
            if "@" in ref:
                col, k = ref.split("@")
                return self.data[col].shift(int(k))
            return self.data[ref]
        raise ValueError(f"Cannot resolve condition operand: {ref!r}")

    def _evaluate(self, cond):
        left = self._resolve(cond["left"])
        right = self._resolve(cond["right"])
        op = cond["op"]

        if op == "<":
            return left < right
        if op == ">":
            return left > right
        if op == "<=":
            return left <= right
        if op == ">=":
            return left >= right

        # Crosses need the previous bar on both sides.
        if op in ("cross_above", "cross_below"):
            prev_left = left.shift(1) if hasattr(left, "shift") else left
            prev_right = right.shift(1) if hasattr(right, "shift") else right
            if op == "cross_above":
                return (prev_left <= prev_right) & (left > right)
            return (prev_left >= prev_right) & (left < right)

        raise ValueError(f"Unknown operator in spec: {op}")

    def _all_true(self, conditions):
        """AND together every condition. Empty list means 'never fires'."""
        if not conditions:
            return pd.Series(False, index=self.data.index)
        mask = pd.Series(True, index=self.data.index)
        for cond in conditions:
            mask = mask & self._evaluate(cond).fillna(False)
        return mask

    def get_features(self):
        # Build every feature the spec asks for
        for f in self.spec.get("features", []):
            self.data = _apply_feature(self.data, f)

        long_mask = self._all_true(self.spec.get("long", []))
        short_mask = self._all_true(self.spec.get("short", []))

        # If both fire on the same bar the rule is self-contradictory there: stand aside.
        both = long_mask & short_mask

        self.data["signal"] = 0
        self.data.loc[long_mask & ~both, "signal"] = 1
        self.data.loc[short_mask & ~both, "signal"] = -1

    # ----------------------------------------------------------------------
    # Entry  (signal[-2] -> enter at this bar's open; no look-ahead)
    # ----------------------------------------------------------------------
    def get_entry_signal(self, time):
        i = self._pos[time]
        if i < 1:
            return 0, self.entry_time

        prev = self._sig_prev[i]

        entry_signal = 0
        if prev == 1:
            entry_signal = 1
        elif prev == -1:
            entry_signal = -1

        if entry_signal == 1 and not self.buy and not self.sell:
            self.buy = True
            self.open_buy_price = self._open[i]
            self.entry_time = time

        elif entry_signal == -1 and not self.sell and not self.buy:
            self.sell = True
            self.open_sell_price = self._open[i]
            self.entry_time = time

        else:
            entry_signal = 0

        return entry_signal, self.entry_time

    # ----------------------------------------------------------------------
    # Exit  (TP / SL, resolved intrabar with high_time vs low_time)
    # ----------------------------------------------------------------------
    def get_exit_signal(self, time):
        i = self._pos[time]
        bar_high, bar_low = self._high[i], self._low[i]
        high_t, low_t = self._high_time[i], self._low_time[i]

        # ------------------------------------------------------------------
        # OPTIONAL SIGNAL EXIT  (spec["exit_on_opposite"] = true)
        #
        # Without this, the only exits are TP and SL, so a rule can sit in a
        # losing trade while its own indicator has already turned. It also means
        # most signals are discarded: on the 4H Ichimoku cross about 69 crosses a
        # year produce only ~30 trades, because the rest fire while a position is
        # already open. Which crosses get traded ends up depending on unrelated
        # history rather than on the signal.
        #
        # Checked BEFORE TP/SL because the open comes first chronologically
        # inside the bar. If the opposite signal is present we are out at the
        # open, before that bar's high or low ever happens.
        #
        # Same look-ahead protection as the entry: the signal comes from the
        # previous bar (_sig_prev) and the fill is at THIS bar's open.
        # ------------------------------------------------------------------
        if self.spec.get("exit_on_opposite", False) and i >= 1:
            prev = self._sig_prev[i]
            px = self._open[i]

            if self.buy and prev == -1:
                ret = (px - self.open_buy_price) / self.open_buy_price
                self.buy, self.open_buy_price = False, None
                self.exit_time = time
                return (ret - self.cost) * self.leverage, self.exit_time

            if self.sell and prev == 1:
                ret = -(px - self.open_sell_price) / self.open_sell_price
                self.sell, self.open_sell_price = False, None
                self.exit_time = time
                return (ret - self.cost) * self.leverage, self.exit_time

        if self.buy:
            self.var_buy_high = (bar_high - self.open_buy_price) / self.open_buy_price
            self.var_buy_low = (bar_low - self.open_buy_price) / self.open_buy_price

            # Both thresholds touched in the same bar: high_time/low_time breaks the tie
            if (self.tp < self.var_buy_high) and (self.var_buy_low < self.sl):
                if high_t < low_t:
                    self.buy, self.open_buy_price = False, None
                    self.exit_time = time
                    return (self.tp - self.cost) * self.leverage, self.exit_time
                elif low_t < high_t:
                    self.buy, self.open_buy_price = False, None
                    self.exit_time = time
                    return (self.sl - self.cost) * self.leverage, self.exit_time
                else:
                    self.buy, self.open_buy_price = False, None
                    self.exit_time = time
                    return 0, self.exit_time

            elif self.tp < self.var_buy_high:
                self.buy, self.open_buy_price = False, None
                self.exit_time = time
                return (self.tp - self.cost) * self.leverage, self.exit_time

            elif self.var_buy_low < self.sl:
                self.buy, self.open_buy_price = False, None
                self.exit_time = time
                return (self.sl - self.cost) * self.leverage, self.exit_time

        if self.sell:
            self.var_sell_high = -(bar_high - self.open_sell_price) / self.open_sell_price
            self.var_sell_low = -(bar_low - self.open_sell_price) / self.open_sell_price

            if (self.tp < self.var_sell_low) and (self.var_sell_high < self.sl):
                if low_t < high_t:
                    self.sell, self.open_sell_price = False, None
                    self.exit_time = time
                    return (self.tp - self.cost) * self.leverage, self.exit_time
                elif high_t < low_t:
                    self.sell, self.open_sell_price = False, None
                    self.exit_time = time
                    return (self.sl - self.cost) * self.leverage, self.exit_time
                else:
                    self.sell, self.open_sell_price = False, None
                    self.exit_time = time
                    return 0, self.exit_time

            elif self.tp < self.var_sell_low:
                self.sell, self.open_sell_price = False, None
                self.exit_time = time
                return (self.tp - self.cost) * self.leverage, self.exit_time

            elif self.var_sell_high < self.sl:
                self.sell, self.open_sell_price = False, None
                self.exit_time = time
                return (self.sl - self.cost) * self.leverage, self.exit_time

        return 0, None
