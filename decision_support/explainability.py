import os
from google import genai
from google.genai import types
import json

class ExplainabilityEngine:
    def __init__(self):
        # We need an API key to run this. If it's not present, we will fallback to a mocked response.
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Use gemini-1.5-flash for faster structured text tasks
            self.model = genai.GenerativeModel('gemini-3.5-flash-lite')
        else:
            self.model = None

    def generate_rationale(self, stock_data, is_mock=False):
        """
        Generates a 2-3 sentence natural language rationale using Gemini.
        `stock_data` is a dictionary containing factor data and scores.
        """
        if not self.model or is_mock:
            return self._mock_rationale(stock_data)

        # Prepare the context safely
        context_str = json.dumps({
            k: v for k, v in stock_data.items()
            if isinstance(v, (int, float, str)) and 'norm' not in k
        }, indent=2)

        prompt = f"""
You are a quantitative trading decision-support assistant. Your task is to explain why a stock was selected by a multi-factor scanner, providing a concise, 2-3 sentence structured rationale based strictly on the provided data.

RULES:
1. DO NOT hallucinate, invent, or assume any numbers, events, or catalysts.
2. Only use the exact numerical values provided in the DATA block.
3. Your output must strictly follow the format requested.

DATA:
{context_str}

REQUIRED OUTPUT FORMAT (JSON):
{{
  "top_factors_summary": "1 sentence highlighting the top 3 factors driving the score, using ACTUAL numbers from the data.",
  "counter_point": "1 sentence highlighting the strongest reason to be cautious based on the data (e.g., extended RSI, low liquidity).",
  "verdict": "A 1-line verdict combining the strengths and the counter-point.",
  "difficulty_label": "One of ['Clean setup', 'Needs confirmation', 'Speculative']"
}}
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            # Parse the JSON response
            return json.loads(response.text)
        except Exception as e:
            print(f"Error generating rationale with Gemini: {e}")
            return self._mock_rationale(stock_data)

    def generate_comparison(self, stocks_data):
         """
         Generates a side-by-side comparison for 2-4 stocks.
         """
         if not self.model:
              return "API Key missing, cannot generate comparison."

         context_str = json.dumps([{
            "symbol": stock.get("symbol"),
            "data": {k: v for k, v in stock.items() if isinstance(v, (int, float, str)) and 'norm' not in k}
         } for stock in stocks_data], indent=2)

         prompt = f"""
You are a quantitative trading decision-support assistant. Compare the following stocks based strictly on the provided factor data.

DATA:
{context_str}

Provide a closing recommendation line: which one fits better given their data, and why. Be honest if it's a coin-flip. DO NOT hallucinate any numbers or outside information. Keep it under 3 sentences.
"""
         try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1)
            )
            return response.text
         except Exception as e:
            return f"Error generating comparison: {e}"

    def _mock_rationale(self, stock_data):
        """Fallback when API is not available."""
        top_factors = stock_data.get('top_factors', 'Trend, Momentum')
        rsi = round(stock_data.get('mom_rsi', 50), 2)
        atr_pct = round(stock_data.get('vol_atr_pct', 0), 2)

        return {
            "top_factors_summary": f"Driven by {top_factors} with RSI currently at {rsi}.",
            "counter_point": f"Volatility is notable with ATR% at {atr_pct}%.",
            "verdict": f"Solid momentum, but position size appropriately for {atr_pct}% volatility.",
            "difficulty_label": "Needs confirmation" if rsi > 70 else "Clean setup"
        }
