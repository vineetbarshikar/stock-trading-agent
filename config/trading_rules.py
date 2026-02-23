"""
Trading rules and risk management parameters.
"""

# ============================================================================
# PORTFOLIO ALLOCATION
# ============================================================================

# Overall allocation
STOCK_ALLOCATION = 0.50  # 50% of capital in stocks
OPTIONS_ALLOCATION = 0.50  # 50% of capital in options

# Cash reserve
MIN_CASH_RESERVE = 0.05  # Keep minimum 5% cash

# ============================================================================
# POSITION SIZING
# ============================================================================

# Maximum position sizes (as percentage of portfolio)
MAX_POSITION_SIZE_STOCK = 0.10  # 10% max per stock position
MAX_POSITION_SIZE_OPTION = 0.05  # 5% max per options position

# Minimum position sizes
MIN_POSITION_SIZE = 1000  # Minimum $1,000 per position

# Maximum number of positions
MAX_TOTAL_POSITIONS = 15
MAX_STOCK_POSITIONS = 8
MAX_OPTIONS_POSITIONS = 12

# ============================================================================
# RISK MANAGEMENT
# ============================================================================

# Portfolio-level risk limits
MAX_DRAWDOWN = 0.40  # Stop all trading if down 40% from peak
DAILY_LOSS_LIMIT = 0.03  # Stop trading if down 3% in one day
MAX_PORTFOLIO_HEAT = 0.30  # Max 30% of portfolio at risk at any time

# Position-level stop losses
STOCK_STOP_LOSS_PCT = 0.08  # 8% stop loss on stocks
STOCK_TRAILING_STOP_PCT = 0.25  # 25% trailing stop from peak

# Options stop losses
OPTION_STOP_LOSS_PCT = 0.50  # Stop out at 50% loss
OPTION_TIME_STOP_DTE = 7  # Close 1 week before expiry if not profitable

# ============================================================================
# SECTOR & CONCENTRATION LIMITS
# ============================================================================

# Sector exposure limits
MAX_SECTOR_EXPOSURE = 0.30  # Max 30% in any single sector

# Correlation limits
MAX_CORRELATION_POSITIONS = 3  # Max 3 highly correlated positions

# ============================================================================
# STOCK STRATEGY PARAMETERS
# ============================================================================

# Stock screening criteria
MIN_STOCK_PRICE = 10.0  # Minimum $10 per share
MAX_STOCK_PRICE = 1000.0  # Maximum $1000 per share
MIN_AVG_VOLUME = 1_000_000  # Minimum 1M shares daily volume
MIN_MARKET_CAP = 1_000_000_000  # Minimum $1B market cap

# Momentum strategy
MOMENTUM_RSI_THRESHOLD = 70  # Relative strength > 70
MOMENTUM_LOOKBACK_DAYS = 90  # 3-month lookback
MOMENTUM_MA_PERIODS = [50, 200]  # Moving average periods

# Breakout strategy
BREAKOUT_VOLUME_MULTIPLIER = 2.0  # 2x average volume
BREAKOUT_CONSOLIDATION_DAYS = 10  # Look for 10-day consolidation

# Profit targets
STOCK_PROFIT_TARGET_MIN = 0.15  # 15% minimum profit target
STOCK_PROFIT_TARGET_MAX = 0.30  # 30% maximum profit target

# Holding periods
STOCK_MIN_HOLD_DAYS = 1  # Minimum 1 day hold
STOCK_MAX_HOLD_DAYS = 30  # Maximum 30 day hold

# ============================================================================
# OPTIONS STRATEGY PARAMETERS
# ============================================================================

# Options allocation breakdown
LONG_CALL_ALLOCATION = 0.30  # 30% of options capital
LONG_PUT_ALLOCATION = 0.30  # 30% of options capital
SPREADS_ALLOCATION = 0.40  # 40% of options capital

# Options expiration
OPTIONS_MIN_DTE = 30  # Minimum 30 days to expiration
OPTIONS_MAX_DTE = 45  # Maximum 45 days to expiration
OPTIONS_TARGET_DTE = 37  # Target ~37 days (monthly options)

# Options Greeks targets
LONG_OPTION_MIN_DELTA = 0.40  # Minimum delta for long options
LONG_OPTION_MAX_DELTA = 0.60  # Maximum delta for long options
LONG_OPTION_TARGET_DELTA = 0.50  # Target delta (slightly OTM)

# Options IV criteria
MAX_IV_PERCENTILE = 50  # Don't buy if IV > 50th percentile (too expensive)
MIN_IV_FOR_PUTS = 30  # Minimum IV for put options

# Spread parameters
SPREAD_MIN_RISK_REWARD = 2.0  # Minimum 1:2 risk/reward
SPREAD_WIDTH_PERCENTAGE = 0.05  # Spread width ~5% of stock price

# Options profit targets
OPTION_PROFIT_TARGET = 1.00  # 100% gain target
OPTION_PARTIAL_EXIT = 0.50  # Take 50% off at 50% gain

# ============================================================================
# ENTRY & EXIT RULES
# ============================================================================

# Entry timing
AVOID_FIRST_15_MIN = True  # Avoid trading first 15 min after open
AVOID_LAST_15_MIN = True  # Avoid trading last 15 min before close

# Order types
DEFAULT_STOCK_ORDER_TYPE = "limit"  # Use limit orders for stocks
DEFAULT_OPTION_ORDER_TYPE = "limit"  # Use limit orders for options
LIMIT_ORDER_OFFSET_PCT = 0.001  # 0.1% offset from mid price

# Exit priorities
EXIT_ON_STOP_LOSS = True
EXIT_ON_PROFIT_TARGET = True
EXIT_ON_TIME_STOP = True
EXIT_ON_TECHNICAL_SIGNAL = True

# ============================================================================
# POSITION MONITORING
# ============================================================================

# How often to check positions
POSITION_CHECK_INTERVAL = 60  # Check every 60 seconds during market hours

# Greeks monitoring (for options)
MAX_PORTFOLIO_DELTA = 100  # Max net delta exposure
MAX_PORTFOLIO_GAMMA = 50  # Max net gamma exposure
MONITOR_THETA_DECAY = True  # Monitor theta decay

# ============================================================================
# STRATEGY ALLOCATION
# ============================================================================

# Stock strategies allocation
MOMENTUM_STRATEGY_ALLOCATION = 0.40  # 40% to momentum
BREAKOUT_STRATEGY_ALLOCATION = 0.40  # 40% to breakout
SECTOR_ROTATION_ALLOCATION = 0.20  # 20% to sector rotation

# Options strategies allocation
DIRECTIONAL_OPTIONS_ALLOCATION = 0.60  # 60% to directional plays
SPREAD_OPTIONS_ALLOCATION = 0.40  # 40% to spreads

# ============================================================================
# SCORING & RANKING
# ============================================================================

# Minimum score for entry
MIN_ENTRY_SCORE = 60  # Score out of 100 (lowered from 70 for broader coverage)

# Signal confidence levels
HIGH_CONFIDENCE_THRESHOLD = 85
MEDIUM_CONFIDENCE_THRESHOLD = 70
LOW_CONFIDENCE_THRESHOLD = 60

# ============================================================================
# MARKET REGIME DETECTION
# ============================================================================

# Use market regime to adjust risk
USE_MARKET_REGIME = True

# SPY indicators for market regime
SPY_SMA_PERIODS = [20, 50, 200]
VIX_THRESHOLD_HIGH = 25  # High volatility
VIX_THRESHOLD_LOW = 15  # Low volatility

# Risk adjustments based on regime
BEAR_MARKET_POSITION_SIZE_MULTIPLIER = 0.50  # Cut sizes in half
HIGH_VOL_POSITION_SIZE_MULTIPLIER = 0.75  # Reduce by 25%

# ============================================================================
# BACKTESTING & OPTIMIZATION
# ============================================================================

# Backtesting parameters
BACKTEST_START_DATE = "2023-01-01"
BACKTEST_END_DATE = "2024-12-31"
BACKTEST_INITIAL_CAPITAL = 50000

# Optimization
OPTIMIZE_PARAMETERS = False  # Enable parameter optimization
OPTIMIZATION_METRIC = "sharpe_ratio"  # Optimize for Sharpe ratio

# ============================================================================
# LOGGING & ALERTS
# ============================================================================

# What to log
LOG_ALL_SIGNALS = True
LOG_ALL_ORDERS = True
LOG_POSITION_CHANGES = True
LOG_PORTFOLIO_SNAPSHOTS = True  # Daily snapshots

# Alert conditions
ALERT_ON_LARGE_POSITION = True  # Alert if position > threshold
ALERT_ON_STOP_LOSS = True
ALERT_ON_DAILY_LIMIT = True
ALERT_ON_SYSTEM_ERROR = True
ALERT_ON_MISSED_OPPORTUNITY = False  # Too noisy

# ============================================================================
# DEVELOPMENT & DEBUGGING
# ============================================================================

# Development mode
DEBUG_MODE = False
DRY_RUN = False  # If True, don't place actual orders
VERBOSE_LOGGING = True

# Paper trading specific
PAPER_TRADING_SLIPPAGE = 0.001  # Assume 0.1% slippage
PAPER_TRADING_COMMISSION = 0.0  # Alpaca is commission-free
