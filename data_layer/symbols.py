import pandas as pd
import requests
import io

def get_nifty500_symbols():
    """
    Fetches Nifty 500 symbols. 
    Downloads the current NIFTY 500 list from NSE India website.
    """
    url = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        # NSE symbols need .NS suffix for yfinance
        symbols = df['Symbol'].apply(lambda x: f"{x}.NS").tolist()
        return symbols
    except Exception as e:
        print(f"Error fetching Nifty 500 symbols from NSE: {e}")
        # Fallback list for testing
        print("Using fallback symbols list.")
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "SBI.NS", "BHARTIARTL.NS", "ITC.NS"]
