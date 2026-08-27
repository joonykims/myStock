#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
myStock 자동 스케줄러 & 알림 발송 엔진
- 국내장 마감 (매주 월~금 15:45 KST)
- 미국장 마감 (매주 화~토 06:30 KST)
"""

import sys
import os
import time
import argparse
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


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
from mystock.notifier import NotificationManager

DEFAULT_TICKERS = [
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


def run_scan_and_notify(
    tickers: list = None,
    anchor_date: str = None,
    signal_lookback_days: int = 7,
    title: str = "📈 [myStock] 수급 신호 감지 알림",
) -> list:
    """Scan market tickers and send notification if recent divergence signals are detected."""
    if tickers is None or len(tickers) == 0:
        tickers = DEFAULT_TICKERS

    if anchor_date is None:
        anchor_date = f"{datetime.now().year}-01-02"

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔍 시장 수급 스캔 및 알림 검사 시작 ({len(tickers)}개 종목)...")

    alert_items = []
    for t in tickers:
        try:
            name = get_stock_name(t)
            df = fetch_stock_data(t, days=365)
            if df is None or df.empty:
                continue

            df_ind = calculate_indicators(df, anchor_date=anchor_date)
            signals, _, _ = detect_obv_divergence(df_ind, order=5)

            cur = df_ind.iloc[-1]
            p_close = cur["Close"]
            p_avwap = cur["AVWAP"]
            diff = ((p_close - p_avwap) / p_avwap * 100) if pd.notna(p_avwap) else 0

            # Filter for recent signals within signal_lookback_days
            if signals:
                for s in signals:
                    days_ago = (df_ind.index[-1] - s["date"]).days
                    if days_ago <= signal_lookback_days:
                        sig_type_kor = "★ 강세 다이버전스 (스마트머니 매집)" if s["type"] == "BULLISH_DIVERGENCE" else "⚠️ 약세 다이버전스 (고점 분산/차익실현)"
                        alert_items.append({
                            "stock": f"{name} ({t})",
                            "price": f"{p_close:,.2f}",
                            "avwap": f"{p_avwap:,.2f}" if pd.notna(p_avwap) else "N/A",
                            "diff": f"{diff:+.1f}%",
                            "sig_type": sig_type_kor,
                            "date": f"{s['date'].strftime('%Y-%m-%d')} ({days_ago}일전)",
                            "message": s["message"],
                        })
        except Exception as e:
            print(f"[스캔 오류] {t}: {e}")

    # Broadcast notification
    notifier = NotificationManager()
    msg = notifier.format_scan_report(alert_items, title=title)
    print("\n--- [발송 메시지 미리보기] ---")
    print(msg)
    print("------------------------------\n")

    results = notifier.broadcast(msg)
    print(f"📡 알림 발송 결과: {results}")
    return alert_items


def start_scheduler_loop():
    """Continuous scheduler loop checking for scheduled times."""
    print("=" * 60)
    print("⏰ [myStock] 자동 알림 스케줄러가 백그라운드에서 시작되었습니다.")
    print("• 국내장 알림: 매주 월~금 15:45 KST")
    print("• 미국장 알림: 매주 화~토 06:30 KST")
    print("• 종료하려면 Ctrl + C를 누르세요.")
    print("=" * 60)

    last_kr_run_day = -1
    last_us_run_day = -1

    while True:
        now = datetime.now()
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        hour = now.hour
        minute = now.minute

        # 1. 국내장 마감 스캔: 월~금(0~4) 15:45
        if weekday in range(0, 5) and hour == 15 and minute >= 45 and last_kr_run_day != now.day:
            print(f"\n[스케줄러 트리거] 국내장 마감 정기 알림 실행 ({now.strftime('%Y-%m-%d %H:%M')})")
            kr_tickers = ["005930", "000660", "005380", "373220", "035420", "035720"]
            run_scan_and_notify(
                tickers=kr_tickers,
                signal_lookback_days=3,
                title="📈 [myStock] 국내장 마감 수급 & 다이버전스 알림",
            )
            last_kr_run_day = now.day

        # 2. 미국장 마감 스캔: 화~토(1~5) 06:30
        if weekday in range(1, 6) and hour == 6 and minute >= 30 and last_us_run_day != now.day:
            print(f"\n[스케줄러 트리거] 미국장 마감 정기 알림 실행 ({now.strftime('%Y-%m-%d %H:%M')})")
            us_tickers = ["NVDA", "AAPL", "MSFT", "TSLA", "QQQ", "SPY"]
            run_scan_and_notify(
                tickers=us_tickers,
                signal_lookback_days=3,
                title="📈 [myStock] 미국장 마감 수급 & 다이버전스 알림",
            )
            last_us_run_day = now.day

        time.sleep(30)


def main():
    parser = argparse.ArgumentParser(description="myStock 자동 스케줄러 및 알림 발송")
    parser.add_argument(
        "--now",
        action="store_true",
        help="스케줄 대기 없이 지금 즉시 전체 종목 스캔 및 알림 발송 1회 실행",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="신호 탐색 기간 (최근 n일 이내 발생 신호, 기본값: 7일)",
    )

    args = parser.parse_args()

    if args.now:
        run_scan_and_notify(signal_lookback_days=args.days)
    else:
        try:
            start_scheduler_loop()
        except KeyboardInterrupt:
            print("\n👋 스케줄러가 종료되었습니다.")


if __name__ == "__main__":
    import pandas as pd
    main()
