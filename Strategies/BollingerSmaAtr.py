
from Quantreo.DataPreprocessing import *


class BollingerSmaAtr:

    def __init__(self, data, parameters):
        self.data = data
        self.bb_period = parameters["bb_period"]
        self.bb_dev = parameters["bb_dev"]
        self.slow_sma = parameters["slow_sma"]
        self.atr_period = parameters["atr_period"]
        self.atr_mult = parameters["atr_mult"]
        self.tp, self.sl = None, None
        self.cost = parameters["cost"]
        self.leverage = parameters["leverage"]
        self.get_features()
        self.start_date_backtest = self.data.index[0]

        self.buy, self.sell = False, False
        self.open_buy_price, self.open_sell_price = None, None
        self.entry_time, self.exit_time = None, None

        self.var_buy_high, self.var_sell_high = None, None
        self.var_buy_low, self.var_sell_low = None, None

        self.output_dictionary = parameters.copy()

    def get_features(self):
        self.data = sma(self.data, "close", self.slow_sma)
        self.data = bollinger(self.data, "close", self.bb_period, self.bb_dev)
        self.data = atr(self.data, self.atr_period)

        # ATR from the previous closed bar, so the stop is known at the open.
        atr_prev = self.data["ATR"].shift(1)
        self.data["TP_level"] = self.data["open"] + self.atr_mult * atr_prev
        self.data["SL_level"] = self.data["open"] - self.atr_mult * atr_prev
        self.data["TP_pct"] = (self.data["TP_level"] - self.data["open"]) / self.data["open"]
        self.data["SL_pct"] = (self.data["SL_level"] - self.data["open"]) / self.data["open"]

        lower = self.data[f"BB_LOWER_{self.bb_period}"]
        upper = self.data[f"BB_UPPER_{self.bb_period}"]
        sma_col = self.data[f"SMA_{self.slow_sma}"]

        # Reclaim: previous close was outside the band, this close is back inside.
        reclaim_lower = (self.data["close"].shift(1) < lower.shift(1)) & (self.data["close"] > lower)
        reject_upper = (self.data["close"].shift(1) > upper.shift(1)) & (self.data["close"] < upper)

        uptrend = self.data["close"] > sma_col
        downtrend = self.data["close"] < sma_col

        self.data["signal"] = 0
        self.data.loc[uptrend & reclaim_lower, "signal"] = 1
        self.data.loc[downtrend & reject_upper, "signal"] = -1

    def get_entry_signal(self, time):
        """
        Entry signal
        :param time: TimeStamp of the row
        :return: Entry signal of the row and entry time
        """
        if len(self.data.loc[:time]) < 2:
            return 0, self.entry_time

        # Trade the signal from the previous closed bar, at this bar's open.
        entry_signal = 0
        if self.data.loc[:time]["signal"][-2] == 1:
            entry_signal = 1
        elif self.data.loc[:time]["signal"][-2] == -1:
            entry_signal = -1

        if entry_signal == 1 and not self.buy and not self.sell:
            self.buy = True
            self.open_buy_price = self.data.loc[time]["open"]
            self.tp, self.sl = self.data.loc[time]["TP_pct"], self.data.loc[time]["SL_pct"]
            self.entry_time = time
        elif entry_signal == -1 and not self.sell and not self.buy:
            self.sell = True
            self.open_sell_price = self.data.loc[time]["open"]
            self.tp, self.sl = self.data.loc[time]["TP_pct"], self.data.loc[time]["SL_pct"]
            self.entry_time = time
        else:
            entry_signal = 0

        return entry_signal, self.entry_time

    def get_exit_signal(self, time):
        """
        Take-profit & Stop-loss exit signal
        :param time: TimeStamp of the row
        :return: P&L of the position IF we close it
        """
        if self.buy:
            self.var_buy_high = (self.data.loc[time]["high"] - self.open_buy_price) / self.open_buy_price
            self.var_buy_low = (self.data.loc[time]["low"] - self.open_buy_price) / self.open_buy_price

            if (self.tp < self.var_buy_high) and (self.var_buy_low < self.sl):
                if self.data.loc[time]["high_time"] < self.data.loc[time]["low_time"]:
                    self.buy = False
                    self.open_buy_price = None
                    position_return_buy = (self.tp - self.cost) * self.leverage
                    self.exit_time = time
                    return position_return_buy, self.exit_time
                elif self.data.loc[time]["low_time"] < self.data.loc[time]["high_time"]:
                    self.buy = False
                    self.open_buy_price = None
                    position_return_buy = (self.sl - self.cost) * self.leverage
                    self.exit_time = time
                    return position_return_buy, self.exit_time
                else:
                    self.buy = False
                    self.open_buy_price = None
                    self.exit_time = time
                    return 0, self.exit_time

            elif self.tp < self.var_buy_high:
                self.buy = False
                self.open_buy_price = None
                position_return_buy = (self.tp - self.cost) * self.leverage
                self.exit_time = time
                return position_return_buy, self.exit_time

            elif self.var_buy_low < self.sl:
                self.buy = False
                self.open_buy_price = None
                position_return_buy = (self.sl - self.cost) * self.leverage
                self.exit_time = time
                return position_return_buy, self.exit_time

        if self.sell:
            self.var_sell_high = -(self.data.loc[time]["high"] - self.open_sell_price) / self.open_sell_price
            self.var_sell_low = -(self.data.loc[time]["low"] - self.open_sell_price) / self.open_sell_price

            if (self.tp < self.var_sell_low) and (self.var_sell_high < self.sl):
                if self.data.loc[time]["low_time"] < self.data.loc[time]["high_time"]:
                    self.sell = False
                    self.open_sell_price = None
                    position_return_sell = (self.tp - self.cost) * self.leverage
                    self.exit_time = time
                    return position_return_sell, self.exit_time
                elif self.data.loc[time]["high_time"] < self.data.loc[time]["low_time"]:
                    self.sell = False
                    self.open_sell_price = None
                    position_return_sell = (self.sl - self.cost) * self.leverage
                    self.exit_time = time
                    return position_return_sell, self.exit_time
                else:
                    self.sell = False
                    self.open_sell_price = None
                    self.exit_time = time
                    return 0, self.exit_time

            elif self.tp < self.var_sell_low:
                self.sell = False
                self.open_sell_price = None
                position_return_sell = (self.tp - self.cost) * self.leverage
                self.exit_time = time
                return position_return_sell, self.exit_time

            elif self.var_sell_high < self.sl:
                self.sell = False
                self.open_sell_price = None
                position_return_sell = (self.sl - self.cost) * self.leverage
                self.exit_time = time
                return position_return_sell, self.exit_time

        return 0, None
