import pandas as pd
import numpy as np
from scipy.stats import rankdata

class ScoringEngine:
    def __init__(self, config):
        self.config = config

    def _normalize_factors(self, df):
        """
        Normalizes factor columns to 0-100 percentiles within the universe.
        """
        # Define which factors need to be inverted (lower is better)
        invert_factors = ['val_pe', 'val_pb', 'qual_debt_eq']
        
        normalized = pd.DataFrame(index=df.index)
        
        for col in df.columns:
            if col in ['symbol', 'passed_liquidity', 'liquidity_reason']:
                normalized[col] = df[col]
                continue
                
            # Drop NaNs for ranking, then reindex
            valid_data = df[col].dropna()
            if valid_data.empty:
                normalized[f'{col}_norm'] = 0
                continue
                
            ranks = rankdata(valid_data, method='average')
            percentiles = (ranks / len(valid_data)) * 100
            
            if col in invert_factors:
                 percentiles = 100 - percentiles
                 
            # Align back with original index, filling NaNs with median (50th percentile)
            series = pd.Series(percentiles, index=valid_data.index)
            normalized[f'{col}_norm'] = series
            
        return normalized.fillna(50) # Neutral score for missing data

    def score_universe(self, raw_factors_df, current_regime):
        """
        Scores the universe using adaptive weights based on the current regime.
        """
        if raw_factors_df.empty:
            return pd.DataFrame()
            
        # Get weights for the current regime, fallback to range_bound if not found
        regime_weights = self.config['regimes']['weights'].get(current_regime, self.config['regimes']['weights']['range_bound'])
        
        # 1. Normalize all factors
        norm_df = self._normalize_factors(raw_factors_df)
        
        # 2. Group factors by category
        # Technical sub-groups
        momentum_cols = [c for c in norm_df.columns if 'mom_' in c]
        trend_cols = [c for c in norm_df.columns if 'trend_' in c or 'pattern_' in c]
        mean_rev_cols = ['vol_bb_pos_norm'] # Using BB Pos as mean reversion proxy (want low BB pos in range bound)
        volatility_cols = ['vol_atr_pct_norm']
        volume_cols = ['volume_relative_norm']
        
        # Fundamental sub-groups
        fundamental_cols = [c for c in norm_df.columns if 'val_' in c or 'qual_' in c or 'growth_' in c]
        
        # 3. Calculate category scores (average of normalized sub-factors)
        # Note: we need to handle the mean reversion differently: in range bound regimes, extreme low RSI/BB_Pos is good.
        # For simplicity in this version, we'll just average the raw percentiles, but ideally, you'd transform BB_Pos based on regime.
        if current_regime in ['range_bound', 'bear']:
             # Inverting BB Pos so lower BB pos (oversold) gets a higher score
             norm_df['vol_bb_pos_norm_adj'] = 100 - norm_df.get('vol_bb_pos_norm', 50)
        else:
             # In bull markets, breaking upper BB (high pos) is good (momentum)
             norm_df['vol_bb_pos_norm_adj'] = norm_df.get('vol_bb_pos_norm', 50)
             
        mean_rev_cols = ['vol_bb_pos_norm_adj']
        
        # Only select columns that actually exist in the dataframe
        momentum_cols = [c for c in momentum_cols if c in norm_df.columns]
        trend_cols = [c for c in trend_cols if c in norm_df.columns]
        mean_rev_cols = [c for c in mean_rev_cols if c in norm_df.columns]
        volatility_cols = [c for c in volatility_cols if c in norm_df.columns]
        fundamental_cols = [c for c in fundamental_cols if c in norm_df.columns]
        volume_cols = [c for c in volume_cols if c in norm_df.columns]

        norm_df['score_momentum'] = norm_df[momentum_cols].mean(axis=1) if momentum_cols else 50
        norm_df['score_trend'] = norm_df[trend_cols].mean(axis=1) if trend_cols else 50
        norm_df['score_mean_rev'] = norm_df[mean_rev_cols].mean(axis=1) if mean_rev_cols else 50
        norm_df['score_volatility'] = norm_df[volatility_cols].mean(axis=1) if volatility_cols else 50
        
        norm_df['score_fundamental'] = norm_df[fundamental_cols].mean(axis=1) if fundamental_cols else 50
        norm_df['score_volume'] = norm_df[volume_cols].mean(axis=1) if volume_cols else 50

        # Aggregate Technicals according to sub_weights
        sub_w = regime_weights['sub_weights']
        norm_df['score_technical'] = (
            norm_df['score_momentum'] * sub_w['momentum'] +
            norm_df['score_trend'] * sub_w['trend'] +
            norm_df['score_mean_rev'] * sub_w['mean_reversion'] +
            norm_df['score_volatility'] * sub_w['volatility']
        )
        
        # 4. Compute Final Composite Score
        norm_df['composite_score'] = (
            norm_df['score_technical'] * regime_weights['technical'] +
            norm_df['score_fundamental'] * regime_weights['fundamental'] +
            norm_df['score_volume'] * regime_weights['volume']
        )
        
        # Ensure it is numeric for sorting
        norm_df['composite_score'] = pd.to_numeric(norm_df['composite_score'], errors='coerce').fillna(0)
        
        # 5. Extract top 3 contributing factors
        def get_top_contributors(row):
            # Evaluate base normalized factors
            factors_only = row[[c for c in norm_df.columns if '_norm' in c and 'adj' not in c]]
            factors_only = pd.to_numeric(factors_only, errors='coerce').fillna(0)
            top_3 = factors_only.nlargest(3).index.str.replace('_norm', '').tolist()
            return ", ".join(top_3)
            
        norm_df['top_factors'] = norm_df.apply(get_top_contributors, axis=1)
        norm_df['regime'] = current_regime
        
        # Merge back symbol and liquidity info
        norm_df['symbol'] = raw_factors_df['symbol']
        norm_df['passed_liquidity'] = raw_factors_df['passed_liquidity']
        norm_df['liquidity_reason'] = raw_factors_df['liquidity_reason']

        return norm_df.sort_values(by='composite_score', ascending=False)
