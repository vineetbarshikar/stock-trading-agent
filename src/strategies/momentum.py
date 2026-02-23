"""
Enhanced momentum strategy incorporating:
  1. Technical analysis (original)
  2. Market sentiment (VIX, SPY trend, news headlines)
  3. ML predictions (gradient boosting directional model)
  4. Market regime detection (bull / bear / neutral)
  5. Bearish signal generation (not just buys)
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
from src.data.market_data import market_data
from src.data.sentiment import sentiment_analyzer
from src.ml.predictor import ml_predictor
from src.utils.logger import logger, log_signal
from config import trading_rules


# ---------------------------------------------------------------------------
# Expanded universe  (80+ liquid large/mid-cap names across sectors)
# ---------------------------------------------------------------------------
DEFAULT_UNIVERSE = [
    # Tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD",
    "CRM", "ADBE", "NFLX", "INTC", "QCOM", "AVGO", "ORCL", "NOW",
    "UBER", "SHOP", "SNOW", "SQ", "PLTR", "PANW", "CRWD", "MRVL",
    # Finance
    "JPM", "GS", "MS", "BAC", "WFC", "BLK", "SCHW", "AXP", "V", "MA",
    # Healthcare
    "UNH", "JNJ", "LLY", "PFE", "ABBV", "MRK", "TMO", "ABT", "AMGN", "GILD",
    # Consumer
    "HD", "MCD", "NKE", "SBUX", "TGT", "COST", "WMT", "LOW", "TJX",
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "OXY",
    # Industrials
    "CAT", "DE", "GE", "BA", "UNP", "RTX", "HON", "LMT",
    # Communication
    "DIS", "CMCSA", "T", "VZ", "TMUS",
    # Materials / Other
    "FCX", "NEM", "LIN", "APD",
    # ETFs (used for hedging signals / sentiment only)
    "SPY", "QQQ",
]


class MomentumStrategy:
    """Enhanced momentum strategy with sentiment + ML."""

    def __init__(self):
        self.name = "momentum_v2"
        self.lookback_days = trading_rules.MOMENTUM_LOOKBACK_DAYS
        self._market_sentiment: Optional[Dict] = None
        self._market_sentiment_ts: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan_for_signals(self, universe: Optional[List[str]] = None) -> List[Dict]:
        """
        Scan universe for trading signals (both BULLISH and BEARISH).

        Each signal dict contains:
            symbol, signal_type (BUY/SELL), direction (BULLISH/BEARISH),
            score (0-100), confidence, current_price, suggested_entry/stop/target,
            reasoning, sentiment_score, ml_probability, market_regime.
        """
        if universe is None:
            universe = [s for s in DEFAULT_UNIVERSE if s not in ("SPY", "QQQ")]

        # Refresh market-level sentiment once per scan (cached 5 min)
        self._refresh_market_sentiment()
        regime = self._market_sentiment.get("regime", "NEUTRAL") if self._market_sentiment else "NEUTRAL"
        logger.info(f"Market regime: {regime} | VIX: {self._market_sentiment.get('vix', '?')}")

        signals: List[Dict] = []

        for symbol in universe:
            try:
                signal = self._analyze_symbol(symbol, regime)
                if signal and signal["score"] >= trading_rules.MIN_ENTRY_SCORE:
                    signals.append(signal)
                    log_signal(self.name, symbol, signal["signal_type"], signal["score"])
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")

        signals.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"Enhanced scan found {len(signals)} signals (regime={regime})")
        return signals

    # ------------------------------------------------------------------
    # Per-symbol analysis
    # ------------------------------------------------------------------

    def _analyze_symbol(self, symbol: str, regime: str) -> Optional[Dict]:
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days + 60)
            df = market_data.get_historical_data(symbol, start_date, end_date)

            if df is None or len(df) < 50:
                return None

            df = market_data.calculate_technical_indicators(df)
            if df.empty or len(df) < 50:
                return None

            latest = df.iloc[-1]
            price = latest["close"]

            # ---- 1. Technical score (0–40) ----
            tech_score, tech_direction, tech_reasons = self._technical_score(df, latest, price)

            # ---- 2. Sentiment score (0–25) ----
            sent_score, sent_direction, sent_reasons, raw_sentiment = self._sentiment_score(symbol)

            # ---- 3. ML score (0–25) ----
            ml_score, ml_direction, ml_reasons, ml_prob = self._ml_score(symbol)

            # ---- 4. Market-regime adjustment (−10 to +10) ----
            regime_adj, regime_reasons = self._regime_adjustment(regime, tech_direction)

            # ---- Composite ----
            raw_score = tech_score + sent_score + ml_score + regime_adj
            score = max(0, min(100, raw_score))

            # Determine overall direction from majority vote
            directions = [tech_direction, sent_direction, ml_direction]
            bull_votes = directions.count("BULLISH")
            bear_votes = directions.count("BEARISH")

            if bull_votes > bear_votes:
                direction = "BULLISH"
                signal_type = "BUY"
            elif bear_votes > bull_votes:
                direction = "BEARISH"
                signal_type = "SELL"
            else:
                direction = "BULLISH" if regime == "BULL" else "BEARISH" if regime == "BEAR" else "BULLISH"
                signal_type = "BUY" if direction == "BULLISH" else "SELL"

            if score < trading_rules.MIN_ENTRY_SCORE:
                return None

            # Stop / target based on direction
            if direction == "BULLISH":
                stop_loss = round(price * (1 - trading_rules.STOCK_STOP_LOSS_PCT), 2)
                profit_target = round(price * (1 + trading_rules.STOCK_PROFIT_TARGET_MIN), 2)
            else:
                stop_loss = round(price * (1 + trading_rules.STOCK_STOP_LOSS_PCT), 2)
                profit_target = round(price * (1 - trading_rules.STOCK_PROFIT_TARGET_MIN), 2)

            confidence = (
                "HIGH" if score >= trading_rules.HIGH_CONFIDENCE_THRESHOLD
                else "MEDIUM" if score >= trading_rules.MEDIUM_CONFIDENCE_THRESHOLD
                else "LOW"
            )

            all_reasons = tech_reasons + sent_reasons + ml_reasons + regime_reasons

            return {
                "symbol": symbol,
                "signal_type": signal_type,
                "direction": direction,
                "strategy": self.name,
                "score": score,
                "confidence": confidence,
                "current_price": round(price, 2),
                "suggested_entry": round(price, 2),
                "suggested_stop": stop_loss,
                "suggested_target": profit_target,
                "reasoning": " | ".join(all_reasons),
                "sentiment_score": raw_sentiment,
                "ml_probability": ml_prob,
                "market_regime": regime,
                "timestamp": datetime.now(),
            }

        except Exception as e:
            logger.error(f"Error in enhanced analysis for {symbol}: {e}")
            return None

    # ------------------------------------------------------------------
    # Component scorers
    # ------------------------------------------------------------------

    def _technical_score(self, df, latest, price) -> tuple:
        """Technical indicators → score (0-40), direction, reasons."""
        score = 0
        reasons = []
        bull_pts, bear_pts = 0, 0

        # SMA position (10 pts)
        if pd.notna(latest.get("sma_50")) and pd.notna(latest.get("sma_200")):
            if price > latest["sma_50"] > latest["sma_200"]:
                score += 10; bull_pts += 1
                reasons.append("Above 50 & 200 SMA (bullish)")
            elif price < latest["sma_50"] < latest["sma_200"]:
                score += 8; bear_pts += 1
                reasons.append("Below 50 & 200 SMA (bearish)")
            elif price > latest["sma_50"]:
                score += 5; bull_pts += 1
                reasons.append("Above 50 SMA")

        # RSI (10 pts)
        if pd.notna(latest.get("rsi")):
            rsi = latest["rsi"]
            if 50 < rsi < 70:
                score += 10; bull_pts += 1
                reasons.append(f"RSI {rsi:.0f} momentum zone")
            elif rsi <= 30:
                score += 8; bull_pts += 1
                reasons.append(f"RSI {rsi:.0f} oversold → reversal")
            elif rsi >= 75:
                score += 6; bear_pts += 1
                reasons.append(f"RSI {rsi:.0f} overbought")
            elif 30 < rsi <= 50:
                score += 4; bear_pts += 1
                reasons.append(f"RSI {rsi:.0f} weak")

        # MACD (10 pts)
        if pd.notna(latest.get("macd")) and pd.notna(latest.get("macd_signal")):
            macd_diff = latest["macd"] - latest["macd_signal"]
            if macd_diff > 0:
                score += 10; bull_pts += 1
                reasons.append("MACD bullish crossover")
            else:
                score += 5; bear_pts += 1
                reasons.append("MACD bearish")

        # Volume confirmation (5 pts)
        if pd.notna(latest.get("volume_sma_20")):
            if latest["volume"] > latest["volume_sma_20"] * 1.3:
                score += 5
                reasons.append("High volume surge")

        # Recent momentum (5 pts)
        if len(df) >= 20:
            ret_20d = (price / df.iloc[-20]["close"] - 1) * 100
            if ret_20d > 5:
                score += 5; bull_pts += 1
                reasons.append(f"+{ret_20d:.1f}% 20d momentum")
            elif ret_20d < -5:
                score += 3; bear_pts += 1
                reasons.append(f"{ret_20d:.1f}% 20d decline")

        direction = "BULLISH" if bull_pts >= bear_pts else "BEARISH"
        return score, direction, reasons

    def _sentiment_score(self, symbol: str) -> tuple:
        """Sentiment → score (0-25), direction, reasons, raw_score."""
        try:
            sent = sentiment_analyzer.get_stock_sentiment(symbol)
            raw = sent["score"]

            if raw > 0.3:
                score, direction = 25, "BULLISH"
                reasons = [f"Sentiment very positive ({raw:+.2f})"]
            elif raw > 0.1:
                score, direction = 18, "BULLISH"
                reasons = [f"Sentiment positive ({raw:+.2f})"]
            elif raw > -0.1:
                score, direction = 12, "NEUTRAL"
                reasons = [f"Sentiment neutral ({raw:+.2f})"]
            elif raw > -0.3:
                score, direction = 8, "BEARISH"
                reasons = [f"Sentiment negative ({raw:+.2f})"]
            else:
                score, direction = 3, "BEARISH"
                reasons = [f"Sentiment very negative ({raw:+.2f})"]

            if sent["headline_count"] > 0:
                reasons.append(f"{sent['positive_count']}+ / {sent['negative_count']}- headlines")

            return score, direction, reasons, raw

        except Exception as e:
            logger.error(f"Sentiment scoring failed for {symbol}: {e}")
            return 12, "NEUTRAL", ["Sentiment unavailable"], 0.0

    def _ml_score(self, symbol: str) -> tuple:
        """ML prediction → score (0-25), direction, reasons, probability.

        Key insight: a strong DOWN signal is just as valuable as a strong
        UP signal — it drives put buying and bearish spreads.  The score
        reflects *conviction strength* regardless of direction.
        """
        try:
            pred = ml_predictor.predict(symbol)
            prob = pred["probability"]  # probability of UP
            acc = pred["model_accuracy"]

            if acc < 0.48:
                return 12, "NEUTRAL", [f"ML low confidence (acc {acc:.0%})"], prob

            # Conviction = distance from 0.50 (either direction)
            conviction = abs(prob - 0.50)

            if prob >= 0.60:
                score, direction = 22, "BULLISH"
                reasons = [f"ML: {prob:.0%} UP (acc {acc:.0%})"]
            elif prob >= 0.52:
                score, direction = 16, "BULLISH"
                reasons = [f"ML: leans UP {prob:.0%}"]
            elif prob >= 0.48:
                score, direction = 12, "NEUTRAL"
                reasons = [f"ML: neutral ({prob:.0%})"]
            elif prob >= 0.40:
                score, direction = 16, "BEARISH"
                reasons = [f"ML: leans DOWN ({1-prob:.0%} down prob)"]
            else:
                score, direction = 22, "BEARISH"
                reasons = [f"ML: strong DOWN signal ({1-prob:.0%} down prob, acc {acc:.0%})"]

            return score, direction, reasons, prob

        except Exception as e:
            logger.error(f"ML scoring failed for {symbol}: {e}")
            return 12, "NEUTRAL", ["ML unavailable"], 0.5

    def _regime_adjustment(self, regime: str, tech_dir: str) -> tuple:
        """Market regime → adjustment (−10 to +10)."""
        if regime == "BULL":
            if tech_dir == "BULLISH":
                return 10, ["Regime boost: BULL market + bullish technicals"]
            return 3, ["BULL regime"]
        elif regime == "BEAR":
            if tech_dir == "BEARISH":
                return 8, ["Regime boost: BEAR market + bearish technicals"]
            return -5, ["Regime drag: BEAR market vs bullish technicals"]
        return 0, []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _refresh_market_sentiment(self):
        now = datetime.now()
        if self._market_sentiment_ts and (now - self._market_sentiment_ts).seconds < 300:
            return
        self._market_sentiment = sentiment_analyzer.get_market_sentiment()
        self._market_sentiment_ts = now


# Global instance
momentum_strategy = MomentumStrategy()

__all__ = ["MomentumStrategy", "momentum_strategy"]
