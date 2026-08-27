import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from typing import List, Dict, Any, Tuple


def detect_obv_divergence(
    df: pd.DataFrame,
    order: int = 5,
    max_lookback_bars: int = 40,
) -> Tuple[List[Dict[str, Any]], np.ndarray, np.ndarray]:
    """
    Detect Bullish and Bearish OBV Divergences.

    Bullish Divergence:
        - Price Lows are Falling or Equal (Low[curr] <= Low[prev])
        - OBV Lows are Rising (OBV[curr] > OBV[prev])
        - Indicates bottom accumulation (Smart money buying)

    Bearish Divergence:
        - Price Highs are Rising or Equal (High[curr] >= High[prev])
        - OBV Highs are Falling (OBV[curr] < OBV[prev])
        - Indicates top distribution (Smart money taking profit)

    Parameters:
        df: DataFrame containing ['High', 'Low', 'Close', 'OBV']
        order: Number of points on each side to use for the comparison in argrelextrema.
        max_lookback_bars: Maximum bar distance between two consecutive peaks/troughs to be considered a valid divergence.

    Returns:
        signals: List of divergence signal dictionaries
        low_extrema_idx: Array of indices for local lows (troughs)
        high_extrema_idx: Array of indices for local highs (peaks)
    """
    if len(df) < (order * 2 + 2):
        return [], np.array([]), np.array([])

    # Extract local troughs (lows) and peaks (highs)
    low_idx = argrelextrema(df["Low"].values, np.less_equal, order=order)[0]
    high_idx = argrelextrema(df["High"].values, np.greater_equal, order=order)[0]

    signals: List[Dict[str, Any]] = []

    # 1. Detect Bullish Divergences (Compare adjacent troughs)
    for i in range(1, len(low_idx)):
        prev_i = low_idx[i - 1]
        curr_i = low_idx[i]

        # Check if the two troughs are within reasonable bar distance
        if curr_i - prev_i > max_lookback_bars:
            continue

        prev_low_price = df["Low"].iloc[prev_i]
        curr_low_price = df["Low"].iloc[curr_i]

        prev_obv = df["OBV"].iloc[prev_i]
        curr_obv = df["OBV"].iloc[curr_i]

        # Condition: Price low is lower or equal, but OBV low is higher
        if curr_low_price <= prev_low_price and curr_obv > prev_obv:
            signals.append({
                "type": "BULLISH_DIVERGENCE",
                "date": df.index[curr_i],
                "price": df["Close"].iloc[curr_i],
                "low_price": curr_low_price,
                "obv": curr_obv,
                "prev_date": df.index[prev_i],
                "prev_price": prev_low_price,
                "prev_obv": prev_obv,
                "bar_index": curr_i,
                "prev_bar_index": prev_i,
                "message": f"★ 강세 다이버전스 (Bullish): 저점 하락({prev_low_price:,.0f} -> {curr_low_price:,.0f}) vs OBV 상승 -> 바닥권 매집 감지",
            })

    # 2. Detect Bearish Divergences (Compare adjacent peaks)
    for i in range(1, len(high_idx)):
        prev_i = high_idx[i - 1]
        curr_i = high_idx[i]

        if curr_i - prev_i > max_lookback_bars:
            continue

        prev_high_price = df["High"].iloc[prev_i]
        curr_high_price = df["High"].iloc[curr_i]

        prev_obv = df["OBV"].iloc[prev_i]
        curr_obv = df["OBV"].iloc[curr_i]

        # Condition: Price high is higher or equal, but OBV high is lower
        if curr_high_price >= prev_high_price and curr_obv < prev_obv:
            signals.append({
                "type": "BEARISH_DIVERGENCE",
                "date": df.index[curr_i],
                "price": df["Close"].iloc[curr_i],
                "high_price": curr_high_price,
                "obv": curr_obv,
                "prev_date": df.index[prev_i],
                "prev_price": prev_high_price,
                "prev_obv": prev_obv,
                "bar_index": curr_i,
                "prev_bar_index": prev_i,
                "message": f"⚠️ 약세 다이버전스 (Bearish): 고점 상승({prev_high_price:,.0f} -> {curr_high_price:,.0f}) vs OBV 하락 -> 고점 분산(차익실현) 경고",
            })

    # Sort all detected signals by date
    signals.sort(key=lambda s: s["date"])
    return signals, low_idx, high_idx
