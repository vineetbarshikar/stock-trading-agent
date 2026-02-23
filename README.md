# 📈 Stock Trading Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Alpaca API](https://img.shields.io/badge/Alpaca-API-green?logo=alpaca)](https://alpaca.markets)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red?logo=streamlit)](https://streamlit.io)
[![Paper Trading](https://img.shields.io/badge/Mode-Paper%20Trading-orange)](/)
[![Experimental](https://img.shields.io/badge/Status-Experimental-purple)](/)

An autonomous stock and options trading bot with sentiment analysis,
ML-based predictions, and multi-layer risk management. 🤖

---

> ## ⚠️ IMPORTANT DISCLAIMER
>
> **This project is for EXPERIMENTAL and EDUCATIONAL purposes only.**
>
> - **Paper trading only.** Use this solution exclusively with paper/simulated trading accounts. Do not use it with real money.
> - **No financial advice.** Nothing in this repository constitutes investment advice, recommendations, or endorsements.
> - **Your responsibility.** Anyone who references or uses this code must conduct their own due diligence before making any investment decisions. Trading involves substantial risk of loss.
> - **Use at your own risk.** The authors and contributors are not responsible for any financial losses resulting from the use of this software.
>
> **If you choose to trade with real capital, you do so entirely at your own risk.**

---

## 💰 Investment Profile

| Parameter     | Value                    |
| ------------- | ------------------------ |
| Capital       | $50,000                  |
| Risk          | Aggressive               |
| Allocation    | 50% stocks / 50% options |
| Options DTE   | 30–45 days (monthlies)   |
| Timeline      | Feb 2026 – Dec 2026      |
| Paper trading | 1–2 months before live   |

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────┐
│                     Stock Trading Agent                │
├──────────┬──────────────┬──────────────┬───────────────┤
│  Data    │  Strategies  │  Execution   │  Portfolio    │
│          │              │              │               │
│ yfinance │ Momentum v2  │ Alpaca API   │ Position mgmt │
│ Alpaca   │ Options      │ Risk manager │ P&L tracking  │
│ News     │              │ Order mgmt   │ Snapshots     │
├──────────┴──────────────┴──────────────┴───────────────┤
│  Sentiment Analysis  │  ML Predictor  │  Market Regime │
└──────────────────────┴────────────────┴────────────────┘
```

### 🎯 Signal scoring (0–100)

| Component          | Points     | Source                                         |
| ------------------ | ---------- | ---------------------------------------------- |
| Technical analysis | 0–40       | SMA, RSI, MACD, volume, momentum               |
| Sentiment          | 0–25       | News headlines, VIX, SPY trend, sector breadth |
| ML prediction      | 0–25       | Gradient boosting (3 yr training, 20 features) |
| Market regime      | −10 to +10 | Bull / bear / neutral adjustment               |

Minimum score for entry: **60**. ✨

### 📊 Strategies

**📈 Stocks** – Momentum / trend-following on 80+ large-cap names across
all sectors. Buys on bullish signals, exits via 8% stop-loss or 15%
profit target.

**📉 Options** – Generated from the same scored signals:

- **📗 Long calls** on high-conviction bullish setups
- **📕 Long puts** on bearish setups
- **📊 Bull call spreads** on moderate conviction (defined risk, ≥ 1:2 R:R)
- 30–45 DTE monthly options, filtered by open interest and IV

### ⚠️ Risk management

| Rule                       | Limit                           |
| -------------------------- | ------------------------------- |
| Max position (stock)       | 10% of portfolio                |
| Max position (option)      | 5% of portfolio                 |
| Daily loss circuit breaker | 3% → trading halted for the day |
| Max drawdown               | 40% → all trading stopped       |
| Max sector exposure        | 30%                             |
| Max total positions        | 15                              |
| Cash reserve               | ≥ 5%                            |

## 📁 Project structure

```
stock-trading-agent/
├── config/
│   ├── settings.py            # Global config (env vars, paths)
│   └── trading_rules.py       # All risk / strategy parameters
├── src/
│   ├── data/
│   │   ├── market_data.py     # Price & indicator data (yfinance)
│   │   ├── options_data.py    # Options chain fetching & analysis
│   │   ├── sentiment.py       # News + market sentiment scoring
│   │   └── database.py        # SQLAlchemy models (trades, signals, …)
│   ├── strategies/
│   │   ├── momentum.py        # Enhanced momentum (tech + sent + ML)
│   │   └── options_strategy.py# Options signal generation
│   ├── execution/
│   │   ├── broker.py          # Alpaca API wrapper
│   │   └── risk_manager.py    # All risk checks & circuit breakers
│   ├── portfolio/
│   │   └── portfolio.py       # Portfolio state & performance
│   ├── ml/
│   │   └── predictor.py       # Gradient boosting stock predictor
│   └── utils/
│       ├── logger.py          # Loguru logging config
│       ├── notifications.py   # Email alerts
│       └── helpers.py         # Utility functions
├── scripts/
│   ├── setup_database.py      # Initialize DB & directories
│   ├── test_connection.py     # Verify Alpaca + data connectivity
│   └── paper_trading.py       # Main trading bot entry point
├── dashboard/
│   └── app.py                 # Streamlit monitoring dashboard
├── database/                  # SQLite DB (auto-created)
├── logs/                      # Rotating log files
├── requirements.txt
└── .env                       # API keys (not committed)
```

## 🚀 Quick start

### 1. 📋 Prerequisites

- Python 3.11+ (tested on 3.14) 🐍
- Alpaca paper trading account (free) – https://alpaca.markets

### 2. 📦 Install

```bash
cd /<your_path>/stock-trading-agent
python3 -m venv stock-trading-agent          # or use existing venv
source stock-trading-agent/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. ⚙️ Configure

Copy `.env.example` to `.env` and fill in your Alpaca API keys: 🔑

```
ALPACA_API_KEY=PKxxxxxxxxxxxxxxxxx
ALPACA_SECRET_KEY=xxxxxxxxxxxxxxxxxx
ALPACA_BASE_URL=https://paper-api.alpaca.markets
EMAIL_ADDRESS=your_email@example.com
PAPER_TRADING=true
```

### 4. 🔧 Initialize & test

```bash
python scripts/setup_database.py     # create DB tables & directories
python scripts/test_connection.py    # verify API keys & data access
```

### 5. ▶️ Run

```bash
# Terminal 1 – trading bot 🖥️
python scripts/paper_trading.py

# Terminal 2 – dashboard (optional) 📊
streamlit run dashboard/app.py       # opens http://localhost:8501
```

The bot scans every 15 minutes during market hours (9:30 AM – 4:00 PM ET). ⏰  
Press `Ctrl+C` to stop.

## ⚙️ Configuration

All trading parameters live in `config/trading_rules.py`. Key knobs: 🔧

```python
STOCK_ALLOCATION      = 0.50   # 50% stocks
OPTIONS_ALLOCATION    = 0.50   # 50% options
MAX_POSITION_SIZE_STOCK  = 0.10
MAX_POSITION_SIZE_OPTION = 0.05
STOCK_STOP_LOSS_PCT   = 0.08   # 8% stop
MAX_DRAWDOWN          = 0.40   # 40% kill switch
DAILY_LOSS_LIMIT      = 0.03   # 3% daily circuit breaker
MIN_ENTRY_SCORE       = 60     # minimum composite score
OPTIONS_MIN_DTE       = 30
OPTIONS_MAX_DTE       = 45
```

Restart the bot after changing config.

## 📊 Monitoring

### 📈 Dashboard

`streamlit run dashboard/app.py` → pages for portfolio, positions,
signals, performance charts, and risk metrics. 🎨

### 📝 Logs

```bash
tail -f logs/trading.log     # all activity 📋
tail -f logs/errors.log      # errors only ⚠️
```

### 📧 Email alerts

Configured via `.env`. Sends alerts on stop-loss triggers,
daily circuit breaker, and large positions (> $5K). 🔔

## ⚠️ Disclaimers

- **🔥 High risk.** Aggressive strategy using options leverage. You can
  lose the entire investment.
- **📉 No guarantees.** Past performance ≠ future results.
- **📄 Paper first.** Test for 1–2 months before risking real money.
- **💸 Tax implications.** Frequent trading has tax consequences.
- **👀 Monitoring required.** Check the bot daily even in paper mode.
