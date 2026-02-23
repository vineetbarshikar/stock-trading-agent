"""
Simple Streamlit dashboard for monitoring the trading bot.
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
from datetime import datetime, timedelta
import pandas as pd

# Page config
st.set_page_config(
    page_title="Trading Bot Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("🤖 Automated Trading Bot Dashboard")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Controls")
    
    if st.button("🔄 Refresh Data"):
        portfolio.refresh()
        st.rerun()
    
    st.markdown("---")
    st.header("📊 Navigation")
    page = st.radio(
        "Go to:",
        ["Portfolio", "Positions", "Signals", "Performance", "Risk Metrics"]
    )

# Main content based on page selection
if page == "Portfolio":
    st.header("💼 Portfolio Overview")
    
    # Refresh portfolio
    portfolio.refresh()
    account_info = portfolio.account_info
    
    if account_info:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Portfolio Value",
                f"${account_info['portfolio_value']:,.2f}",
                f"${account_info['portfolio_value'] - 50000:,.2f}"
            )
        
        with col2:
            pnl_data = portfolio.calculate_daily_pnl()
            st.metric(
                "Today's P&L",
                f"${pnl_data['daily_pnl']:,.2f}",
                f"{pnl_data['daily_pnl_pct']:.2f}%"
            )
        
        with col3:
            st.metric(
                "Cash",
                f"${account_info['cash']:,.2f}"
            )
        
        with col4:
            st.metric(
                "Buying Power",
                f"${account_info['buying_power']:,.2f}"
            )
        
        st.markdown("---")
        
        # Account details
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Account Details")
            st.write(f"**Equity:** ${account_info['equity']:,.2f}")
            st.write(f"**Long Market Value:** ${account_info['long_market_value']:,.2f}")
            st.write(f"**Day Trades Used:** {account_info['daytrade_count']}/3")
        
        with col2:
            st.subheader("Allocation")
            position_counts = portfolio.get_position_counts()
            st.write(f"**Total Positions:** {position_counts['total']}")
            st.write(f"**Stock Positions:** {position_counts['stocks']}")
            st.write(f"**Options Positions:** {position_counts['options']}")
    else:
        st.error("Failed to load account information")

elif page == "Positions":
    st.header("📊 Current Positions")
    
    positions = broker.get_positions()
    
    if positions:
        # Create DataFrame
        df = pd.DataFrame(positions)
        df = df[['symbol', 'qty', 'avg_entry_price', 'current_price', 'market_value', 'unrealized_pl', 'unrealized_plpc']]
        df.columns = ['Symbol', 'Qty', 'Entry Price', 'Current Price', 'Market Value', 'Unrealized P&L', 'P&L %']
        
        # Format columns
        df['Entry Price'] = df['Entry Price'].apply(lambda x: f"${x:.2f}")
        df['Current Price'] = df['Current Price'].apply(lambda x: f"${x:.2f}")
        df['Market Value'] = df['Market Value'].apply(lambda x: f"${x:,.2f}")
        df['Unrealized P&L'] = df['Unrealized P&L'].apply(lambda x: f"${x:,.2f}")
        df['P&L %'] = df['P&L %'].apply(lambda x: f"{x*100:.2f}%")
        
        st.dataframe(df, use_container_width=True)
        
        # Summary
        total_value = sum([p['market_value'] for p in positions])
        total_pnl = sum([p['unrealized_pl'] for p in positions])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Position Value", f"${total_value:,.2f}")
        with col2:
            st.metric("Total Unrealized P&L", f"${total_pnl:,.2f}")
    else:
        st.info("No open positions")

elif page == "Signals":
    st.header("🎯 Trading Signals")
    
    db = get_db_session()
    
    # Recent signals
    signals = db.query(Signal).order_by(Signal.timestamp.desc()).limit(20).all()
    
    if signals:
        data = []
        for signal in signals:
            data.append({
                "Time": signal.timestamp.strftime("%Y-%m-%d %H:%M"),
                "Symbol": signal.symbol,
                "Type": signal.signal_type,
                "Strategy": signal.strategy,
                "Score": signal.score,
                "Confidence": signal.confidence,
                "Price": f"${signal.current_price:.2f}",
                "Executed": "✅" if signal.is_executed else "⏳"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No signals generated yet")
    
    db.close()

elif page == "Performance":
    st.header("📈 Performance Metrics")
    
    db = get_db_session()
    
    # Get recent snapshots
    snapshots = db.query(PortfolioSnapshot).order_by(
        PortfolioSnapshot.timestamp.desc()
    ).limit(30).all()
    
    if snapshots:
        # Create DataFrame
        data = []
        for snap in reversed(snapshots):
            data.append({
                "Date": snap.date,
                "Value": snap.total_value,
                "Daily Return": snap.daily_return,
                "Daily Return %": snap.daily_return_pct,
            })
        
        df = pd.DataFrame(data)
        
        # Plot
        st.line_chart(df.set_index("Date")["Value"])
        
        st.markdown("---")
        
        # Recent trades
        st.subheader("Recent Trades")
        trades = db.query(Trade).order_by(Trade.timestamp.desc()).limit(10).all()
        
        if trades:
            trade_data = []
            for trade in trades:
                trade_data.append({
                    "Time": trade.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "Action": trade.action,
                    "Symbol": trade.symbol,
                    "Qty": trade.quantity,
                    "Price": f"${trade.price:.2f}",
                    "Value": f"${trade.value:,.2f}",
                    "Strategy": trade.strategy
                })
            
            trade_df = pd.DataFrame(trade_data)
            st.dataframe(trade_df, use_container_width=True)
    else:
        st.info("No performance data yet. Run the bot for at least one day.")
    
    db.close()

elif page == "Risk Metrics":
    st.header("⚠️ Risk Metrics")
    
    portfolio.refresh()
    account_info = portfolio.account_info
    
    if account_info:
        risk_metrics = risk_manager.get_risk_metrics(account_info)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Current Risk Status")
            
            status = risk_metrics['risk_status']
            if status == "LOW":
                st.success(f"✅ Risk Status: {status}")
            elif status == "MEDIUM":
                st.warning(f"⚠️ Risk Status: {status}")
            else:
                st.error(f"🚨 Risk Status: {status}")
            
            st.metric(
                "Current Drawdown",
                f"{risk_metrics['current_drawdown']*100:.2f}%",
                f"Limit: {risk_metrics['max_drawdown_limit']*100:.0f}%"
            )
            
            st.metric(
                "Today's P&L",
                f"${risk_metrics['daily_pnl']:,.2f}",
                f"{risk_metrics['daily_pnl_pct']*100:.2f}%"
            )
        
        with col2:
            st.subheader("Circuit Breakers")
            
            if risk_metrics['circuit_breaker_triggered']:
                st.error("🚨 Daily Loss Limit Hit!")
            else:
                st.success("✅ Daily Limit OK")
            
            if risk_metrics['max_drawdown_triggered']:
                st.error("🚨 Max Drawdown Hit!")
            else:
                st.success("✅ Max Drawdown OK")
            
            # Progress bars
            st.write("**Daily Loss Limit**")
            daily_loss_pct = abs(risk_metrics['daily_pnl_pct'])
            st.progress(min(daily_loss_pct / risk_metrics['daily_loss_limit'], 1.0))
            
            st.write("**Max Drawdown**")
            drawdown_pct = risk_metrics['current_drawdown']
            st.progress(min(drawdown_pct / risk_metrics['max_drawdown_limit'], 1.0))
    else:
        st.error("Failed to load risk metrics")

# Footer
st.markdown("---")
st.caption("🤖 Automated Trading Bot | Paper Trading Mode | Data refreshes on page reload")
