"""Yahoo Finance data provider using the :mod:`yfinance` package."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from .base import DataProvider, PriceData


class YahooFinanceDataProvider(DataProvider):
    """Fetch price history via the public Yahoo Finance API."""

    def __init__(self, auto_adjust: bool = True):
        self.auto_adjust = auto_adjust

    def _load_yfinance(self):  # pragma: no cover - thin import wrapper
        try:
            import yfinance as yf
        except ImportError as exc:  # pragma: no cover - handled at runtime
            raise ImportError(
                "yfinance is required for YahooFinanceDataProvider. Install it via"
                " 'pip install yfinance'."
            ) from exc
        return yf

    def fetch(
        self,
        ticker: str,
        start: datetime,
        end: datetime,
        interval: str,
    ) -> PriceData:
        yf = self._load_yfinance()
        data = yf.download(
            tickers=ticker,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=self.auto_adjust,
            progress=False,
        )
        if data.empty:
            raise ValueError(f"No data returned for ticker {ticker!r} from Yahoo Finance")

        if "Adj Close" in data.columns:
            price_series = data["Adj Close"].rename(ticker)
        elif "Close" in data.columns:
            price_series = data["Close"].rename(ticker)
        else:  # pragma: no cover - defensive fallback
            first_col = data.columns[0]
            price_series = data[first_col].rename(ticker)

        price_series.index = pd.to_datetime(price_series.index, utc=True)
        currency = self._extract_currency(yf, ticker)
        return PriceData(prices=price_series, currency=currency)

    @staticmethod
    def _extract_currency(yf: Any, ticker: str) -> str:
        """Determine the listing currency of ``ticker`` using yfinance metadata."""

        try:
            info = yf.Ticker(ticker).fast_info
            currency = getattr(info, "currency", None)
        except Exception:  # pragma: no cover - metadata lookup best effort
            currency = None

        if not currency:
            try:
                currency = yf.Ticker(ticker).info.get("currency")
            except Exception:  # pragma: no cover - metadata lookup best effort
                currency = None

        return (currency or "USD").upper()
