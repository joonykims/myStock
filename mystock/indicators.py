import pandas as pd
import numpy as np
from typing import Optional, Union


def calculate_typical_price(df: pd.DataFrame) -> pd.Series:
    """Calculate Representative / Typical Price: (High + Low + Close) / 3."""
    return (df["High"] + df["Low"] + df["Close"]) / 3.0


def calculate_avwap(
    df: pd.DataFrame,
    anchor_date: Optional[Union[str, pd.Timestamp]] = None,
) -> pd.Series:
    """
    Calculate Anchored VWAP (Volume-Weighted Average Price) starting from anchor_date.

    Parameters:
        df: DataFrame with ['High', 'Low', 'Close', 'Volume']
        anchor_date: Anchor point date ('YYYY-MM-DD'). If None, defaults to the start of the data.

    Returns:
        pd.Series containing the AVWAP values (NaN before anchor_date).
    """
    tp = calculate_typical_price(df)
    tp_volume = tp * df["Volume"]

    avwap = pd.Series(index=df.index, dtype="float64")

    if anchor_date is None:
        anchor_dt = df.index[0]
    else:
        anchor_dt = pd.to_datetime(anchor_date)

    # Filter rows on or after anchor date
    mask = df.index >= anchor_dt
    if not mask.any():
        # If anchor date is after the dataset, anchor at the earliest available bar
        mask = df.index >= df.index[0]

    cum_tp_vol = tp_volume[mask].cumsum()
    cum_vol = df.loc[mask, "Volume"].cumsum()

    # Avoid division by zero
    cum_vol_safe = cum_vol.replace(0, np.nan)
    avwap_values = cum_tp_vol / cum_vol_safe

    avwap.loc[mask] = avwap_values
    return avwap


def calculate_obv(
    df: pd.DataFrame,
    ema_span: int = 20,
) -> pd.DataFrame:
    """
    Calculate On-Balance Volume (OBV) and its EMA signal line.

    OBV Formula:
        If Close[t] > Close[t-1]: OBV[t] = OBV[t-1] + Volume[t]
        If Close[t] < Close[t-1]: OBV[t] = OBV[t-1] - Volume[t]
        If Close[t] == Close[t-1]: OBV[t] = OBV[t-1]

    Parameters:
        df: DataFrame with ['Close', 'Volume']
        ema_span: Period for the OBV exponential moving average (default 20)

    Returns:
        pd.DataFrame with ['OBV', 'OBV_EMA']
    """
    close_diff = df["Close"].diff()
    direction = np.sign(close_diff).fillna(0)
    # First row has no diff, direction is 0
    signed_vol = direction * df["Volume"]
    obv = signed_vol.cumsum()
    obv_ema = obv.ewm(span=ema_span, adjust=False).mean()

    return pd.DataFrame({"OBV": obv, "OBV_EMA": obv_ema}, index=df.index)


def calculate_indicators(
    df: pd.DataFrame,
    anchor_date: Optional[Union[str, pd.Timestamp]] = None,
    obv_ema_span: int = 20,
) -> pd.DataFrame:
    """
    Calculate full technical indicator suite: Typical Price, AVWAP, OBV, OBV_EMA, SMA20, SMA60.

    Parameters:
        df: DataFrame with OHLCV data
        anchor_date: Anchor point for AVWAP
        obv_ema_span: Span for OBV EMA signal line

    Returns:
        pd.DataFrame with original columns + indicators
    """
    result = df.copy()
    result["Typical_Price"] = calculate_typical_price(result)
    result["AVWAP"] = calculate_avwap(result, anchor_date=anchor_date)

    obv_df = calculate_obv(result, ema_span=obv_ema_span)
    result["OBV"] = obv_df["OBV"]
    result["OBV_EMA"] = obv_df["OBV_EMA"]

    # Moving averages for context
    result["SMA20"] = result["Close"].rolling(window=20).mean()
    result["SMA60"] = result["Close"].rolling(window=60).mean()

    return result
