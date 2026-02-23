"""
ML-based stock movement predictor using gradient boosting.

Trains on recent price/volume features and outputs a probability
that a stock will be UP after a configurable horizon (default 5 days).
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from src.data.market_data import market_data
from src.utils.logger import logger


class MLPredictor:
    """Gradient-boosting classifier for directional stock predictions."""

    def __init__(self, horizon: int = 5, retrain_days: int = 7):
        """
        Args:
            horizon: Predict price direction N days ahead.
            retrain_days: Re-train model every N calendar days.
        """
        self.horizon = horizon
        self.retrain_days = retrain_days
        self._models: Dict[str, Tuple[GradientBoostingClassifier, StandardScaler, datetime]] = {}

    def predict(self, symbol: str) -> Dict:
        """
        Predict directional move for *symbol*.

        Returns:
            {
                "symbol": str,
                "prediction": "UP" | "DOWN",
                "probability": float (0-1 for UP),
                "features": dict of latest feature values,
                "model_accuracy": float (cross-val accuracy),
            }
        """
        try:
            model, scaler, accuracy = self._get_or_train(symbol)
            if model is None:
                return self._empty(symbol)

            features_df = self._build_features(symbol)
            if features_df is None or features_df.empty:
                return self._empty(symbol)

            latest = features_df.iloc[[-1]].copy()
            # Drop 'close' to match training features
            latest_features = latest.drop(columns=["close"], errors="ignore")
            X = scaler.transform(latest_features)
            prob_up = float(model.predict_proba(X)[0][1])

            return {
                "symbol": symbol,
                "prediction": "UP" if prob_up >= 0.5 else "DOWN",
                "probability": round(prob_up, 4),
                "features": latest.iloc[0].to_dict(),
                "model_accuracy": round(accuracy, 4),
            }

        except Exception as e:
            logger.error(f"ML prediction failed for {symbol}: {e}")
            return self._empty(symbol)

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def _get_or_train(self, symbol: str):
        """Return cached model or retrain."""
        cached = self._models.get(symbol)
        if cached:
            model, scaler, trained_at = cached
            if (datetime.now() - trained_at).days < self.retrain_days:
                # Need to return accuracy too - compute from cached metadata
                return model, scaler, getattr(model, "_cv_accuracy_", 0.5)

        return self._train(symbol)

    def _train(self, symbol: str):
        """Train a new model for the symbol."""
        try:
            features_df = self._build_features(symbol)
            if features_df is None or len(features_df) < 100:
                logger.warning(f"Not enough data to train ML model for {symbol}")
                return None, None, 0.0

            # Target: is the price higher after `horizon` days?
            features_df["target"] = (
                features_df["close"].shift(-self.horizon) > features_df["close"]
            ).astype(int)

            # Drop rows with NaN target
            features_df = features_df.dropna()
            if len(features_df) < 80:
                return None, None, 0.0

            feature_cols = [c for c in features_df.columns if c not in ("target", "close")]
            X = features_df[feature_cols].values
            y = features_df["target"].values

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            model = GradientBoostingClassifier(
                n_estimators=150,
                max_depth=4,
                learning_rate=0.08,
                subsample=0.8,
                min_samples_leaf=10,
                random_state=42,
            )

            # Time-series cross-validation for accuracy estimate
            tscv = TimeSeriesSplit(n_splits=3)
            cv_scores = []
            for train_idx, val_idx in tscv.split(X_scaled):
                model.fit(X_scaled[train_idx], y[train_idx])
                cv_scores.append(model.score(X_scaled[val_idx], y[val_idx]))

            accuracy = float(np.mean(cv_scores))

            # Final fit on all data
            model.fit(X_scaled, y)
            model._cv_accuracy_ = accuracy

            self._models[symbol] = (model, scaler, datetime.now())
            logger.info(
                f"ML model trained for {symbol}: accuracy={accuracy:.2%}, "
                f"samples={len(y)}, features={len(feature_cols)}"
            )
            return model, scaler, accuracy

        except Exception as e:
            logger.error(f"Error training ML model for {symbol}: {e}")
            return None, None, 0.0

    # ------------------------------------------------------------------
    # Feature Engineering
    # ------------------------------------------------------------------

    def _build_features(self, symbol: str) -> Optional[pd.DataFrame]:
        """Build feature matrix from historical data."""
        try:
            end = datetime.now()
            start = end - timedelta(days=1100)  # ~3 years of daily data for better accuracy
            df = market_data.get_historical_data(symbol, start, end)
            if df is None or len(df) < 100:
                return None

            df = market_data.calculate_technical_indicators(df)

            feat = pd.DataFrame(index=df.index)
            feat["close"] = df["close"]

            # --- Returns ---
            for w in (1, 3, 5, 10, 20, 60):
                feat[f"ret_{w}d"] = df["close"].pct_change(w)

            # --- Volatility ---
            feat["volatility_10"] = df["close"].pct_change().rolling(10).std()
            feat["volatility_20"] = df["close"].pct_change().rolling(20).std()

            # --- Volume features ---
            feat["vol_ratio"] = df["volume"] / df["volume"].rolling(20).mean()
            feat["vol_trend"] = df["volume"].rolling(5).mean() / df["volume"].rolling(20).mean()

            # --- Technical indicators ---
            feat["rsi"] = df.get("rsi", pd.Series(dtype=float))
            feat["macd_hist"] = df.get("macd", 0) - df.get("macd_signal", 0)

            # SMA ratios
            if "sma_20" in df.columns:
                feat["price_to_sma20"] = df["close"] / df["sma_20"]
            if "sma_50" in df.columns:
                feat["price_to_sma50"] = df["close"] / df["sma_50"]
            if "sma_200" in df.columns:
                feat["price_to_sma200"] = df["close"] / df["sma_200"]

            # Bollinger %B
            if "bb_upper" in df.columns and "bb_lower" in df.columns:
                bb_range = df["bb_upper"] - df["bb_lower"]
                feat["bb_pctb"] = (df["close"] - df["bb_lower"]) / bb_range.replace(0, np.nan)

            # --- Price patterns ---
            feat["high_low_range"] = (df["high"] - df["low"]) / df["close"]
            feat["close_position"] = (df["close"] - df["low"]) / (df["high"] - df["low"]).replace(0, np.nan)

            # --- Day of week (cyclical) ---
            dow = df.index.dayofweek
            feat["dow_sin"] = np.sin(2 * np.pi * dow / 5)
            feat["dow_cos"] = np.cos(2 * np.pi * dow / 5)

            # Drop rows with NaNs in features (keep close for target construction)
            feature_cols = [c for c in feat.columns if c != "close"]
            feat = feat.dropna(subset=feature_cols)

            return feat

        except Exception as e:
            logger.error(f"Feature building failed for {symbol}: {e}")
            return None

    # ------------------------------------------------------------------
    @staticmethod
    def _empty(symbol: str) -> Dict:
        return {
            "symbol": symbol,
            "prediction": "NEUTRAL",
            "probability": 0.5,
            "features": {},
            "model_accuracy": 0.0,
        }


# Global instance
ml_predictor = MLPredictor()

__all__ = ["MLPredictor", "ml_predictor"]
