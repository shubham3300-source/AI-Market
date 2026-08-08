import pandas as pd

class PortfolioAnalyzer:
    def __init__(self):
        self.holdings = pd.DataFrame()

    def update_holdings(self, holdings_df):
        """
        Updates the current portfolio holdings.
        Expected columns: 'symbol', 'sector', 'weight'
        """
        self.holdings = holdings_df

    def evaluate_pick(self, symbol, sector):
        """
        Evaluates a new pick against current holdings.
        """
        if self.holdings.empty or sector not in self.holdings.columns if 'sector' in self.holdings.columns else True:
            # Fallback if no sector data in holdings yet (mock logic for demo)
            # In a real app, sector mapping would exist in the data layer.
            # For this exercise, we will just mock a sector response if we don't have it.
            return {
                "flag": "None",
                "message": f"First exposure to this sector — genuine diversification."
            }

        sector_weight = self.holdings[self.holdings['sector'] == sector]['weight'].sum()

        if sector_weight > 0.30:
            return {
                "flag": "Warning",
                "message": f"You're already {sector_weight*100:.0f}% weighted to {sector} — this pick adds concentration risk."
            }
        elif sector_weight > 0:
            return {
                "flag": "Info",
                "message": f"Adds to existing {sector} exposure ({sector_weight*100:.0f}%)."
            }
        else:
             return {
                "flag": "Good",
                "message": f"First exposure to {sector} — genuine diversification."
            }
