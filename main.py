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
from mystock.watchlist import load_watchlist, get_all_tickers


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

    if df is None or df.empty:
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
    group: str = None,
    anchor_date: str = None,
    days: int = 365,
    order: int = 5,
):
    """Scan a list of stocks for recent divergence signals and AVWAP status."""
    watchlist = load_watchlist()

    target_items = []
    if tickers:
        for t in tickers:
            target_items.append({"ticker": t, "name": get_stock_name(t), "category": "사용자지정", "anchor": anchor_date})
    elif group:
        items = watchlist.get(group, [])
        for it in items:
            t = it["ticker"] if isinstance(it, dict) else str(it)
            n = it.get("name", t) if isinstance(it, dict) else t
            a = it.get("anchor", anchor_date) if isinstance(it, dict) else anchor_date
            target_items.append({"ticker": t, "name": n, "category": group, "anchor": a})
    else:
        target_items = get_all_tickers()

    group_title = f" [{group}]" if group else ""
    print(f"\n🔍 [관심 종목 일괄 스캐너]{group_title} {len(target_items)}개 종목 분석 중...\n")

    results = []
    default_anchor = anchor_date or f"{datetime.now().year}-01-02"

    for item in target_items:
        t = item["ticker"]
        name = item.get("name") or get_stock_name(t)
        cat = item.get("category", "")
        item_anchor = item.get("anchor") or default_anchor

        try:
            df = fetch_stock_data(t, days=days)
            if df is None or df.empty:
                continue

            df_ind = calculate_indicators(df, anchor_date=item_anchor)
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
                    sig_name = "BULL(강세)" if last_sig["type"] == "BULLISH_DIVERGENCE" else "BEAR(약세)"
                    recent_signal = f"{sig_name} ({days_ago}일전)"

            results.append({
                "구분": cat if cat else "-",
                "종목": name,
                "티커": t,
                "현재가": f"{close:,.1f}",
                "AVWAP": f"{avwap:,.1f}" if pd.notna(avwap) else "N/A",
                "이격률": f"{diff:+.1f}%",
                "최근 시그널 (30일내)": recent_signal if recent_signal else "-",
            })
        except Exception as e:
            print(f"[스캔 건너뜀] {t}: {e}")

    if results:
        res_df = pd.DataFrame(results)
        print("==========================================================================================")
        print(f"                         📋 시장 수급 스캔 결과{group_title}")
        print("==========================================================================================")
        print(res_df.to_string(index=False))
        print("==========================================================================================")
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
        "-g", "--group",
        type=str,
        default=None,
        help="분석/스캔할 종목 그룹 (예: 보유종목, 초관심종목, 관심종목)",
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
        help="관심 종목 일괄 스캔 모드 실행 (watchlist.json 기반)",
    )
    parser.add_argument(
        "-w", "--web", "--dashboard",
        dest="dashboard",
        action="store_true",
        help="웹 브라우저에서 인터랙티브 대시보드 (Streamlit) 실행",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="전체 종목 스캔 후 텔레그램/슬랙/디스코드 웹훅 알림 1회 즉시 발송",
    )
    parser.add_argument(
        "--test-notify",
        action="store_true",
        help="설정된 텔레그램/슬랙/디스코드 메신저로 테스트 메시지 1회 발송",
    )
    parser.add_argument(
        "--scheduler",
        action="store_true",
        help="장 마감 시간별(국내 15:45, 미국 06:30) 자동 알림 백그라운드 스케줄러 실행",
    )

    args = parser.parse_args()

    if args.dashboard:
        import subprocess
        print("🚀 [myStock] 웹 대시보드(Streamlit)를 시작합니다...")
        app_path = os.path.join(os.path.dirname(__file__), "app.py")
        subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])
    elif args.test_notify:
        from mystock.notifier import NotificationManager
        mgr = NotificationManager()
        test_msg = "🔔 [myStock] 텔레그램 봇 연동 테스트 메시지입니다.\n알림 설정이 정상적으로 완료되었습니다! 🎉"
        print("📡 테스트 메시지 발송 중...")
        res = mgr.broadcast(test_msg)
        print(f"결과: {res}")
    elif args.notify:
        from scheduler import run_scan_and_notify
        run_scan_and_notify(group=args.group, anchor_date=args.anchor)
    elif args.scheduler:
        from scheduler import start_scheduler_loop
        start_scheduler_loop()
    elif args.scan:
        scan_market(group=args.group, anchor_date=args.anchor, days=args.days, order=args.order)
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
