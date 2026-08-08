import pandas as pd
import numpy as np
from factors import indicators as ta

class TechnicalFactors:
    @staticmethod
    def calculate(df):
        """
        Calculates technical factors for a given OHLCV dataframe.
        Returns a dictionary of the latest factor values.
        """
        if df.empty or len(df) < 200:
            return {}

        # Ensure close is float
        close = df['Close'].astype(float)
        
        # Trend
        df['SMA_20'] = ta.sma(close, length=20)
        df['SMA_50'] = ta.sma(close, length=50)
        df['SMA_200'] = ta.sma(close, length=200)
        
        adx = ta.adx(df['High'], df['Low'], close, length=14)
        if not adx.empty:
             df = pd.concat([df, adx], axis=1)
        else:
             df['ADX'] = 0

        # Momentum
        df['RSI_14'] = ta.rsi(close, length=14)
        
        macd = ta.macd(close, fast=12, slow=26, signal=9)
        if not macd.empty:
            df = pd.concat([df, macd], axis=1)
        else:
            df['MACD_Hist'] = 0
            
        df['ROC_20'] = ta.roc(close, length=20)

        # Volatility
        df['ATR_14'] = ta.atr(df['High'], df['Low'], close, length=14)
        # ATR percentage
        df['ATR_Pct'] = (df['ATR_14'] / close) * 100
        
        bbands = ta.bbands(close, length=20, std=2)
        if not bbands.empty:
             df = pd.concat([df, bbands], axis=1)
             df['BB_Width'] = (df['BBU'] - df['BBL']) / df['SMA_20']
             df['BB_Pos'] = (close - df['BBL']) / (df['BBU'] - df['BBL'])
        else:
             df['BB_Width'] = 0
             df['BB_Pos'] = 0.5

        # Volume
        df['Vol_SMA_20'] = ta.sma(df['Volume'], length=20)
        df['Rel_Volume'] = df['Volume'] / df['Vol_SMA_20']
        df['OBV'] = ta.obv(close, df['Volume'])

        # Pattern Flags
        df['52W_High'] = df['High'].rolling(window=252).max()
        df['52W_Low'] = df['Low'].rolling(window=252).min()
        df['Dist_to_52WH'] = (close - df['52W_High']) / df['52W_High']
        
        latest = df.iloc[-1]
        
        # Score generation (higher is better for most, some are situational based on regime)
        # For simplicity, returning raw values, the scoring engine will normalize them
        
        factors = {
            'trend_dma_score': (latest['Close'] > latest['SMA_50']) + (latest['Close'] > latest['SMA_200']) + (latest['SMA_50'] > latest['SMA_200']), # 0 to 3
            'trend_adx': latest.get('ADX', 0),
            'mom_rsi': latest.get('RSI_14', 50),
            'mom_macd_hist': latest.get('MACD_Hist', 0),
            'mom_roc': latest.get('ROC_20', 0),
            'vol_bb_pos': latest.get('BB_Pos', 0.5), # Mean reversion likes low BB_pos, trend likes high
            'vol_atr_pct': latest.get('ATR_Pct', 0),
            'volume_relative': latest.get('Rel_Volume', 1),
            'pattern_dist_52wh': latest.get('Dist_to_52WH', -1) # Closer to 0 is better (breaking out)
        }
        
        # Fill NaNs with 0
        return {k: (0 if pd.isna(v) else v) for k, v in factors.items()}