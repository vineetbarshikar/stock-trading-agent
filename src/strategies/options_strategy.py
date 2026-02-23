"""
Options trading strategy.

Generates options signals (long calls, long puts, bull-call spreads)
based on the same stock scoring pipeline (technicals + sentiment + ML)
but uses the directional bias to choose the right options play.
"""
from typing import Dict, List, Optional
from datetime import datetime
from src.data.options_data import options_data
from src.utils.logger import logger, log_signal
from config import trading_rules


class OptionsStrategy:
    """Generates options trading signals."""

    def __init__(self):
        self.name = "options"

    def generate_options_signals(
        self,
        stock_signals: List[Dict],
        options_budget: float,
    ) -> List[Dict]:
        """
        Given scored stock signals, create matching options trades.

        Args:
            stock_signals: List of dicts from the enhanced momentum scanner.
                           Each must have: symbol, score, direction (BULLISH/BEARISH),
                           current_price.
            options_budget: Total capital available for options.

        Returns:
            List of options signal dicts ready for execution.
        """
        if not stock_signals:
            return []

        max_per_trade = options_budget * trading_rules.MAX_POSITION_SIZE_OPTION * 2
        signals: List[Dict] = []

        for sig in stock_signals:
            symbol = sig["symbol"]
            direction = sig.get("direction", "BULLISH")
            score = sig.get("score", 0)
            confidence = sig.get("confidence", "LOW")

            if score < trading_rules.MIN_ENTRY_SCORE:
                continue

            try:
                opt_signal = None

                if direction == "BULLISH":
                    if confidence == "HIGH" and score >= trading_rules.HIGH_CONFIDENCE_THRESHOLD:
                        # High conviction: long call
                        opt_signal = self._long_call_signal(symbol, score, max_per_trade)
                    else:
                        # Moderate conviction: bull call spread (defined risk)
                        opt_signal = self._spread_signal(symbol, score, max_per_trade)
                        if opt_signal is None:
                            opt_signal = self._long_call_signal(symbol, score, max_per_trade)

                elif direction == "BEARISH":
                    opt_signal = self._long_put_signal(symbol, score, max_per_trade)

                if opt_signal:
                    signals.append(opt_signal)
                    log_signal(
                        self.name,
                        symbol,
                        opt_signal["signal_type"],
                        score,
                        option_type=opt_signal.get("option_type"),
                    )

            except Exception as e:
                logger.error(f"Error generating options signal for {symbol}: {e}")
                continue

        signals.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"Options strategy generated {len(signals)} signals")
        return signals

    # ------------------------------------------------------------------
    # Signal builders
    # ------------------------------------------------------------------

    def _long_call_signal(self, symbol: str, score: float, budget: float) -> Optional[Dict]:
        """Build a long-call signal."""
        pick = options_data.find_best_call(symbol, max_budget=budget)
        if pick is None:
            return None

        return {
            "symbol": symbol,
            "signal_type": "BUY_CALL",
            "asset_type": "OPTION",
            "strategy": f"{self.name}_long_call",
            "score": score,
            "confidence": self._confidence(score),
            "option_type": "CALL",
            "strike": pick["strike"],
            "expiration": pick["expiration"],
            "dte": pick["dte"],
            "premium": pick["premium"],
            "cost_per_contract": pick["cost_per_contract"],
            "suggested_qty": pick["suggested_qty"],
            "total_cost": pick["total_cost"],
            "underlying_price": pick["underlying_price"],
            "implied_volatility": pick.get("implied_volatility", 0),
            "reasoning": f"Long call | Strike {pick['strike']} | {pick['dte']}DTE | IV {pick.get('implied_volatility',0):.1f}%",
            "timestamp": datetime.now(),
        }

    def _long_put_signal(self, symbol: str, score: float, budget: float) -> Optional[Dict]:
        """Build a long-put signal."""
        pick = options_data.find_best_put(symbol, max_budget=budget)
        if pick is None:
            return None

        return {
            "symbol": symbol,
            "signal_type": "BUY_PUT",
            "asset_type": "OPTION",
            "strategy": f"{self.name}_long_put",
            "score": score,
            "confidence": self._confidence(score),
            "option_type": "PUT",
            "strike": pick["strike"],
            "expiration": pick["expiration"],
            "dte": pick["dte"],
            "premium": pick["premium"],
            "cost_per_contract": pick["cost_per_contract"],
            "suggested_qty": pick["suggested_qty"],
            "total_cost": pick["total_cost"],
            "underlying_price": pick["underlying_price"],
            "implied_volatility": pick.get("implied_volatility", 0),
            "reasoning": f"Long put | Strike {pick['strike']} | {pick['dte']}DTE | IV {pick.get('implied_volatility',0):.1f}%",
            "timestamp": datetime.now(),
        }

    def _spread_signal(self, symbol: str, score: float, budget: float) -> Optional[Dict]:
        """Build a bull-call-spread signal."""
        pick = options_data.find_bull_call_spread(symbol, max_budget=budget)
        if pick is None:
            return None

        return {
            "symbol": symbol,
            "signal_type": "BUY_SPREAD",
            "asset_type": "OPTION",
            "strategy": f"{self.name}_bull_spread",
            "score": score,
            "confidence": self._confidence(score),
            "option_type": "SPREAD",
            "strike": pick["long_strike"],
            "short_strike": pick["short_strike"],
            "expiration": pick["expiration"],
            "dte": pick["dte"],
            "premium": pick["net_debit"],
            "cost_per_contract": pick["cost_per_contract"],
            "suggested_qty": pick["suggested_qty"],
            "total_cost": pick["total_cost"],
            "max_profit": pick["max_profit"],
            "max_loss": pick["max_loss"],
            "risk_reward": pick["risk_reward"],
            "underlying_price": pick["underlying_price"],
            "reasoning": (
                f"Bull call spread | {pick['long_strike']}/{pick['short_strike']} "
                f"| R:R {pick['risk_reward']:.1f} | {pick['dte']}DTE"
            ),
            "timestamp": datetime.now(),
        }

    @staticmethod
    def _confidence(score: float) -> str:
        if score >= trading_rules.HIGH_CONFIDENCE_THRESHOLD:
            return "HIGH"
        if score >= trading_rules.MEDIUM_CONFIDENCE_THRESHOLD:
            return "MEDIUM"
        return "LOW"


# Global instance
options_strategy = OptionsStrategy()

__all__ = ["OptionsStrategy", "options_strategy"]
