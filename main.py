#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
myStock CLI - 주식 수급 지표 분석기 (AVWAP & OBV 다이버전스 감지)
"""

import argparse
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Ensure UTF-8 output encoding for Windows consoles
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


from mystock.data_loader import fetch_stock_data, get_stock_name
from mystock.indicators import calculate_indicators
from mystock.divergence import detect_obv_divergence
from mystock.visualizer import create_stock_chart

DEFAULT_SCAN_TICKERS = [
    # 국내 대형주
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "005380",  # 현대차
    "373220",  # LG에너지솔루션
    "035420",  # NAVER
    "035720",  # 카카오
    # 미국 주요 기술주 / ETF
    "NVDA",
    "AAPL",
    "MSFT",
    "TSLA",
    "QQQ",
    "SPY",
]


def analyze_stock(
    ticker: str,
    anchor_date: str = None,
    days: int = 365,
    order: int = 5,
    chart: bool = False,
    output_html: str = None,
    auto_open: bool = False,
) -> dict:
    """Analyze a single stock ticker."""
    stock_name = get_stock_name(ticker)
    print(f"\n=======================================================")
    print(f" 📊 [{stock_name}] 주식 수급 분석 보고서")
    print(f"=======================================================")

    try:
        df = fetch_stock_data(ticker=ticker, days=days)
    except Exception as e:
        print(f"❌ 데이터 수집 실패: {e}")
        return {}

    if df.empty:
        print("❌ 조회된 데이터가 없습니다.")
        return {}

    # Anchor date default: Start of current year if not specified
    if anchor_date is None:
        anchor_date = f"{datetime.now().year}-01-02"

    # Compute indicators
    df_ind = calculate_indicators(df, anchor_date=anchor_date)

    # Detect divergences
    signals, low_idx, high_idx = detect_obv_divergence(df_ind, order=order)

    # Latest price & AVWAP summary
    latest = df_ind.iloc[-1]
    latest_date = df_ind.index[-1].strftime("%Y-%m-%d")
    latest_close = latest["Close"]
    latest_avwap = latest["AVWAP"]
    latest_obv = latest["OBV"]
    latest_obv_ema = latest["OBV_EMA"]

    avwap_diff_pct = ((latest_close - latest_avwap) / latest_avwap * 100) if pd.notna(latest_avwap) else 0

    print(f"• 기준일자 (최신): {latest_date}")
    print(f"• 현재 종가: {latest_close:,.2f}원/달러")
    if pd.notna(latest_avwap):
        print(f"• 에이브이왑 (AVWAP, 앵커 {anchor_date}~): {latest_avwap:,.2f} (괴리율: {avwap_diff_pct:+.2f}%)")
        if avwap_diff_pct > 0:
            print(f"  └ 📈 주가가 AVWAP 상단에 위치: 매수 주도권 유지 중 (지지선 역할 기대)")
        else:
            print(f"  └ 📉 주가가 AVWAP 하단에 위치: 매도세 우위 (저항선 역할 주의)")
    
    print(f"• OBV: {latest_obv:,.0f} (20-EMA: {latest_obv_ema:,.0f})")
    if latest_obv > latest_obv_ema:
        print(f"  └ 🟢 OBV > EMA20: 단기 수급 유입 우세")
    else:
        print(f"  └ 🔴 OBV < EMA20: 단기 수급 이탈 우세")

    print(f"\n[다이버전스 시그널 분석 내역 (최근 {days}일)]")
    if signals:
        print(f"총 {len(signals)}건의 신호가 포착되었습니다:")
        for s in signals:
            sig_date = s["date"].strftime("%Y-%m-%d")
            sig_type = s["type"]
            msg = s["message"]
            print(f" - [{sig_date}] {msg}")
    else:
        print(" -> 최근 유의미한 다이버전스(극값 불일치) 신호가 발생하지 않았습니다.")

    # Generate Chart if requested
    chart_path = None
    if chart:
        if output_html is None:
            clean_name = ticker.replace(":", "_").replace(".", "_")
            output_html = f"chart_{clean_name}.html"
        chart_path = create_stock_chart(
            df_ind,
            ticker=ticker,
            stock_name=stock_name,
            signals=signals,
            anchor_date=anchor_date,
            output_html_path=output_html,
            auto_open=auto_open,
        )
        print(f"\n✨ 인터랙티브 차트가 생성되었습니다: {chart_path}")

    return {
        "ticker": ticker,
        "name": stock_name,
        "date": latest_date,
        "close": latest_close,
        "avwap": latest_avwap,
        "avwap_diff_pct": avwap_diff_pct,
        "obv": latest_obv,
        "signals_count": len(signals),
        "latest_signal": signals[-1] if signals else None,
        "chart_path": chart_path,
    }


def scan_market(
    tickers: list = None,
    anchor_date: str = None,
    days: int = 365,
    order: int = 5,
):
    """Scan a list of stocks for recent divergence signals and AVWAP status."""
    if tickers is None or len(tickers) == 0:
        tickers = DEFAULT_SCAN_TICKERS

    print(f"\n🔍 [관심 종목 일괄 스캐너] {len(tickers)}개 종목 분석 중...\n")

    results = []
    for t in tickers:
        try:
            stock_name = get_stock_name(t)
            df = fetch_stock_data(t, days=days)
            if df.empty:
                continue

            if anchor_date is None:
                anchor_date = f"{datetime.now().year}-01-02"

            df_ind = calculate_indicators(df, anchor_date=anchor_date)
            signals, _, _ = detect_obv_divergence(df_ind, order=order)

            latest = df_ind.iloc[-1]
            close = latest["Close"]
            avwap = latest["AVWAP"]
            diff = ((close - avwap) / avwap * 100) if pd.notna(avwap) else 0

            # Filter for recent signals within 30 days
            recent_signal = None
            if signals:
                last_sig = signals[-1]
                days_ago = (df_ind.index[-1] - last_sig["date"]).days
                if days_ago <= 30:
                    recent_signal = f"{last_sig['type'][:4]} ({days_ago}일전)"

            results.append({
                "종목": stock_name,
                "현재가": f"{close:,.1f}",
                "AVWAP": f"{avwap:,.1f}" if pd.notna(avwap) else "N/A",
                "이격률": f"{diff:+.1f}%",
                "최근 시그널 (30일내)": recent_signal if recent_signal else "-",
            })
        except Exception as e:
            print(f"[스캔 건너뜀] {t}: {e}")

    if results:
        res_df = pd.DataFrame(results)
        print("==========================================================================")
        print("                         📋 시장 수급 스캔 결과")
        print("==========================================================================")
        print(res_df.to_string(index=False))
        print("==========================================================================")
    else:
        print("스캔 결과가 없습니다.")


def main():
    parser = argparse.ArgumentParser(
        description="myStock - AVWAP 및 OBV 다이버전스 주식 수급 분석 시스템"
    )
    parser.add_argument(
        "-t", "--ticker",
        type=str,
        default="005930",
        help="분석할 종목 코드 또는 티커 (기본값: 005930 삼성전자, 예: 000660, NVDA, AAPL)",
    )
    parser.add_argument(
        "-a", "--anchor",
        type=str,
        default=None,
        help="AVWAP 앵커 기준일 (YYYY-MM-DD, 기본값: 당해년도 1월 2일)",
    )
    parser.add_argument(
        "-d", "--days",
        type=int,
        default=365,
        help="데이터 조회 기간(일 단위, 기본값: 365)",
    )
    parser.add_argument(
        "-o", "--order",
        type=int,
        default=5,
        help="극값 탐색 윈도우 크기 (기본값: 5)",
    )
    parser.add_argument(
        "-c", "--chart",
        action="store_true",
        help="인터랙티브 Plotly HTML 차트 생성",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="차트 생성 후 기본 웹 브라우저에서 자동 열기",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="차트 HTML 저장 파일명 (예: result.html)",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="주요 관심 종목(국내 대형주 + 미국 빅테크) 일괄 스캔 모드 실행",
    )
    parser.add_argument(
        "-w", "--web", "--dashboard",
        dest="dashboard",
        action="store_true",
        help="웹 브라우저에서 인터랙티브 대시보드 (Streamlit) 실행",
    )

    args = parser.parse_args()


    if args.dashboard:
        import subprocess
        print("🚀 [myStock] 웹 대시보드(Streamlit)를 시작합니다...")
        app_path = os.path.join(os.path.dirname(__file__), "app.py")
        subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])
    elif args.scan:
        scan_market(anchor_date=args.anchor, days=args.days, order=args.order)
    else:
        analyze_stock(
            ticker=args.ticker,
            anchor_date=args.anchor,
            days=args.days,
            order=args.order,
            chart=args.chart,
            output_html=args.out,
            auto_open=args.open,
        )


if __name__ == "__main__":
    main()

