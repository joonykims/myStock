import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from mystock.data_loader import fetch_stock_data, get_stock_name
from mystock.indicators import calculate_indicators
from mystock.divergence import detect_obv_divergence
from mystock.visualizer import create_stock_figure

# 1. Page Configuration
st.set_page_config(
    page_title="myStock - 수급 지표 & 다이버전스 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #334155;
        margin-bottom: 12px;
    }
    .metric-title {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .metric-sub {
        font-size: 0.8rem;
        font-weight: 500;
    }
    .badge-bull {
        background-color: #065f46;
        color: #34d399;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-bear {
        background-color: #881337;
        color: #fb7185;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# 2. Sidebar - Inputs & Controls
st.sidebar.title("📈 myStock 분석 설정")

POPULAR_STOCKS = {
    "삼성전자 (005930)": "005930",
    "SK하이닉스 (000660)": "000660",
    "현대차 (005380)": "005380",
    "LG에너지솔루션 (373220)": "373220",
    "NAVER (035420)": "035420",
    "카카오 (035720)": "035720",
    "엔비디아 (NVDA)": "NVDA",
    "애플 (AAPL)": "AAPL",
    "마이크로소프트 (MSFT)": "MSFT",
    "테슬라 (TSLA)": "TSLA",
    "나스닥 100 ETF (QQQ)": "QQQ",
    "S&P 500 ETF (SPY)": "SPY",
}

stock_choice = st.sidebar.selectbox(
    "인기 종목 빠른 선택",
    options=["직접 입력"] + list(POPULAR_STOCKS.keys()),
    index=1,
)

if stock_choice == "직접 입력":
    ticker = st.sidebar.text_input("종목 코드 / 티커 입력", value="005930", help="국내 6자리 종목코드 또는 미국 티커")
else:
    ticker = POPULAR_STOCKS[stock_choice]

# Date & Lookback controls
col_d1, col_d2 = st.sidebar.columns(2)
with col_d1:
    default_anchor = datetime(datetime.now().year, 1, 2).date()
    anchor_date = st.date_input(
        "AVWAP 앵커 기준일",
        value=default_anchor,
        help="기관/세력의 누적 매입 단가를 계산할 시작일",
    )
with col_d2:
    days_lookback = st.selectbox(
        "데이터 조회 기간",
        options=[180, 365, 730, 1095],
        index=1,
        format_func=lambda x: f"{x}일 ({x//365}년)" if x >= 365 else f"{x}일",
    )

order_param = st.sidebar.slider(
    "다이버전스 탐색 윈도우 (Order)",
    min_value=3,
    max_value=15,
    value=5,
    help="국소 극값(고점/저점)을 판별하기 위한 좌우 봉 개수",
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**💡 빠른 도움말**\n"
    "- **AVWAP**: 특정 이벤트/기준일 이후 누적된 자금의 실제 평균 단가\n"
    "- **강세 다이버전스(★)**: 주가 저점 하락 vs OBV 저점 상승 ➔ 매수 신호\n"
    "- **약세 다이버전스(⚠️)**: 주가 고점 상승 vs OBV 고점 하락 ➔ 매도/경고 신호"
)

# 3. Main Dashboard Body
stock_name = get_stock_name(ticker)

tab_chart, tab_scanner, tab_guide = st.tabs([
    f"📊 {stock_name} 상세 차트 분석",
    "🔍 시장 수급 스캐너 (전종목)",
    "💡 수급 지표 활용 가이드",
])

# --- TAB 1: Detailed Chart & Metrics ---
with tab_chart:
    with st.spinner(f"[{stock_name}] 주가 및 수급 데이터를 분석 중입니다..."):
        try:
            df = fetch_stock_data(ticker=ticker, days=days_lookback)
            if df.empty:
                st.error(f"❌ {ticker} 데이터를 가져올 수 없습니다.")
                st.stop()

            anchor_str = anchor_date.strftime("%Y-%m-%d")
            df_ind = calculate_indicators(df, anchor_date=anchor_str)
            signals, low_idx, high_idx = detect_obv_divergence(df_ind, order=order_param)

            # Latest KPI calculations
            latest = df_ind.iloc[-1]
            prev = df_ind.iloc[-2] if len(df_ind) > 1 else latest
            latest_close = latest["Close"]
            prev_close = prev["Close"]
            day_change = latest_close - prev_close
            day_change_pct = (day_change / prev_close * 100) if prev_close != 0 else 0

            latest_avwap = latest["AVWAP"]
            avwap_diff_pct = ((latest_close - latest_avwap) / latest_avwap * 100) if pd.notna(latest_avwap) else 0

            latest_obv = latest["OBV"]
            latest_obv_ema = latest["OBV_EMA"]

            # 4 Metric Cards
            m1, m2, m3, m4 = st.columns(4)

            with m1:
                st.metric(
                    label="현재 종가",
                    value=f"{latest_close:,.2f}",
                    delta=f"{day_change:+,.2f} ({day_change_pct:+.2f}%)",
                )

            with m2:
                if pd.notna(latest_avwap):
                    status_text = "상회 (지지)" if avwap_diff_pct > 0 else "하회 (저항)"
                    st.metric(
                        label=f"AVWAP ({anchor_str}~)",
                        value=f"{latest_avwap:,.2f}",
                        delta=f"{avwap_diff_pct:+.2f}% ({status_text})",
                        delta_color="normal" if avwap_diff_pct > 0 else "inverse",
                    )
                else:
                    st.metric(label="AVWAP", value="N/A")

            with m3:
                obv_status = "단기 유입 우세" if latest_obv > latest_obv_ema else "단기 이탈 우세"
                st.metric(
                    label="OBV 수급 상태",
                    value=f"{latest_obv:,.0f}",
                    delta=obv_status,
                    delta_color="normal" if latest_obv > latest_obv_ema else "inverse",
                )

            with m4:
                recent_signals = [s for s in signals if (df_ind.index[-1] - s["date"]).days <= 30]
                if recent_signals:
                    last_sig = recent_signals[-1]
                    sig_label = "★ 강세 (매수)" if last_sig["type"] == "BULLISH_DIVERGENCE" else "⚠️ 약세 (경고)"
                    days_ago = (df_ind.index[-1] - last_sig["date"]).days
                    st.metric(
                        label="최근 30일 다이버전스",
                        value=sig_label,
                        delta=f"{days_ago}일 전 감지",
                        delta_color="normal" if last_sig["type"] == "BULLISH_DIVERGENCE" else "inverse",
                    )
                else:
                    st.metric(
                        label="최근 30일 다이버전스",
                        value="특이 신호 없음",
                        delta="안정 추세",
                    )

            # Interactive Plotly Chart
            fig = create_stock_figure(
                df=df_ind,
                ticker=ticker,
                stock_name=stock_name,
                signals=signals,
                anchor_date=anchor_str,
            )
            st.plotly_chart(fig, use_container_width=True)

            # Signal Table
            st.subheader(f"📋 포착된 다이버전스 시그널 목록 (최근 {days_lookback}일)")
            if signals:
                sig_rows = []
                for s in reversed(signals):
                    is_bull = s["type"] == "BULLISH_DIVERGENCE"
                    sig_rows.append({
                        "발생일자": s["date"].strftime("%Y-%m-%d"),
                        "신호 유형": "★ 강세 (스마트머니 매집)" if is_bull else "⚠️ 약세 (고점 분산/차익실현)",
                        "발생 시점 주가": f"{s['price']:,.2f}",
                        "이전 극값 일자": s["prev_date"].strftime("%Y-%m-%d"),
                        "이전 극값 주가": f"{s['prev_price']:,.2f}",
                        "분석 내용": s["message"],
                    })
                sig_table_df = pd.DataFrame(sig_rows)
                st.dataframe(sig_table_df, use_container_width=True, hide_index=True)
            else:
                st.info("조회 기간 동안 발생한 다이버전스 신호가 없습니다.")

        except Exception as e:
            st.error(f"분석 중 오류가 발생했습니다: {e}")

# --- TAB 2: Multi-Stock Scanner ---
with tab_scanner:
    st.subheader("🔍 주요 관심 종목 수급 및 시그널 일괄 스캔")
    st.caption("국내 대표 대형주와 미국 주요 빅테크/ETF의 AVWAP 이격률과 최근 30일 다이버전스를 실시간 스크리닝합니다.")

    if st.button("🔄 전체 종목 새로고침 스캔 실행", type="primary"):
        st.cache_data.clear()

    @st.cache_data(ttl=300)
    def run_market_scan(anchor_s):
        scan_list = [
            "005930", "000660", "005380", "373220", "035420", "035720",
            "NVDA", "AAPL", "MSFT", "TSLA", "QQQ", "SPY"
        ]
        results = []
        for t in scan_list:
            try:
                name = get_stock_name(t)
                d = fetch_stock_data(t, days=365)
                if d.empty:
                    continue
                d_ind = calculate_indicators(d, anchor_date=anchor_s)
                sigs, _, _ = detect_obv_divergence(d_ind, order=5)

                cur = d_ind.iloc[-1]
                p_close = cur["Close"]
                p_avwap = cur["AVWAP"]
                diff = ((p_close - p_avwap) / p_avwap * 100) if pd.notna(p_avwap) else 0

                sig_status = "-"
                if sigs:
                    last_s = sigs[-1]
                    d_ago = (d_ind.index[-1] - last_s["date"]).days
                    if d_ago <= 30:
                        sig_type_kor = "★ 강세 매집" if last_s["type"] == "BULLISH_DIVERGENCE" else "⚠️ 약세 분산"
                        sig_status = f"{sig_type_kor} ({d_ago}일전)"

                results.append({
                    "종목": name,
                    "티커": t,
                    "현재가": f"{p_close:,.2f}",
                    "AVWAP": f"{p_avwap:,.2f}" if pd.notna(p_avwap) else "N/A",
                    "이격률(%)": round(diff, 2),
                    "최근 30일 신호": sig_status,
                })
            except Exception:
                pass
        return pd.DataFrame(results)

    with st.spinner("시장 주요 종목을 일괄 스캔 중입니다..."):
        scan_df = run_market_scan(anchor_str)
        if not scan_df.empty:
            # Highlight positive/negative differences
            def style_diff(val):
                if isinstance(val, (int, float)):
                    if val > 0:
                        return "color: #ef4444; font-weight: bold;"
                    elif val < 0:
                        return "color: #3b82f6; font-weight: bold;"
                return ""

            st.dataframe(
                scan_df.style.map(style_diff, subset=["이격률(%)"]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("스캔 데이터를 불러오지 못했습니다.")

# --- TAB 3: Guide ---
with tab_guide:
    st.markdown("""
    ### 📖 수급 지표 및 다이버전스 분석 전략 가이드

    #### 1. AVWAP (고정형 거래량 가중 평균가)의 원리와 활용
    - **개념**: 사용자가 지정한 특정 이벤트(실적 발표일, 전고점/전저점 돌파, 연초 등) 시점부터 현재까지 거래된 모든 주식의 거래량 가중 평균가입니다.
    - **세력 평단가 추적**: 대규모 자금을 운용하는 기관/외국인의 실질 매입 단가를 의미합니다.
    - **실전 활용**:
      - 주가가 AVWAP **상단**에 위치할 때: 매수 세력이 시장을 통제하고 있으며, 주가 하락 시 AVWAP 선이 강력한 **지지선** 역할을 합니다.
      - 주가가 AVWAP **하단**에 위치할 때: 매도 압력이 우세하며, 반등 시 AVWAP 선이 강력한 **저항선**으로 작용합니다.

    ---

    #### 2. OBV (On-Balance Volume) & 다이버전스(Divergence) 감지
    - **원리**: "거래량은 가격에 선행한다"는 원칙을 바탕으로 주가 상승일에는 거래량을 더하고, 하락일에는 거래량을 차감하여 누적합니다.
    - **★ 강세 다이버전스 (Bullish Divergence)**:
      - **형태**: 가격은 신저가를 갱신하거나 횡보하는데, OBV의 저점은 명확하게 상승하는 패턴
      - **시사점**: 가격은 눌려 있으나 스마트 머니가 바닥권에서 조용히 매집 중임을 시사 ➔ **강력한 반등/매수 신호**
    - **⚠️ 약세 다이버전스 (Bearish Divergence)**:
      - **형태**: 가격은 신고가를 경신하며 상승하는데, OBV의 고점은 하락하는 패턴
      - **시사점**: 적은 거래량으로 가격만 띄운 상태에서 메이저 자금이 차익 실현(물량 분산) 중 ➔ **고점 추락 경고/매도 신호**
    """)
