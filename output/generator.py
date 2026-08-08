import os
import pandas as pd
from datetime import datetime

class OutputGenerator:
    def __init__(self, output_dir="output/"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.today = datetime.now().strftime("%Y-%m-%d")

    def generate_reports(self, scored_df, top_n=20):
        """
        Generates CSV reports for different views.
        """
        if scored_df.empty:
             print("No data to export.")
             return
             
        # Filter out hard exclusions (e.g. failed liquidity check)
        valid_df = scored_df[scored_df['passed_liquidity'] == True].copy()
        
        # Base columns to export
        export_cols = ['symbol', 'composite_score', 'regime', 'top_factors']
        # Add sub-scores if they exist
        sub_scores = [c for c in valid_df.columns if c.startswith('score_')]
        export_cols.extend(sub_scores)

        # Ensure we only select columns that exist
        export_cols = [c for c in export_cols if c in valid_df.columns]

        # 1. Overall Top N
        overall_top = valid_df.nlargest(top_n, 'composite_score')[export_cols]
        overall_top.to_csv(os.path.join(self.output_dir, f"{self.today}_overall_top_{top_n}.csv"), index=False)
        print(f"Exported overall top {top_n}")

        # 2. Top Momentum
        if 'score_momentum' in valid_df.columns:
            mom_top = valid_df.nlargest(10, 'score_momentum')[export_cols]
            mom_top.to_csv(os.path.join(self.output_dir, f"{self.today}_momentum_top_10.csv"), index=False)
            print("Exported momentum top 10")

        # 3. Top Quality/Value (Fundamental)
        if 'score_fundamental' in valid_df.columns:
            qual_top = valid_df.nlargest(10, 'score_fundamental')[export_cols]
            qual_top.to_csv(os.path.join(self.output_dir, f"{self.today}_fundamental_top_10.csv"), index=False)
            print("Exported fundamental top 10")
            
        # 4. Save full results for review
        valid_df.to_csv(os.path.join(self.output_dir, f"{self.today}_full_scan.csv"), index=False)
        print("Exported full scan results")
