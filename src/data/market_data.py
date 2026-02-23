"""
Market data fetching from Alpaca and Yahoo Finance.
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from config.settings import settings
from src.utils.logger import logger


class MarketDataFetcher:
    """Fetches real-time and historical market data."""
    
    def __init__(self):
        """Initialize the market data fetcher."""
        try:
            self.alpaca_client = StockHistoricalDataClient(
                api_key=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                raw_data=False,
                url_override=None,
            )
        except Exception as e:
            logger.warning(f"Could not initialize Alpaca data client: {e}")
            self.alpaca_client = None
        self._cache = {}
        self._use_yfinance_fallback = True  # Use yfinance as primary for reliability
        
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Current price or None if error
        """
        try:
            # Use yfinance for current price (more reliable)
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")
            
            if not data.empty:
                return float(data['Close'].iloc[-1])
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            
            # Fallback to Alpaca if yfinance fails
            if self.alpaca_client:
                try:
                    request = StockLatestQuoteRequest(symbol_or_symbols=[symbol])
                    quotes = self.alpaca_client.get_stock_latest_quote(request)
                    
                    if symbol in quotes:
                        quote = quotes[symbol]
                        return (quote.ask_price + quote.bid_price) / 2
                except:
                    pass
            
            return None
    
    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get current prices for multiple symbols.
        
        Args:
            symbols: List of ticker symbols
            
        Returns:
            Dictionary of symbol: price
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbols)
            quotes = self.alpaca_client.get_stock_latest_quote(request)
            
            prices = {}
            for symbol in symbols:
                if symbol in quotes:
                    quote = quotes[symbol]
                    prices[symbol] = (quote.ask_price + quote.bid_price) / 2
                    
            return prices
            
        except Exception as e:
            logger.error(f"Error fetching prices for {symbols}: {e}")
            return {}
    
    def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        timeframe: str = "1D"
    ) -> Optional[pd.DataFrame]:
        """
        Get historical price data.
        
        Args:
            symbol: Stock ticker symbol
            start_date: Start date
            end_date: End date (defaults to now)
            timeframe: Timeframe (1D, 1H, etc.)
            
        Returns:
            DataFrame with OHLCV data or None if error
        """
        try:
            # Use yfinance as primary (more reliable and no timeout issues)
            return self._get_yfinance_data(symbol, start_date, end_date)
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return None
    
    def _get_yfinance_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """Fallback to yfinance for historical data."""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty:
                return None
                
            # Standardize column names
            df.columns = [col.lower() for col in df.columns]
            return df
            
        except Exception as e:
            logger.error(f"Error fetching yfinance data for {symbol}: {e}")
            return None
    
    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """
        Get stock information (sector, market cap, etc.).
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary of stock info or None if error
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                "symbol": symbol,
                "name": info.get("longName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap", 0),
                "avg_volume": info.get("averageVolume", 0),
                "pe_ratio": info.get("trailingPE", None),
                "52w_high": info.get("fiftyTwoWeekHigh", 0),
                "52w_low": info.get("fiftyTwoWeekLow", 0),
            }
            
        except Exception as e:
            logger.error(f"Error fetching info for {symbol}: {e}")
            return None
    
    def get_movers(self, n: int = 20) -> Dict[str, List[str]]:
        """
        Get market movers (gainers and losers).
        
        Args:
            n: Number of movers to return
            
        Returns:
            Dictionary with 'gainers' and 'losers' lists
        """
        try:
            # Get S&P 500 constituents
            sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            tables = pd.read_html(sp500_url)
            sp500_df = tables[0]
            symbols = sp500_df['Symbol'].tolist()[:100]  # Sample top 100
            
            # Get current prices and changes
            changes = {}
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="2d")
                    if len(hist) >= 2:
                        change_pct = (hist['Close'].iloc[-1] / hist['Close'].iloc[-2] - 1) * 100
                        changes[symbol] = change_pct
                except:
                    continue
            
            # Sort by change
            sorted_changes = sorted(changes.items(), key=lambda x: x[1], reverse=True)
            
            gainers = [symbol for symbol, _ in sorted_changes[:n]]
            losers = [symbol for symbol, _ in sorted_changes[-n:]]
            
            return {"gainers": gainers, "losers": losers}
            
        except Exception as e:
            logger.error(f"Error fetching movers: {e}")
            return {"gainers": [], "losers": []}
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators on OHLCV data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added technical indicators
        """
        try:
            # Simple moving averages
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['sma_200'] = df['close'].rolling(window=200).mean()
            
            # Exponential moving averages
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
            # Volume averages
            df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return df


# Global instance
market_data = MarketDataFetcher()


__all__ = ["MarketDataFetcher", "market_data"]
