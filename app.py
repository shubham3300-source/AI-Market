import streamlit as st
import pandas as pd
from main import scan_market
import yaml
from decision_support.explainability import ExplainabilityEngine
from decision_support.conviction import ConvictionEngine
from decision_support.risk_sizing import RiskSizingEngine
from decision_support.portfolio import PortfolioAnalyzer
from decision_support.journal import TradeJournal


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

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏆 Decision Support Top Picks", "⚖️ Comparison Mode", "💼 Portfolio & Journal", "🔥 Raw Momentum", "💎 Raw Quality"])

    # Base columns to display cleanly
    display_cols = ['symbol', 'composite_score', 'top_factors']

    with tab1:
        st.subheader("Top Picks & Decision Support")
        st.warning("⚠️ DISCLAIMER: This is a decision-support tool, not investment advice. Past factor performance doesn't guarantee future results.")

        top5 = valid_df.nlargest(5, 'composite_score').to_dict('records')

        # Initialize modules
        ee = ExplainabilityEngine()
        rs = RiskSizingEngine(config)

        for stock in top5:
            with st.expander(f"{stock['symbol']} - Score: {stock['composite_score']:.1f}", expanded=True):
                col1, col2, col3 = st.columns([2, 1, 1])

                # Conviction
                conviction = ConvictionEngine.calculate_conviction(stock)

                # Rationale (Mocked to save API calls for generic viewing unless specified)
                # In prod you would pass is_mock=False if API key exists
                rationale = ee.generate_rationale(stock, is_mock=True)

                # Risk Sizing
                current_price = stock.get('Close', 100) # Mock price if missing
                atr_pct = stock.get('vol_atr_pct', 5)
                risk = rs.calculate(current_price, atr_pct, stock['symbol'])

                with col1:
                    st.markdown(f"**Verdict:** {rationale['verdict']}")
                    st.markdown(f"**Why:** {rationale['top_factors_summary']}")
                    st.markdown(f"**Caution:** {rationale['counter_point']}")
                    st.caption(f"Difficulty: {rationale['difficulty_label']}")

                with col2:
                    st.metric("Conviction Score", conviction['conviction_score'])
                    st.caption(f"Driver: {conviction['conviction_driver']}")
                    st.caption(f"Historical Hit-rate: {conviction['historical_hit_rate']}")

                with col3:
                    st.metric("Suggested Pos Size", f"{risk.get('position_size_shares', 0)} shares")
                    st.caption(f"R:R {risk.get('risk_reward')} | Stop: {risk.get('stop_loss')}")
                    st.caption(risk.get('sizing_note', ''))


    with tab2:
        st.subheader("Comparison Mode")
        symbols = valid_df['symbol'].tolist()
        selected_symbols = st.multiselect("Select 2-4 stocks to compare:", symbols, max_selections=4)

        if len(selected_symbols) >= 2:
            comp_df = valid_df[valid_df['symbol'].isin(selected_symbols)].copy()

            # Prepare side-by-side data
            comp_data = []
            for _, row in comp_df.iterrows():
                stock_dict = row.to_dict()
                conv = ConvictionEngine.calculate_conviction(stock_dict)
                comp_data.append({
                    "Symbol": stock_dict['symbol'],
                    "Composite Score": round(stock_dict['composite_score'], 1),
                    "Conviction": conv['conviction_score'],
                    "Conviction Driver": conv['conviction_driver'],
                    "Top Factors": stock_dict['top_factors']
                })

            st.table(pd.DataFrame(comp_data).set_index('Symbol').astype(str).T)

            if st.button("Generate LLM Verdict"):
                with st.spinner("Analyzing..."):
                    ee = ExplainabilityEngine()
                    # Only use actual LLM if API key is present, otherwise fallback message
                    if ee.model:
                        verdict = ee.generate_comparison(comp_df.to_dict('records'))
                        st.info(f"🤖 **AI Verdict:** {verdict}")
                    else:
                        st.info("🤖 **AI Verdict:** (API Key missing) Stock with highest conviction score presents the cleaner technical setup, but ensure risk parameters align with your profile.")
        elif len(selected_symbols) > 0:
            st.warning("Select at least 2 stocks to compare.")

    with tab4:
        st.subheader("Top Picks (Momentum/Trend Focused)")
        if 'score_momentum' in valid_df.columns:
            mom_top = valid_df.nlargest(10, 'score_momentum')
            cols = display_cols + ['score_momentum', 'score_trend']
            st.dataframe(mom_top[[c for c in cols if c in mom_top.columns]], use_container_width=True, hide_index=True)
        else:
            st.warning("Momentum scores not available in current configuration.")

    with tab3:
        st.subheader("Portfolio & Trade Journal")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Portfolio Evaluator")
            st.write("Evaluate a new pick against your current holdings.")
            # Mock portfolio for UI demo
            mock_holdings = pd.DataFrame([
                {"symbol": "TCS", "sector": "IT", "weight": 0.35},
                {"symbol": "HDFCBANK", "sector": "Financials", "weight": 0.20}
            ])
            st.dataframe(mock_holdings, hide_index=True)

            test_symbol = st.selectbox("Select a pick to evaluate:", valid_df['symbol'].tolist())
            if test_symbol:
                pa = PortfolioAnalyzer()
                pa.update_holdings(mock_holdings)
                # Mock sector lookup
                mock_sector = "IT" if test_symbol in ["INFY", "WIPRO", "HCLTECH", "TECHM"] else "Other"
                eval_res = pa.evaluate_pick(test_symbol, mock_sector)

                if eval_res['flag'] == 'Warning':
                    st.error(eval_res['message'])
                elif eval_res['flag'] == 'Info':
                    st.info(eval_res['message'])
                else:
                    st.success(eval_res['message'])

        with col2:
            st.markdown("### Trade Journal Insights")
            tj = TradeJournal()

            # Form to log a trade
            with st.form("log_trade"):
                st.write("Log a new trade")
                log_sym = st.selectbox("Symbol", valid_df['symbol'].tolist())
                log_price = st.number_input("Entry Price", value=100.0)
                log_diff = st.selectbox("Difficulty Tag", ["Clean setup", "Needs confirmation", "Speculative"])
                log_conv = st.slider("Conviction Score", 0, 100, 50)
                submitted = st.form_submit_button("Log Trade")
                if submitted:
                    tj.log_trade(log_sym, log_price, log_diff, log_conv)
                    st.success(f"Logged {log_sym}")

            st.markdown("#### Performance Feedback")
            st.write(tj.get_insights())

    with tab5:
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