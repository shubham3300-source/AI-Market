import pandas as pd
from factors import indicators as ta

class RegimeDetector:
    def __init__(self, data_layer):
        self.dl = data_layer

    def detect_current_regime(self):
        """
        Calculates the current market regime based on Nifty 50 and India VIX.
        Returns the regime label as a string.
        """
        nifty = self.dl.fetch_nifty50_index()
        vix = self.dl.fetch_india_vix()

        if nifty.empty or vix.empty:
            return "unknown"

        # Calculate indicators on Nifty
        nifty['SMA_50'] = ta.sma(nifty['Close'], length=50)
        nifty['SMA_200'] = ta.sma(nifty['Close'], length=200)
        
        adx = ta.adx(nifty['High'], nifty['Low'], nifty['Close'], length=14)
        if not adx.empty:
            nifty = pd.concat([nifty, adx], axis=1)
        else:
            nifty['ADX'] = 0

        # Get the latest row
        latest_nifty = nifty.iloc[-1]
        latest_vix = vix.iloc[-1]

        price = latest_nifty['Close']
        sma_50 = latest_nifty['SMA_50']
        sma_200 = latest_nifty['SMA_200']
        adx_val = latest_nifty.get('ADX', 0)
        vix_val = latest_vix['Close']

        # Handling NaNs in initial periods
        if pd.isna(sma_50) or pd.isna(sma_200):
            return "unknown"

        # Regime Logic based on config definitions
        # strong_bull: "Nifty > 50 DMA, Nifty > 200 DMA, ADX > 25, VIX < 20"
        if price > sma_50 and price > sma_200 and adx_val > 25 and vix_val < 20:
            return "strong_bull"
        
        # choppy_bull: "Nifty > 200 DMA, Nifty < 50 DMA, VIX < 25"
        if price > sma_200 and price < sma_50 and vix_val < 25:
            return "choppy_bull"
            
        # range_bound: "Nifty ADX < 20, VIX < 20"
        if adx_val < 20 and vix_val < 20:
            return "range_bound"
            
        # correction: "Nifty < 50 DMA, Nifty > 200 DMA, VIX > 20"
        if price < sma_50 and price > sma_200 and vix_val > 20:
            return "correction"
            
        # bear: "Nifty < 200 DMA"
        if price < sma_200:
            return "bear"

        # Fallback
        return "range_bound"

    def get_historical_regimes(self, start_date=None):
        """
        Returns a time series of market regimes for backtesting.
        """
        nifty = self.dl.fetch_nifty50_index()
        vix = self.dl.fetch_india_vix()

        if nifty.empty or vix.empty:
            return pd.Series()

        nifty['SMA_50'] = ta.sma(nifty['Close'], length=50)
        nifty['SMA_200'] = ta.sma(nifty['Close'], length=200)
        adx = ta.adx(nifty['High'], nifty['Low'], nifty['Close'], length=14)
        if not adx.empty:
            nifty = pd.concat([nifty, adx], axis=1)
        else:
             nifty['ADX'] = 0

        # align VIX dates
        nifty = nifty.join(vix[['Close']].rename(columns={'Close': 'VIX'}), how='left')
        
        # Forward fill VIX in case of minor calendar mismatches
        nifty['VIX'] = nifty['VIX'].ffill()

        def apply_regime_logic(row):
            if pd.isna(row['SMA_50']) or pd.isna(row['SMA_200']):
                return "unknown"
            
            price = row['Close']
            sma_50 = row['SMA_50']
            sma_200 = row['SMA_200']
            adx_val = row.get('ADX', 0)
            vix_val = row['VIX']

            if price > sma_50 and price > sma_200 and adx_val > 25 and vix_val < 20:
                return "strong_bull"
            if price > sma_200 and price < sma_50 and vix_val < 25:
                return "choppy_bull"
            if adx_val < 20 and vix_val < 20:
                return "range_bound"
            if price < sma_50 and price > sma_200 and vix_val > 20:
                return "correction"
            if price < sma_200:
                return "bear"
            return "range_bound"

        nifty['Regime'] = nifty.apply(apply_regime_logic, axis=1)
        
        if start_date:
            nifty = nifty[nifty.index >= start_date]

        return nifty['Regime']