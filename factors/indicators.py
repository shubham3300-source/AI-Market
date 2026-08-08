import pandas as pd
import numpy as np

def sma(series, length):
    return series.rolling(window=length).mean()

def rsi(series, length=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    
    # Use exponential moving average for typical RSI calculation (Wilder's smoothing)
    ma_up = up.ewm(com=length - 1, adjust=False).mean()
    ma_down = down.ewm(com=length - 1, adjust=False).mean()
    
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))

def macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - signal_line
    return pd.DataFrame({'MACD': macd_line, 'MACD_Signal': signal_line, 'MACD_Hist': macd_hist})

def roc(series, length=20):
    return series.pct_change(periods=length) * 100

def atr(high, low, close, length=14):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    return tr.ewm(alpha=1/length, adjust=False).mean()

def adx(high, low, close, length=14):
    # True Range
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    
    # Directional Movement
    up_move = high - high.shift()
    down_move = low.shift() - low
    
    pos_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0), index=close.index)
    neg_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0), index=close.index)
    
    # Smoothed True Range and DM (Wilder's Smoothing)
    tr_smooth = tr.ewm(alpha=1/length, adjust=False).mean()
    pos_dm_smooth = pos_dm.ewm(alpha=1/length, adjust=False).mean()
    neg_dm_smooth = neg_dm.ewm(alpha=1/length, adjust=False).mean()
    
    # Directional Indicators
    pos_di = 100 * (pos_dm_smooth / tr_smooth)
    neg_di = 100 * (neg_dm_smooth / tr_smooth)
    
    # Average Directional Index (ADX)
    dx = 100 * (abs(pos_di - neg_di) / (pos_di + neg_di))
    adx = dx.ewm(alpha=1/length, adjust=False).mean()
    
    return pd.DataFrame({'ADX': adx, 'DI+': pos_di, 'DI-': neg_di})

def bbands(series, length=20, std=2):
    basis = series.rolling(window=length).mean()
    dev = series.rolling(window=length).std() * std
    upper = basis + dev
    lower = basis - dev
    return pd.DataFrame({'BBU': upper, 'BBL': lower, 'BBM': basis})

def obv(close, volume):
    direction = np.sign(close.diff())
    # Fill first value with 1 to avoid NaN dropping the whole sum
    direction = direction.fillna(1)
    return (direction * volume).cumsum()