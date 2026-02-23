"""
Notification system for email and SMS alerts.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional
from config.settings import settings
from src.utils.logger import logger


class NotificationManager:
    """Manages email and SMS notifications."""
    
    def __init__(self):
        self.email_address = settings.email_address
        self.email_password = settings.email_password
        self.smtp_server = settings.email_smtp_server
        self.smtp_port = settings.email_smtp_port
        
    def send_email(
        self,
        subject: str,
        body: str,
        recipient: Optional[str] = None,
        html: bool = False
    ) -> bool:
        """
        Send an email notification.
        
        Args:
            subject: Email subject
            body: Email body content
            recipient: Email recipient (defaults to settings.email_address)
            html: Whether body is HTML content
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not self.email_password:
                logger.warning("Email password not configured, skipping email notification")
                return False
                
            recipient = recipient or self.email_address
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_address
            msg['To'] = recipient
            
            # Add body
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
                
            logger.info(f"Email sent: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_trade_alert(
        self,
        action: str,
        symbol: str,
        quantity: float,
        price: float,
        position_value: float,
        **kwargs
    ):
        """Send alert for a new trade."""
        subject = f"🔔 Trade Alert: {action} {symbol}"
        
        body = f"""
Trading Alert
=============
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}

Action: {action}
Symbol: {symbol}
Quantity: {quantity}
Price: ${price:.2f}
Position Value: ${position_value:,.2f}

{self._format_kwargs(kwargs)}

---
Automated Trading Agent
"""
        
        self.send_email(subject, body)
    
    def send_stop_loss_alert(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        loss: float,
        loss_pct: float
    ):
        """Send alert when stop loss is triggered."""
        subject = f"🚨 Stop Loss Triggered: {symbol}"
        
        body = f"""
Stop Loss Alert
===============
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}

Symbol: {symbol}
Entry Price: ${entry_price:.2f}
Exit Price: ${exit_price:.2f}
Loss: ${loss:,.2f} ({loss_pct:.2f}%)

This position has been closed automatically.

---
Automated Trading Agent
"""
        
        self.send_email(subject, body)
    
    def send_daily_report(self, report_data: dict):
        """Send end-of-day performance report."""
        subject = f"📊 Daily Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        body = f"""
Daily Trading Report
====================
Date: {datetime.now().strftime('%Y-%m-%d')}

PORTFOLIO SUMMARY
-----------------
Portfolio Value: ${report_data.get('portfolio_value', 0):,.2f}
Today's P&L: ${report_data.get('daily_pnl', 0):,.2f} ({report_data.get('daily_pnl_pct', 0):.2f}%)
Total Return: ${report_data.get('total_return', 0):,.2f} ({report_data.get('total_return_pct', 0):.2f}%)

SPY Performance: {report_data.get('spy_return', 0):.2f}%
Alpha: {report_data.get('alpha', 0):.2f}%

TRADES TODAY
------------
Total Trades: {report_data.get('trades_count', 0)}
Winners: {report_data.get('winners', 0)}
Losers: {report_data.get('losers', 0)}
Win Rate: {report_data.get('win_rate', 0):.1f}%

CURRENT POSITIONS
-----------------
Total Positions: {report_data.get('positions_count', 0)}
Stocks: {report_data.get('stock_positions', 0)}
Options: {report_data.get('option_positions', 0)}

RISK METRICS
------------
Max Drawdown: {report_data.get('max_drawdown', 0):.2f}%
Current Drawdown: {report_data.get('current_drawdown', 0):.2f}%
Portfolio Heat: {report_data.get('portfolio_heat', 0):.2f}%
Buying Power: ${report_data.get('buying_power', 0):,.2f}

TOP PERFORMERS TODAY
--------------------
{self._format_top_performers(report_data.get('top_performers', []))}

UPCOMING ACTIONS
----------------
{self._format_upcoming_actions(report_data.get('upcoming_actions', []))}

---
Automated Trading Agent
"""
        
        self.send_email(subject, body)
    
    def send_risk_alert(self, alert_type: str, message: str, severity: str = "WARNING"):
        """Send risk management alert."""
        emoji = "🚨" if severity == "CRITICAL" else "⚠️"
        subject = f"{emoji} Risk Alert: {alert_type}"
        
        body = f"""
Risk Management Alert
=====================
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}
Severity: {severity}

Alert Type: {alert_type}

{message}

Please review your trading dashboard for details.

---
Automated Trading Agent
"""
        
        self.send_email(subject, body)
    
    def send_system_error(self, error_type: str, error_message: str, stack_trace: Optional[str] = None):
        """Send system error notification."""
        subject = f"❌ System Error: {error_type}"
        stack_section = f"Stack Trace:\n{stack_trace}" if stack_trace else ""

        body = f"""
System Error Alert
==================
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}

Error Type: {error_type}
Error Message: {error_message}

{stack_section}

The system may require attention.

---
Automated Trading Agent
"""
        
        self.send_email(subject, body)
    
    def _format_kwargs(self, kwargs: dict) -> str:
        """Format additional kwargs for display."""
        if not kwargs:
            return ""
        return "\n".join([f"{k}: {v}" for k, v in kwargs.items()])
    
    def _format_top_performers(self, performers: List[dict]) -> str:
        """Format top performers list."""
        if not performers:
            return "No positions with significant moves today"
        
        lines = []
        for p in performers[:5]:  # Top 5
            lines.append(
                f"  {p['symbol']}: ${p['value']:,.2f} "
                f"({'+' if p['pnl_pct'] > 0 else ''}{p['pnl_pct']:.2f}%)"
            )
        return "\n".join(lines)
    
    def _format_upcoming_actions(self, actions: List[str]) -> str:
        """Format upcoming actions list."""
        if not actions:
            return "No pending actions"
        return "\n".join([f"  - {action}" for action in actions])


# Global notification manager instance
notifier = NotificationManager()


__all__ = ["NotificationManager", "notifier"]
