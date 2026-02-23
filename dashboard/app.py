"""
Streamlit dashboard for monitoring the trading bot.
Run with: streamlit run dashboard/app.py
"""
import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.execution.broker import broker
from src.portfolio.portfolio import portfolio
from src.execution.risk_manager import risk_manager
from src.data.database import get_db_session, Signal, Trade, PortfolioSnapshot
from config.settings import settings
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Page config
st.set_page_config(
    page_title="Trading Bot Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a jazzy, modern look
st.markdown("""
<style>
    /* Import a distinctive font */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Outfit:wght@300;400;600;700&display=swap');
    
    /* Main styling */
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    /* Metric cards with glassmorphism */
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.8rem !important;
        font-weight: 600 !important;
        background: linear-gradient(90deg, #00d9ff, #00ff88);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    [data-testid="stMetricDelta"] {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    /* Section headers */
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif !important;
        color: #e8e8e8 !important;
    }
    
    /* Cards/containers */
    .stMetric {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(0, 217, 255, 0.2);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .stMetric:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 24px rgba(0, 217, 255, 0.15);
    }
    
    /* DataFrames */
    .dataframe {
        font-family: 'JetBrains Mono', monospace !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d0d14 0%, #1a1a2e 100%) !important;
        border-right: 1px solid rgba(0, 217, 255, 0.15) !important;
    }
    
    [data-testid="stSidebar"] .stRadio label {
        color: #b8b8c8 !important;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .status-low { background: rgba(0, 255, 136, 0.2); color: #00ff88; border: 1px solid rgba(0, 255, 136, 0.4); }
    .status-medium { background: rgba(255, 193, 7, 0.2); color: #ffc107; border: 1px solid rgba(255, 193, 7, 0.4); }
    .status-high { background: rgba(255, 87, 34, 0.2); color: #ff5722; border: 1px solid rgba(255, 87, 34, 0.4); }
    .status-critical { background: rgba(244, 67, 54, 0.2); color: #f44336; border: 1px solid rgba(244, 67, 54, 0.4); }
    
    /* Hero header */
    .hero-header {
        background: linear-gradient(90deg, rgba(0, 217, 255, 0.1), rgba(0, 255, 136, 0.05));
        border: 1px solid rgba(0, 217, 255, 0.2);
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .hero-header h1 {
        margin: 0 !important;
        font-size: 2.2rem !important;
    }
    
    /* Plotly chart container */
    .js-plotly-plot {
        border-radius: 12px !important;
        overflow: hidden !important;
        background: rgba(0, 0, 0, 0.2) !important;
    }
    
    /* Market status pill */
    .market-open { color: #00ff88 !important; }
    .market-closed { color: #ff6b6b !important; }
</style>
""", unsafe_allow_html=True)


def is_market_open() -> bool:
    """Check if US market is open (9:30 AM - 4:00 PM ET)."""
    try:
        import pytz
        et = pytz.timezone("America/New_York")
        now = datetime.now(et).time()
        from datetime import time
        open_time = time(9, 30)
        close_time = time(16, 0)
        return open_time <= now <= close_time
    except Exception:
        return False


def get_plotly_theme():
    """Return dark theme config for Plotly charts."""
    return {
        "layout": {
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": {"color": "#b8b8c8", "family": "Outfit, sans-serif"},
            "xaxis": {"gridcolor": "rgba(255,255,255,0.08)", "zerolinecolor": "rgba(255,255,255,0.1)"},
            "yaxis": {"gridcolor": "rgba(255,255,255,0.08)", "zerolinecolor": "rgba(255,255,255,0.1)"},
            "margin": {"t": 40, "b": 40, "l": 60, "r": 30},
            "hoverlabel": {"bgcolor": "#1a1a2e", "font_size": 12},
        },
        "config": {"displayModeBar": True, "displaylogo": False},
    }


# Title and header
st.markdown('<div class="hero-header">', unsafe_allow_html=True)
col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown("# 🤖 Automated Trading Bot Dashboard")
with col_status:
    market_status = "🟢 Market Open" if is_market_open() else "🔴 Market Closed"
    st.markdown(f"### {market_status}")
st.markdown("</div>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Controls")
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        portfolio.refresh()
        st.rerun()
    
    st.markdown("---")
    st.header("📊 Navigation")
    page = st.radio(
        "Go to:",
        ["Overview", "Portfolio", "Positions", "Signals", "Performance", "Risk Metrics"],
        label_visibility="collapsed"
    )


# =============================================================================
# OVERVIEW PAGE
# =============================================================================
if page == "Overview":
    st.header("📊 At a Glance")
    
    portfolio.refresh()
    account_info = portfolio.account_info
    
    if account_info:
        pnl_data = portfolio.calculate_daily_pnl()
        risk_metrics = risk_manager.get_risk_metrics(account_info)
        
        # Key metrics row
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Portfolio Value",
                f"${account_info['portfolio_value']:,.0f}",
                f"{pnl_data['daily_pnl_pct']:+.2f}% today"
            )
        
        with col2:
            delta_color = "normal" if pnl_data['daily_pnl'] >= 0 else "inverse"
            st.metric("Today's P&L", f"${pnl_data['daily_pnl']:,.0f}", f"{pnl_data['daily_pnl_pct']:+.2f}%")
        
        with col3:
            initial = settings.initial_capital
            total_return = account_info['portfolio_value'] - initial
            total_return_pct = (total_return / initial) * 100
            st.metric("Total Return", f"${total_return:+,.0f}", f"{total_return_pct:+.2f}%")
        
        with col4:
            position_counts = portfolio.get_position_counts()
            st.metric("Open Positions", position_counts['total'], f"{position_counts['stocks']} stocks")
        
        with col5:
            status_class = f"status-{risk_metrics['risk_status'].lower()}"
            st.markdown(f"**Risk Status**")
            st.markdown(f'<span class="status-badge {status_class}">{risk_metrics["risk_status"]}</span>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Quick charts
        db = get_db_session()
        snapshots = db.query(PortfolioSnapshot).order_by(PortfolioSnapshot.timestamp.asc()).limit(60).all()
        db.close()
        
        if snapshots:
            df_equity = pd.DataFrame([{
                "Date": s.date,
                "Value": s.total_value,
            } for s in snapshots])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_equity["Date"], y=df_equity["Value"],
                mode="lines+markers",
                line=dict(color="#00d9ff", width=3),
                fill="tozeroy",
                fillcolor="rgba(0, 217, 255, 0.15)",
                marker=dict(size=6),
            ))
            fig.update_layout(**get_plotly_theme()["layout"], height=280, showlegend=False, xaxis_title="", yaxis_title="Portfolio Value ($)")
            fig.update_yaxes(tickprefix="$")
            st.plotly_chart(fig, use_container_width=True, config=get_plotly_theme()["config"])
        
        # Recent activity
        db = get_db_session()
        recent_trades = db.query(Trade).order_by(Trade.timestamp.desc()).limit(5).all()
        recent_signals = db.query(Signal).order_by(Signal.timestamp.desc()).limit(5).all()
        db.close()
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📋 Recent Trades")
            if recent_trades:
                for t in recent_trades:
                    emoji = "🟢" if t.action == "BUY" else "🔴"
                    st.markdown(f"{emoji} **{t.action}** {t.quantity:.0f} {t.symbol} @ ${t.price:.2f}")
            else:
                st.info("No recent trades")
        
        with col2:
            st.subheader("🎯 Recent Signals")
            if recent_signals:
                for s in recent_signals:
                    status = "✅" if s.is_executed else "⏳"
                    st.markdown(f"{status} **{s.signal_type}** {s.symbol} (score: {s.score:.0f})")
            else:
                st.info("No recent signals")
    else:
        st.error("Failed to load account information")


# =============================================================================
# PORTFOLIO PAGE
# =============================================================================
elif page == "Portfolio":
    st.header("💼 Portfolio Overview")
    
    portfolio.refresh()
    account_info = portfolio.account_info
    
    if account_info:
        pnl_data = portfolio.calculate_daily_pnl()
        initial = settings.initial_capital
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Portfolio Value", f"${account_info['portfolio_value']:,.2f}", f"${account_info['portfolio_value'] - initial:+,.2f}")
        
        with col2:
            st.metric("Today's P&L", f"${pnl_data['daily_pnl']:,.2f}", f"{pnl_data['daily_pnl_pct']:+.2f}%")
        
        with col3:
            st.metric("Cash", f"${account_info['cash']:,.2f}")
        
        with col4:
            st.metric("Buying Power", f"${account_info['buying_power']:,.2f}")
        
        st.markdown("---")
        
        # Allocation pie chart
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📊 Allocation")
            position_counts = portfolio.get_position_counts()
            
            labels = ["Cash", "Equities"]
            values = [account_info['cash'], account_info['long_market_value'] or 0]
            if sum(values) > 0:
                fig = go.Figure(data=[go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.6,
                    marker=dict(colors=["#00d9ff", "#00ff88"]),
                    textinfo="percent+label",
                    pull=[0.02, 0],
                )])
                fig.update_layout(**get_plotly_theme()["layout"], height=320, showlegend=True, legend=dict(orientation="h"))
                st.plotly_chart(fig, use_container_width=True, config=get_plotly_theme()["config"])
            else:
                st.info("No allocation data yet")
        
        with col2:
            st.subheader("Account Details")
            st.write(f"**Equity:** ${account_info['equity']:,.2f}")
            st.write(f"**Long Market Value:** ${account_info['long_market_value']:,.2f}")
            st.write(f"**Day Trades Used:** {account_info['daytrade_count']}/3")
            st.write(f"**Stock Positions:** {position_counts['stocks']}")
            st.write(f"**Options Positions:** {position_counts['options']}")
    else:
        st.error("Failed to load account information")


# =============================================================================
# POSITIONS PAGE
# =============================================================================
elif page == "Positions":
    st.header("📊 Current Positions")
    
    positions = broker.get_positions()
    
    if positions:
        df = pd.DataFrame(positions)
        df = df[['symbol', 'qty', 'avg_entry_price', 'current_price', 'market_value', 'unrealized_pl', 'unrealized_plpc']]
        df.columns = ['Symbol', 'Qty', 'Entry Price', 'Current Price', 'Market Value', 'Unrealized P&L', 'P&L %']
        
        # Keep numeric for styling
        df_display = df.copy()
        df_display['Entry Price'] = df_display['Entry Price'].apply(lambda x: f"${x:.2f}")
        df_display['Current Price'] = df_display['Current Price'].apply(lambda x: f"${x:.2f}")
        df_display['Market Value'] = df_display['Market Value'].apply(lambda x: f"${x:,.2f}")
        df_display['Unrealized P&L'] = df_display['Unrealized P&L'].apply(lambda x: f"${x:,.2f}")
        df_display['P&L %'] = df_display['P&L %'].apply(lambda x: f"{x*100:+.2f}%")
        
        total_value = sum(p['market_value'] for p in positions)
        total_pnl = sum(p['unrealized_pl'] for p in positions)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Position Value", f"${total_value:,.2f}")
        with col2:
            st.metric("Total Unrealized P&L", f"${total_pnl:,.2f}", f"{(total_pnl/total_value*100) if total_value else 0:+.2f}%")
        with col3:
            st.metric("Position Count", len(positions))
        
        # Allocation bar chart
        if len(positions) > 0:
            df_chart = pd.DataFrame([{"Symbol": p["symbol"], "Value": p["market_value"]} for p in positions])
            df_chart = df_chart.sort_values("Value", ascending=True).tail(10)
            fig = px.bar(df_chart, x="Value", y="Symbol", orientation="h", color="Value",
                         color_continuous_scale=["#00d9ff", "#00ff88"])
            fig.update_layout(**get_plotly_theme()["layout"], height=300, showlegend=False, xaxis_title="Market Value ($)", yaxis_title="")
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True, config=get_plotly_theme()["config"])
        
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("No open positions")


# =============================================================================
# SIGNALS PAGE
# =============================================================================
elif page == "Signals":
    st.header("🎯 Trading Signals")
    
    db = get_db_session()
    signals = db.query(Signal).order_by(Signal.timestamp.desc()).limit(50).all()
    
    if signals:
        data = []
        for s in signals:
            data.append({
                "Time": s.timestamp.strftime("%Y-%m-%d %H:%M"),
                "Symbol": s.symbol,
                "Type": s.signal_type,
                "Strategy": s.strategy,
                "Score": s.score,
                "Confidence": s.confidence,
                "Price": f"${s.current_price:.2f}",
                "Executed": "✅" if s.is_executed else "⏳",
            })
        
        df = pd.DataFrame(data)
        
        # Score distribution
        fig = px.histogram(df, x="Score", nbins=20, color_discrete_sequence=["#00d9ff"])
        fig.update_layout(**get_plotly_theme()["layout"], height=250, xaxis_title="Signal Score", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True, config=get_plotly_theme()["config"])
        
        # Signal type breakdown
        col1, col2 = st.columns(2)
        with col1:
            type_counts = df["Type"].value_counts()
            fig_pie = go.Figure(data=[go.Pie(labels=type_counts.index, values=type_counts.values, hole=0.5,
                                             marker=dict(colors=["#00ff88", "#ff6b6b"]))])
            fig_pie.update_layout(**get_plotly_theme()["layout"], height=280, title="Signal Type Distribution")
            st.plotly_chart(fig_pie, use_container_width=True, config=get_plotly_theme()["config"])
        
        with col2:
            exec_rate = df["Executed"].value_counts()
            fig_pie2 = go.Figure(data=[go.Pie(labels=["Executed", "Pending"], values=[exec_rate.get("✅", 0), exec_rate.get("⏳", 0)],
                                            hole=0.5, marker=dict(colors=["#00ff88", "#00d9ff"]))])
            fig_pie2.update_layout(**get_plotly_theme()["layout"], height=280, title="Execution Status")
            st.plotly_chart(fig_pie2, use_container_width=True, config=get_plotly_theme()["config"])
        
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No signals generated yet")
    
    db.close()


# =============================================================================
# PERFORMANCE PAGE
# =============================================================================
elif page == "Performance":
    st.header("📈 Performance Metrics")
    
    db = get_db_session()
    snapshots = db.query(PortfolioSnapshot).order_by(PortfolioSnapshot.timestamp.asc()).limit(90).all()
    
    if snapshots:
        data = []
        for snap in snapshots:
            data.append({
                "Date": snap.date,
                "Value": snap.total_value,
                "Daily Return": snap.daily_return,
                "Daily Return %": snap.daily_return_pct or 0,
            })
        
        df = pd.DataFrame(data)
        
        # Equity curve
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["Date"], y=df["Value"],
            mode="lines",
            line=dict(color="#00d9ff", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(0, 217, 255, 0.2)",
        ))
        fig.update_layout(**get_plotly_theme()["layout"], height=350, title="Portfolio Value Over Time",
                         xaxis_title="Date", yaxis_title="Portfolio Value ($)")
        fig.update_yaxes(tickprefix="$")
        st.plotly_chart(fig, use_container_width=True, config=get_plotly_theme()["config"])
        
        # Daily returns bar chart
        fig_ret = px.bar(df, x="Date", y="Daily Return %", color="Daily Return %",
                         color_continuous_scale=["#ff6b6b", "#b8b8c8", "#00ff88"])
        fig_ret.update_layout(**get_plotly_theme()["layout"], height=280, title="Daily Returns (%)")
        fig_ret.update_coloraxes(showscale=False)
        st.plotly_chart(fig_ret, use_container_width=True, config=get_plotly_theme()["config"])
        
        st.markdown("---")
        st.subheader("Recent Trades")
        
        trades = db.query(Trade).order_by(Trade.timestamp.desc()).limit(15).all()
        
        if trades:
            trade_data = []
            for t in trades:
                trade_data.append({
                    "Time": t.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "Action": t.action,
                    "Symbol": t.symbol,
                    "Qty": t.quantity,
                    "Price": f"${t.price:.2f}",
                    "Value": f"${t.value:,.2f}",
                    "Strategy": t.strategy,
                })
            
            trade_df = pd.DataFrame(trade_data)
            st.dataframe(trade_df, use_container_width=True)
        else:
            st.info("No trades yet")
    else:
        st.info("No performance data yet. Run the bot for at least one day.")
    
    db.close()


# =============================================================================
# RISK METRICS PAGE
# =============================================================================
elif page == "Risk Metrics":
    st.header("⚠️ Risk Metrics")
    
    portfolio.refresh()
    account_info = portfolio.account_info
    
    if account_info:
        risk_metrics = risk_manager.get_risk_metrics(account_info)
        
        status = risk_metrics['risk_status']
        status_class = f"status-{status.lower()}"
        st.markdown(f'<span class="status-badge {status_class}" style="font-size:1.2rem; padding:0.5rem 1rem;">Risk Level: {status}</span>', unsafe_allow_html=True)
        st.markdown("")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Current Risk Status")
            
            if status == "LOW":
                st.success(f"✅ Risk Status: {status}")
            elif status == "MEDIUM":
                st.warning(f"⚠️ Risk Status: {status}")
            elif status == "HIGH":
                st.error(f"⚠️ Risk Status: {status}")
            else:
                st.error(f"🚨 Risk Status: {status}")
            
            # Drawdown gauge
            dd = risk_metrics['current_drawdown'] * 100
            dd_limit = risk_metrics['max_drawdown_limit'] * 100
            st.metric("Current Drawdown", f"{dd:.2f}%", f"Limit: {dd_limit:.0f}%")
            st.progress(min(risk_metrics['current_drawdown'] / risk_metrics['max_drawdown_limit'], 1.0))
            
            st.metric("Today's P&L", f"${risk_metrics['daily_pnl']:,.2f}", f"{risk_metrics['daily_pnl_pct']*100:+.2f}%")
        
        with col2:
            st.subheader("Circuit Breakers")
            
            cb1 = st.container()
            with cb1:
                if risk_metrics['circuit_breaker_triggered']:
                    st.error("🚨 Daily Loss Limit Hit!")
                else:
                    st.success("✅ Daily Limit OK")
            
            cb2 = st.container()
            with cb2:
                if risk_metrics['max_drawdown_triggered']:
                    st.error("🚨 Max Drawdown Hit!")
                else:
                    st.success("✅ Max Drawdown OK")
            
            st.write("**Daily Loss Limit Usage**")
            daily_usage = min(abs(risk_metrics['daily_pnl_pct']) / risk_metrics['daily_loss_limit'], 1.0)
            st.progress(daily_usage)
            
            st.write("**Max Drawdown Usage**")
            dd_usage = min(risk_metrics['current_drawdown'] / risk_metrics['max_drawdown_limit'], 1.0)
            st.progress(dd_usage)
        
        # Visual risk gauge
        st.markdown("---")
        st.subheader("Risk Utilization")
        
        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=dd,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Drawdown %"},
            number={"suffix": "%", "font": {"size": 28}},
            gauge={
                "axis": {"range": [0, dd_limit], "tickwidth": 1},
                "bar": {"color": "#00d9ff"},
                "bgcolor": "rgba(0,0,0,0.3)",
                "borderwidth": 2,
                "bordercolor": "rgba(0,217,255,0.3)",
                "steps": [
                    {"range": [0, dd_limit * 0.5], "color": "rgba(0, 255, 136, 0.3)"},
                    {"range": [dd_limit * 0.5, dd_limit * 0.75], "color": "rgba(255, 193, 7, 0.3)"},
                    {"range": [dd_limit * 0.75, dd_limit], "color": "rgba(255, 87, 34, 0.3)"},
                ],
                "threshold": {
                    "line": {"color": "#f44336", "width": 4},
                    "thickness": 0.75,
                    "value": dd_limit,
                },
            },
        ))
        gauge_fig.update_layout(**get_plotly_theme()["layout"], height=300)
        st.plotly_chart(gauge_fig, use_container_width=True, config=get_plotly_theme()["config"])
    else:
        st.error("Failed to load risk metrics")

# Footer
st.markdown("---")
st.caption("🤖 Automated Trading Bot | Paper Trading Mode | Data refreshes on page reload or button click")
