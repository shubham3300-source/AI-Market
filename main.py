import yaml
from data_layer.data_provider import DataLayer
from data_layer.symbols import get_nifty500_symbols
from regime.detector import RegimeDetector
from factors.technical import TechnicalFactors
from factors.fundamental import FundamentalFactors, LiquidityRedFlags
from scoring.engine import ScoringEngine
from output.generator import OutputGenerator
import pandas as pd

def scan_market(progress_callback=None):
    """
    Core function to scan the market. 
    Accepts an optional progress_callback(current, total, msg) for UI updates.
    Returns (scored_df, current_regime).
    """
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    if progress_callback: progress_callback(0, 100, "Initializing Data Layer...")
    dl = DataLayer()
    
    if progress_callback: progress_callback(5, 100, "Detecting Market Regime...")
    rd = RegimeDetector(dl)
    current_regime = rd.detect_current_regime()
    
    if progress_callback: progress_callback(10, 100, "Fetching Universe Symbols...")
    symbols = get_nifty500_symbols()
    
    factors_list = []
    total_symbols = len(symbols)
    
    for i, sym in enumerate(symbols):
        if progress_callback and i % 10 == 0:
            progress_callback(10 + int((i/total_symbols)*80), 100, f"Processing {sym} ({i}/{total_symbols})...")
            
        df = dl.fetch_ohlcv(sym)
        if df.empty or len(df) < 50:
            continue
            
        # Tech Factors
        tech_factors = TechnicalFactors.calculate(df)
        
        # Fundamental Factors
        fund_data = dl.fetch_fundamentals(sym)
        fund_factors = FundamentalFactors.calculate(fund_data)
        
        # Liquidity Check
        liq_check = LiquidityRedFlags.check(df, config)
        
        row = {'symbol': sym, 'passed_liquidity': liq_check['passed'], 'liquidity_reason': liq_check['reason']}
        row.update(tech_factors)
        row.update(fund_factors)
        factors_list.append(row)
        
    factors_df = pd.DataFrame(factors_list)
    
    if progress_callback: progress_callback(95, 100, "Scoring Universe...")
    se = ScoringEngine(config)
    scored_df = se.score_universe(factors_df, current_regime)
    
    if progress_callback: progress_callback(100, 100, "Scan Complete.")
    
    return scored_df, current_regime

def run_daily_scan():
    print("Starting daily scan...")
    scored_df, current_regime = scan_market(lambda c, t, msg: print(msg))
    
    print(f"Current Regime: {current_regime.upper()}")
    print("Generating Output Reports...")
    og = OutputGenerator()
    og.generate_reports(scored_df)
    
    print("Scan Complete.")

if __name__ == "__main__":
    run_daily_scan()