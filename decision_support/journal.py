import pandas as pd
import json
import os
from datetime import datetime

class TradeJournal:
    def __init__(self, filepath="data_layer/cache/trade_journal.json"):
        self.filepath = filepath
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w') as f:
                json.dump([], f)

    def log_trade(self, symbol, entry_price, difficulty_tag, conviction_score):
        """Logs a new trade."""
        with open(self.filepath, 'r') as f:
            trades = json.load(f)

        trades.append({
            "id": len(trades) + 1,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "symbol": symbol,
            "entry_price": entry_price,
            "difficulty_tag": difficulty_tag,
            "conviction_score": conviction_score,
            "status": "Open",
            "exit_price": None,
            "pnl_pct": None
        })

        with open(self.filepath, 'w') as f:
            json.dump(trades, f, indent=2)

    def close_trade(self, trade_id, exit_price):
        """Closes a trade and calculates PnL."""
        with open(self.filepath, 'r') as f:
            trades = json.load(f)

        for t in trades:
            if t["id"] == trade_id and t["status"] == "Open":
                t["exit_price"] = exit_price
                t["pnl_pct"] = ((exit_price - t["entry_price"]) / t["entry_price"]) * 100
                t["status"] = "Closed"
                break

        with open(self.filepath, 'w') as f:
            json.dump(trades, f, indent=2)

    def get_insights(self):
        """Analyzes past trades to surface insights."""
        with open(self.filepath, 'r') as f:
            trades = json.load(f)

        df = pd.DataFrame(trades)
        if df.empty or df[df['status'] == 'Closed'].empty:
            return "Not enough closed trades to generate insights."

        closed = df[df['status'] == 'Closed']

        # Analyze by difficulty tag
        tag_perf = closed.groupby('difficulty_tag')['pnl_pct'].mean()

        insights = []
        if 'Clean setup' in tag_perf and 'Needs confirmation' in tag_perf:
             clean = tag_perf['Clean setup']
             needs = tag_perf['Needs confirmation']
             if clean > needs and clean > 0:
                 ratio = clean / max(abs(needs), 0.1)
                 insights.append(f"Insight: Your trades on 'Clean setup' tags outperformed 'Needs confirmation' by {ratio:.1f}x avg return. Consider filtering out setups that need confirmation.")

        if not insights:
            return f"Average PnL across {len(closed)} closed trades: {closed['pnl_pct'].mean():.2f}%"

        return " | ".join(insights)

    def get_all_trades(self):
        with open(self.filepath, 'r') as f:
             return pd.DataFrame(json.load(f))
