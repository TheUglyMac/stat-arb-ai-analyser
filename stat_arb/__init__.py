"""Minimal statistical arbitrage toolkit."""
from .backtest import BacktestResult, BacktestStats, Trade, backtest_bollinger, run_multi_window_backtest
from .data import PairData, load_pair_data
from .data_providers import CSVDataProvider, CSVSpecification, DataProvider, PriceData, YahooFinanceDataProvider
from .hedge import HedgeRatioResult, compute_spread, estimate_hedge_ratio
from .plotting import plot_equity_curve, plot_spread_with_bands
from .signals import BollingerBands, compute_bollinger_bands, compute_multi_bollinger
from .stationarity import ADFResult, adf_test

__all__ = [
    "ADFResult",
    "BacktestResult",
    "BacktestStats",
    "BollingerBands",
    "CSVDataProvider",
    "CSVSpecification",
    "DataProvider",
    "HedgeRatioResult",
    "PairData",
    "PriceData",
    "Trade",
    "YahooFinanceDataProvider",
    "adf_test",
    "backtest_bollinger",
    "compute_bollinger_bands",
    "compute_multi_bollinger",
    "compute_spread",
    "estimate_hedge_ratio",
    "load_pair_data",
    "plot_equity_curve",
    "plot_spread_with_bands",
    "run_multi_window_backtest",
]
