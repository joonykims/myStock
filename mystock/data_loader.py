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


_HTTP_SESSION = None


def _get_http_session():
    """Reusable requests session with browser-like User-Agent to prevent Yahoo Finance 429/Crumb blocking."""
    global _HTTP_SESSION
    if _HTTP_SESSION is None:
        import requests
        _HTTP_SESSION = requests.Session()
        _HTTP_SESSION.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
    return _HTTP_SESSION


def _fetch_yahoo_direct(
    ticker: str,
    start_dt: datetime.datetime,
    end_dt: datetime.datetime,
    timeout: int = 5,
) -> Optional[pd.DataFrame]:
    """
    Directly query Yahoo Finance v8 Chart API for ultra-fast, robust OHLCV data.
    Bypasses yfinance crumb/cookie issues and downloads in < 1 second.
    """
    session = _get_http_session()
    p1 = int(start_dt.timestamp())
    p2 = int((end_dt + datetime.timedelta(days=1)).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={p1}&period2={p2}&interval=1d&includePrePost=false"
    try:
        resp = session.get(url, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("chart", {}).get("result")
            if results and len(results) > 0:
                item = results[0]
                timestamps = item.get("timestamp")
                quote = item.get("indicators", {}).get("quote", [{}])[0]
                if timestamps and quote and "close" in quote:
                    raw_df = pd.DataFrame({
                        "Open": quote.get("open"),
                        "High": quote.get("high"),
                        "Low": quote.get("low"),
                        "Close": quote.get("close"),
                        "Volume": quote.get("volume"),
                    }, index=pd.to_datetime(timestamps, unit="s"))
                    std_df = _standardize_ohlcv_df(raw_df)
                    if not std_df.empty:
                        return std_df
    except Exception:
        pass
    return None


def _raw_fetch_stock_data(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = 365,
    max_retries: int = 2,
) -> pd.DataFrame:
    """
    Raw OHLCV fetcher — always hits the network API (pykrx / direct Yahoo API / yfinance).

    This is the internal implementation. External callers should use
    fetch_stock_data() which wraps this with the incremental cache.
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

    # Strategy 2: Ultra-fast Direct Yahoo API + yfinance fallback (US stocks & KRX fallback)
    yf_ticker = clean_ticker
    if is_korean_ticker(clean_ticker) and not clean_ticker.endswith(".KS") and not clean_ticker.endswith(".KQ"):
        yf_ticker = f"{clean_ticker}.KS"

    for attempt in range(max_retries):
        # Attempt 2.1: Direct Yahoo Finance v8 Chart API (fastest, < 1s, bypasses crumb/blocking)
        direct_df = _fetch_yahoo_direct(yf_ticker, start_dt, end_dt, timeout=5)
        if direct_df is not None and not direct_df.empty:
            return direct_df

        # Attempt 2.2: yf.Ticker with custom session
        if YFINANCE_AVAILABLE:
            try:
                session = _get_http_session()
                t_obj = yf.Ticker(yf_ticker, session=session)
                period_str = f"{max(days, 30)}d" if days <= 730 else "5y"
                df = t_obj.history(period=period_str, auto_adjust=False, timeout=5)
                std_df = _standardize_ohlcv_df(df)
                if not std_df.empty:
                    std_df = std_df[std_df.index >= pd.to_datetime(start_dt.strftime("%Y-%m-%d"))]
                    if not std_df.empty:
                        return std_df
            except Exception:
                pass

            # Attempt 2.3: yf.download with custom session
            try:
                session = _get_http_session()
                s_str = start_dt.strftime("%Y-%m-%d")
                e_str = (end_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                df = yf.download(yf_ticker, start=s_str, end=e_str, progress=False, timeout=5, session=session)
                std_df = _standardize_ohlcv_df(df)
                if not std_df.empty:
                    return std_df
            except Exception:
                pass

        # If Korean stock failed on KOSPI (.KS), try KOSDAQ (.KQ)
        if is_korean_ticker(clean_ticker) and yf_ticker.endswith(".KS"):
            yf_ticker = f"{clean_ticker.replace('.KS', '')}.KQ"

        time.sleep(0.3 * (attempt + 1))

    raise ValueError(f"Could not fetch stock data for ticker: '{ticker}'")


def fetch_stock_data(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = 365,
    max_retries: int = 3,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Fetch OHLCV historical stock data with incremental local cache.

    On first call, fetches the full date range from APIs and saves to local
    Parquet cache. On subsequent calls, loads cached data and only fetches
    the delta (new trading days since the last cached date).

    Parameters:
        ticker: Stock symbol (e.g., '005930', 'NVDA', 'AAPL', 'QQQ')
        start_date: Start date string ('YYYY-MM-DD' or 'YYYYMMDD').
        end_date: End date string ('YYYY-MM-DD' or 'YYYYMMDD').
        days: Lookback period in days if start_date is not provided.
        max_retries: Number of retry attempts on network/timeout errors.
        use_cache: If True (default), use incremental Parquet cache.
                   If False, always fetch full range from API.

    Returns:
        pd.DataFrame with DatetimeIndex and columns ['Open', 'High', 'Low', 'Close', 'Volume']
    """
    if use_cache:
        try:
            from .stock_cache import get_or_fetch

            return get_or_fetch(
                ticker=ticker,
                days=days,
                fetch_fn=_raw_fetch_stock_data,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception:
            # If cache layer fails for any reason, fall through to raw fetch
            pass

    return _raw_fetch_stock_data(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        days=days,
        max_retries=max_retries,
    )


