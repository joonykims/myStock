import os
import webbrowser
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_stock_chart(
    df: pd.DataFrame,
    ticker: str,
    stock_name: str,
    signals: List[Dict[str, Any]],
    anchor_date: Optional[str] = None,
    output_html_path: str = "chart.html",
    auto_open: bool = False,
) -> str:
    """
    Generate an interactive Plotly chart with Candlestick, AVWAP, Volume, OBV, and Divergence Signals.

    Parameters:
        df: DataFrame with OHLCV and indicator columns
        ticker: Stock ticker
        stock_name: Stock display name
        signals: List of detected divergence signal dicts
        anchor_date: AVWAP anchor date string
        output_html_path: Output file path for HTML chart
        auto_open: Whether to automatically launch the default browser

    Returns:
        Absolute path to the created HTML file
    """
    # Create 3 subplots: Price (row 1, 60%), Volume (row 2, 15%), OBV (row 3, 25%)
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.60, 0.15, 0.25],
        subplot_titles=(
            f"{stock_name} ({ticker}) - 주가 & AVWAP & 다이버전스 시그널",
            "거래량 (Volume)",
            "OBV (On-Balance Volume) & OBV 20-EMA",
        ),
    )

    # 1. Price Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="주가 (OHLC)",
            increasing_line_color="#ef4444",  # Red for up (KR style)
            decreasing_line_color="#3b82f6",  # Blue for down (KR style)
        ),
        row=1,
        col=1,
    )

    # 2. AVWAP Line
    if "AVWAP" in df.columns and df["AVWAP"].notna().any():
        anchor_label = f"AVWAP (Anchor: {anchor_date})" if anchor_date else "AVWAP"
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["AVWAP"],
                mode="lines",
                name=anchor_label,
                line=dict(color="#f59e0b", width=2.5),
            ),
            row=1,
            col=1,
        )

    # 3. Simple Moving Averages
    if "SMA20" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["SMA20"],
                mode="lines",
                name="SMA 20",
                line=dict(color="#10b981", width=1.2, dash="dot"),
                opacity=0.7,
            ),
            row=1,
            col=1,
        )

    if "SMA60" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["SMA60"],
                mode="lines",
                name="SMA 60",
                line=dict(color="#8b5cf6", width=1.2, dash="dash"),
                opacity=0.7,
            ),
            row=1,
            col=1,
        )

    # 4. Divergence Signal Markers & Trend Lines on Price Subplot
    for s in signals:
        is_bull = s["type"] == "BULLISH_DIVERGENCE"
        color = "#22c55e" if is_bull else "#ef4444"
        symbol = "triangle-up" if is_bull else "triangle-down"
        label = "★ 강세 다이버전스 (매수)" if is_bull else "⚠️ 약세 다이버전스 (매도/경고)"

        # Signal Marker
        target_y = s["low_price"] * 0.985 if is_bull else s["high_price"] * 1.015
        fig.add_trace(
            go.Scatter(
                x=[s["date"]],
                y=[target_y],
                mode="markers+text",
                name=label,
                text=[label.split(" ")[0]],
                textposition="bottom center" if is_bull else "top center",
                marker=dict(
                    symbol=symbol,
                    size=14,
                    color=color,
                    line=dict(width=2, color="#ffffff"),
                ),
                hovertext=f"{s['message']}<br>날짜: {s['date'].strftime('%Y-%m-%d')}<br>종가: {s['price']:,.0f}",
                hoverinfo="text",
                showlegend=False,
            ),
            row=1,
            col=1,
        )

        # Draw connecting line between the two peaks / troughs
        fig.add_trace(
            go.Scatter(
                x=[s["prev_date"], s["date"]],
                y=[s["prev_price"], s["low_price"] if is_bull else s["high_price"]],
                mode="lines",
                line=dict(color=color, width=2, dash="dashdot"),
                hoverinfo="skip",
                showlegend=False,
            ),
            row=1,
            col=1,
        )

    # 5. Volume Bars (row 2)
    colors = np.where(df["Close"] >= df["Open"], "#ef4444", "#3b82f6")
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            name="거래량",
            marker_color=colors,
            opacity=0.7,
        ),
        row=2,
        col=1,
    )

    # 6. OBV & OBV EMA (row 3)
    if "OBV" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["OBV"],
                mode="lines",
                name="OBV",
                line=dict(color="#06b6d4", width=2),
            ),
            row=3,
            col=1,
        )

    if "OBV_EMA" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["OBV_EMA"],
                mode="lines",
                name="OBV EMA(20)",
                line=dict(color="#f97316", width=1.5, dash="dot"),
            ),
            row=3,
            col=1,
        )

    # Divergence connecting lines on OBV Subplot
    for s in signals:
        is_bull = s["type"] == "BULLISH_DIVERGENCE"
        color = "#22c55e" if is_bull else "#ef4444"
        fig.add_trace(
            go.Scatter(
                x=[s["prev_date"], s["date"]],
                y=[s["prev_obv"], s["obv"]],
                mode="lines+markers",
                line=dict(color=color, width=2, dash="dashdot"),
                marker=dict(size=6, color=color),
                hoverinfo="skip",
                showlegend=False,
            ),
            row=3,
            col=1,
        )

    # Update Layout
    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        margin=dict(l=40, r=40, t=50, b=40),
        height=850,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    # Hide weekend gaps on x-axis
    fig.update_xaxes(
        rangebreaks=[
            dict(bounds=["sat", "mon"]),  # hide weekends
        ]
    )

    abs_path = os.path.abspath(output_html_path)
    fig.write_html(abs_path)

    if auto_open:
        webbrowser.open(f"file:///{abs_path}")

    return abs_path
