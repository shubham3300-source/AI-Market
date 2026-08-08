import streamlit as st
import pandas as pd
from main import scan_market
import yaml

st.set_page_config(page_title="Regime-Adaptive Stock Scanner", layout="wide")

st.title("📈 Regime-Adaptive Indian Equity Scanner")
st.markdown("""
This system screens the NIFTY 500 daily, calculates technical, fundamental, and volume factors, 
and dynamically adjusts its scoring weights based on the current market regime (e.g., Bull, Bear, Range-bound).
""")

# Load config to show settings
try:
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
except Exception as e:
    st.error("Could not load config.yaml")
    config = {}

# Sidebar for settings/info
with st.sidebar:
    st.header("⚙️ Configuration")
    st.write(f"**Universe:** {config.get('universe', {}).get('name', 'N/A')}")
    st.write("To change regime weights, edit `config.yaml`.")
    st.markdown("---")
    if st.button("🚀 Run Daily Scan", type="primary"):
        st.session_state['run_scan'] = True

# Main app logic
if st.session_state.get('run_scan', False):
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def ui_progress_callback(current, total, msg):
        progress_bar.progress(current / total)
        status_text.text(msg)
        
    with st.spinner("Scanning universe... This may take a few minutes if data is not cached."):
        scored_df, current_regime = scan_market(progress_callback=ui_progress_callback)
        
    st.session_state['scored_df'] = scored_df
    st.session_state['current_regime'] = current_regime
    st.session_state['run_scan'] = False
    
    status_text.text("Scan complete!")
    progress_bar.empty()

# Display results if available
if 'scored_df' in st.session_state and not st.session_state['scored_df'].empty:
    scored_df = st.session_state['scored_df']
    current_regime = st.session_state['current_regime']
    
    # Filter out liquidations
    valid_df = scored_df[scored_df['passed_liquidity'] == True].copy()
    
    # Regime display banner
    st.markdown(f"### 🚦 Current Market Regime: **`{current_regime.upper().replace('_', ' ')}`**")
    st.info(f"Weights are automatically optimized for a {current_regime.replace('_', ' ')} environment.")
    
    tab1, tab2, tab3 = st.tabs(["🏆 Overall Top 20", "🔥 Top Momentum", "💎 Top Quality/Value"])
    
    # Base columns to display cleanly
    display_cols = ['symbol', 'composite_score', 'top_factors']
    
    with tab1:
        st.subheader("Top Picks (Composite Score)")
        top20 = valid_df.nlargest(20, 'composite_score')
        cols = display_cols + [c for c in top20.columns if c.startswith('score_')]
        st.dataframe(top20[[c for c in cols if c in top20.columns]], use_container_width=True, hide_index=True)
        
    with tab2:
        st.subheader("Top Picks (Momentum/Trend Focused)")
        if 'score_momentum' in valid_df.columns:
            mom_top = valid_df.nlargest(10, 'score_momentum')
            cols = display_cols + ['score_momentum', 'score_trend']
            st.dataframe(mom_top[[c for c in cols if c in mom_top.columns]], use_container_width=True, hide_index=True)
        else:
            st.warning("Momentum scores not available in current configuration.")
            
    with tab3:
        st.subheader("Top Picks (Fundamental/Quality Focused)")
        if 'score_fundamental' in valid_df.columns:
            fund_top = valid_df.nlargest(10, 'score_fundamental')
            cols = display_cols + ['score_fundamental']
            st.dataframe(fund_top[[c for c in cols if c in fund_top.columns]], use_container_width=True, hide_index=True)
        else:
            st.warning("Fundamental scores not available in current configuration.")
            
    st.markdown("---")
    st.subheader("Raw Data Explorer")
    st.dataframe(valid_df, use_container_width=True)
    
elif 'run_scan' not in st.session_state:
    st.info("👈 Click **Run Daily Scan** in the sidebar to start.")