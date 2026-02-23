"""
Portfolio management and tracking.
"""
from typing import Dict, List, Optional
from datetime import datetime
from src.execution.broker import broker
from src.data.database import get_db_session, Position, PortfolioSnapshot
from src.utils.logger import logger, log_performance
from src.utils.helpers import safe_divide


class Portfolio:
    """Manages portfolio state and performance tracking."""
    
    def __init__(self):
        """Initialize portfolio manager."""
        self.account_info = None
        self.positions = []
        self.db = get_db_session()
        
    def refresh(self):
        """Refresh portfolio data from broker."""
        try:
            self.account_info = broker.get_account()
            self.positions = broker.get_positions()
            
            if self.account_info:
                logger.debug(f"Portfolio refreshed: ${self.account_info['portfolio_value']:,.2f}")
            
        except Exception as e:
            logger.error(f"Error refreshing portfolio: {e}")
    
    def get_portfolio_value(self) -> float:
        """Get current portfolio value."""
        if not self.account_info:
            self.refresh()
        return self.account_info.get("portfolio_value", 0) if self.account_info else 0
    
    def get_cash(self) -> float:
        """Get available cash."""
        if not self.account_info:
            self.refresh()
        return self.account_info.get("cash", 0) if self.account_info else 0
    
    def get_buying_power(self) -> float:
        """Get buying power."""
        if not self.account_info:
            self.refresh()
        return self.account_info.get("buying_power", 0) if self.account_info else 0
    
    def get_position_counts(self) -> Dict[str, int]:
        """Get position counts by type."""
        if not self.positions:
            self.refresh()
        
        # For now, treat all as stocks (options would need special handling)
        total = len(self.positions)
        
        return {
            "total": total,
            "stocks": total,  # Simplified
            "options": 0,
        }
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get a specific position."""
        if not self.positions:
            self.refresh()
        
        for pos in self.positions:
            if pos["symbol"] == symbol:
                return pos
        
        return None
    
    def has_position(self, symbol: str) -> bool:
        """Check if we have a position in a symbol."""
        return self.get_position(symbol) is not None
    
    def get_sector_exposure(self) -> Dict[str, float]:
        """Get exposure by sector."""
        # This would require fetching sector info for each position
        # Simplified for now
        return {}
    
    def calculate_daily_pnl(self) -> Dict[str, float]:
        """Calculate today's P&L."""
        if not self.account_info:
            self.refresh()
        
        current_equity = self.account_info.get("equity", 0)
        last_equity = self.account_info.get("last_equity", 0)
        
        daily_pnl = current_equity - last_equity
        daily_pnl_pct = safe_divide(daily_pnl, last_equity, 0) * 100
        
        return {
            "daily_pnl": daily_pnl,
            "daily_pnl_pct": daily_pnl_pct,
        }
    
    def save_snapshot(self):
        """Save daily portfolio snapshot to database."""
        try:
            if not self.account_info:
                self.refresh()
            
            pnl_data = self.calculate_daily_pnl()
            position_counts = self.get_position_counts()
            
            snapshot = PortfolioSnapshot(
                date=datetime.now().strftime("%Y-%m-%d"),
                total_value=self.account_info.get("portfolio_value", 0),
                cash=self.account_info.get("cash", 0),
                stock_value=self.account_info.get("long_market_value", 0),
                options_value=0,  # TODO: Track separately
                daily_return=pnl_data.get("daily_pnl", 0),
                daily_return_pct=pnl_data.get("daily_pnl_pct", 0),
                num_positions=position_counts["total"],
                num_stock_positions=position_counts["stocks"],
                num_option_positions=position_counts["options"],
                max_drawdown=0,  # TODO: Calculate from history
                current_drawdown=0,  # TODO: Calculate
            )
            
            # Check if snapshot for today already exists
            existing = self.db.query(PortfolioSnapshot).filter(
                PortfolioSnapshot.date == snapshot.date
            ).first()
            
            if existing:
                # Update existing
                for key, value in snapshot.__dict__.items():
                    if not key.startswith('_'):
                        setattr(existing, key, value)
            else:
                # Create new
                self.db.add(snapshot)
            
            self.db.commit()
            logger.info("Portfolio snapshot saved")
            
        except Exception as e:
            logger.error(f"Error saving portfolio snapshot: {e}")
            self.db.rollback()
    
    def get_performance_metrics(self) -> Dict:
        """Calculate performance metrics."""
        try:
            # Get recent snapshots
            snapshots = self.db.query(PortfolioSnapshot).order_by(
                PortfolioSnapshot.timestamp.desc()
            ).limit(30).all()
            
            if not snapshots:
                return {}
            
            # Calculate metrics
            total_return = snapshots[0].total_return or 0
            total_return_pct = snapshots[0].total_return_pct or 0
            
            # Calculate Sharpe ratio (simplified)
            returns = [s.daily_return_pct for s in snapshots if s.daily_return_pct]
            if len(returns) > 1:
                import numpy as np
                sharpe_ratio = np.mean(returns) / (np.std(returns) + 0.0001) * np.sqrt(252)
            else:
                sharpe_ratio = 0
            
            return {
                "total_return": total_return,
                "total_return_pct": total_return_pct,
                "sharpe_ratio": sharpe_ratio,
                "num_days": len(snapshots),
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {}


# Global portfolio instance
portfolio = Portfolio()


__all__ = ["Portfolio", "portfolio"]
