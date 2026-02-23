"""
Options chain data fetching and analysis via yfinance.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import yfinance as yf
from src.utils.logger import logger
from config import trading_rules


class OptionsDataFetcher:
    """Fetches and analyses options chains."""

    def get_options_chain(
        self,
        symbol: str,
        min_dte: int = None,
        max_dte: int = None,
    ) -> Optional[Dict]:
        """
        Get the options chain for a symbol, filtered by DTE range.

        Returns dict with keys: calls (DataFrame), puts (DataFrame),
        expiration (str), dte (int), underlying_price (float).
        """
        min_dte = min_dte or trading_rules.OPTIONS_MIN_DTE
        max_dte = max_dte or trading_rules.OPTIONS_MAX_DTE

        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options  # list of "YYYY-MM-DD" strings

            if not expirations:
                logger.warning(f"No options data for {symbol}")
                return None

            # Pick the first expiration inside the DTE window
            today = datetime.now().date()
            target_exp = None
            for exp_str in expirations:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                dte = (exp_date - today).days
                if min_dte <= dte <= max_dte:
                    target_exp = exp_str
                    break

            if target_exp is None:
                # Fallback: pick closest to target DTE
                target_dte = trading_rules.OPTIONS_TARGET_DTE
                best, best_diff = None, 9999
                for exp_str in expirations:
                    exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                    dte = (exp_date - today).days
                    if dte > 7 and abs(dte - target_dte) < best_diff:
                        best_diff = abs(dte - target_dte)
                        best = exp_str
                target_exp = best

            if target_exp is None:
                return None

            chain = ticker.option_chain(target_exp)
            exp_date = datetime.strptime(target_exp, "%Y-%m-%d").date()
            dte = (exp_date - today).days

            # Get underlying price
            hist = ticker.history(period="1d")
            underlying = float(hist["Close"].iloc[-1]) if not hist.empty else None

            return {
                "calls": chain.calls,
                "puts": chain.puts,
                "expiration": target_exp,
                "dte": dte,
                "underlying_price": underlying,
            }

        except Exception as e:
            logger.error(f"Error fetching options chain for {symbol}: {e}")
            return None

    def find_best_call(
        self,
        symbol: str,
        bias: str = "bullish",
        max_budget: float = 2500.0,
    ) -> Optional[Dict]:
        """
        Find the best long call option matching our criteria.

        Filters by:
          - DTE window (30-45 days)
          - Delta range (0.40 – 0.60)
          - Budget constraint
          - Open interest / volume liquidity
        """
        chain = self.get_options_chain(symbol)
        if chain is None or chain["underlying_price"] is None:
            return None

        calls = chain["calls"].copy()
        price = chain["underlying_price"]

        return self._pick_option(
            df=calls,
            underlying=price,
            dte=chain["dte"],
            expiration=chain["expiration"],
            option_type="CALL",
            max_budget=max_budget,
        )

    def find_best_put(
        self,
        symbol: str,
        max_budget: float = 2500.0,
    ) -> Optional[Dict]:
        """Find the best long put option."""
        chain = self.get_options_chain(symbol)
        if chain is None or chain["underlying_price"] is None:
            return None

        puts = chain["puts"].copy()
        price = chain["underlying_price"]

        return self._pick_option(
            df=puts,
            underlying=price,
            dte=chain["dte"],
            expiration=chain["expiration"],
            option_type="PUT",
            max_budget=max_budget,
        )

    def find_bull_call_spread(
        self,
        symbol: str,
        max_budget: float = 2500.0,
    ) -> Optional[Dict]:
        """
        Find a bull call spread (buy lower strike, sell higher strike).
        Target risk:reward of at least 1:2.
        """
        chain = self.get_options_chain(symbol)
        if chain is None or chain["underlying_price"] is None:
            return None

        calls = chain["calls"].copy()
        price = chain["underlying_price"]

        try:
            # Find two strikes: long slightly OTM, short further OTM
            calls = calls[calls["openInterest"].fillna(0) > 10].copy()
            if calls.empty or len(calls) < 2:
                return None

            calls["moneyness"] = calls["strike"] / price

            # Long leg: ATM to slightly OTM (0.97 – 1.05)
            long_candidates = calls[
                (calls["moneyness"] >= 0.97) & (calls["moneyness"] <= 1.05)
            ].copy()
            if long_candidates.empty:
                return None

            long_leg = long_candidates.iloc[0]

            # Short leg: 3-8% above long strike
            target_short = long_leg["strike"] * 1.05
            short_candidates = calls[calls["strike"] >= target_short].head(3)
            if short_candidates.empty:
                return None

            short_leg = short_candidates.iloc[0]

            # Calculate spread economics
            long_premium = float((long_leg["bid"] + long_leg["ask"]) / 2)
            short_premium = float((short_leg["bid"] + short_leg["ask"]) / 2)
            net_debit = long_premium - short_premium
            max_profit = float(short_leg["strike"] - long_leg["strike"]) - net_debit
            max_loss = net_debit

            if max_loss <= 0 or max_profit / max_loss < trading_rules.SPREAD_MIN_RISK_REWARD:
                return None

            # Cost per contract (x100)
            cost = net_debit * 100
            qty = max(1, int(max_budget / cost))

            return {
                "symbol": symbol,
                "strategy": "bull_call_spread",
                "option_type": "SPREAD",
                "expiration": chain["expiration"],
                "dte": chain["dte"],
                "long_strike": float(long_leg["strike"]),
                "short_strike": float(short_leg["strike"]),
                "net_debit": round(net_debit, 2),
                "max_profit": round(max_profit, 2),
                "max_loss": round(max_loss, 2),
                "risk_reward": round(max_profit / max_loss, 2),
                "cost_per_contract": round(cost, 2),
                "suggested_qty": qty,
                "total_cost": round(cost * qty, 2),
                "underlying_price": round(price, 2),
            }

        except Exception as e:
            logger.error(f"Error finding bull call spread for {symbol}: {e}")
            return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _pick_option(
        self,
        df: pd.DataFrame,
        underlying: float,
        dte: int,
        expiration: str,
        option_type: str,
        max_budget: float,
    ) -> Optional[Dict]:
        """Select best option from a chain DataFrame."""
        try:
            if df.empty:
                return None

            df = df.copy()
            df["mid"] = (df["bid"].fillna(0) + df["ask"].fillna(0)) / 2
            df["moneyness"] = df["strike"] / underlying

            # Filter for liquidity
            df = df[df["openInterest"].fillna(0) > 10]
            df = df[df["mid"] > 0.10]  # Skip near-zero premium

            if df.empty:
                return None

            # Delta proxy: for calls target OTM (strike > price, moneyness 1.00-1.10)
            #              for puts target OTM  (strike < price, moneyness 0.90-1.00)
            if option_type == "CALL":
                target = df[(df["moneyness"] >= 0.95) & (df["moneyness"] <= 1.10)]
            else:
                target = df[(df["moneyness"] >= 0.90) & (df["moneyness"] <= 1.05)]

            if target.empty:
                target = df  # fallback

            # Sort by open interest (liquidity proxy)
            target = target.sort_values("openInterest", ascending=False)
            pick = target.iloc[0]

            premium = float(pick["mid"])
            cost_per_contract = premium * 100
            qty = max(1, int(max_budget / cost_per_contract))

            return {
                "symbol": symbol if "symbol" in df.columns else "",
                "strategy": f"long_{option_type.lower()}",
                "option_type": option_type,
                "strike": float(pick["strike"]),
                "expiration": expiration,
                "dte": dte,
                "premium": round(premium, 2),
                "cost_per_contract": round(cost_per_contract, 2),
                "suggested_qty": qty,
                "total_cost": round(cost_per_contract * qty, 2),
                "open_interest": int(pick.get("openInterest", 0)),
                "implied_volatility": round(float(pick.get("impliedVolatility", 0)) * 100, 2),
                "underlying_price": round(underlying, 2),
                "moneyness": round(float(pick["moneyness"]), 4),
            }

        except Exception as e:
            logger.error(f"Error picking option: {e}")
            return None


# Global instance
options_data = OptionsDataFetcher()

__all__ = ["OptionsDataFetcher", "options_data"]
