"""OANDA REST API data provider."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping

import pandas as pd
import requests

from .base import DataProvider, PriceData


class OandaDataProvider(DataProvider):
    """Load historical candle data from the OANDA v20 REST API."""

    _GRANULARITY_MAP: Mapping[str, str] = {
        "1m": "M1",
        "5m": "M5",
        "15m": "M15",
        "30m": "M30",
        "1h": "H1",
        "4h": "H4",
        "1d": "D",
        "1w": "W",
    }
    _GRANULARITY_TO_DELTA: Mapping[str, pd.Timedelta] = {
        "M1": pd.Timedelta(minutes=1),
        "M5": pd.Timedelta(minutes=5),
        "M15": pd.Timedelta(minutes=15),
        "M30": pd.Timedelta(minutes=30),
        "H1": pd.Timedelta(hours=1),
        "H4": pd.Timedelta(hours=4),
        "D": pd.Timedelta(days=1),
        "W": pd.Timedelta(weeks=1),
    }
    _MAX_BATCH = 5000

    def __init__(
        self,
        api_key: str,
        environment: str = "practice",
        *,
        instrument_currencies: Mapping[str, str] | None = None,
        session: requests.Session | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Create the provider.

        Args:
            api_key: Personal access token generated from the OANDA dashboard.
            environment: Either ``"practice"`` (default) or ``"live"`` to
                determine which REST endpoint is used.
            instrument_currencies: Optional overrides for the price currency of
                specific instruments, keyed by instrument name.
            session: Optional :class:`requests.Session` to reuse connections.
            timeout: HTTP timeout applied to each request in seconds.
        """

        if not api_key:
            raise ValueError("api_key must be provided for OandaDataProvider")

        env = environment.lower()
        if env == "practice":
            self._base_url = "https://api-fxpractice.oanda.com"
        elif env in {"live", "trade", "fxtrade"}:
            self._base_url = "https://api-fxtrade.oanda.com"
        else:  # pragma: no cover - defensive configuration guard
            raise ValueError(
                "environment must be either 'practice' or 'live' for OandaDataProvider"
            )

        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            }
        )
        self._timeout = timeout
        self._instrument_currencies = {
            symbol: currency.upper() for symbol, currency in (instrument_currencies or {}).items()
        }

    def _normalise_granularity(self, interval: str) -> str:
        norm = interval.strip()
        if not norm:
            raise ValueError("Interval string must not be empty")
        lower = norm.lower()
        if lower in self._GRANULARITY_MAP:
            return self._GRANULARITY_MAP[lower]
        upper = norm.upper()
        if upper in self._GRANULARITY_TO_DELTA:
            return upper
        raise ValueError(f"Unsupported interval {interval!r} for OANDA candles")

    @staticmethod
    def _ensure_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def _format_datetime(dt: datetime) -> str:
        return dt.isoformat().replace("+00:00", "Z")

    def _infer_currency(self, instrument: str) -> str:
        if instrument in self._instrument_currencies:
            return self._instrument_currencies[instrument]
        if "_" in instrument:
            return instrument.rsplit("_", 1)[-1].upper()
        return "USD"

    def fetch(
        self,
        ticker: str,
        start: datetime,
        end: datetime,
        interval: str,
    ) -> PriceData:
        granularity = self._normalise_granularity(interval)
        start_utc = self._ensure_utc(start)
        end_utc = self._ensure_utc(end)
        if start_utc >= end_utc:
            raise ValueError("start must be earlier than end for OandaDataProvider.fetch")

        candles = []
        next_from = start_utc
        delta = self._GRANULARITY_TO_DELTA[granularity]
        url = f"{self._base_url}/v3/instruments/{ticker}/candles"

        while next_from < end_utc:
            params = {
                "granularity": granularity,
                "from": self._format_datetime(next_from),
                "to": self._format_datetime(end_utc),
                "price": "M",
                "count": self._MAX_BATCH,
            }
            response = self._session.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()
            payload = response.json()
            batch = payload.get("candles", [])
            if not batch:
                break

            last_time = None
            for candle in batch:
                if not candle.get("complete", False):
                    continue
                time_str = candle.get("time")
                mid = candle.get("mid", {})
                close_str = mid.get("c")
                if time_str is None or close_str is None:
                    continue
                ts = pd.to_datetime(time_str, utc=True)
                if ts < start_utc or ts > end_utc:
                    continue
                if candles and ts <= candles[-1][0]:
                    continue
                candles.append((ts, float(close_str)))
                last_time = ts

            if last_time is None:
                break

            next_from = last_time + delta
            if len(batch) < self._MAX_BATCH:
                break

        if not candles:
            raise ValueError(f"No candles returned for {ticker!r} from OANDA")

        index = pd.DatetimeIndex([ts for ts, _ in candles], name="timestamp")
        prices = pd.Series([close for _, close in candles], index=index, name=ticker)
        currency = self._infer_currency(ticker)
        return PriceData(prices=prices, currency=currency)
