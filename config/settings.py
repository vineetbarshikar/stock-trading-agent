"""
Global configuration settings for the trading agent.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()


class Settings(BaseSettings):
    """Global settings for the trading system."""
    
    model_config = {
        "extra": "ignore",  # Ignore extra fields in .env
        "env_file": ".env",
        "case_sensitive": False
    }
    
    # Alpaca API Configuration
    alpaca_api_key: str = Field(default="", env="ALPACA_API_KEY")
    alpaca_secret_key: str = Field(default="", env="ALPACA_SECRET_KEY")
    alpaca_base_url: str = Field(
        default="https://paper-api.alpaca.markets",
        env="ALPACA_BASE_URL"
    )
    
    # Trading Configuration
    initial_capital: float = Field(default=50000.0, env="INITIAL_CAPITAL")
    paper_trading: bool = Field(default=True, env="PAPER_TRADING")
    environment: str = Field(default="paper", env="ENVIRONMENT")
    
    # Email Configuration
    email_address: str = Field(default="vbarshikar@gmail.com", env="EMAIL_ADDRESS")
    email_password: str = Field(default="", env="EMAIL_PASSWORD")
    email_smtp_server: str = Field(default="smtp.gmail.com", env="EMAIL_SMTP_SERVER")
    email_smtp_port: int = Field(default=587, env="EMAIL_SMTP_PORT")
    
    # Database Configuration
    database_url: str = Field(
        default=f"sqlite:///{PROJECT_ROOT}/database/trading.db",
        env="DATABASE_URL"
    )
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_to_file: bool = Field(default=True, env="LOG_TO_FILE")
    
    # Directories
    data_dir: Path = PROJECT_ROOT / "data"
    logs_dir: Path = PROJECT_ROOT / "logs"
    database_dir: Path = PROJECT_ROOT / "database"
    
    # Market Configuration
    market_open_hour: int = 9
    market_open_minute: int = 30
    market_close_hour: int = 16
    market_close_minute: int = 0
    
    # Scanning Configuration
    scan_interval_minutes: int = 15  # How often to scan for opportunities


# Global settings instance
settings = Settings()


# Market hours (Eastern Time)
MARKET_TIMEZONE = "America/New_York"

# Data refresh intervals
DATA_REFRESH_INTERVAL = 60  # seconds

# API rate limits
ALPACA_RATE_LIMIT = 200  # requests per minute

# Notification settings
SEND_DAILY_REPORT = True
DAILY_REPORT_TIME = "17:00"  # 5 PM ET

# Alert thresholds
LARGE_POSITION_ALERT_THRESHOLD = 5000  # Alert if position > $5K
POSITION_LOSS_ALERT_THRESHOLD = 0.10  # Alert if position down > 10%
