class FundamentalFactors:
    @staticmethod
    def calculate(fundamentals_dict):
        """
        Processes fundamental data dictionary into scoring metrics.
        """
        if not fundamentals_dict:
            return {}
            
        factors = {
            'val_pe': fundamentals_dict.get('pe_ratio', 0), # Lower is better, need to invert in scoring
            'val_pb': fundamentals_dict.get('pb_ratio', 0), # Lower is better
            'qual_roe': fundamentals_dict.get('roe', 0) * 100 if fundamentals_dict.get('roe') else 0, # Higher is better
            'qual_debt_eq': fundamentals_dict.get('debt_to_equity', 0), # Lower is better
            'growth_rev': fundamentals_dict.get('revenue_growth', 0) * 100 if fundamentals_dict.get('revenue_growth') else 0, # Higher is better
            'growth_earn': fundamentals_dict.get('earnings_growth', 0) * 100 if fundamentals_dict.get('earnings_growth') else 0, # Higher is better
        }
        
        # Handle Nones - use None to let Pandas convert to NaN so that percentiles are neutral,
        # instead of 0 which could accidentally give a perfect score for inverted metrics like PE.
        return {k: (None if v is None else v) for k, v in factors.items()}

class LiquidityRedFlags:
    @staticmethod
    def check(df, config):
        """
        Checks for liquidity and red flags.
        Returns a dictionary with a boolean 'passed' flag and reason if failed.
        """
        if df.empty or len(df) < 20:
             return {'passed': False, 'reason': 'Not enough data'}
             
        latest = df.iloc[-1]
        
        # Avg daily turnover (Close * Volume) over last 20 days
        df['Turnover'] = df['Close'] * df['Volume']
        avg_turnover = df['Turnover'].rolling(window=20).mean().iloc[-1]
        
        threshold = config['universe'].get('exclude_illiquid_below_turnover', 10000000)
        
        if avg_turnover < threshold:
            return {'passed': False, 'reason': f'Low turnover: {avg_turnover:,.0f} < {threshold}'}
            
        return {'passed': True, 'reason': ''}
