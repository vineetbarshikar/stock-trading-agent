"""
Market sentiment analysis using news headlines from yfinance
and market-wide fear/greed indicators.
"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yfinance as yf
import pandas as pd
from src.utils.logger import logger


# Word lists for sentiment scoring.  Scored in (negative, positive) tuples
# so the analyser picks up the most common financial language patterns.
POSITIVE_WORDS = {
    "surge", "surges", "surging", "soar", "soars", "soaring",
    "rally", "rallies", "rallying", "jump", "jumps", "jumped",
    "gain", "gains", "gained", "rise", "rises", "rising", "risen",
    "beat", "beats", "beating", "exceed", "exceeds", "exceeded",
    "upgrade", "upgrades", "upgraded", "outperform", "buy",
    "bullish", "boom", "booming", "record", "high", "highs",
    "growth", "profit", "profits", "profitable", "revenue",
    "strong", "stronger", "strongest", "positive", "optimistic",
    "breakthrough", "innovation", "momentum", "upbeat",
    "recover", "recovery", "rebound", "rebounds", "accelerate",
    "expand", "expansion", "dividend", "upside", "opportunity",
    "confident", "confidence", "boost", "boosted",
}

NEGATIVE_WORDS = {
    "crash", "crashes", "crashing", "plunge", "plunges", "plunging",
    "drop", "drops", "dropped", "fall", "falls", "falling", "fell",
    "decline", "declines", "declining", "loss", "losses",
    "miss", "misses", "missed", "disappoint", "disappoints",
    "downgrade", "downgrades", "downgraded", "underperform", "sell",
    "bearish", "bust", "recession", "low", "lows", "weak", "weaker",
    "risk", "risks", "risky", "fear", "fears", "worried", "warning",
    "layoff", "layoffs", "cut", "cuts", "slash", "slashed",
    "debt", "default", "bankruptcy", "crisis", "trouble",
    "negative", "pessimistic", "volatile", "uncertainty",
    "lawsuit", "investigation", "fraud", "scandal",
    "inflation", "tariff", "tariffs", "war", "sanctions",
    "overvalued", "bubble", "correction", "selloff", "sell-off",
    "downside", "stagnant", "struggle", "struggles",
}


class SentimentAnalyzer:
    """Analyzes market sentiment from multiple sources."""

    def __init__(self):
        self._vix_cache: Optional[Tuple[float, datetime]] = None

    def get_stock_sentiment(self, symbol: str) -> Dict:
        """
        Get sentiment score for a stock based on recent news headlines.

        Returns dict with:
            score: -1.0 (very bearish) to +1.0 (very bullish)
            headline_count: number of headlines analysed
            positive_count / negative_count
            top_headlines: list of (headline, score) tuples
        """
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news

            if not news:
                return self._empty_sentiment()

            scored_headlines: List[Tuple[str, float]] = []

            for item in news[:20]:  # Analyse up to 20 recent items
                title = item.get("title", "")
                if not title:
                    continue
                score = self._score_headline(title)
                scored_headlines.append((title, score))

            if not scored_headlines:
                return self._empty_sentiment()

            scores = [s for _, s in scored_headlines]
            avg_score = sum(scores) / len(scores)
            pos_count = sum(1 for s in scores if s > 0)
            neg_count = sum(1 for s in scores if s < 0)

            return {
                "score": round(avg_score, 4),
                "headline_count": len(scored_headlines),
                "positive_count": pos_count,
                "negative_count": neg_count,
                "neutral_count": len(scored_headlines) - pos_count - neg_count,
                "top_headlines": scored_headlines[:5],
            }

        except Exception as e:
            logger.error(f"Error getting sentiment for {symbol}: {e}")
            return self._empty_sentiment()

    def get_market_sentiment(self) -> Dict:
        """
        Get broad market sentiment using VIX, SPY trend, and market breadth.

        Returns dict with:
            regime: BULL / BEAR / NEUTRAL
            vix: current VIX level
            vix_signal: LOW_VOL / NORMAL / HIGH_VOL / EXTREME
            spy_trend: BULLISH / BEARISH / NEUTRAL
            composite_score: -1.0 to +1.0
        """
        try:
            # --- VIX ---
            vix = self._get_vix()
            if vix is None:
                vix = 20.0  # Assume normal if unavailable

            if vix < 15:
                vix_signal, vix_score = "LOW_VOL", 0.3
            elif vix < 20:
                vix_signal, vix_score = "NORMAL", 0.1
            elif vix < 25:
                vix_signal, vix_score = "HIGH_VOL", -0.2
            elif vix < 30:
                vix_signal, vix_score = "ELEVATED", -0.4
            else:
                vix_signal, vix_score = "EXTREME", -0.6

            # --- SPY trend ---
            spy_data = yf.Ticker("SPY").history(period="6mo")
            if spy_data.empty:
                spy_trend, spy_score = "NEUTRAL", 0.0
            else:
                spy_data.columns = [c.lower() for c in spy_data.columns]
                close = spy_data["close"]
                sma20 = close.rolling(20).mean().iloc[-1]
                sma50 = close.rolling(50).mean().iloc[-1]
                current = close.iloc[-1]

                if current > sma20 > sma50:
                    spy_trend, spy_score = "BULLISH", 0.4
                elif current < sma20 < sma50:
                    spy_trend, spy_score = "BEARISH", -0.4
                elif current > sma50:
                    spy_trend, spy_score = "NEUTRAL_BULL", 0.15
                else:
                    spy_trend, spy_score = "NEUTRAL_BEAR", -0.15

            # --- Market breadth (advancers vs decliners proxy) ---
            breadth_score = self._estimate_breadth()

            composite = round((vix_score + spy_score + breadth_score) / 3, 4)

            if composite > 0.15:
                regime = "BULL"
            elif composite < -0.15:
                regime = "BEAR"
            else:
                regime = "NEUTRAL"

            return {
                "regime": regime,
                "composite_score": composite,
                "vix": round(vix, 2),
                "vix_signal": vix_signal,
                "spy_trend": spy_trend,
                "spy_score": spy_score,
                "breadth_score": breadth_score,
            }

        except Exception as e:
            logger.error(f"Error getting market sentiment: {e}")
            return {
                "regime": "NEUTRAL",
                "composite_score": 0.0,
                "vix": 20.0,
                "vix_signal": "NORMAL",
                "spy_trend": "NEUTRAL",
                "spy_score": 0.0,
                "breadth_score": 0.0,
            }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _score_headline(self, headline: str) -> float:
        """Score a single headline from -1.0 to +1.0."""
        words = set(re.findall(r"[a-z]+", headline.lower()))
        pos = len(words & POSITIVE_WORDS)
        neg = len(words & NEGATIVE_WORDS)
        total = pos + neg
        if total == 0:
            return 0.0
        return round((pos - neg) / total, 4)

    def _get_vix(self) -> Optional[float]:
        """Get the current VIX level, cached for 5 minutes."""
        now = datetime.now()
        if self._vix_cache and (now - self._vix_cache[1]).seconds < 300:
            return self._vix_cache[0]

        try:
            vix_data = yf.Ticker("^VIX").history(period="5d")
            if not vix_data.empty:
                val = float(vix_data["Close"].iloc[-1])
                self._vix_cache = (val, now)
                return val
        except Exception:
            pass
        return None

    def _estimate_breadth(self) -> float:
        """Quick breadth estimate using a basket of sector ETFs."""
        etfs = ["XLK", "XLF", "XLV", "XLE", "XLI", "XLY", "XLP", "XLU", "XLRE", "XLC", "XLB"]
        try:
            up, down = 0, 0
            for etf in etfs:
                hist = yf.Ticker(etf).history(period="5d")
                if len(hist) >= 2:
                    chg = hist["Close"].iloc[-1] / hist["Close"].iloc[-2] - 1
                    if chg > 0:
                        up += 1
                    else:
                        down += 1
            total = up + down
            if total == 0:
                return 0.0
            return round((up - down) / total, 4)
        except Exception:
            return 0.0

    @staticmethod
    def _empty_sentiment() -> Dict:
        return {
            "score": 0.0,
            "headline_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "top_headlines": [],
        }


# Global instance
sentiment_analyzer = SentimentAnalyzer()

__all__ = ["SentimentAnalyzer", "sentiment_analyzer"]
