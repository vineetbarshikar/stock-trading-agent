"""
Database models and connection management using SQLAlchemy.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from config.settings import settings

# Create declarative base
Base = declarative_base()

# Create engine
engine = create_engine(
    settings.database_url,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ============================================================================
# DATABASE MODELS
# ============================================================================

class Trade(Base):
    """Model for executed trades."""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Trade details
    symbol = Column(String(10), index=True)
    action = Column(String(10))  # BUY, SELL
    asset_type = Column(String(10))  # STOCK, OPTION
    quantity = Column(Float)
    price = Column(Float)
    value = Column(Float)  # Total value of trade
    
    # Strategy info
    strategy = Column(String(50), index=True)
    signal_score = Column(Float)
    
    # Order info
    order_id = Column(String(50), unique=True, index=True)
    order_type = Column(String(20))
    status = Column(String(20))
    
    # P&L (for closing trades)
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    
    # Additional data
    notes = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)


class Position(Base):
    """Model for current and historical positions."""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    opened_at = Column(DateTime, default=datetime.utcnow, index=True)
    closed_at = Column(DateTime, nullable=True, index=True)
    
    # Position details
    symbol = Column(String(10), index=True)
    asset_type = Column(String(10))  # STOCK, OPTION
    quantity = Column(Float)
    
    # Entry/Exit
    entry_price = Column(Float)
    current_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    
    # Cost basis
    cost_basis = Column(Float)
    current_value = Column(Float, nullable=True)
    
    # P&L
    unrealized_pnl = Column(Float, nullable=True)
    realized_pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    
    # Risk management
    stop_loss = Column(Float, nullable=True)
    profit_target = Column(Float, nullable=True)
    trailing_stop = Column(Float, nullable=True)
    
    # Strategy
    strategy = Column(String(50), index=True)
    
    # Status
    is_open = Column(Boolean, default=True, index=True)
    
    # Options specific
    option_type = Column(String(10), nullable=True)  # CALL, PUT
    strike = Column(Float, nullable=True)
    expiration = Column(DateTime, nullable=True)
    
    # Greeks (for options)
    delta = Column(Float, nullable=True)
    gamma = Column(Float, nullable=True)
    theta = Column(Float, nullable=True)
    vega = Column(Float, nullable=True)
    iv = Column(Float, nullable=True)  # Implied volatility
    
    # Additional data
    extra_data = Column(JSON, nullable=True)


class PortfolioSnapshot(Base):
    """Daily portfolio snapshots for performance tracking."""
    __tablename__ = "portfolio_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    date = Column(String(10), unique=True, index=True)  # YYYY-MM-DD
    
    # Portfolio values
    total_value = Column(Float)
    cash = Column(Float)
    stock_value = Column(Float)
    options_value = Column(Float)
    
    # Returns
    daily_return = Column(Float)
    daily_return_pct = Column(Float)
    total_return = Column(Float)
    total_return_pct = Column(Float)
    
    # Positions
    num_positions = Column(Integer)
    num_stock_positions = Column(Integer)
    num_option_positions = Column(Integer)
    
    # Risk metrics
    portfolio_beta = Column(Float, nullable=True)
    portfolio_delta = Column(Float, nullable=True)
    max_drawdown = Column(Float)
    current_drawdown = Column(Float)
    
    # Performance metrics
    sharpe_ratio = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    
    # Benchmark comparison
    spy_return = Column(Float, nullable=True)
    alpha = Column(Float, nullable=True)
    
    # Additional data
    extra_data = Column(JSON, nullable=True)


class Signal(Base):
    """Trading signals generated by strategies."""
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Signal details
    symbol = Column(String(10), index=True)
    asset_type = Column(String(10))  # STOCK, OPTION
    signal_type = Column(String(10))  # BUY, SELL
    strategy = Column(String(50), index=True)
    
    # Signal strength
    score = Column(Float)
    confidence = Column(String(20))  # HIGH, MEDIUM, LOW
    
    # Price info
    current_price = Column(Float)
    suggested_entry = Column(Float, nullable=True)
    suggested_stop = Column(Float, nullable=True)
    suggested_target = Column(Float, nullable=True)
    
    # Position sizing
    suggested_size = Column(Float, nullable=True)
    risk_amount = Column(Float, nullable=True)
    
    # Status
    is_executed = Column(Boolean, default=False, index=True)
    executed_at = Column(DateTime, nullable=True)
    
    # Options specific
    option_type = Column(String(10), nullable=True)
    strike = Column(Float, nullable=True)
    expiration = Column(DateTime, nullable=True)
    
    # Additional data
    reasoning = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)


class MarketData(Base):
    """Cached market data."""
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Symbol info
    symbol = Column(String(10), index=True)
    
    # OHLCV data
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    
    # Technical indicators
    sma_20 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    sma_200 = Column(Float, nullable=True)
    rsi = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    
    # Additional data
    extra_data = Column(JSON, nullable=True)


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def init_db():
    """Initialize the database (create all tables)."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """Get a database session (for non-generator context)."""
    return SessionLocal()


__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "Trade",
    "Position",
    "PortfolioSnapshot",
    "Signal",
    "MarketData",
    "init_db",
    "get_db",
    "get_db_session",
]
