import pandas as pd
import numpy as np
from datetime import timedelta
import yaml

class Backtester:
    def __init__(self, data_layer, config):
        self.dl = data_layer
        self.config = config
        self.bt_config = config['backtest']

    def run_backtest(self, start_date, end_date, top_n=10, holding_period=5):
        """
        Runs a simplified forward-returns backtest over historical regimes.
        Selects top_n stocks at frequency of holding_period.
        """
        print(f"Starting backtest from {start_date} to {end_date}")
        
        # 1. Get historical regimes
        from regime.detector import RegimeDetector
        rd = RegimeDetector(self.dl)
        regimes = rd.get_historical_regimes(start_date=start_date)
        
        if regimes.empty:
            print("No regime data available for backtest period.")
            return {}
            
        # Filter to target range
        regimes = regimes[(regimes.index >= pd.to_datetime(start_date)) & (regimes.index <= pd.to_datetime(end_date))]
        
        # 2. Get Universe Data
        from data_layer.symbols import get_nifty500_symbols
        # Limit symbols for backtest speed to a small subset if testing
        symbols = get_nifty500_symbols()[:50] # using top 50 for realistic speed
        
        historical_data = {}
        for sym in symbols:
            df = self.dl.fetch_ohlcv(sym)
            if not df.empty:
                 historical_data[sym] = df
                 
        if not historical_data:
            print("No historical data fetched.")
            return {}

        # 3. Simulate portfolio
        portfolio_val = self.bt_config['initial_capital']
        portfolio_history = []
        
        transaction_cost = self.bt_config['transaction_costs_pct']
        
        # To avoid computing factors for 500 stocks every single day, we compute them 
        # on rebalance days (every `holding_period` days)
        
        rebalance_dates = regimes.index[::holding_period]
        
        from factors.technical import TechnicalFactors
        from scoring.engine import ScoringEngine
        se = ScoringEngine(self.config)
        
        for i in range(len(rebalance_dates) - 1):
             current_date = rebalance_dates[i]
             sell_date = rebalance_dates[i+1]
             current_regime = regimes.loc[current_date]
             
             # Step A: compute factors as of current_date
             daily_factors = []
             for sym, df in historical_data.items():
                 # Slice data up to current date
                 df_slice = df[df.index <= current_date]
                 if df_slice.empty or len(df_slice) < 50:
                     continue
                     
                 # Tech factors
                 tech = TechnicalFactors.calculate(df_slice)
                 
                 # Basic liquidity check (simple volume filter for backtest)
                 avg_vol = df_slice['Volume'].rolling(20).mean().iloc[-1]
                 close_p = df_slice['Close'].iloc[-1]
                 turnover = avg_vol * close_p
                 
                 passed_liq = turnover > self.config['universe'].get('exclude_illiquid_below_turnover', 10000000)
                 
                 row = {'symbol': sym, 'passed_liquidity': passed_liq, 'liquidity_reason': ''}
                 row.update(tech)
                 daily_factors.append(row)
                 
             if not daily_factors:
                 # Carry forward portfolio value if no valid data
                 portfolio_history.append({'Date': sell_date, 'Value': portfolio_val, 'Regime': current_regime})
                 continue
                 
             factors_df = pd.DataFrame(daily_factors)
             
             # Step B: Score and select Top N
             scored = se.score_universe(factors_df, current_regime)
             valid_scored = scored[scored['passed_liquidity'] == True]
             
             if valid_scored.empty:
                 portfolio_history.append({'Date': sell_date, 'Value': portfolio_val, 'Regime': current_regime})
                 continue
                 
             top_picks = valid_scored.head(top_n)['symbol'].tolist()
             
             # Step C: Calculate returns over holding period
             period_return = 0
             allocation_per_stock = 1.0 / len(top_picks)
             
             for sym in top_picks:
                 df = historical_data[sym]
                 # entry next open, exit next open
                 entry_slice = df[df.index > current_date]
                 exit_slice = df[df.index >= sell_date]
                 
                 if entry_slice.empty or exit_slice.empty:
                     continue
                     
                 entry_price = entry_slice['Open'].iloc[0]
                 exit_price = exit_slice['Open'].iloc[0]
                 
                 stock_ret = (exit_price - entry_price) / entry_price
                 # apply costs (entry + exit)
                 stock_ret -= (transaction_cost * 2)
                 
                 period_return += allocation_per_stock * stock_ret
                 
             portfolio_val *= (1 + period_return)
             portfolio_history.append({'Date': sell_date, 'Value': portfolio_val, 'Regime': current_regime})
             
        # Format results
        res_df = pd.DataFrame(portfolio_history)
        if not res_df.empty:
            res_df.set_index('Date', inplace=True)
            
            # Benchmark (Nifty)
            nifty = self.dl.fetch_nifty50_index()
            nifty = nifty[(nifty.index >= pd.to_datetime(start_date)) & (nifty.index <= pd.to_datetime(end_date))]
            
            if not nifty.empty:
                nifty_ret = (nifty['Close'].iloc[-1] / nifty['Close'].iloc[0]) - 1
            else:
                nifty_ret = 0
                
            total_ret = (portfolio_val / self.bt_config['initial_capital']) - 1
            
            print(f"\nBacktest Complete.")
            print(f"Total Return: {total_ret*100:.2f}% | Nifty Benchmark Return: {nifty_ret*100:.2f}%")
            
            # Max Drawdown
            res_df['Peak'] = res_df['Value'].cummax()
            res_df['Drawdown'] = (res_df['Value'] - res_df['Peak']) / res_df['Peak']
            max_dd = res_df['Drawdown'].min()
            print(f"Max Drawdown: {max_dd*100:.2f}%")
            
            # Returns by Regime
            print("\nPerformance by Regime:")
            res_df['Period_Ret'] = res_df['Value'].pct_change()
            regime_perf = res_df.groupby('Regime')['Period_Ret'].apply(lambda x: (1 + x).prod() - 1)
            for r, perf in regime_perf.items():
                print(f"  {r}: {perf*100:.2f}%")
                
            return res_df
        return pd.DataFrame()

