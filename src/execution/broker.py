"""
Alpaca broker interface for paper and live trading.
"""
from typing import Optional, List, Dict
from decimal import Decimal
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from config.settings import settings
from src.utils.logger import logger, log_trade


class AlpacaBroker:
    """Interface to Alpaca trading API."""
    
    def __init__(self):
        """Initialize the Alpaca broker client."""
        self.client = TradingClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            paper=settings.paper_trading,
            raw_data=False,
            url_override=None,
        )
        logger.info(f"Alpaca broker initialized (paper={settings.paper_trading})")
        
    def get_account(self) -> Optional[Dict]:
        """
        Get account information.
        
        Returns:
            Dictionary with account info or None if error
        """
        try:
            account = self.client.get_account()
            
            return {
                "portfolio_value": float(account.portfolio_value),
                "cash": float(account.cash),
                "buying_power": float(account.buying_power),
                "equity": float(account.equity),
                "last_equity": float(account.last_equity),
                "long_market_value": float(account.long_market_value),
                "short_market_value": float(account.short_market_value),
                "initial_margin": float(account.initial_margin),
                "maintenance_margin": float(account.maintenance_margin),
                "daytrade_count": int(account.daytrade_count),
                "daytrading_buying_power": float(account.daytrading_buying_power),
            }
            
        except Exception as e:
            logger.error(f"Error fetching account info: {e}")
            return None
    
    def get_positions(self) -> List[Dict]:
        """
        Get all open positions.
        
        Returns:
            List of position dictionaries
        """
        try:
            positions = self.client.get_all_positions()
            
            result = []
            for pos in positions:
                result.append({
                    "symbol": pos.symbol,
                    "qty": float(pos.qty),
                    "side": pos.side,
                    "avg_entry_price": float(pos.avg_entry_price),
                    "current_price": float(pos.current_price),
                    "market_value": float(pos.market_value),
                    "cost_basis": float(pos.cost_basis),
                    "unrealized_pl": float(pos.unrealized_pl),
                    "unrealized_plpc": float(pos.unrealized_plpc),
                    "unrealized_intraday_pl": float(pos.unrealized_intraday_pl),
                    "unrealized_intraday_plpc": float(pos.unrealized_intraday_plpc),
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get a specific position.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Position dictionary or None if not found
        """
        try:
            position = self.client.get_open_position(symbol)
            
            return {
                "symbol": position.symbol,
                "qty": float(position.qty),
                "side": position.side,
                "avg_entry_price": float(position.avg_entry_price),
                "current_price": float(position.current_price),
                "market_value": float(position.market_value),
                "cost_basis": float(position.cost_basis),
                "unrealized_pl": float(position.unrealized_pl),
                "unrealized_plpc": float(position.unrealized_plpc),
            }
            
        except Exception as e:
            # Position doesn't exist
            return None
    
    def place_market_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        time_in_force: str = "day"
    ) -> Optional[Dict]:
        """
        Place a market order.
        
        Args:
            symbol: Stock ticker symbol
            qty: Quantity to trade
            side: 'buy' or 'sell'
            time_in_force: Order duration ('day', 'gtc', etc.)
            
        Returns:
            Order dictionary or None if error
        """
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            tif = TimeInForce.DAY if time_in_force == "day" else TimeInForce.GTC
            
            request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=tif
            )
            
            order = self.client.submit_order(request)
            
            order_dict = {
                "id": order.id,
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side.value,
                "type": order.type.value,
                "status": order.status.value,
                "created_at": order.created_at,
                "filled_at": order.filled_at,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
            }
            
            log_trade(side.upper(), symbol, qty, 0, order_id=order.id)
            logger.info(f"Market order placed: {side} {qty} {symbol}")
            
            return order_dict
            
        except Exception as e:
            logger.error(f"Error placing market order for {symbol}: {e}")
            return None
    
    def place_limit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        limit_price: float,
        time_in_force: str = "day"
    ) -> Optional[Dict]:
        """
        Place a limit order.
        
        Args:
            symbol: Stock ticker symbol
            qty: Quantity to trade
            side: 'buy' or 'sell'
            limit_price: Limit price
            time_in_force: Order duration ('day', 'gtc', etc.)
            
        Returns:
            Order dictionary or None if error
        """
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            tif = TimeInForce.DAY if time_in_force == "day" else TimeInForce.GTC
            
            # Round price to 2 decimal places (penny increment)
            limit_price = round(limit_price, 2)
            
            request = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=tif,
                limit_price=limit_price
            )
            
            order = self.client.submit_order(request)
            
            order_dict = {
                "id": order.id,
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side.value,
                "type": order.type.value,
                "status": order.status.value,
                "limit_price": float(order.limit_price),
                "created_at": order.created_at,
                "filled_at": order.filled_at,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
            }
            
            log_trade(side.upper(), symbol, qty, limit_price, order_id=order.id)
            logger.info(f"Limit order placed: {side} {qty} {symbol} @ ${limit_price}")
            
            return order_dict
            
        except Exception as e:
            logger.error(f"Error placing limit order for {symbol}: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        try:
            self.client.cancel_order_by_id(order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_orders(self, status: str = "open") -> List[Dict]:
        """
        Get orders.
        
        Args:
            status: Order status ('open', 'closed', 'all')
            
        Returns:
            List of order dictionaries
        """
        try:
            status_map = {
                "open": QueryOrderStatus.OPEN,
                "closed": QueryOrderStatus.CLOSED,
                "all": QueryOrderStatus.ALL,
            }
            
            request = GetOrdersRequest(
                status=status_map.get(status, QueryOrderStatus.OPEN)
            )
            
            orders = self.client.get_orders(request)
            
            result = []
            for order in orders:
                result.append({
                    "id": order.id,
                    "symbol": order.symbol,
                    "qty": float(order.qty),
                    "side": order.side.value,
                    "type": order.type.value,
                    "status": order.status.value,
                    "created_at": order.created_at,
                    "filled_at": order.filled_at,
                    "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                    "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            return []
    
    def close_position(self, symbol: str) -> bool:
        """
        Close a position (market order).
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            True if closed successfully
        """
        try:
            self.client.close_position(symbol)
            logger.info(f"Position closed: {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")
            return False
    
    def close_all_positions(self) -> bool:
        """
        Close all positions.
        
        Returns:
            True if all closed successfully
        """
        try:
            self.client.close_all_positions(cancel_orders=True)
            logger.warning("All positions closed")
            return True
            
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            return False


# Global broker instance
broker = AlpacaBroker()


__all__ = ["AlpacaBroker", "broker"]
