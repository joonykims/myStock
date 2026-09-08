"""
mystock/scanner.py
──────────────────
이광수식 지수 역행 주도주 스캐너 엔진 (Relative Strength & Leading Stocks Scanner)

핵심 원칙:
1. 지수 하락장 속 상대 강도(RS) 포착: 지수가 하락/급락할 때 버티거나 양봉 마감
2. 거래대금/거래량 동반 폭발: 스마트 머니 유입 확인 (단기 테마/품절주 배제)
3. AVWAP 수급 지지선 위 위치: 메이저 자금의 평단가 위에서 가격 유지
4. 5종목 이내 압축 & 기계적 손절선(-10%) 및 트레이딩 플랜 자동 산출
"""

import datetime
from typing import List, Dict, Optional, Any
import numpy as np
import pandas as pd

from .data_loader import fetch_stock_data, get_stock_name, is_korean_ticker
from .indicators import calculate_indicators
from .universe import get_universe_items


def get_default_benchmark_ticker(ticker: str) -> str:
    """Return appropriate market benchmark index ticker for a given stock ticker."""
    clean = ticker.strip().upper()
    if is_korean_ticker(clean):
        if clean.endswith(".KQ"):
            return "^KQ11"  # 코스닥 지수
        return "^KS11"     # 코스피 지수
    return "SPY"          # 미국 S&P 500 ETF


def evaluate_stock_leader(
    df_stock: pd.DataFrame,
    df_bench: pd.DataFrame,
    anchor_date: Optional[str] = None,
    target_date: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Evaluate single stock against market benchmark using Lee Kwang-soo's principles.
    
    Returns structured analysis dict with RS spread, volume surge, candle pattern,
    AVWAP positioning, composite score (0-100), and trading plan.
    """
    if df_stock is None or df_stock.empty or len(df_stock) < 5:
        return None
    if df_bench is None or df_bench.empty or len(df_bench) < 5:
        return None

    # Determine anchor date (default: start of year)
    if anchor_date is None:
        anchor_date = f"{datetime.datetime.now().year}-01-02"

    # Calculate indicators (including AVWAP)
    df_ind = calculate_indicators(df_stock, anchor_date=anchor_date)
    if df_ind.empty:
        return None

    # Target date evaluation (latest if None)
    if target_date is not None:
        tgt_dt = pd.to_datetime(target_date)
        stock_matched = df_ind[df_ind.index <= tgt_dt]
        bench_matched = df_bench[df_bench.index <= tgt_dt]
    else:
        stock_matched = df_ind
        bench_matched = df_bench

    if stock_matched.empty or bench_matched.empty:
        return None

    # Find common latest trading date
    common_dates = stock_matched.index.intersection(bench_matched.index)
    if len(common_dates) < 2:
        eval_date = stock_matched.index[-1]
        bench_eval_date = bench_matched.index[-1]
    else:
        eval_date = common_dates[-1]
        bench_eval_date = eval_date

    stock_row = stock_matched.loc[eval_date]
    if isinstance(stock_row, pd.DataFrame):
        stock_row = stock_row.iloc[-1]

    bench_row = bench_matched.loc[bench_eval_date]
    if isinstance(bench_row, pd.DataFrame):
        bench_row = bench_row.iloc[-1]

    # Prior day rows for daily change calculation
    stock_idx_loc = stock_matched.index.get_loc(eval_date)
    if isinstance(stock_idx_loc, slice):
        stock_idx_loc = stock_idx_loc.stop - 1
    elif isinstance(stock_idx_loc, np.ndarray):
        stock_idx_loc = np.where(stock_idx_loc)[0][-1]

    if stock_idx_loc < 1:
        return None
    prev_stock_row = stock_matched.iloc[stock_idx_loc - 1]

    bench_idx_loc = bench_matched.index.get_loc(bench_eval_date)
    if isinstance(bench_idx_loc, slice):
        bench_idx_loc = bench_idx_loc.stop - 1
    elif isinstance(bench_idx_loc, np.ndarray):
        bench_idx_loc = np.where(bench_idx_loc)[0][-1]

    if bench_idx_loc < 1:
        bench_change_pct = 0.0
    else:
        prev_bench_row = bench_matched.iloc[bench_idx_loc - 1]
        bench_change_pct = float((bench_row["Close"] - prev_bench_row["Close"]) / prev_bench_row["Close"] * 100)

    # 1. Price metrics
    close_p = float(stock_row["Close"])
    open_p = float(stock_row["Open"])
    prev_close_p = float(prev_stock_row["Close"])
    vol = float(stock_row["Volume"])

    stock_change_pct = float((close_p - prev_close_p) / prev_close_p * 100) if prev_close_p > 0 else 0.0
    candle_pct = float((close_p - open_p) / open_p * 100) if open_p > 0 else 0.0
    is_yangbong = bool(close_p >= open_p)

    # 2. Volume & Liquidity (20-day MA volume)
    hist_window = stock_matched.iloc[max(0, stock_idx_loc - 20):stock_idx_loc]
    vol_20_ma = float(hist_window["Volume"].mean()) if not hist_window.empty else vol
    vol_ratio = float(vol / vol_20_ma) if vol_20_ma > 0 else 1.0
    trading_value_est = close_p * vol

    # 3. Relative Strength (RS)
    rs_spread = float(stock_change_pct - bench_change_pct)
    is_counter_trend = bool(bench_change_pct < 0 and (stock_change_pct >= 0 or is_yangbong))
    is_outperforming = bool(rs_spread > 0)

    # 4. AVWAP Positioning
    avwap_val = float(stock_row["AVWAP"]) if pd.notna(stock_row.get("AVWAP")) else None
    if avwap_val is not None and avwap_val > 0:
        avwap_diff_pct = float((close_p - avwap_val) / avwap_val * 100)
        above_avwap = bool(close_p >= avwap_val)
    else:
        avwap_diff_pct = 0.0
        above_avwap = False

    # 5. Composite Score Calculation (0 ~ 100)
    score = 0.0

    # (1) Relative Strength spread (max 40 pts)
    if rs_spread >= 4.0:
        score += 40.0
    elif rs_spread >= 2.5:
        score += 35.0
    elif rs_spread >= 1.0:
        score += 28.0
    elif rs_spread >= 0.0:
        score += 20.0
    elif rs_spread >= -1.5:
        score += 10.0

    # Extra bonus for pure counter-trend (market fell, but stock stayed green or positive)
    if is_counter_trend:
        score += 5.0

    # (2) Candlestick strength (max 20 pts)
    if candle_pct >= 2.0:
        score += 20.0
    elif candle_pct >= 0.5:
        score += 17.0
    elif is_yangbong:
        score += 14.0
    elif candle_pct >= -1.0:
        score += 5.0

    # (3) Volume Surge (max 25 pts)
    if vol_ratio >= 2.5:
        score += 25.0
    elif vol_ratio >= 1.8:
        score += 22.0
    elif vol_ratio >= 1.3:
        score += 18.0
    elif vol_ratio >= 1.0:
        score += 12.0
    else:
        score += 5.0

    # (4) AVWAP support (max 15 pts)
    if above_avwap:
        if 0.0 <= avwap_diff_pct <= 10.0:
            score += 15.0  # Ideal support zone
        elif avwap_diff_pct > 10.0:
            score += 11.0  # Strong trend but slightly extended
        else:
            score += 10.0
    else:
        if -5.0 <= avwap_diff_pct < 0.0:
            score += 6.0   # Near reclaim
        else:
            score += 1.0

    score = min(100.0, max(0.0, score))

    # Grade
    if score >= 85.0:
        grade = "S (초강력 주도주)"
        grade_badge = "🌟 S"
    elif score >= 70.0:
        grade = "A (우량 주도주)"
        grade_badge = "🟢 A"
    elif score >= 55.0:
        grade = "B (관심 관찰)"
        grade_badge = "🟡 B"
    else:
        grade = "C/D (관망)"
        grade_badge = "⚪ C"

    # 6. Trading Plan (투자 노트 가이드)
    stop_loss_price = close_p * 0.90  # 기계적 -10% 손절 원칙
    # Round stop loss price cleanly
    if stop_loss_price >= 1000:
        stop_loss_price = round(stop_loss_price, -1)
    else:
        stop_loss_price = round(stop_loss_price, 2)

    # Narrative rationale
    reasons = []
    if is_counter_trend:
        reasons.append(f"지수 하락({bench_change_pct:+.2f}%) 속 역행 양봉 마감")
    elif is_outperforming:
        reasons.append(f"지수 대비 +{rs_spread:+.2f}%p 초과 상승")

    if vol_ratio >= 1.5:
        reasons.append(f"20일 평균 대비 거래량 {vol_ratio:.1f}배 급증")

    if above_avwap:
        reasons.append(f"세력 평단가(AVWAP) 상단 안착 (+{avwap_diff_pct:.1f}%)")

    return {
        "date": eval_date.strftime("%Y-%m-%d"),
        "close": close_p,
        "open": open_p,
        "stock_change_pct": stock_change_pct,
        "candle_pct": candle_pct,
        "is_yangbong": is_yangbong,
        "volume": vol,
        "vol_20_ma": vol_20_ma,
        "vol_ratio": vol_ratio,
        "trading_value_est": trading_value_est,
        "bench_date": bench_eval_date.strftime("%Y-%m-%d"),
        "bench_close": float(bench_row["Close"]),
        "bench_change_pct": bench_change_pct,
        "rs_spread": rs_spread,
        "is_counter_trend": is_counter_trend,
        "is_outperforming": is_outperforming,
        "avwap": avwap_val,
        "avwap_diff_pct": avwap_diff_pct,
        "above_avwap": above_avwap,
        "score": round(score, 1),
        "grade": grade,
        "grade_badge": grade_badge,
        "stop_loss_price": stop_loss_price,
        "rationale": " / ".join(reasons) if reasons else "기준 충족",
    }


def scan_market_leaders(
    universe_type: str = "korea",
    custom_tickers: Optional[List[Dict[str, Any]]] = None,
    benchmark_ticker: Optional[str] = None,
    anchor_date: Optional[str] = None,
    target_date: Optional[str] = None,
    min_score: float = 50.0,
    days: int = 120,
) -> Dict[str, Any]:
    """
    Run full market leading stock scan based on Lee Kwang-soo's principles.
    
    Args:
        universe_type: 'korea', 'us', 'all', or 'custom'
        custom_tickers: list of item dicts with at least 'ticker' key
        benchmark_ticker: index benchmark symbol (e.g. '^KS11', 'SPY')
        anchor_date: AVWAP anchor date (YYYY-MM-DD)
        target_date: evaluation date (YYYY-MM-DD, defaults to latest)
        min_score: minimum score filter (0-100)
        days: lookback days for data fetch
    
    Returns:
        Dict with 'benchmark_info', 'results' (sorted list), 'summary'
    """
    # 1. Resolve Universe items
    if custom_tickers:
        items = custom_tickers
    else:
        items = get_universe_items(universe_type)

    if not items:
        return {"benchmark_info": {}, "results": [], "summary": "스캔할 대상 종목이 없습니다."}

    # 2. Determine Benchmark Ticker
    first_ticker = items[0]["ticker"] if isinstance(items[0], dict) else str(items[0])
    if benchmark_ticker is None:
        benchmark_ticker = get_default_benchmark_ticker(first_ticker)

    # 3. Fetch Benchmark OHLCV
    bench_df = fetch_stock_data(benchmark_ticker, days=days)
    if bench_df is None or bench_df.empty:
        # Fallback to KOSPI or SPY
        fallback_bench = "^KS11" if is_korean_ticker(first_ticker) else "SPY"
        bench_df = fetch_stock_data(fallback_bench, days=days)
        benchmark_ticker = fallback_bench

    bench_info = {}
    if bench_df is not None and not bench_df.empty:
        latest_b_idx = bench_df.index[-1]
        latest_b_close = float(bench_df.iloc[-1]["Close"])
        prev_b_close = float(bench_df.iloc[-2]["Close"]) if len(bench_df) > 1 else latest_b_close
        b_chg = float((latest_b_close - prev_b_close) / prev_b_close * 100) if prev_b_close > 0 else 0.0
        bench_info = {
            "ticker": benchmark_ticker,
            "date": latest_b_idx.strftime("%Y-%m-%d"),
            "close": latest_b_close,
            "change_pct": b_chg,
            "is_down": bool(b_chg < 0),
            "is_crash": bool(b_chg <= -1.0),  # 지수 -1% 이상 급락 여부
        }

    # 4. Evaluate each stock in universe
    evaluated_results = []
    for item in items:
        t = item["ticker"] if isinstance(item, dict) else str(item)
        name = item.get("name") if isinstance(item, dict) else get_stock_name(t)
        sector = item.get("sector", "") if isinstance(item, dict) else ""
        item_anchor = item.get("anchor") or anchor_date

        try:
            df_stock = fetch_stock_data(t, days=days)
            if df_stock is None or df_stock.empty:
                continue

            eval_res = evaluate_stock_leader(
                df_stock=df_stock,
                df_bench=bench_df,
                anchor_date=item_anchor,
                target_date=target_date,
            )
            if eval_res and eval_res["score"] >= min_score:
                eval_res["ticker"] = t
                eval_res["name"] = name
                eval_res["sector"] = sector
                evaluated_results.append(eval_res)
        except Exception:
            continue

    # 5. Sort by Composite Score descending
    evaluated_results.sort(key=lambda x: x["score"], reverse=True)

    summary_text = (
        f"총 {len(items)}개 종목 중 {len(evaluated_results)}개 종목이 "
        f"주도주 기준(최소 {min_score}점)을 충족했습니다."
    )

    return {
        "benchmark_info": bench_info,
        "results": evaluated_results,
        "summary": summary_text,
    }
