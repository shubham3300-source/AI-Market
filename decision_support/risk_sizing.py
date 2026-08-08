import pandas as pd
import math

class RiskSizingEngine:
    def __init__(self, config):
        profile = config.get('user_profile', {})
        self.account_size = profile.get('account_size', 1000000)
        self.max_risk_pct = profile.get('max_risk_per_trade_pct', 0.01)
        self.max_risk_amount = self.account_size * self.max_risk_pct

    def calculate(self, current_price, atr_pct, symbol):
        """
        Calculates Stop Loss, Target, R:R, and Position Size.
        Uses ATR percentage for dynamic stop loss placement.
        """
        if not current_price or pd.isna(current_price) or current_price == 0:
             return {"error": "Invalid price"}

        # Use 2x ATR for stop distance (or 5% minimum if ATR is missing)
        atr_val = (atr_pct / 100) * current_price if pd.notna(atr_pct) and atr_pct > 0 else (0.05 * current_price)
        stop_dist = max(atr_val * 2, current_price * 0.02) # Minimum 2% stop distance

        stop_loss = current_price - stop_dist

        # Target based on min 1:2 R:R
        # Could be enhanced by looking for recent resistance in actual price data
        target = current_price + (stop_dist * 2.5)

        # Calculate shares
        risk_per_share = current_price - stop_loss

        if risk_per_share <= 0:
            return {"error": "Invalid risk calculation"}

        position_size_shares = math.floor(self.max_risk_amount / risk_per_share)
        position_value = position_size_shares * current_price

        # Cap position value to not exceed 25% of account
        if position_value > (self.account_size * 0.25):
             position_value = self.account_size * 0.25
             position_size_shares = math.floor(position_value / current_price)

        return {
            "entry_price": round(current_price, 2),
            "stop_loss": round(stop_loss, 2),
            "target": round(target, 2),
            "risk_reward": "1:2.5",
            "position_size_shares": position_size_shares,
            "position_value": round(position_size_shares * current_price, 2),
            "risk_amount": round(position_size_shares * risk_per_share, 2),
            "sizing_note": f"Risking {(self.max_risk_amount/self.account_size)*100:.1f}% of ₹{self.account_size:,.0f} → {position_size_shares} shares"
        }
