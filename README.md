# Alpha Quant Trading Strategies

A Python research and trading framework for building, backtesting, validating and live-trading systematic forex strategies through MetaTrader 5. The repository contains a small in-house library (`Quantreo/`), a set of rule-based and machine-learning strategies, launcher scripts for three robustness-validation methods (Walk-Forward Optimization, Monte Carlo simulation and Combinatorial Purged Cross-Validation), live-trading bots, historical price data, course notebooks, and research notebooks and a full strategy study written by team members.

This README explains the repository from top to bottom: where everything lives, what each piece does, how the pieces fit together, and how a team member should add a new strategy.

---

## Contents

1. [Origin of this repository](#origin-of-this-repository)
2. [Repository map](#repository-map)
3. [Capabilities](#capabilities)
4. [How it works, step by step](#how-it-works-step-by-step)
5. [Recommended workflow for team members](#recommended-workflow-for-team-members)
6. [Known issues and caveats](#known-issues-and-caveats)
7. [Disclaimer](#disclaimer)
8. [Previous README](#previous-readme)

---

## Origin of this repository

This repository is Jacob Attia's fork, published as [attiaj/Alpha-Quant-Trading-Strategies](https://github.com/attiaj/Alpha-Quant-Trading-Strategies). It is based on the **Alpha Quant Course** by **Lucas Inglese (Quantreo)**, whose original code lives at [Quantreo/Alpha-Quant-Course](https://github.com/Quantreo/Alpha-Quant-Course). The `Quantreo/` library, the `LI_2023_02_*` strategies and their launcher and live scripts, the numbered notebooks `01`-`06`, the `OUT OF SERIES/` folder, the `*_Admiral*` data files and the saved models originate from the course. On top of that, this copy adds environment setup, MT5 demo data, a shared EURUSD 15-minute dataset, bug fixes, and the team's own research notebooks and strategies.

The local clone is set up with two remotes:

| Remote | URL | Purpose |
| --- | --- | --- |
| `origin` | `https://github.com/attiaj/Alpha-Quant-Trading-Strategies` | The team's repository. Push here. |
| `upstream` | `https://github.com/Quantreo/Alpha-Quant-Course` | The original course. Pull updates from here, never push. |

### Pulling updates from the original course

```bash
git fetch upstream
git merge upstream/main
```

If you cloned from `origin` and do not have the `upstream` remote yet, add it first:

```bash
git remote add upstream https://github.com/Quantreo/Alpha-Quant-Course
```

Notes:

- At the time of writing, `main` already contains everything on `upstream/main` (`git log main..upstream/main` is empty).
- Upstream also has a **`v2-beta`** branch. As of the last fetch it has one commit not on `main`, "Fix CPCV Leakage" (2025-10-17). Inspect it before adopting anything from it:

  ```bash
  git fetch upstream
  git log main..upstream/v2-beta
  git diff main...upstream/v2-beta
  ```

  If you only want specific fixes, `git cherry-pick <commit>` is safer than merging the whole branch.
- Upstream still names its dependency file `requierements.txt` (misspelled). This fork renamed it to `requirements.txt`, so upstream changes to that file may need to be copied over by hand.

---

## Repository map

Folder names containing spaces or parentheses are linked with URL-encoded paths.

| Path | What it contains |
| --- | --- |
| [`Quantreo/`](Quantreo/) | The core library: backtester, optimizers, validation methods, indicators, MT5 helpers and live signal functions. See [Quantreo library](#the-quantreo-library). |
| [`Strategies/`](Strategies/) | Strategy classes. The course strategies are one per file, named `LI_2023_02_<Name>.py`; team members' strategies live in their own subfolders. |
| [`Launching (WFO)/`](Launching%20%28WFO%29/) | One Walk-Forward Optimization launcher per strategy (`Launching_LI_2023_02_<Name>.py`). The ML launchers can also save trained models. |
| [`Launching (MC)/`](Launching%20%28MC%29/) | One Monte Carlo launcher per strategy (`Launching_MC_LI_2023_02_<Name>.py`). |
| [`Launching (CPCV)/`](Launching%20%28CPCV%29/) | One Combinatorial Purged Cross-Validation launcher per strategy (`Launching_CPCV_LI_2023_02_<Name>.py`). |
| [`LiveTrading/`](LiveTrading/) | Live bots that run on a MetaTrader 5 terminal (`Live_<SYMBOL>_<TF>_LI_2023_02_<Name>.py`), plus `Live_TEST_CONFIGURATION.py`, a random-signal bot for testing the MT5 connection. |
| [`models/saved/`](models/saved/) | Trained scikit-learn objects saved with `joblib` (extension `.jolib`): models, scalers and PCA transforms used by the live ML bots. |
| [`models/train/`](models/train/) | Empty placeholder folder. |
| [`Data/create_databases.py`](Data/create_databases.py) | Downloads OHLCV bars from MT5 and optionally saves them to CSV. |
| [`Data/HighLowTime.py`](Data/HighLowTime.py) | Adds `high_time` / `low_time` columns to a bar file using a lower-timeframe file, producing the `*_READY.csv` files the backtester needs. |
| [`Data/FixTimeBars/`](Data/FixTimeBars/) | Historical price data in CSV. See [Data files](#data-files). |
| [`Notebooks/`](Notebooks/) | Course notebooks `01`-`06` and team research notebooks `<Name>_<Topic>.ipynb`. |
| [`OUT OF SERIES/`](OUT%20OF%20SERIES/) | Two extra course notebooks with Parquet data: intra-bar features (Hurst exponent) and market-trend features (rolling regression slope). |
| [`requirements.txt`](requirements.txt) | Pinned Python dependencies. |
| `.gitignore` | Ignores `__pycache__/`, `*.pyc`, `.vscode/settings.json` and `Alpha Quant Notes.docx` (Jacob's personal notes). |
| `.gitattributes` | Line-ending normalisation (`* text=auto`). |

### Data files

All files in `Data/FixTimeBars/` share the MT5 bar format: a `time` index column followed by `open, high, low, close, tick_volume, spread, real_volume`. Files ending in `_READY` (or `_Ready`) also have `low_time` and `high_time`, the timestamps at which the bar's low and high occurred. The backtester needs those two columns.

| File | Bars | Range | Notes |
| --- | --- | --- | --- |
| `AUDUSD_4H_Admiral_READY.csv` | 4H | 2015-02 to 2023-02 | Used by almost every course launcher. |
| `EURUSD_4H_Admiral_READY.csv` | 4H | 2015-01 to 2023-02 | Used by the BinLogReg WFO launcher and notebook 06. |
| `GBPUSD_4H_Demo_READY.csv` | 4H | 2018-05 to 2026-05 | Built from MT5 demo data by `HighLowTime.py`. |
| `EURUSD_15M_Demo_Ready.csv` | 15M | 2016-10-13 to 2026-10-13 | Shared team dataset from MetaQuotes-Demo, with `high_time` / `low_time` resolved from 1-minute bars. |
| `AUDUSD_4H_Admiral.csv`, `EURUSD_4H_Admiral.csv` | 4H | 2003 to 2023 | Raw, no high/low times. |
| `AUDUSD_30M_Admiral.csv`, `EURUSD_30M_Admiral.csv`, `GBPUSD_30M_Admiral.csv` | 30M | 2015 to 2023 | Raw lower-timeframe inputs for `HighLowTime.py`. |
| `GBPUSD_4H_Demo.csv`, `GBPUSD_30M_Demo.csv` | 4H / 30M | 2016-2018 to 2026-05 | Raw MT5 demo inputs for `GBPUSD_4H_Demo_READY.csv`. |
| `GBPUSD_Admiral_ticks_imbalance_bars_50.csv` | Tick imbalance bars | 2017 to 2022 | Non-time bars with `number_ticks`, `high_time`, `low_time` and bid/ask slippage columns. Not used by any script. |

Some scripts and notebooks expect data files that are **not committed** and must be generated locally with `Data/create_databases.py` and `Data/HighLowTime.py`. Check the first cells of a notebook or the top of a script for the files it reads.

---

## Capabilities

### The Quantreo library

| Module | Contents |
| --- | --- |
| [`Backtest.py`](Quantreo/Backtest.py) | `Backtest(data, TradingStrategy, parameters, run_directly=False, title=None)`. Instantiates the strategy, then `run()` walks bar by bar, calling `get_entry_signal` and `get_exit_signal`, and records each closed trade's return, duration and buy/sell counts. `display_metrics()` prints average trade lifetime, number of buys and sells, total return, maximum drawdown, hit ratio, reward/risk ratio, best and worst month, average monthly return and share of profitable months. `display_graphs()` plots the cumulative return and drawdown. `get_ret_dd()` returns (return %, max drawdown %) for optimizers. Returns are summed, not compounded. |
| [`ParamsOptimization.py`](Quantreo/ParamsOptimization.py) | `ParamsOptimization`: a simple grid search over every combination of `parameters_range` (merged with `fixed_parameters`) on one dataset, ranked by return / drawdown. The course describes it as the first building block of the walk-forward optimizer. |
| [`WalkForwardOptimization.py`](Quantreo/WalkForwardOptimization.py) | `WalkForwardOptimization`. Splits the data into consecutive train/test windows (anchored by default), grid-searches each train window, smooths the chosen parameters across windows and tests them on the following out-of-sample window. Details in [Validation methods](#validation-methods). |
| [`MonteCarlo.py`](Quantreo/MonteCarlo.py) | `MonteCarlo`. Generates synthetic price paths by resampling real bars and backtests the strategy on each path. |
| [`CombinatorialPurgedCV.py`](Quantreo/CombinatorialPurgedCV.py) | `CombinatorialPurgedCV`. Combinatorial train/test splits with purging and embargo, plus a Probability of Backtest Overfitting (PBO) estimate. |
| [`DataPreprocessing.py`](Quantreo/DataPreprocessing.py) | Indicator and labelling functions built on the `ta` library: `sma`, `sma_diff` (fast SMA minus slow SMA), `rsi`, `atr`, `sto_rsi` (Stochastic RSI with K and D lines, scaled 0-100), `ichimoku` (Span A, Span B, Base, Conversion), `previous_ret` (return over `n` bars), `k_enveloppe` (distance from EMAs of highs and lows), `candle_information` (candle direction, body filling ratio, amplitude). ML helpers: `data_split` (time-ordered train/test split with the target shifted one bar ahead), `binary_signal` (label +1 if the `n`-bar forward return is positive, else -1) and `quantile_signal` (label +1 above the upper quantile of forward returns, -1 below the lower quantile, 0 otherwise; quantiles are computed on the training part only). |
| [`MetaTrader5.py`](Quantreo/MetaTrader5.py) | MT5 helpers: `timeframes_mapping` (names such as `"4-hours"` mapped to an MT5 constant and a length in minutes), `get_verification_time` (list of clock times at which a bar of that length closes), `get_rates` (latest `n` bars as a DataFrame), `find_filling_mode` (works around brokers whose filling mode is misreported), `send_order` (open with percentage TP/SL, or close a position by ticket), `resume` (DataFrame of open positions) and `run` (closes the strategy's existing position when the signal no longer agrees with it, then opens new trades). |
| [`LiveTradingSignal.py`](Quantreo/LiveTradingSignal.py) | One function per strategy that downloads the last 500 bars from MT5, rebuilds the features and returns `buy, sell` (and, for the ATR strategies, `pct_tp, pct_sl`) for the latest bar: `random`, `li_2023_02_RsiSma`, `li_2023_02_LogRegQuantile`, `li_2023_02_RsiSmaAtr`, `li_2023_02_Ichimoku_1`, `li_2023_02_StoRsiAtr`, `li_2023_02_LinSvcQuantile`, `li_2023_02_TreePcaQuantile`. ML functions load saved models from disk. |

### The strategy class contract

Every strategy is a class that the backtester and all three validators can drive. To be compatible, a class must:

- take `(data, parameters)` in `__init__`, where `data` is a DataFrame with at least `open, high, low, close, high_time, low_time` and `parameters` is a dictionary;
- compute its features and a `signal` column (or `ml_signal` for ML strategies) of +1, -1 or 0;
- set `self.start_date_backtest` and `self.output_dictionary` (a copy of the parameters; ML strategies also put the trained model, scaler and PCA in it and set `train_mode` to `False`, which is how a model trained on one window is reused on the next);
- implement `get_entry_signal(time)`, returning `(entry_signal, entry_time)`. The signal is read from the **previous** bar (`signal[-2]`) and the trade is filled at the **current** bar's open, which avoids look-ahead bias. Only one position is open at a time;
- implement `get_exit_signal(time)`, returning `(position_return, exit_time)`. Trades exit at the take-profit (`tp`) or stop-loss (`sl`, a negative number). If both are touched in the same bar, `high_time` and `low_time` decide which was hit first. The return is `(tp - cost) * leverage` or `(sl - cost) * leverage`.

### Strategies

All course strategies use `cost = 0.0001` and `leverage = 5` in their launchers.

| File / class | Type | Entry logic | Exit | Backtest data in launchers | Live script |
| --- | --- | --- | --- | --- | --- |
| [`LI_2023_02_RsiSma`](Strategies/LI_2023_02_RsiSma.py) / `RsiSma` | Rules | Divergence: buy when the fast SMA is below the slow SMA (downtrend) **and** RSI is rising; sell when the fast SMA is above the slow SMA **and** RSI is falling. | Fixed TP/SL | AUDUSD 4H (fast 72, slow 120, RSI 25) | EURUSD-Z, 8H, SMA 60/120, RSI 21, TP 0.63%, SL 0.5% |
| [`LI_2023_02_RsiSmaAtr`](Strategies/LI_2023_02_RsiSmaAtr.py) / `RsiSmaAtr` | Rules | Same signal as `RsiSma`. | Dynamic: TP and SL at plus/minus 3 x ATR(15) of the previous bar, converted to a percentage at entry | AUDUSD 4H | AUDUSD-Z, 4H |
| [`LI_2023_02_StoRsiAtr`](Strategies/LI_2023_02_StoRsiAtr.py) / `StoRsiAtr` | Rules | Stochastic RSI: buy when K and D are both below 30 and K crosses below D; sell when both are above 70 and K crosses above D. | Dynamic: plus/minus 2 x ATR(`atr_period`) | AUDUSD 4H (`sto_period`, `atr_period` in 7 or 14) | `Live_EURUSD_8H_LI_2023_02_RsiStoAtr.py`, AUDUSD-Z, 8H |
| [`LI_2023_02_Ichimoku_1`](Strategies/LI_2023_02_Ichimoku_1.py) / `Ichimoku_1` | Rules | Trend following: buy when Span A is above Span B and the Conversion line crosses above the Base line; sell on the mirror condition. | Fixed TP/SL | AUDUSD 4H (windows 7/9/12 and 26/39/52) | AUDUSD-Z, 4H, windows 9/26 |
| [`LI_2023_02_BinLogReg`](Strategies/LI_2023_02_BinLogReg.py) / `BinLogReg` | ML | Logistic regression on `SMA_diff`, `RSI`, `ATR`, trained on a binary label (is the `look_ahead_period`-bar forward return positive?). Trades the predicted direction. | Fixed TP/SL | EURUSD 4H in WFO, AUDUSD 4H in MC/CPCV | AUDUSD-Z, 4H, long-only signal function |
| [`LI_2023_02_LinSvcQuantile`](Strategies/LI_2023_02_LinSvcQuantile.py) / `LinSvcQuantile` | ML | `StandardScaler` + `LinearSVC` on `SMA_diff`, `RSI`, `ATR`, trained on the three-class quantile label (+1 / 0 / -1). | Fixed TP/SL | AUDUSD 4H | AUDUSD-Z, 8H |
| [`LI_2023_02_TreePcaQuantile`](Strategies/LI_2023_02_TreePcaQuantile.py) / `TreePcaQuantile` | ML | 13 features (`SMA_diff`, `RSI`, `ATR`, candle direction/filling/amplitude, Ichimoku Span A/B/Base, Stochastic RSI and its K/D, 60-bar previous return), standardised, reduced to 3 PCA components, fed to a `DecisionTreeClassifier(max_depth=6)` trained on the quantile label. | Fixed TP/SL | AUDUSD 4H | AUDUSD-Z, 8H |
The live scripts are named after EURUSD, but most of them trade `AUDUSD-Z` (the `-Z` suffix is a broker symbol name). Check the `symbol` variable before running one.

### Validation methods

All three validators take the strategy **class**, a `fixed_parameters` dictionary and a `parameters_range` dictionary (lists of values to try). They run on the `*_READY.csv` data.

#### Walk-Forward Optimization (`Launching (WFO)/`)

- The data is cut into windows of `length_train_set` bars for training, followed by a test window of `length_train_set / pct_train_set - length_train_set` bars (with the default `pct_train_set=0.80`, a 5,000-bar train window gives a 1,250-bar test window). Windows are anchored (training always starts at the beginning) unless `anchored=False`.
- On each train window, a random fraction `randomness` of the parameter grid is backtested and ranked by `return + 2 * drawdown` (drawdown is negative, so this penalises it twice).
- The best parameters are smoothed across windows (exponential mean for float parameters, mode otherwise). For ML strategies the model is retrained on the train window and passed to the test window through `output_dictionary`.
- **Launcher output:** a progress bar, `BEST PARAMETERS` (the smoothed parameters of the last window, including any trained model), then `WFO.display()`: the metrics table and equity/drawdown chart of all out-of-sample windows stitched together.
- **Model saving:** the BinLogReg, LinSvcQuantile and TreePcaQuantile WFO launchers have `save` and `name` variables at the top. With `save = True` they `joblib.dump` the last window's model (and scaler / PCA) to `../models/saved/<name>_model.jolib`, `_sc.jolib` and `_pca.jolib`. Only the LinSvcQuantile launcher currently has `save = True`.

#### Monte Carlo (`Launching (MC)/`)

- `generate_path` resamples whole real bars (open-to-low, open-to-high and open-to-close percentage moves together with bar length and the timing of the high and low) and chains them into a synthetic path that starts from the last real open. Resampling whole bars keeps each synthetic bar internally consistent; notebook `06_Monte_Carlo.ipynb` explains why sampling each move independently gives unrealistic bars.
- The launchers call `generate_paths(500, 2000)` (500 paths of 2,000 bars; the StoRsiAtr launcher uses 10 paths) with a single parameter set, backtest every path and call `display_results()`.
- **Launcher output:** three histograms: return distribution, drawdown distribution and annualised Calmar ratio distribution (`discount_calmar_ratio = 252*6` 4H bars per year in the launchers).

#### Combinatorial Purged Cross-Validation (`Launching (CPCV)/`)

- The data is split into `N=10` equal groups and every combination of `k=2` test groups is evaluated (45 train/test splits). Training groups next to a test group are purged (`purge_pct=0.10` of the group before a test group) and embargoed (twice that after it) to limit leakage.
- For each split, every parameter combination is scored on the train and test sets with return / |drawdown|. The best train combination is recorded.
- `get_pbo()` ranks the best-in-train combination within the test results, converts each rank to a logit and reports the **Probability of Backtest Overfitting** as the share of negative logits.
- **Launcher output:** each split's rank and logit printed to the console, then one figure with (A) a histogram of rank logits annotated with the PBO, (B) a train-versus-test criterion scatter with a regression line and the share of splits with a positive out-of-sample criterion, and (C) a map of the train and test periods of every split.

### Live trading with MetaTrader 5

Each live script in `LiveTrading/`:

1. connects to the running MT5 terminal (`mt5.initialize()`) and prints the login, server, balance and equity;
2. loops forever and, at each bar close given by `get_verification_time`, selects the symbol in the Market Watch;
3. calls its signal function from `Quantreo/LiveTradingSignal.py` (ML functions load the `.jolib` files from `../models/saved/`);
4. calls `resume()` and, if the strategy has no open position with the same symbol and lot size, calls `run()`, which sends market orders with take-profit and stop-loss set as percentages of price (`pct_tp`, `pct_sl`, with the SL given as a positive number). A `magic` number tags the strategy's orders.

`Live_TEST_CONFIGURATION.py` uses the `random` signal on a 1-minute timeframe to check that orders can be sent.

### Data preparation

1. [`Data/create_databases.py`](Data/create_databases.py) pulls up to 99,999 bars for one symbol and timeframe from MT5 (edit the `get_rates(...)` call), prints the first and last 100 rows, and asks for a path to save the CSV.
2. [`Data/HighLowTime.py`](Data/HighLowTime.py) takes a higher-timeframe file and a lower-timeframe file covering the same period. For every higher-timeframe bar it finds when the high and the low occurred in the lower-timeframe bars, adds `high_time` and `low_time`, prints the share of rows where they could not be resolved ("garbage rows") and saves the `_READY.csv` file. It is currently set to build `GBPUSD_4H_Demo_READY.csv` from the GBPUSD 4H and 30M demo files.

### Notebooks

| Notebook | Content |
| --- | --- |
| `01_MQL5_Basics.ipynb` | Connecting Python to MT5: `initialize`, `shutdown`, `last_error`, account info, adding symbols to the Market Watch, symbol info (bid, ask, minimum volume, contract size). |
| `02_Asset_prices_import.ipynb` | Downloading ticks and bars with `copy_ticks_from`, `copy_ticks_range`, `copy_rates_from`, `copy_rates_range`. |
| `03_Backtest_Peace_Code.ipynb` | How cumulative returns, running maximum and drawdown are computed (the maths inside `Backtest`). |
| `04_Walk_Forward_Optimization_peace_of_code.ipynb` | Building the parameter grid with `itertools.product` and cutting anchored or rolling train/test windows. |
| `05_Send_orders.ipynb` | Finding the filling mode, sending buy and sell orders, closing positions and wrapping it all in `send_order`. |
| `06_Monte_Carlo.ipynb` | Monte Carlo intuition: the wrong way (independent sampling) and the right way (whole-bar sampling) to build synthetic bars. Imports `mplfinance`, which is not in `requirements.txt`. |
| `OUT OF SERIES/INTRA BAR FEATURES/INTRA-BARS FEATURES AQP.ipynb` | Aggregates 1-minute EURUSD (2020-2024) into 4H bars with a rolling Hurst exponent and saves `4H_EURUSD.parquet`. Needs the `hurst` package. |
| `OUT OF SERIES/MARKET TREND FEATURES/TREND FEATURES.ipynb` | Rolling linear-regression slope of the 4H close as a trend feature, plotted against price. |

Team members' research notebooks also live in `Notebooks/`, named `<Name>_<Topic>.ipynb`.

---

## How it works, step by step

```text
MT5 terminal
   |  Data/create_databases.py            (download bars)
   v
Raw bars: SYMBOL_TF_Broker.csv  +  lower-timeframe file
   |  Data/HighLowTime.py                 (add high_time / low_time)
   v
SYMBOL_TF_Broker_READY.csv
   |  Quantreo/DataPreprocessing.py       (indicators, ML labels)
   v
Strategy class in Strategies/            (features, signal, entry/exit rules, ML training)
   |  Quantreo/Backtest.py                (bar-by-bar simulation, metrics, charts)
   v
Parameter search                         (ParamsOptimization or the grids inside the validators)
   |
   v
Robustness validation                    (Launching (WFO) / Launching (MC) / Launching (CPCV))
   |  joblib.dump in the WFO launcher     (ML models -> models/saved/*.jolib)
   v
Live signal function in Quantreo/LiveTradingSignal.py
   |  LiveTrading/Live_*.py + Quantreo/MetaTrader5.py
   v
Orders on the MT5 account (demo first)
```

1. **Get data.** Download bars from MT5 with `create_databases.py` (or use the committed files). You need the trading timeframe and a lower timeframe covering the same dates.
2. **Resolve intrabar timing.** Run `HighLowTime.py` to add `high_time` and `low_time`. Without them the backtester cannot tell whether the take-profit or stop-loss was hit first in a bar.
3. **Engineer features.** Use the functions in `DataPreprocessing.py` (or research new ones in a notebook, as the team notebooks do) and check that each feature is predictive, stable and not redundant.
4. **Write the strategy class.** Follow [the contract](#the-strategy-class-contract): build features and a signal in `get_features`, enter on the previous bar's signal at the current open, exit on TP/SL. ML strategies train in `train_model` when `train_mode` is `True` and store the fitted objects in `output_dictionary`.
5. **Backtest.** `Backtest(data, MyStrategy, params).display()` prints the metrics and plots the equity and drawdown curves.
6. **Optimise parameters.** Define `params_fixed` and `params_range`. A plain grid search is available in `ParamsOptimization`, but the validators below search the grid themselves, so parameters are always chosen on training data only.
7. **Validate robustness.** Run the WFO launcher (stitched out-of-sample performance), the MC launcher (distribution of results on synthetic paths) and the CPCV launcher (probability of overfitting). A strategy that only looks good in-sample should be dropped here.
8. **Save models.** For ML strategies, set `save = True` in the WFO launcher to write the last window's model, scaler and PCA to `models/saved/`.
9. **Write the live signal function.** Add a function to `LiveTradingSignal.py` (or your own signal file) that rebuilds exactly the same features from `get_rates` and returns `buy, sell`.
10. **Trade live.** Copy a script in `LiveTrading/`, set `symbol`, `lot`, `magic`, `timeframe`, `pct_tp`, `pct_sl` and the signal call, and run it on a machine with MT5 open. Start on a demo account.

---

## Recommended workflow for team members

### 1. Environment setup

Use a dedicated Conda environment named **AlphaQuant** with Python 3.10 so dependencies match `requirements.txt`.

```bash
conda create -n AlphaQuant python=3.10 -y
conda activate AlphaQuant
pip install -r requirements.txt
```

Register a Jupyter kernel for the notebooks in `Notebooks/`:

```bash
pip install ipykernel
python -m ipykernel install --user --name AlphaQuant --display-name "Python (AlphaQuant)"
```

Some notebooks need packages that are not in `requirements.txt`: `mplfinance` (notebook 06), `hurst` (OUT OF SERIES intra-bar notebook) and a Parquet engine such as `pyarrow` (both OUT OF SERIES notebooks). Install them only if you need those notebooks:

```bash
pip install mplfinance hurst pyarrow
```

**Editor setup (VS Code / Cursor).** `.vscode/settings.json` is listed in `.gitignore`, so it is not shipped with the repository and each person keeps their own. To use the AlphaQuant interpreter and open terminals with the environment activated, create `.vscode/settings.json` with your own paths, for example:

```json
{
  "python.defaultInterpreterPath": "C:\\Users\\<you>\\anaconda3\\envs\\AlphaQuant\\python.exe",
  "python.condaPath": "C:\\Users\\<you>\\anaconda3\\Scripts\\conda.exe",
  "python.terminal.activateEnvironment": false,
  "terminal.integrated.profiles.windows": {
    "AlphaQuant": {
      "source": "PowerShell",
      "args": ["-NoExit", "-Command", "conda activate AlphaQuant"]
    }
  },
  "terminal.integrated.defaultProfile.windows": "AlphaQuant"
}
```

Reload the editor window and choose **Python (AlphaQuant)** in the notebook kernel picker.

**MetaTrader 5.** The `MetaTrader5` Python package only works on Windows with the MT5 terminal installed and logged in. Enable **Algo Trading** in the terminal, and add every symbol you trade to the Market Watch. Data download, notebooks 01, 02 and 05 and the live scripts all need MT5 running. Backtesting and validation on the committed CSV files do not, but `Quantreo/LiveTradingSignal.py` and `Quantreo/MetaTrader5.py` import `MetaTrader5`, so the package must still be installed.

### 2. Running scripts

The course launchers import `Strategies` and `Quantreo` as packages and read data from `../Data/...`. Run them **from inside their folder** with the **repository root on `PYTHONPATH`** (PowerShell):

```powershell
cd "<path>\Alpha-Quant-Course"
$env:PYTHONPATH = (Get-Location).Path
cd "Launching (WFO)"
python Launching_LI_2023_02_RsiSma.py
```

The same applies to `Launching (MC)/`, `Launching (CPCV)/` and `LiveTrading/` (whose model paths are `../models/saved/...`). Notebooks resolve paths relative to `Notebooks/`, which is Jupyter's default working directory when you open them there. Expect WFO and CPCV runs to take a long time: the backtester re-slices the data on every bar.

### 3. Building and validating a new strategy

Follow the existing conventions so that every launcher and live script keeps working.

1. **Create a branch** (see [Git tips](#5-git-tips)).
2. **Pick an identifier.** The course files use `LI_2023_02_<Name>` (Lucas Inglese's initials, then a year and month). Use your own initials and the current date, for example `JA_2026_11_VwapRsi`, or a personal subfolder in `Strategies/` with files prefixed by your initials.
3. **Prepare data.** Use a committed `_READY` file or the shared `EURUSD_15M_Demo_Ready.csv`. For a new symbol or timeframe, run `create_databases.py` for both timeframes and then `HighLowTime.py`, and save the result as `Data/FixTimeBars/<SYMBOL>_<TF>_<Broker>_READY.csv`.
4. **Research features** in a notebook (`Notebooks/<YourName>_<Topic>.ipynb`). If a feature is reusable, add it to `Quantreo/DataPreprocessing.py` in the same style (`def name(df, col, n)`, returning `df` with a new column), and commit it together with any notebook that imports it.
5. **Write the class** in `Strategies/<ID>.py`. Start from the closest existing strategy (`LI_2023_02_RsiSma.py` for rules, `LI_2023_02_LinSvcQuantile.py` for ML) and change `get_features` (and `train_model` for ML). Keep the entry and exit methods unchanged unless you understand the look-ahead protection.
6. **Backtest quickly** in a notebook or a scratch script with `Backtest(df, MyStrategy, params).display()`. Do not leave test code at module level in the strategy file, because the launchers import it with `from Strategies.<ID> import *`.
7. **Add launchers** by copying the existing ones and changing the import, data path, `params_fixed` and `params_range`:
   - `Launching (WFO)/Launching_<ID>.py`
   - `Launching (MC)/Launching_MC_<ID>.py`
   - `Launching (CPCV)/Launching_CPCV_<ID>.py`
8. **Validate.** Keep a strategy only if the stitched WFO result is acceptable, the Monte Carlo distributions are not dominated by losses, and the CPCV probability of overfitting is low. Write down how many variants you tried; the more you try, the higher the bar.
9. **Save models** (ML only) with `save = True` and `name = "<ID>_<SYMBOL>"`, producing `models/saved/<ID>_<SYMBOL>_model.jolib` (plus `_sc` / `_pca`).
10. **Go live on demo.** Add a `<id_lowercase>(symbol, timeframe, ...)` function to `Quantreo/LiveTradingSignal.py` (or a separate signal file) that rebuilds the same features with the same parameters used in training, then copy a live script to `LiveTrading/Live_<SYMBOL>_<TF>_<ID>.py`. Give it a unique `magic` number.

### 4. Adding notebooks

- Put research notebooks in `Notebooks/` and name them `<YourName>_<Topic>.ipynb`.
- Read data relative to the repository (for example `../Data/FixTimeBars/...`), and import shared code by adding the repository root to `sys.path`.
- If the notebook needs a data file that is not committed, say how to generate it in the first cell.
- Start with a short markdown summary (question, data, method) and end with a conclusion.
- Never put account numbers or passwords in a notebook or script that you commit.

### 5. Git tips

- Work on a branch rather than uploading files on the GitHub website:

  ```bash
  git checkout main
  git pull origin main
  git checkout -b <yourname>/<topic>
  # ...work...
  git add <files you changed>
  git commit -m "Short description of the change"
  git push -u origin <yourname>/<topic>
  ```

- Open a pull request on [attiaj/Alpha-Quant-Trading-Strategies](https://github.com/attiaj/Alpha-Quant-Trading-Strategies) and ask a teammate to review it. Describe what changed, which data you used and the validation results.
- Keep changes to shared code (`Quantreo/`, existing strategies) in separate, small pull requests, and say in the description which results they affect.
- Do not commit `__pycache__/`, `.vscode/settings.json`, large generated data or personal notes.
- To bring in course updates: `git fetch upstream` then `git merge upstream/main` (see [Origin of this repository](#origin-of-this-repository)).

---

## Known issues and caveats

These are things found while reading the code. They are listed so that nobody is surprised; none of them is fixed by this README.

- **8-hour timeframe.** `timeframes_mapping["8-hours"]` in `Quantreo/MetaTrader5.py` is `[mt5.TIMEFRAME_H8, 420]`. 420 minutes is 7 hours, so the 8H live scripts check for signals on a 7-hour clock rather than at 8-hour bar closes.
- **`Ichimoku_1` long exit.** In `get_exit_signal`, a long position that hits neither TP nor SL on a bar is closed with a return of 0 on that bar (there is an extra `else` branch on the buy side only). Short positions are held until TP or SL.
- **Live versus backtest differences.** `li_2023_02_StoRsiAtr` uses 3 x ATR for TP/SL while the `StoRsiAtr` class uses 2 x ATR. `li_2023_02_LogRegQuantile` (used by the BinLogReg live script) only ever returns `sell = False`. The ML live scripts call their signal functions with SMA/RSI/ATR periods (30, 80, 14, 5) that do not all match the fixed parameters in the corresponding WFO launchers. Check that live features match what the saved model was trained on.
- **Monthly metrics years.** `Backtest.display_metrics` only aggregates months from 2015 to 2025, so monthly statistics ignore 2026 data (for example in the 2026 demo files).
- **Optimisation criteria differ.** WFO ranks by `return + 2 * drawdown`, CPCV by return / |drawdown| and `ParamsOptimization` by return / drawdown, so the three can pick different parameters from the same grid.
- **Live exits.** The live scripts only call `run()` when there is no open position with the same symbol and lot, so in practice positions close by TP/SL rather than by signal.

---

## Disclaimer

This repository is for **educational and research purposes only**. Nothing in it is investment advice or a recommendation to buy or sell any instrument. Backtests and validation results describe the past under simplifying assumptions (fixed costs, no slippage model, summed returns) and do not guarantee future performance. Leveraged forex trading can lose more than the money you put in. The live-trading scripts send real orders to whatever account the MT5 terminal is logged into: run them on a **demo account** first, use the smallest lot sizes, monitor them, and never trade money you cannot afford to lose. The authors and contributors accept no responsibility for any losses.

---

## Previous README

The README below is the version Jacob wrote before this one, kept verbatim with its headings demoted (`#` to `###`, `##` to `####`, `###` to `#####`). Note that `.vscode/settings.json` is no longer tracked in git, so the link to it below only works on machines that have created that file locally.

### Alpha Quant Trading Strategies

Course materials and code for quantitative trading research (strategies, backtests, walk-forward optimization, live trading scripts, and Jupyter notebooks).

#### Environment setup

Use a dedicated Conda environment named **AlphaQuant** so dependencies match `requirements.txt`.

##### 1. Create and activate the environment

```bash
conda create -n AlphaQuant python=3.10 -y
conda activate AlphaQuant
```

##### 2. Install dependencies

From the repository root:

```bash
pip install -r requirements.txt
```

##### 3. Jupyter notebooks (optional but recommended)

Notebooks in `Notebooks/` need a Jupyter kernel in this environment:

```bash
pip install ipykernel
python -m ipykernel install --user --name AlphaQuant --display-name "Python (AlphaQuant)"
```

#### Editor setup (VS Code / Cursor)

This repo includes [`.vscode/settings.json`](.vscode/settings.json) to use the **AlphaQuant** interpreter and auto-activate it in the terminal.

After cloning, **update the paths** in that file to match your machine (Anaconda install location and env name). Typical keys to edit:

- `python.defaultInterpreterPath` — path to `...\envs\AlphaQuant\python.exe`
- `python.condaPath` — path to your `conda.exe` (e.g. `...\anaconda3\Scripts\conda.exe`)

Then reload the editor window and, for notebooks, choose **Python (AlphaQuant)** or the AlphaQuant environment from the kernel picker.

#### Notes

- **MetaTrader5** and several packages are Windows-oriented; live trading and MT5 notebooks expect MetaTrader 5 installed and algo trading enabled in the platform.
- To pull updates from the original course repository, use the `upstream` remote if configured: `git fetch upstream` then merge as needed.
