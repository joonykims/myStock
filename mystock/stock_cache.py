"""
mystock/stock_cache.py
──────────────────────
Incremental Parquet-based local cache for per-ticker OHLCV data.

Instead of fetching the full date range from APIs on every call,
this module persists data to local Parquet files and only fetches
the delta (new trading days since the last cached date).
"""

import os
import shutil
import datetime
import pandas as pd
from pathlib import Path
from typing import Optional, Callable, Dict

# Cache directory lives at project root / .cache
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = _PROJECT_ROOT / ".cache"


def _ensure_cache_dir() -> Path:
    """Create cache directory if it doesn't exist."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def _cache_path(ticker: str) -> Path:
    """Return the Parquet file path for a given ticker."""
    safe_name = ticker.strip().upper().replace("/", "_").replace("\\", "_")
    return _ensure_cache_dir() / f"{safe_name}.parquet"


def get_cached_data(ticker: str) -> Optional[pd.DataFrame]:
    """
    Load cached OHLCV data for a ticker from local Parquet file.

    Returns:
        DataFrame with DatetimeIndex and OHLCV columns, or None if no cache exists.
    """
    path = _cache_path(ticker)
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        return df.sort_index()
    except Exception:
        # Corrupted cache — remove it
        path.unlink(missing_ok=True)
        return None


def save_cache(ticker: str, df: pd.DataFrame) -> None:
    """Save OHLCV DataFrame to local Parquet cache."""
    if df is None or df.empty:
        return
    path = _cache_path(ticker)
    clean = df.copy()
    clean.index = pd.to_datetime(clean.index)
    if clean.index.tz is not None:
        clean.index = clean.index.tz_localize(None)
    clean = clean.sort_index()
    # Remove exact duplicate indices (can happen on merge boundaries)
    clean = clean[~clean.index.duplicated(keep="last")]
    clean.to_parquet(path, compression="snappy")


def get_or_fetch(
    ticker: str,
    days: int,
    fetch_fn: Callable,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Smart data loader: cache-first with incremental fetch.

    1. Check local Parquet cache for the ticker.
    2. If cache exists and covers the requested range, return cached data.
    3. If cache exists but is stale, fetch only the missing delta and merge.
    4. If no cache, do a full fetch and save.

    Args:
        ticker: Stock ticker symbol.
        days: Lookback period in calendar days.
        fetch_fn: Callable(ticker, start_date, end_date, days) -> DataFrame.
                  The raw API fetcher (pykrx / yfinance).
        start_date: Optional explicit start date string.
        end_date: Optional explicit end date string.

    Returns:
        DataFrame with OHLCV data covering the requested range.
    """
    now = datetime.datetime.now()
    if end_date is not None:
        end_dt = pd.to_datetime(end_date)
    else:
        end_dt = now

    if start_date is not None:
        start_dt = pd.to_datetime(start_date)
    else:
        start_dt = end_dt - datetime.timedelta(days=days)

    cached = get_cached_data(ticker)

    if cached is not None and not cached.empty:
        cache_last_date = cached.index.max()
        cache_first_date = cached.index.min()

        # Determine if cache sufficiently covers the requested start
        # Allow 5-day tolerance for weekends/holidays
        covers_start = cache_first_date <= start_dt + datetime.timedelta(days=5)

        # Determine if cache is fresh (last cached date is today or yesterday)
        today = pd.Timestamp(now.date())
        is_fresh = cache_last_date >= today - datetime.timedelta(days=1)

        if covers_start and is_fresh:
            # Cache fully covers the request — no API call needed
            result = cached[cached.index >= pd.Timestamp(start_dt)]
            if not result.empty:
                return result

        # Cache exists but needs updating
        if covers_start:
            # Only fetch the delta: from last cached date + 1 day to now
            delta_start = (cache_last_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            delta_end = end_dt.strftime("%Y-%m-%d")

            try:
                delta_df = fetch_fn(
                    ticker=ticker,
                    start_date=delta_start,
                    end_date=delta_end,
                    days=days,
                )
                if delta_df is not None and not delta_df.empty:
                    merged = pd.concat([cached, delta_df])
                    merged = merged[~merged.index.duplicated(keep="last")].sort_index()
                    save_cache(ticker, merged)
                    result = merged[merged.index >= pd.Timestamp(start_dt)]
                    return result if not result.empty else merged
                else:
                    # No new data (market closed, holiday, etc.) — mark as fresh
                    save_cache(ticker, cached)
                    result = cached[cached.index >= pd.Timestamp(start_dt)]
                    return result if not result.empty else cached
            except Exception:
                # Delta fetch failed — use stale cache rather than failing
                result = cached[cached.index >= pd.Timestamp(start_dt)]
                return result if not result.empty else cached

    # No usable cache — full fetch
    full_df = fetch_fn(
        ticker=ticker,
        start_date=start_dt.strftime("%Y-%m-%d"),
        end_date=end_dt.strftime("%Y-%m-%d"),
        days=days,
    )
    if full_df is not None and not full_df.empty:
        # If we had a partial cache that didn't cover the start, merge with it
        if cached is not None and not cached.empty:
            full_df = pd.concat([full_df, cached])
            full_df = full_df[~full_df.index.duplicated(keep="last")].sort_index()
        save_cache(ticker, full_df)
    return full_df


def invalidate_cache(ticker: Optional[str] = None) -> int:
    """
    Delete cached data.

    Args:
        ticker: If provided, delete only this ticker's cache.
                If None, delete all cached data.

    Returns:
        Number of cache files deleted.
    """
    if ticker is not None:
        path = _cache_path(ticker)
        if path.exists():
            path.unlink()
            return 1
        return 0
    else:
        if CACHE_DIR.exists():
            files = list(CACHE_DIR.glob("*.parquet"))
            count = len(files)
            for f in files:
                f.unlink(missing_ok=True)
            return count
        return 0


def get_cache_info() -> Dict:
    """
    Return a summary of the current cache state.

    Returns:
        dict with keys:
          - ticker_count: number of cached tickers
          - total_size_kb: total cache size in KB
          - tickers: list of dicts with {ticker, last_date, size_kb, rows}
    """
    info = {"ticker_count": 0, "total_size_kb": 0.0, "tickers": []}
    if not CACHE_DIR.exists():
        return info

    files = sorted(CACHE_DIR.glob("*.parquet"))
    total_size = 0
    ticker_details = []

    for f in files:
        size = f.stat().st_size
        total_size += size
        ticker_name = f.stem

        last_date_str = "N/A"
        row_count = 0
        try:
            df = pd.read_parquet(f)
            if not df.empty:
                df.index = pd.to_datetime(df.index)
                last_date_str = df.index.max().strftime("%Y-%m-%d")
                row_count = len(df)
        except Exception:
            last_date_str = "오류"

        ticker_details.append({
            "ticker": ticker_name,
            "last_date": last_date_str,
            "size_kb": round(size / 1024, 1),
            "rows": row_count,
        })

    info["ticker_count"] = len(files)
    info["total_size_kb"] = round(total_size / 1024, 1)
    info["tickers"] = ticker_details
    return info
