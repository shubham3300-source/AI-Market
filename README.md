# Indian Equity Regime-Adaptive Scanner

A daily stock scanner for the NSE 500 universe that detects the current market regime (using Nifty 50 and India VIX) and adaptively adjusts scoring weights for technical, fundamental, and volume factors.

## Modules

* **data_layer**: Fetches and caches OHLCV and fundamental data from yfinance.
* **regime**: Detects the current market condition (bull, bear, range-bound).
* **factors**: Calculates technical indicators (trend, momentum, volatility) and maps fundamental data.
* **scoring**: Normalizes factor metrics to percentiles and weights them based on the active regime.
* **backtest**: Allows for walk-forward performance testing over historical regimes.
* **output**: Generates CSV reports of top stock picks tailored to the current regime.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the daily scan:
   ```bash
   python main.py
   ```
   *Reports will be generated in the `output/` directory.*
3. Run the backtester:
   ```bash
   python test_bt.py
   ```

## Configuration

Adjust settings like universe size, liquidity thresholds, and regime weights in `config.yaml`.
