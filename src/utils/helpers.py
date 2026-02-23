"""
Helper utility functions.
"""
import pytz
from datetime import datetime, time as dt_time
from typing import Optional
from config.settings import MARKET_TIMEZONE


def is_market_open(current_time: Optional[datetime] = None) -> bool:
    """
    Check if the market is currently open.
    
    Args:
        current_time: Time to check (defaults to now)
        
    Returns:
        True if market is open, False otherwise
    """
    if current_time is None:
        current_time = datetime.now(pytz.timezone(MARKET_TIMEZONE))
    
    # Check if it's a weekday
    if current_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Market hours: 9:30 AM - 4:00 PM ET
    market_open = dt_time(9, 30)
    market_close = dt_time(16, 0)
    
    current_time_only = current_time.time()
    
    return market_open <= current_time_only < market_close


def get_market_time() -> datetime:
    """Get current time in market timezone (Eastern)."""
    return datetime.now(pytz.timezone(MARKET_TIMEZONE))


def format_currency(value: float) -> str:
    """Format a number as currency."""
    return f"${value:,.2f}"


def format_percentage(value: float) -> str:
    """Format a number as percentage."""
    return f"{value:.2f}%"


def calculate_position_size(
    portfolio_value: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss_price: float
) -> int:
    """
    Calculate position size based on risk parameters.
    
    Args:
        portfolio_value: Current portfolio value
        risk_per_trade: Risk per trade as decimal (e.g., 0.01 for 1%)
        entry_price: Entry price per share
        stop_loss_price: Stop loss price per share
        
    Returns:
        Number of shares to buy
    """
    risk_amount = portfolio_value * risk_per_trade
    risk_per_share = abs(entry_price - stop_loss_price)
    
    if risk_per_share == 0:
        return 0
    
    shares = int(risk_amount / risk_per_share)
    return max(shares, 0)


def calculate_stop_loss(entry_price: float, stop_loss_pct: float, direction: str = "long") -> float:
    """
    Calculate stop loss price.
    
    Args:
        entry_price: Entry price
        stop_loss_pct: Stop loss percentage as decimal (e.g., 0.08 for 8%)
        direction: 'long' or 'short'
        
    Returns:
        Stop loss price
    """
    if direction.lower() == "long":
        return entry_price * (1 - stop_loss_pct)
    else:  # short
        return entry_price * (1 + stop_loss_pct)


def calculate_profit_target(entry_price: float, profit_pct: float, direction: str = "long") -> float:
    """
    Calculate profit target price.
    
    Args:
        entry_price: Entry price
        profit_pct: Profit target percentage as decimal (e.g., 0.20 for 20%)
        direction: 'long' or 'short'
        
    Returns:
        Profit target price
    """
    if direction.lower() == "long":
        return entry_price * (1 + profit_pct)
    else:  # short
        return entry_price * (1 - profit_pct)


def round_to_penny(price: float) -> float:
    """Round price to nearest penny."""
    return round(price, 2)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero."""
    if denominator == 0:
        return default
    return numerator / denominator


__all__ = [
    "is_market_open",
    "get_market_time",
    "format_currency",
    "format_percentage",
    "calculate_position_size",
    "calculate_stop_loss",
    "calculate_profit_target",
    "round_to_penny",
    "safe_divide",
]
