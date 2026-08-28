import datetime
import re
import os
import sys
import io
import contextlib
import pandas as pd
from typing import Tuple, Optional

try:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from pykrx import stock as krx
    PYKRX_AVAILABLE = True
except Exception:
    PYKRX_AVAILABLE = False



try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


def is_korean_ticker(ticker: str) -> bool:
    """
    Check if the ticker is a Korean stock or ETF/ETN (6-digit numeric/alphanumeric or .KS/.KQ).
    Supports standard 6-digit codes (e.g. 005930), alphanumeric ETF/ETN codes (e.g. 0072R0),
    and A-prefixed codes (e.g. A0072R0).
    """
    clean_ticker = ticker.strip().upper()
    if clean_ticker.endswith(".KS") or clean_ticker.endswith(".KQ"):
        return True
    if clean_ticker.startswith("A") and len(clean_ticker) == 7 and re.match(r"^A[0-9A-Z]{6}$", clean_ticker):
        return True
    # Standard KRX codes: 6 alphanumeric characters starting with digits
    if re.match(r"^\d[0-9A-Z]{5}$", clean_ticker) or re.match(r"^\d{6}$", clean_ticker):
        return True
    return False


def get_stock_name(ticker: str) -> str:
    """Get human-readable stock name with watchlist and pykrx fallbacks."""
    clean_ticker = ticker.strip().upper()
    pure_code = clean_ticker.replace(".KS", "").replace(".KQ", "")
    if pure_code.startswith("A") and len(pure_code) == 7:
        pure_code = pure_code[1:]

    # 1. Check watchlist.json for custom name
    try:
        from .watchlist import load_watchlist
        wl = load_watchlist()
        for cat, items in wl.items():
            for it in items:
                if isinstance(it, dict) and it.get("ticker", "").strip().upper() == pure_code:
                    n = it.get("name")
                    if n and n != pure_code:
                        return f"{n} ({pure_code})"
    except Exception:
        pass

    # 2. Check pykrx for Korean stocks and ETFs
    if is_korean_ticker(clean_ticker):
        if PYKRX_AVAILABLE:
            try:
                with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                    name = krx.get_market_ticker_name(pure_code)
                if isinstance(name, str) and name.strip():
                    return f"{name.strip()} ({pure_code})"
            except Exception:
                pass
            try:
                with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                    name = krx.get_etf_ticker_name(pure_code)
                if isinstance(name, str) and name.strip():
                    return f"{name.strip()} ({pure_code})"
            except Exception:
                pass
        return f"KRX:{pure_code}"

    return clean_ticker



def _standardize_ohlcv_df(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize OHLCV dataframe columns, index, and strip timezone."""
    if df is None or df.empty:
        return pd.DataFrame()

    # Handle MultiIndex columns (e.g. from yfinance)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Standardize column names
    rename_map = {
        "시가": "Open", "고가": "High", "저가": "Low", "종가": "Close", "거래량": "Volume",
        "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume",
        "Adj Close": "Close",
    }
    df = df.rename(columns=rename_map)

    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    available_cols = [c for c in required_cols if c in df.columns]
    if len(available_cols) < 4:  # At least need OHLC
        return pd.DataFrame()

    res = df[available_cols].copy()
    # Strip timezone for clean Plotly / Pandas date alignment
    res.index = pd.to_datetime(res.index)
    if res.index.tz is not None:
        res.index = res.index.tz_localize(None)

    # Convert columns to float
    for c in res.columns:
        res[c] = pd.to_numeric(res[c], errors="coerce")

    res = res.dropna(subset=["Close"]).sort_index()
    return res


def fetch_stock_data(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = 365,
    max_retries: int = 3,
) -> pd.DataFrame:
    """
    Fetch OHLCV historical stock data for Korean or US markets with robust fallback & retry.

    Parameters:
        ticker: Stock symbol (e.g., '005930', 'NVDA', 'AAPL', 'QQQ')
        start_date: Start date string ('YYYY-MM-DD' or 'YYYYMMDD').
        end_date: End date string ('YYYY-MM-DD' or 'YYYYMMDD').
        days: Lookback period in days if start_date is not provided.
        max_retries: Number of retry attempts on network/timeout errors.

    Returns:
        pd.DataFrame with DatetimeIndex and columns ['Open', 'High', 'Low', 'Close', 'Volume']
    """
    import time

    now = datetime.datetime.now()
    if end_date is None:
        end_dt = now
    else:
        end_dt = pd.to_datetime(end_date)

    if start_date is None:
        start_dt = end_dt - datetime.timedelta(days=days)
    else:
        start_dt = pd.to_datetime(start_date)

    clean_ticker = ticker.strip()

    # Strategy 1: Korean stock via pykrx
    if is_korean_ticker(clean_ticker) and PYKRX_AVAILABLE:
        pure_code = clean_ticker.replace(".KS", "").replace(".KQ", "")
        s_str = start_dt.strftime("%Y%m%d")
        e_str = end_dt.strftime("%Y%m%d")
        for attempt in range(max_retries):
            try:
                with contextlib.redirect_stderr(io.StringIO()):
                    df = krx.get_market_ohlcv(s_str, e_str, pure_code)
                std_df = _standardize_ohlcv_df(df)
                if not std_df.empty:
                    return std_df
            except Exception:
                time.sleep(0.3 * (attempt + 1))

    # Strategy 2: Fetch via yfinance (US stock or fallback for KRX stock)
    if YFINANCE_AVAILABLE:
        yf_ticker = clean_ticker
        if is_korean_ticker(clean_ticker) and not clean_ticker.endswith(".KS") and not clean_ticker.endswith(".KQ"):
            yf_ticker = f"{clean_ticker}.KS"

        s_str = start_dt.strftime("%Y-%m-%d")
        e_str = (end_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        for attempt in range(max_retries):
            # Attempt 2.1: yf.download with start and end
            try:
                df = yf.download(yf_ticker, start=s_str, end=e_str, progress=False, timeout=10)
                std_df = _standardize_ohlcv_df(df)
                if not std_df.empty:
                    return std_df
            except Exception:
                pass

            # Attempt 2.2: yf.Ticker.history with period
            try:
                t_obj = yf.Ticker(yf_ticker)
                period_str = f"{max(days, 30)}d" if days <= 730 else "5y"
                df = t_obj.history(period=period_str, auto_adjust=False, timeout=10)
                std_df = _standardize_ohlcv_df(df)
                if not std_df.empty:
                    # Filter to start_dt
                    std_df = std_df[std_df.index >= pd.to_datetime(s_str)]
                    if not std_df.empty:
                        return std_df
            except Exception:
                pass

            # Attempt 2.3: yf.download with period
            try:
                period_str = f"{max(days, 30)}d" if days <= 730 else "5y"
                df = yf.download(yf_ticker, period=period_str, progress=False, timeout=10)
                std_df = _standardize_ohlcv_df(df)
                if not std_df.empty:
                    std_df = std_df[std_df.index >= pd.to_datetime(s_str)]
                    if not std_df.empty:
                        return std_df
            except Exception:
                pass

            # If Korean stock failed on KOSPI (.KS), try KOSDAQ (.KQ)
            if is_korean_ticker(clean_ticker) and yf_ticker.endswith(".KS"):
                yf_ticker = f"{clean_ticker.replace('.KS', '')}.KQ"

            time.sleep(0.5 * (attempt + 1))

    raise ValueError(f"Could not fetch stock data for ticker: '{ticker}'")

