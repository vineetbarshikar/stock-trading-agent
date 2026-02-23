#!/usr/bin/env python3
"""
Test connection to Alpaca API and verify everything is working.
Run this after setting up your .env file with API credentials.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.execution.broker import broker
from src.data.market_data import market_data
from src.utils.logger import logger
from config.settings import settings


def test_alpaca_connection():
    """Test Alpaca API connection."""
    print("🔌 Testing Alpaca API connection...")
    
    try:
        account = broker.get_account()
        
        if account:
            print("✅ Alpaca API connected successfully!")
            print()
            print("Account Information:")
            print(f"  Portfolio Value: ${account['portfolio_value']:,.2f}")
            print(f"  Cash: ${account['cash']:,.2f}")
            print(f"  Buying Power: ${account['buying_power']:,.2f}")
            print(f"  Day Trades: {account['daytrade_count']}")
            print()
            return True
        else:
            print("❌ Failed to fetch account info")
            return False
            
    except Exception as e:
        print(f"❌ Alpaca API connection failed: {e}")
        print()
        print("Please check:")
        print("1. Your API keys in .env file are correct")
        print("2. You're using paper trading keys (should start with 'PK')")
        print("3. Your internet connection is working")
        return False


def test_market_data():
    """Test market data fetching."""
    print("📊 Testing market data fetching...")
    
    try:
        # Test with Apple stock
        price = market_data.get_current_price("AAPL")
        
        if price:
            print(f"✅ Market data working! AAPL current price: ${price:.2f}")
            print()
            return True
        else:
            print("❌ Failed to fetch market data")
            return False
            
    except Exception as e:
        print(f"❌ Market data fetch failed: {e}")
        return False


def test_positions():
    """Test fetching positions."""
    print("📋 Testing positions fetch...")
    
    try:
        positions = broker.get_positions()
        print(f"✅ Found {len(positions)} open positions")
        
        if positions:
            print("\nCurrent Positions:")
            for pos in positions:
                print(f"  {pos['symbol']}: {pos['qty']} shares @ ${pos['avg_entry_price']:.2f}")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Failed to fetch positions: {e}")
        return False


def main():
    """Run all connection tests."""
    print("=" * 60)
    print("TRADING SYSTEM - CONNECTION TEST")
    print("=" * 60)
    print()
    
    # Check environment
    print(f"Environment: {settings.environment}")
    print(f"Paper Trading: {settings.paper_trading}")
    print(f"API URL: {settings.alpaca_base_url}")
    print()
    
    if not settings.alpaca_api_key or settings.alpaca_api_key == "your_api_key_here":
        print("❌ ERROR: Alpaca API keys not configured!")
        print()
        print("Please edit your .env file and add:")
        print("  ALPACA_API_KEY=your_key_here")
        print("  ALPACA_SECRET_KEY=your_secret_here")
        print()
        sys.exit(1)
    
    # Run tests
    tests_passed = 0
    tests_total = 3
    
    if test_alpaca_connection():
        tests_passed += 1
    
    if test_market_data():
        tests_passed += 1
    
    if test_positions():
        tests_passed += 1
    
    # Summary
    print("=" * 60)
    print(f"TEST RESULTS: {tests_passed}/{tests_total} passed")
    print("=" * 60)
    print()
    
    if tests_passed == tests_total:
        print("✅ ALL SYSTEMS GO!")
        print()
        print("You're ready to start paper trading!")
        print("Run: python scripts/paper_trading.py")
        print()
        return 0
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
