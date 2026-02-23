"""
Risk management system - THE MOST CRITICAL MODULE.
This module enforces all risk limits and prevents dangerous trades.
"""
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from config import trading_rules
from src.utils.logger import logger, log_risk_event
from src.utils.notifications import notifier


class RiskManager:
    """Manages all risk controls for the trading system."""
    
    def __init__(self):
        """Initialize the risk manager."""
        self.daily_start_equity = None
        self.peak_equity = None
        self.circuit_breaker_triggered = False
        self.max_drawdown_triggered = False
        self.daily_loss_count = 0
        self.last_reset_date = None
        
        logger.info("Risk Manager initialized")
    
    def reset_daily_limits(self, current_equity: float):
        """Reset daily risk limits (call at market open)."""
        today = datetime.now().date()
        
        if self.last_reset_date != today:
            self.daily_start_equity = current_equity
            self.circuit_breaker_triggered = False
            self.daily_loss_count = 0
            self.last_reset_date = today
            
            logger.info(f"Daily limits reset. Starting equity: ${current_equity:,.2f}")
    
    def update_peak_equity(self, current_equity: float):
        """Update peak equity for drawdown calculation."""
        if self.peak_equity is None or current_equity > self.peak_equity:
            self.peak_equity = current_equity
    
    def check_daily_loss_limit(self, current_equity: float) -> Tuple[bool, str]:
        """
        Check if daily loss limit has been hit.
        
        Args:
            current_equity: Current portfolio equity
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        if self.circuit_breaker_triggered:
            return False, "Circuit breaker already triggered today"
        
        if self.daily_start_equity is None:
            self.daily_start_equity = current_equity
            return True, ""
        
        daily_loss = self.daily_start_equity - current_equity
        daily_loss_pct = daily_loss / self.daily_start_equity
        
        if daily_loss_pct >= trading_rules.DAILY_LOSS_LIMIT:
            self.circuit_breaker_triggered = True
            
            log_risk_event(
                "CIRCUIT_BREAKER",
                "CRITICAL",
                f"Daily loss limit hit: {daily_loss_pct:.2%}. Trading stopped for today."
            )
            
            notifier.send_risk_alert(
                "Daily Loss Limit Hit - Circuit Breaker Triggered",
                f"Portfolio down {daily_loss_pct:.2%} today (${daily_loss:,.2f}).\n"
                f"Trading has been stopped for the remainder of the day.\n"
                f"System will reset tomorrow at market open.",
                "CRITICAL"
            )
            
            return False, f"Daily loss limit hit: {daily_loss_pct:.2%}"
        
        return True, ""
    
    def check_max_drawdown(self, current_equity: float) -> Tuple[bool, str]:
        """
        Check if maximum drawdown limit has been hit.
        
        Args:
            current_equity: Current portfolio equity
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        if self.max_drawdown_triggered:
            return False, "Max drawdown limit already triggered"
        
        if self.peak_equity is None:
            self.peak_equity = current_equity
            return True, ""
        
        self.update_peak_equity(current_equity)
        
        drawdown = (self.peak_equity - current_equity) / self.peak_equity
        
        if drawdown >= trading_rules.MAX_DRAWDOWN:
            self.max_drawdown_triggered = True
            
            log_risk_event(
                "MAX_DRAWDOWN",
                "CRITICAL",
                f"Maximum drawdown hit: {drawdown:.2%}. ALL TRADING STOPPED."
            )
            
            notifier.send_risk_alert(
                "MAXIMUM DRAWDOWN LIMIT HIT - TRADING STOPPED",
                f"Portfolio is down {drawdown:.2%} from peak (${self.peak_equity - current_equity:,.2f}).\n"
                f"Peak equity was: ${self.peak_equity:,.2f}\n"
                f"Current equity: ${current_equity:,.2f}\n\n"
                f"ALL TRADING HAS BEEN STOPPED.\n"
                f"Manual intervention required to restart the system.",
                "CRITICAL"
            )
            
            return False, f"Max drawdown hit: {drawdown:.2%}"
        
        # Warning at 75% of max drawdown
        if drawdown >= trading_rules.MAX_DRAWDOWN * 0.75:
            log_risk_event(
                "DRAWDOWN_WARNING",
                "WARNING",
                f"Approaching max drawdown: {drawdown:.2%}"
            )
        
        return True, ""
    
    def check_position_size(
        self,
        position_value: float,
        portfolio_value: float,
        asset_type: str
    ) -> Tuple[bool, str]:
        """
        Check if position size is within limits.
        
        Args:
            position_value: Value of the position
            portfolio_value: Total portfolio value
            asset_type: 'stock' or 'option'
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        position_pct = position_value / portfolio_value
        
        if asset_type.lower() == "stock":
            max_size = trading_rules.MAX_POSITION_SIZE_STOCK
        else:  # option
            max_size = trading_rules.MAX_POSITION_SIZE_OPTION
        
        if position_pct > max_size:
            reason = f"Position too large: {position_pct:.2%} > {max_size:.2%} limit"
            log_risk_event("POSITION_SIZE", "WARNING", reason)
            return False, reason
        
        if position_value < trading_rules.MIN_POSITION_SIZE:
            reason = f"Position too small: ${position_value:,.2f} < ${trading_rules.MIN_POSITION_SIZE:,.2f}"
            return False, reason
        
        return True, ""
    
    def check_position_count(
        self,
        current_positions: Dict[str, int]
    ) -> Tuple[bool, str]:
        """
        Check if we can add more positions.
        
        Args:
            current_positions: Dict with 'total', 'stocks', 'options' counts
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        total = current_positions.get("total", 0)
        stocks = current_positions.get("stocks", 0)
        options = current_positions.get("options", 0)
        
        if total >= trading_rules.MAX_TOTAL_POSITIONS:
            return False, f"Max positions reached: {total}/{trading_rules.MAX_TOTAL_POSITIONS}"
        
        if stocks >= trading_rules.MAX_STOCK_POSITIONS:
            return False, f"Max stock positions reached: {stocks}/{trading_rules.MAX_STOCK_POSITIONS}"
        
        if options >= trading_rules.MAX_OPTIONS_POSITIONS:
            return False, f"Max option positions reached: {options}/{trading_rules.MAX_OPTIONS_POSITIONS}"
        
        return True, ""
    
    def check_buying_power(
        self,
        required_capital: float,
        available_buying_power: float
    ) -> Tuple[bool, str]:
        """
        Check if sufficient buying power exists.
        
        Args:
            required_capital: Capital needed for trade
            available_buying_power: Available buying power
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        if required_capital > available_buying_power:
            reason = f"Insufficient buying power: ${required_capital:,.2f} needed, ${available_buying_power:,.2f} available"
            log_risk_event("BUYING_POWER", "WARNING", reason)
            return False, reason
        
        return True, ""
    
    def check_sector_exposure(
        self,
        sector: str,
        new_position_value: float,
        current_sector_exposure: Dict[str, float],
        portfolio_value: float
    ) -> Tuple[bool, str]:
        """
        Check if adding position would exceed sector limits.
        
        Args:
            sector: Sector name
            new_position_value: Value of new position
            current_sector_exposure: Dict of sector: value
            portfolio_value: Total portfolio value
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        current_exposure = current_sector_exposure.get(sector, 0)
        new_exposure = current_exposure + new_position_value
        exposure_pct = new_exposure / portfolio_value
        
        if exposure_pct > trading_rules.MAX_SECTOR_EXPOSURE:
            reason = f"Sector exposure too high: {sector} would be {exposure_pct:.2%} > {trading_rules.MAX_SECTOR_EXPOSURE:.2%}"
            log_risk_event("SECTOR_EXPOSURE", "WARNING", reason)
            return False, reason
        
        return True, ""
    
    def validate_trade(
        self,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        asset_type: str,
        account_info: Dict,
        current_positions: Dict,
        sector: Optional[str] = None,
        sector_exposure: Optional[Dict] = None
    ) -> Tuple[bool, str]:
        """
        Validate a trade against all risk rules.
        
        Args:
            symbol: Stock ticker
            action: 'buy' or 'sell'
            quantity: Number of shares/contracts
            price: Price per share/contract
            asset_type: 'stock' or 'option'
            account_info: Account information dict
            current_positions: Current position counts
            sector: Stock sector (optional)
            sector_exposure: Current sector exposure (optional)
            
        Returns:
            Tuple of (is_approved, reason_if_rejected)
        """
        portfolio_value = account_info.get("portfolio_value", 0)
        buying_power = account_info.get("buying_power", 0)
        
        # Check daily loss limit
        is_allowed, reason = self.check_daily_loss_limit(portfolio_value)
        if not is_allowed:
            return False, reason
        
        # Check max drawdown
        is_allowed, reason = self.check_max_drawdown(portfolio_value)
        if not is_allowed:
            return False, reason
        
        # For buy orders, check additional constraints
        if action.lower() == "buy":
            position_value = quantity * price
            
            # Check position size
            is_allowed, reason = self.check_position_size(
                position_value, portfolio_value, asset_type
            )
            if not is_allowed:
                return False, reason
            
            # Check buying power
            is_allowed, reason = self.check_buying_power(
                position_value, buying_power
            )
            if not is_allowed:
                return False, reason
            
            # Check position count
            is_allowed, reason = self.check_position_count(current_positions)
            if not is_allowed:
                return False, reason
            
            # Check sector exposure (if provided)
            if sector and sector_exposure is not None:
                is_allowed, reason = self.check_sector_exposure(
                    sector, position_value, sector_exposure, portfolio_value
                )
                if not is_allowed:
                    return False, reason
        
        # All checks passed
        logger.info(f"Trade validated: {action} {quantity} {symbol} @ ${price}")
        return True, ""
    
    def should_exit_position(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        position_type: str,
        stop_loss: Optional[float] = None,
        profit_target: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Check if a position should be exited based on risk rules.
        
        Args:
            symbol: Stock ticker
            entry_price: Entry price
            current_price: Current price
            position_type: 'stock' or 'option'
            stop_loss: Stop loss price (optional)
            profit_target: Profit target price (optional)
            
        Returns:
            Tuple of (should_exit, reason)
        """
        # Check stop loss
        if stop_loss and current_price <= stop_loss:
            log_risk_event(
                "STOP_LOSS",
                "WARNING",
                f"{symbol} hit stop loss: ${current_price} <= ${stop_loss}"
            )
            
            loss_pct = (entry_price - current_price) / entry_price
            notifier.send_stop_loss_alert(
                symbol, entry_price, current_price,
                entry_price - current_price, loss_pct * 100
            )
            
            return True, "Stop loss triggered"
        
        # Check profit target
        if profit_target and current_price >= profit_target:
            logger.info(f"{symbol} hit profit target: ${current_price} >= ${profit_target}")
            return True, "Profit target reached"
        
        # For options, check if approaching expiration with loss
        # (This would need expiration date to be passed in)
        
        return False, ""
    
    def get_risk_metrics(self, account_info: Dict) -> Dict:
        """
        Calculate current risk metrics.
        
        Args:
            account_info: Account information
            
        Returns:
            Dictionary of risk metrics
        """
        current_equity = account_info.get("portfolio_value", 0)
        
        # Calculate drawdown
        if self.peak_equity:
            current_drawdown = (self.peak_equity - current_equity) / self.peak_equity
        else:
            current_drawdown = 0
        
        # Calculate daily P&L
        if self.daily_start_equity:
            daily_pnl = current_equity - self.daily_start_equity
            daily_pnl_pct = daily_pnl / self.daily_start_equity
        else:
            daily_pnl = 0
            daily_pnl_pct = 0
        
        return {
            "current_equity": current_equity,
            "peak_equity": self.peak_equity or current_equity,
            "current_drawdown": current_drawdown,
            "max_drawdown_limit": trading_rules.MAX_DRAWDOWN,
            "daily_pnl": daily_pnl,
            "daily_pnl_pct": daily_pnl_pct,
            "daily_loss_limit": trading_rules.DAILY_LOSS_LIMIT,
            "circuit_breaker_triggered": self.circuit_breaker_triggered,
            "max_drawdown_triggered": self.max_drawdown_triggered,
            "risk_status": self._get_risk_status(current_drawdown, daily_pnl_pct),
        }
    
    def _get_risk_status(self, drawdown: float, daily_loss_pct: float) -> str:
        """Get overall risk status."""
        if self.max_drawdown_triggered or self.circuit_breaker_triggered:
            return "CRITICAL"
        elif drawdown > trading_rules.MAX_DRAWDOWN * 0.75:
            return "HIGH"
        elif drawdown > trading_rules.MAX_DRAWDOWN * 0.50 or abs(daily_loss_pct) > trading_rules.DAILY_LOSS_LIMIT * 0.75:
            return "MEDIUM"
        else:
            return "LOW"


# Global risk manager instance
risk_manager = RiskManager()


__all__ = ["RiskManager", "risk_manager"]
