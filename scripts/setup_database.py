#!/usr/bin/env python3
"""
Initialize the database and create all tables.
Run this script once before starting the trading system.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.database import init_db, engine
from src.utils.logger import logger
from config.settings import settings


def main():
    """Initialize the database."""
    print("=" * 60)
    print("TRADING SYSTEM - DATABASE SETUP")
    print("=" * 60)
    print()
    
    # Ensure database directory exists
    settings.database_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure logs directory exists
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure data directories exist
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "market_data").mkdir(exist_ok=True)
    (settings.data_dir / "backtest_results").mkdir(exist_ok=True)
    (settings.data_dir / "reports").mkdir(exist_ok=True)
    
    print(f"📁 Database location: {settings.database_url}")
    print()
    
    try:
        print("🔧 Creating database tables...")
        init_db()
        print("✅ Database tables created successfully!")
        print()
        
        # Test connection
        print("🔌 Testing database connection...")
        with engine.connect() as conn:
            print("✅ Database connection successful!")
        print()
        
        print("=" * 60)
        print("✅ DATABASE SETUP COMPLETE")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Add your Alpaca API keys to .env file")
        print("2. Run: python scripts/test_connection.py")
        print("3. Run: python scripts/paper_trading.py")
        print()
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        print(f"❌ Error: {e}")
        print()
        print("Please check:")
        print("- Database directory is writable")
        print("- No other process is using the database")
        print("- You have necessary permissions")
        sys.exit(1)


if __name__ == "__main__":
    main()
