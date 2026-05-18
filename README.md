# Alpha Quant Trading Strategies

Course materials and code for quantitative trading research (strategies, backtests, walk-forward optimization, live trading scripts, and Jupyter notebooks).

## Environment setup

Use a dedicated Conda environment named **AlphaQuant** so dependencies match `requirements.txt`.

### 1. Create and activate the environment

```bash
conda create -n AlphaQuant python=3.10 -y
conda activate AlphaQuant
```

### 2. Install dependencies

From the repository root:

```bash
pip install -r requirements.txt
```

### 3. Jupyter notebooks (optional but recommended)

Notebooks in `Notebooks/` need a Jupyter kernel in this environment:

```bash
pip install ipykernel
python -m ipykernel install --user --name AlphaQuant --display-name "Python (AlphaQuant)"
```

## Editor setup (VS Code / Cursor)

This repo includes [`.vscode/settings.json`](.vscode/settings.json) to use the **AlphaQuant** interpreter and auto-activate it in the terminal.

After cloning, **update the paths** in that file to match your machine (Anaconda install location and env name). Typical keys to edit:

- `python.defaultInterpreterPath` — path to `...\envs\AlphaQuant\python.exe`
- `python.condaPath` — path to your `conda.exe` (e.g. `...\anaconda3\Scripts\conda.exe`)

Then reload the editor window and, for notebooks, choose **Python (AlphaQuant)** or the AlphaQuant environment from the kernel picker.

## Notes

- **MetaTrader5** and several packages are Windows-oriented; live trading and MT5 notebooks expect MetaTrader 5 installed and algo trading enabled in the platform.
- To pull updates from the original course repository, use the `upstream` remote if configured: `git fetch upstream` then merge as needed.
