"""Configuration package."""

from .settings import settings, Settings
from . import trading_rules

__all__ = ["settings", "Settings", "trading_rules"]
