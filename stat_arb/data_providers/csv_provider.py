"""CSV-based data provider for offline experiments."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping

import pandas as pd

from .base import DataProvider, PriceData


@dataclass(slots=True)
class CSVSpecification:
    """Configuration that maps a symbol to a CSV file and column schema."""

    path: Path
    price_column: str = "close"
    timestamp_column: str = "timestamp"
    currency: str = "USD"


class CSVDataProvider(DataProvider):
    """Load price history from CSV files.

    The provider expects CSV files with a timestamp column and a price column.
    Additional columns are ignored. Timestamps are parsed as UTC.
    """

    def __init__(self, mapping: Mapping[str, CSVSpecification | Mapping[str, str | Path]]):
        """Create the provider with a mapping from tickers to CSV files.

        Args:
            mapping: Dictionary describing where to load each ticker from.
                Each value can either be a :class:`CSVSpecification` or a raw
                mapping with ``path`` and optional ``price_column``,
                ``timestamp_column`` and ``currency`` keys.
        """

        self._mapping: dict[str, CSVSpecification] = {}
        for symbol, spec in mapping.items():
            if isinstance(spec, CSVSpecification):
                self._mapping[symbol] = spec
            else:
                path = Path(spec["path"])
                price_column = str(spec.get("price_column", "close"))
                timestamp_column = str(spec.get("timestamp_column", "timestamp"))
                currency = str(spec.get("currency", "USD"))
                self._mapping[symbol] = CSVSpecification(
                    path=path,
                    price_column=price_column,
                    timestamp_column=timestamp_column,
                    currency=currency,
                )

    def fetch(
        self,
        ticker: str,
        start: datetime,
        end: datetime,
        interval: str,
    ) -> PriceData:
        try:
            spec = self._mapping[ticker]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise KeyError(f"Ticker {ticker!r} is not configured for the CSV provider") from exc

        df = pd.read_csv(spec.path)
        if spec.timestamp_column not in df.columns:
            raise KeyError(
                f"Column '{spec.timestamp_column}' not found in {spec.path}. "
                "Adjust the CSVSpecification or rename the column."
            )
        if spec.price_column not in df.columns:
            raise KeyError(
                f"Column '{spec.price_column}' not found in {spec.path}. "
                "Adjust the CSVSpecification or rename the column."
            )

        df[spec.timestamp_column] = pd.to_datetime(df[spec.timestamp_column], utc=True)
        df = df.set_index(spec.timestamp_column).sort_index()
        filtered = df.loc[start:end]
        series = filtered[spec.price_column].rename(ticker).astype(float)
        return PriceData(prices=series, currency=spec.currency)
