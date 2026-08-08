import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import yaml

class DataLayer:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        
        self.cache_dir = self.config['data']['cache_dir']
        os.makedirs(self.cache_dir, exist_ok=True)
        self.history_years = self.config['data']['history_years']

    def _get_cache_path(self, symbol, data_type):
        safe_symbol = symbol.replace(".", "_")
        return os.path.join(self.cache_dir, f"{safe_symbol}_{data_type}.parquet")

    def fetch_ohlcv(self, symbol, force_refresh=False):
        """
        Fetches OHLCV data for a given symbol, caching to local parquet files.
        """
        cache_path = self._get_cache_path(symbol, "ohlcv")
        
        if not force_refresh and os.path.exists(cache_path):
            df = pd.read_parquet(cache_path)
            # Simple check to see if we need to update
            if not df.empty and df.index.max().date() >= (datetime.now() - timedelta(days=2)).date():
                return df
                
        # Fetch fresh data
        start_date = datetime.now() - timedelta(days=365 * self.history_years)
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date)
            
            if df.empty:
                print(f"Warning: No data found for {symbol}")
                return df
                
            # yfinance returns timezone-aware datetimes, we make them naive for parquet compatibility in older pandas
            df.index = df.index.tz_localize(None) 
            
            # Cache it
            df.to_parquet(cache_path)
            return df
        except Exception as e:
            print(f"Error fetching OHLCV for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_fundamentals(self, symbol, force_refresh=False):
        """
        Fetches basic fundamental data using yfinance (fallback if Screener not available/rate limited).
        Returns a dict of metrics.
        """
        cache_path = self._get_cache_path(symbol, "fundamentals")
        
        if not force_refresh and os.path.exists(cache_path):
            df = pd.read_parquet(cache_path)
            if not df.empty and df.index.max() >= datetime.now() - timedelta(days=7): # Refresh weekly
                 # we stored dict as single row df
                return df.iloc[-1].to_dict() 
                
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Extract key metrics
            fundamentals = {
                'pe_ratio': info.get('trailingPE', None),
                'pb_ratio': info.get('priceToBook', None),
                'roe': info.get('returnOnEquity', None),
                'debt_to_equity': info.get('debtToEquity', None),
                'revenue_growth': info.get('revenueGrowth', None),
                'earnings_growth': info.get('earningsGrowth', None),
                'market_cap': info.get('marketCap', None),
                'timestamp': datetime.now()
            }
            
            # Cache as a single row dataframe
            df = pd.DataFrame([fundamentals])
            df.set_index('timestamp', inplace=True)
            df.to_parquet(cache_path)
            
            return fundamentals
            
        except Exception as e:
            print(f"Error fetching fundamentals for {symbol}: {e}")
            return {}

    def fetch_nifty50_index(self, force_refresh=False):
        """
        Fetches Nifty 50 OHLC data for regime detection.
        """
        return self.fetch_ohlcv("^NSEI", force_refresh=force_refresh)
        
    def fetch_india_vix(self, force_refresh=False):
        """
        Fetches India VIX data.
        """
        return self.fetch_ohlcv("^INDIAVIX", force_refresh=force_refresh)
