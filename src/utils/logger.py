"""
Logging configuration using loguru.
"""
import sys
from pathlib import Path
from loguru import logger
from config.settings import settings

# Remove default logger
logger.remove()

# Console logging (with colors)
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level,
    colorize=True,
)

# File logging - Main log
if settings.log_to_file:
    logger.add(
        settings.logs_dir / "trading.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="1 day",
        retention="30 days",
        compression="zip",
    )
    
    # Error log
    logger.add(
        settings.logs_dir / "errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="1 week",
        retention="60 days",
        compression="zip",
    )
    
    # Performance log
    logger.add(
        settings.logs_dir / "performance.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
        level="INFO",
        rotation="1 day",
        retention="90 days",
        compression="zip",
        filter=lambda record: "PERFORMANCE" in record["extra"],
    )


def get_logger(name: str):
    """Get a logger instance with the given name."""
    return logger.bind(name=name)


def log_trade(action: str, symbol: str, quantity: float, price: float, **kwargs):
    """Log a trade action."""
    logger.bind(PERFORMANCE=True).info(
        f"TRADE | {action} | {symbol} | Qty: {quantity} | Price: ${price:.2f} | {kwargs}"
    )


def log_performance(metric: str, value: float, **kwargs):
    """Log a performance metric."""
    logger.bind(PERFORMANCE=True).info(
        f"METRIC | {metric} | Value: {value:.4f} | {kwargs}"
    )


def log_signal(strategy: str, symbol: str, signal_type: str, score: float, **kwargs):
    """Log a trading signal."""
    logger.info(
        f"SIGNAL | {strategy} | {symbol} | {signal_type} | Score: {score:.2f} | {kwargs}"
    )


def log_risk_event(event_type: str, severity: str, message: str, **kwargs):
    """Log a risk management event."""
    if severity.upper() == "CRITICAL":
        logger.critical(f"RISK | {event_type} | {message} | {kwargs}")
    elif severity.upper() == "WARNING":
        logger.warning(f"RISK | {event_type} | {message} | {kwargs}")
    else:
        logger.info(f"RISK | {event_type} | {message} | {kwargs}")


# Export the logger
__all__ = ["logger", "get_logger", "log_trade", "log_performance", "log_signal", "log_risk_event"]
