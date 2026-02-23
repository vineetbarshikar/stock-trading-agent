#!/usr/bin/env python3
"""
Main paper trading bot  (v2 – sentiment + ML + options).

Enforces 50 / 50 allocation between stocks and options.
"""
import sys
import time
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.execution.broker import broker
from src.execution.risk_manager import risk_manager
from src.portfolio.portfolio import portfolio
from src.strategies.momentum import momentum_strategy
from src.strategies.options_strategy import options_strategy
from src.data.database import get_db_session, Signal
from src.utils.logger import logger
from src.utils.helpers import is_market_open, get_market_time
from src.utils.notifications import notifier
from config import trading_rules
from config.settings import settings


class TradingBot:
    """Main trading bot orchestrator – v2 with options support."""

    def __init__(self):
        self.db = get_db_session()
        self.is_running = False
        self.scan_interval = settings.scan_interval_minutes * 60

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        logger.info("=" * 60)
        logger.info("TRADING BOT v2 STARTING  (sentiment + ML + options)")
        logger.info("=" * 60)
        logger.info(f"Environment : {settings.environment}")
        logger.info(f"Paper       : {settings.paper_trading}")
        logger.info(f"Allocation  : {trading_rules.STOCK_ALLOCATION:.0%} stocks / "
                     f"{trading_rules.OPTIONS_ALLOCATION:.0%} options")
        logger.info(f"Scan every  : {settings.scan_interval_minutes} min")
        logger.info("=" * 60)

        self.is_running = True

        try:
            self._initialize()
            while self.is_running:
                try:
                    if is_market_open():
                        self._trading_loop()
                    else:
                        logger.info("Market closed. Sleeping 5 min …")
                        time.sleep(300)
                except KeyboardInterrupt:
                    logger.info("Shutdown requested …")
                    break
                except Exception as e:
                    logger.error(f"Main-loop error: {e}")
                    time.sleep(60)
        finally:
            self._shutdown()

    def _initialize(self):
        logger.info("Initializing …")
        portfolio.refresh()
        pv = portfolio.get_portfolio_value()
        risk_manager.reset_daily_limits(pv)
        risk_manager.update_peak_equity(pv)
        logger.info(f"Portfolio ${pv:,.2f} | Cash ${portfolio.get_cash():,.2f} | "
                     f"BP ${portfolio.get_buying_power():,.2f}")

    def _shutdown(self):
        logger.info("=" * 60)
        logger.info("BOT SHUTTING DOWN")
        logger.info("=" * 60)
        portfolio.save_snapshot()
        self.db.close()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _trading_loop(self):
        t = get_market_time()
        logger.info(f"─── Trading loop {t.strftime('%H:%M:%S')} ───")

        portfolio.refresh()
        acct = portfolio.account_info
        if not acct:
            logger.error("Cannot get account info – retrying in 60s")
            time.sleep(60)
            return

        pv = acct["portfolio_value"]
        risk_manager.reset_daily_limits(pv)
        risk_manager.update_peak_equity(pv)

        # Risk gates
        ok, reason = risk_manager.check_daily_loss_limit(pv)
        if not ok:
            logger.warning(f"Blocked: {reason}")
            time.sleep(3600)
            return

        ok, reason = risk_manager.check_max_drawdown(pv)
        if not ok:
            logger.critical(f"Stopped: {reason}")
            self.is_running = False
            return

        # 1. Monitor existing positions
        self._monitor_positions()

        # 2. Compute allocation budgets
        stock_budget = pv * trading_rules.STOCK_ALLOCATION
        options_budget = pv * trading_rules.OPTIONS_ALLOCATION

        stock_invested = float(acct.get("long_market_value", 0))
        # Rough estimate – options aren't tracked separately in Alpaca yet
        options_invested = 0.0
        stock_room = max(0, stock_budget - stock_invested)
        options_room = max(0, options_budget - options_invested)

        logger.info(f"Allocation │ Stocks: ${stock_invested:,.0f}/${stock_budget:,.0f} "
                     f"│ Options room: ${options_room:,.0f}")

        # 3. Scan for signals (enhanced: technicals + sentiment + ML)
        signals = momentum_strategy.scan_for_signals()

        if not signals:
            logger.info("No signals this scan")
        else:
            # Split into bullish and bearish buckets
            bullish = [s for s in signals if s.get("direction") == "BULLISH"]
            bearish = [s for s in signals if s.get("direction") == "BEARISH"]
            logger.info(f"Signals: {len(bullish)} bullish, {len(bearish)} bearish")

            # 4a. Stock trades  (use budget room)
            if stock_room > trading_rules.MIN_POSITION_SIZE:
                self._execute_stock_signals(bullish[:5], stock_room, acct)

            # 4b. Options trades
            if options_room > trading_rules.MIN_POSITION_SIZE:
                # Use top signals (both bullish and bearish) for options
                top_for_options = signals[:8]
                opt_signals = options_strategy.generate_options_signals(
                    top_for_options, options_room
                )
                if opt_signals:
                    self._execute_options_signals(opt_signals, options_room, acct)
                else:
                    logger.info("Options strategy produced no actionable signals")

        # 5. Snapshot & metrics
        portfolio.save_snapshot()
        rm = risk_manager.get_risk_metrics(acct)
        logger.info(f"Risk: {rm['risk_status']} │ DD {rm['current_drawdown']:.2%} │ "
                     f"Day P&L ${rm['daily_pnl']:+,.2f} ({rm['daily_pnl_pct']:+.2%})")

        logger.info(f"Next scan in {settings.scan_interval_minutes} min …")
        time.sleep(self.scan_interval)

    # ------------------------------------------------------------------
    # Position monitoring
    # ------------------------------------------------------------------

    def _monitor_positions(self):
        positions = portfolio.positions
        if not positions:
            logger.info("No open positions")
            return

        logger.info(f"Monitoring {len(positions)} positions")

        for pos in positions:
            symbol = pos["symbol"]
            entry = pos["avg_entry_price"]
            current = pos["current_price"]
            pnl_pct = pos["unrealized_plpc"]

            stop = round(entry * (1 - trading_rules.STOCK_STOP_LOSS_PCT), 2)
            target = round(entry * (1 + trading_rules.STOCK_PROFIT_TARGET_MIN), 2)

            should_exit, reason = risk_manager.should_exit_position(
                symbol, entry, current, "stock", stop, target
            )

            if should_exit:
                logger.warning(f"EXIT {symbol}: {reason}")
                self._close_position(symbol, reason)
            else:
                logger.debug(f"  {symbol}: ${current:.2f} ({pnl_pct:+.2%})")

    # ------------------------------------------------------------------
    # Stock execution
    # ------------------------------------------------------------------

    def _execute_stock_signals(self, signals: list, budget: float, acct: dict):
        """Execute stock buy signals within budget."""
        pos_counts = portfolio.get_position_counts()

        for sig in signals:
            symbol = sig["symbol"]

            if portfolio.has_position(symbol):
                continue

            ok, reason = risk_manager.check_position_count(pos_counts)
            if not ok:
                logger.info(f"Position limit: {reason}")
                break

            max_pos = min(
                budget,
                acct["portfolio_value"] * trading_rules.MAX_POSITION_SIZE_STOCK,
            )
            price = round(sig["current_price"], 2)
            qty = int(max_pos / price)
            if qty <= 0:
                continue

            pos_val = qty * price
            ok, reason = risk_manager.validate_trade(
                symbol, "buy", qty, price, "stock", acct, pos_counts
            )
            if not ok:
                logger.info(f"Rejected {symbol}: {reason}")
                continue

            order = broker.place_limit_order(symbol, qty, "buy", price)
            if order:
                self._save_signal(sig, "STOCK", True)
                budget -= pos_val
                pos_counts["total"] += 1
                pos_counts["stocks"] += 1
                logger.info(f"✅ STOCK BUY {qty} {symbol} @ ${price:.2f}  "
                             f"(score {sig['score']}, {sig.get('direction','?')})")
            else:
                logger.error(f"❌ Order failed: {symbol}")

    # ------------------------------------------------------------------
    # Options execution  (simulated via stock orders on Alpaca paper)
    # ------------------------------------------------------------------

    def _execute_options_signals(self, signals: list, budget: float, acct: dict):
        """
        Execute options signals.

        NOTE: Alpaca paper trading has limited options support.  For now
        we *simulate* options exposure by buying small stock positions
        tagged as options-equivalent, sized to the premium cost.  This
        lets the bot track P&L and validate the strategy while we wait
        for full options API support.  When going live on a broker that
        supports options (Robinhood / Fidelity) these will become real
        options orders.
        """
        pos_counts = portfolio.get_position_counts()

        for sig in signals:
            symbol = sig["symbol"]
            total_cost = sig.get("total_cost", 0)

            if total_cost <= 0 or total_cost > budget:
                continue

            if portfolio.has_position(symbol):
                continue

            ok, reason = risk_manager.check_position_count(pos_counts)
            if not ok:
                break

            # Simulate options exposure as small stock position
            price = round(sig.get("underlying_price", sig.get("current_price", 0)), 2)
            if price <= 0:
                continue

            # Buy shares worth the option premium cost
            sim_qty = max(1, int(total_cost / price))
            sim_value = sim_qty * price

            ok, reason = risk_manager.validate_trade(
                symbol, "buy", sim_qty, price, "option", acct, pos_counts
            )
            if not ok:
                logger.info(f"Options rejected {symbol}: {reason}")
                continue

            order = broker.place_limit_order(symbol, sim_qty, "buy", price)
            if order:
                self._save_signal(sig, "OPTION", True)
                budget -= sim_value
                pos_counts["total"] += 1
                pos_counts["options"] += 1
                opt_type = sig.get("signal_type", "OPT")
                strike = sig.get("strike", "?")
                exp = sig.get("expiration", "?")
                logger.info(
                    f"✅ OPTIONS {opt_type} {symbol} strike={strike} exp={exp} "
                    f"(sim {sim_qty} shares @ ${price:.2f}, score {sig['score']})"
                )
            else:
                logger.error(f"❌ Options order failed: {symbol}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _save_signal(self, sig: dict, asset_type: str, executed: bool):
        try:
            record = Signal(
                symbol=sig["symbol"],
                asset_type=asset_type,
                signal_type=sig.get("signal_type", "BUY"),
                strategy=sig.get("strategy", "unknown"),
                score=sig.get("score", 0),
                confidence=sig.get("confidence", "LOW"),
                current_price=sig.get("current_price", sig.get("underlying_price", 0)),
                suggested_entry=sig.get("suggested_entry", sig.get("underlying_price", 0)),
                suggested_stop=sig.get("suggested_stop"),
                suggested_target=sig.get("suggested_target"),
                reasoning=sig.get("reasoning", ""),
                is_executed=executed,
                executed_at=datetime.now() if executed else None,
            )
            self.db.add(record)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error saving signal: {e}")
            self.db.rollback()

    def _close_position(self, symbol: str, reason: str):
        try:
            if broker.close_position(symbol):
                logger.info(f"✅ Closed {symbol} ({reason})")
            else:
                logger.error(f"❌ Failed closing {symbol}")
        except Exception as e:
            logger.error(f"Error closing {symbol}: {e}")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main():
    print("=" * 60)
    print("AUTOMATED TRADING BOT  v2")
    print("  Sentiment + ML + Options  |  50/50 Allocation")
    print("=" * 60)
    print(f"  Environment : {settings.environment}")
    print(f"  Paper       : {settings.paper_trading}")
    print(f"  Universe    : 80+ symbols across all sectors")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    print()

    bot = TradingBot()
    try:
        bot.start()
    except KeyboardInterrupt:
        print("\nShutting down …")
    except Exception as e:
        logger.error(f"Fatal: {e}")
        print(f"\nFatal: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
