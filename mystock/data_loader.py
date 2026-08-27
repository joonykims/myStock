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
    """Check if the ticker is a Korean stock (e.g. 6-digit numeric string)."""
    clean_ticker = ticker.strip().upper()
    return bool(re.match(r"^\d{6}$", clean_ticker)) or clean_ticker.endswith(".KS") or clean_ticker.endswith(".KQ")


def get_stock_name(ticker: str) -> str:
    """Get human-readable stock name."""
    clean_ticker = ticker.strip().upper()
    if is_korean_ticker(clean_ticker):
        pure_code = clean_ticker.replace(".KS", "").replace(".KQ", "")
        if PYKRX_AVAILABLE:
            try:
                with contextlib.redirect_stderr(io.StringIO()):
                    name = krx.get_market_ticker_name(pure_code)
                if name:
                    return f"{name} ({pure_code})"
            except Exception:
                pass
        return f"KRX:{pure_code}"
    return clean_ticker


def fetch_stock_data(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = 365,
) -> pd.DataFrame:
    """
    Fetch OHLCV historical stock data for Korean or US markets.

    Parameters:
        ticker: Stock symbol (e.g., '005930', 'NVDA', 'AAPL')
        start_date: Start date string ('YYYY-MM-DD' or 'YYYYMMDD'). If None, defaults to `days` before today.
        end_date: End date string ('YYYY-MM-DD' or 'YYYYMMDD'). If None, defaults to today.
        days: Lookback period in days if start_date is not provided.

    Returns:
        pd.DataFrame with DatetimeIndex and columns ['Open', 'High', 'Low', 'Close', 'Volume']
    """
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
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                df = krx.get_market_ohlcv(s_str, e_str, pure_code)
            if df is not None and not df.empty:

                df = df.rename(columns={
                    "시가": "Open",
                    "고가": "High",
                    "저가": "Low",
                    "종가": "Close",
                    "거래량": "Volume",
                })
                # Keep standard OHLCV columns
                cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
                df = df[cols].copy()
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()
                return df
        except Exception as e:
            print(f"[Warning] pykrx fetch failed for {ticker} ({e}), falling back to yfinance...")

    # Strategy 2: Fetch via yfinance (US stock or fallback for KRX stock)
    if YFINANCE_AVAILABLE:
        yf_ticker = clean_ticker
        if is_korean_ticker(clean_ticker) and not clean_ticker.endswith(".KS") and not clean_ticker.endswith(".KQ"):
            # Default to .KS (KOSPI) first, if empty try .KQ (KOSDAQ)
            yf_ticker = f"{clean_ticker}.KS"

        s_str = start_dt.strftime("%Y-%m-%d")
        e_str = (end_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        try:
            df = yf.download(yf_ticker, start=s_str, end=e_str, progress=False)
            if (df is None or df.empty) and is_korean_ticker(clean_ticker):
                # Try KOSDAQ (.KQ)
                yf_ticker = f"{clean_ticker.replace('.KS', '')}.KQ"
                df = yf.download(yf_ticker, start=s_str, end=e_str, progress=False)

            if df is not None and not df.empty:
                # Handle MultiIndex columns from recent yfinance versions
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
                df = df[cols].copy()
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()
                return df
        except Exception as e:
            print(f"[Error] yfinance fetch failed for {ticker}: {e}")

    raise ValueError(f"Could not fetch stock data for ticker: '{ticker}'")
