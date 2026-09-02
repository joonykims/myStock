import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from mystock.data_loader import fetch_stock_data, get_stock_name
from mystock.indicators import calculate_indicators
from mystock.divergence import detect_obv_divergence
from mystock.visualizer import create_stock_figure
from mystock.watchlist import (
    load_watchlist,
    save_watchlist,
    get_all_tickers,
    add_ticker_to_category,
    remove_ticker_from_category,
    move_ticker_between_categories,
    copy_ticker_between_categories,
)

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
    /* Top tab radio styling */
    div[data-testid="stRadio"] > div {
        gap: 10px;
    }
</style>
""", unsafe_allow_html=True)

# 2. Session State Initialization
if "selected_ticker" not in st.session_state:
    st.session_state["selected_ticker"] = "005930"

TAB_NAMES = [
    "📊 상세 차트 분석",
    "🔍 시장 수급 스캐너 (그룹별)",
    "⚙️ 보유/관심 종목 관리",
    "💡 수급 지표 활용 가이드",
]

if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = TAB_NAMES[0]

# Load categorized watchlist
watchlist_data = load_watchlist()
available_categories = list(watchlist_data.keys())

# 3. Sidebar - Inputs & Controls
st.sidebar.title("📈 myStock 분석 설정")

# Category selector in sidebar
selected_group = st.sidebar.selectbox(
    "📁 종목 그룹 선택",
    options=["전체 보기"] + available_categories + ["직접 입력"],
    index=0,
)

# Build dynamic stock options based on category
stock_options = {}
default_index = 0

if selected_group == "직접 입력":
    ticker_input = st.sidebar.text_input(
        "종목 코드 / 티커 입력",
        value=st.session_state["selected_ticker"],
        help="국내 6자리 종목코드 또는 미국 티커",
    )
    ticker = ticker_input.strip().upper()
    current_item_anchor = None
else:
    if selected_group == "전체 보기":
        target_list = get_all_tickers()
    else:
        raw_items = watchlist_data.get(selected_group, [])
        target_list = [
            {"ticker": it["ticker"], "name": it.get("name", it["ticker"]), "category": selected_group, "anchor": it.get("anchor"), "memo": it.get("memo", "")}
            if isinstance(it, dict) else {"ticker": str(it), "name": str(it), "category": selected_group, "anchor": None, "memo": ""}
            for it in raw_items
        ]

    option_keys = []
    ticker_to_label = {}
    for item in target_list:
        t = item["ticker"]
        n = item.get("name", t)
        cat = item.get("category", "")
        cat_badge = f"[{cat}] " if cat and selected_group == "전체 보기" else ""
        label = f"{cat_badge}{n} ({t})"
        stock_options[label] = item
        option_keys.append(label)
        ticker_to_label[t.upper()] = label

    if stock_options:
        # If ticker was set programmatically (e.g. scanner button), sync the widget key.
        # The flag "programmatic_ticker_change" is set by buttons before st.rerun().
        if st.session_state.pop("programmatic_ticker_change", False):
            desired = ticker_to_label.get(
                st.session_state["selected_ticker"].upper(), option_keys[0]
            )
            st.session_state["_ticker_select_widget"] = desired
        elif st.session_state.get("_ticker_select_widget") not in option_keys:
            # Widget state is invalid (e.g. group changed) — reset to first valid item
            desired = ticker_to_label.get(
                st.session_state["selected_ticker"].upper(), option_keys[0]
            )
            st.session_state["_ticker_select_widget"] = desired

        st.sidebar.selectbox(
            "🎯 분석할 종목 선택",
            options=option_keys,
            key="_ticker_select_widget",
        )
        selected_label = st.session_state["_ticker_select_widget"]
        selected_item = stock_options[selected_label]
        ticker = selected_item["ticker"]
        st.session_state["selected_ticker"] = ticker
        current_item_anchor = selected_item.get("anchor")
    else:
        ticker = st.session_state["selected_ticker"]
        current_item_anchor = None

# Date & Lookback controls
col_d1, col_d2 = st.sidebar.columns(2)
with col_d1:
    if current_item_anchor:
        try:
            default_anchor = datetime.strptime(current_item_anchor, "%Y-%m-%d").date()
        except Exception:
            default_anchor = datetime(datetime.now().year, 1, 2).date()
    else:
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

anchor_str = anchor_date.strftime("%Y-%m-%d")

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

# --- Cache Status & Controls in Sidebar ---
from mystock.stock_cache import get_cache_info, invalidate_cache

st.sidebar.markdown("---")
st.sidebar.markdown("**💾 데이터 캐시 상태**")

cache_info = get_cache_info()
if cache_info["ticker_count"] > 0:
    st.sidebar.caption(
        f"캐시 종목: **{cache_info['ticker_count']}개** · "
        f"용량: **{cache_info['total_size_kb']:.0f} KB**"
    )
    cache_col1, cache_col2 = st.sidebar.columns(2)
    with cache_col1:
        if st.button("🔄 현재 종목 갱신", key="cache_refresh_one", use_container_width=True):
            invalidate_cache(ticker)
            st.cache_data.clear()
            st.rerun()
    with cache_col2:
        if st.button("🗑️ 전체 캐시 삭제", key="cache_clear_all", use_container_width=True):
            invalidate_cache()
            st.cache_data.clear()
            st.rerun()
else:
    st.sidebar.caption("캐시 없음 — 첫 조회 시 자동 생성됩니다.")

# 4. Main Dashboard Header & Top Tab Navigation
stock_name = get_stock_name(ticker)


# Layer 1: st.cache_data (in-memory, short TTL) prevents redundant Parquet reads within same session.
# Layer 2: Parquet disk cache (in fetch_stock_data) prevents redundant API calls across sessions.
@st.cache_data(ttl=60, show_spinner=False)
def load_stock_data(ticker_symbol: str, days_cnt: int) -> pd.DataFrame:
    """Two-layer cache: Streamlit memory (60s) → Parquet disk → API (only for delta)."""
    return fetch_stock_data(ticker=ticker_symbol, days=days_cnt)


def render_stock_chart_view(
    target_ticker: str,
    target_name: str,
    anchor_date: str,
    days_cnt: int = 365,
    order_val: int = 3,
    compact: bool = False,
):
    """Reusable component to render KPI metrics, Plotly interactive chart, and signal summary."""
    try:
        df = load_stock_data(ticker_symbol=target_ticker, days_cnt=days_cnt)
        if df is None or df.empty:
            st.warning(f"⚠️ {target_ticker} ({target_name})의 데이터를 불러오지 못했습니다.")
            return

        df_ind = calculate_indicators(df, anchor_date=anchor_date)
        signals, low_idx, high_idx = detect_obv_divergence(df_ind, order=order_val)

        # KPI calculations
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

        # Metrics layout
        if compact:
            m1, m2 = st.columns(2)
            m3, m4 = st.columns(2)
        else:
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
                    label=f"AVWAP ({anchor_date}~)",
                    value=f"{latest_avwap:,.2f}",
                    delta=f"{avwap_diff_pct:+.2f}% ({status_text})",
                    delta_color="normal" if avwap_diff_pct > 0 else "inverse",
                )
            else:
                st.metric(label="AVWAP", value="N/A")

        with m3:
            obv_status = "단기 유입 우세" if latest_obv > latest_obv_ema else "단기 이탈 우세"
            st.metric(
                label="OBV 수급",
                value=f"{latest_obv:,.0f}",
                delta=obv_status,
                delta_color="normal" if latest_obv > latest_obv_ema else "inverse",
            )

        with m4:
            recent_signals = [s for s in signals if (df_ind.index[-1] - s["date"]).days <= 30]
            if recent_signals:
                last_sig = recent_signals[-1]
                sig_label = "★ 강세" if last_sig["type"] == "BULLISH_DIVERGENCE" else "⚠️ 약세"
                days_ago = (df_ind.index[-1] - last_sig["date"]).days
                st.metric(
                    label="최근 30일 신호",
                    value=sig_label,
                    delta=f"{days_ago}일 전",
                    delta_color="normal" if last_sig["type"] == "BULLISH_DIVERGENCE" else "inverse",
                )
            else:
                st.metric(
                    label="최근 30일 신호",
                    value="특이 신호 없음",
                    delta="안정 추세",
                )

        # Interactive Plotly Chart
        fig = create_stock_figure(
            df=df_ind,
            ticker=target_ticker,
            stock_name=target_name,
            signals=signals,
            anchor_date=anchor_date,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Signal Table
        if compact:
            with st.expander(f"📋 최근 다이버전스 시그널 ({len(signals)}건)", expanded=False):
                if signals:
                    sig_rows = []
                    for s in reversed(signals[-5:]):
                        is_bull = s["type"] == "BULLISH_DIVERGENCE"
                        sig_rows.append({
                            "일자": s["date"].strftime("%Y-%m-%d"),
                            "유형": "★ 강세" if is_bull else "⚠️ 약세",
                            "가격": f"{s['price']:,.2f}",
                            "내용": s["message"],
                        })
                    st.dataframe(pd.DataFrame(sig_rows), use_container_width=True, hide_index=True)
                else:
                    st.caption("발생한 다이버전스 신호가 없습니다.")
        else:
            st.subheader(f"📋 포착된 다이버전스 시그널 목록 (최근 {days_cnt}일)")
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
                st.dataframe(pd.DataFrame(sig_rows), use_container_width=True, hide_index=True)
            else:
                st.info("조회 기간 동안 발생한 다이버전스 신호가 없습니다.")
    except Exception as e:
        st.error(f"분석 중 오류가 발생했습니다: {e}")


@st.dialog("📊 종목 상세 차트 (Center Peek 모달)", width="large")
def show_chart_modal(target_ticker: str, target_name: str, anchor_date: str, days_cnt: int = 365, order_val: int = 3):
    """Notion-style Center Peek large modal popup."""
    st.markdown(f"### **{target_name}** (`{target_ticker}`)")
    render_stock_chart_view(
        target_ticker=target_ticker,
        target_name=target_name,
        anchor_date=anchor_date,
        days_cnt=days_cnt,
        order_val=order_val,
        compact=False,
    )


# Top Navigation Bar
current_tab_index = TAB_NAMES.index(st.session_state["active_tab"]) if st.session_state["active_tab"] in TAB_NAMES else 0
selected_nav = st.radio(
    "메뉴 탭",
    options=TAB_NAMES,
    index=current_tab_index,
    horizontal=True,
    label_visibility="collapsed",
)

# Update state if user clicked another tab manually
if selected_nav != st.session_state["active_tab"]:
    st.session_state["active_tab"] = selected_nav
    st.rerun()

st.markdown("---")

# ==========================================
# TAB 1: Detailed Chart & Metrics
# ==========================================
if st.session_state["active_tab"] == "📊 상세 차트 분석":
    st.markdown(f"### 📊 {stock_name} 상세 수급 & 차트 분석")

    with st.spinner(f"[{stock_name}] 주가 및 수급 데이터를 분석 중입니다..."):
        render_stock_chart_view(
            target_ticker=ticker,
            target_name=stock_name,
            anchor_date=anchor_str,
            days_cnt=days_lookback,
            order_val=order_param,
            compact=False,
        )

# ==========================================
# TAB 2: Multi-Stock Scanner with Notion-style Side Peek & Modal
# ==========================================
elif st.session_state["active_tab"] == "🔍 시장 수급 스캐너 (그룹별)":
    st.subheader("🔍 보유/관심 종목 그룹별 실시간 수급 스캔")

    # Category filter pills
    scan_cat_tabs = ["전체 종목"] + available_categories
    selected_scan_cat = st.radio("필터 그룹 선택", scan_cat_tabs, horizontal=True, key="scan_cat_radio")

    col_btn_sc1, col_btn_sc2 = st.columns([1, 4])
    with col_btn_sc1:
        force_rescan = st.button("🔄 스캔 새로고침", type="secondary")

    # -- Scan logic: session_state cache for instant tab switches --
    scan_cache_key = f"_scan_result_{anchor_str}_{selected_scan_cat}"

    def _run_scan():
        """Execute market scan for all tickers in the selected group."""
        if selected_scan_cat == "전체 종목":
            scan_items = get_all_tickers()
        else:
            raw = watchlist_data.get(selected_scan_cat, [])
            scan_items = [
                {"ticker": it["ticker"], "name": it.get("name", it["ticker"]), "category": selected_scan_cat, "anchor": it.get("anchor"), "memo": it.get("memo", "")}
                if isinstance(it, dict) else {"ticker": str(it), "name": str(it), "category": selected_scan_cat, "anchor": None, "memo": ""}
                for it in raw
            ]

        results = []
        for it in scan_items:
            t = it["ticker"]
            n = it.get("name", t)
            cat = it.get("category", "")
            item_a = it.get("anchor") or anchor_str
            memo = it.get("memo", "")

            try:
                d = load_stock_data(t, 365)
                if d is None or d.empty:
                    continue
                d_ind = calculate_indicators(d, anchor_date=item_a)
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
                    "그룹": cat,
                    "종목명": n,
                    "티커": t,
                    "현재가": f"{p_close:,.2f}",
                    "AVWAP": f"{p_avwap:,.2f}" if pd.notna(p_avwap) else "N/A",
                    "이격률(%)": round(diff, 2),
                    "최근 30일 신호": sig_status,
                    "개별앵커": it.get("anchor"),
                    "메모": memo,
                })
            except Exception:
                pass
        return pd.DataFrame(results)

    # Force rescan: clear session cache for this scan
    if force_rescan:
        for k in list(st.session_state.keys()):
            if k.startswith("_scan_result_"):
                del st.session_state[k]
        st.cache_data.clear()
        st.rerun()

    # Use session_state to cache scan results — instant on tab switches
    if scan_cache_key not in st.session_state:
        with st.spinner("종목 그룹을 스캔 중입니다..."):
            st.session_state[scan_cache_key] = _run_scan()

    scan_df = st.session_state[scan_cache_key]

    if not scan_df.empty:
        # Check if a ticker is currently peeked in side panel
        peek_ticker = st.session_state.get("scanner_peek_ticker", None)

        def style_diff(val):
            if isinstance(val, (int, float)):
                if val > 0:
                    return "color: #ef4444; font-weight: bold;"
                elif val < 0:
                    return "color: #3b82f6; font-weight: bold;"
            return ""

        # Drop internal columns for clean table display
        table_cols = [c for c in scan_df.columns if c != "개별앵커"]
        table_df = scan_df[table_cols]

        # Side Peek Card Styling CSS
        st.markdown("""
        <style>
            .side-peek-card {
                background-color: #0b1329 !important;
                border: 1px solid #334155 !important;
                border-radius: 12px !important;
                padding: 18px 20px !important;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
                margin-bottom: 20px !important;
            }
        </style>
        """, unsafe_allow_html=True)

        # --- SIDE-BY-SIDE LAYOUT (Matches the red box area in screenshot) ---
        if peek_ticker:
            col_scan_list, col_side_panel = st.columns([0.43, 0.57], gap="medium")

            with col_scan_list:
                st.caption("💡 종목을 클릭하면 우측 패널 차트가 즉시 전환됩니다.")
                event = st.dataframe(
                    table_df.style.map(style_diff, subset=["이격률(%)"]),
                    use_container_width=True,
                    hide_index=True,
                    height=560,
                    on_select="rerun",
                    selection_mode="single-row",
                )

                # Handle row selection
                if event and event.selection and event.selection.rows:
                    clicked_row_idx = event.selection.rows[0]
                    new_ticker = scan_df.iloc[clicked_row_idx]["티커"]
                    if new_ticker != peek_ticker:
                        st.session_state["scanner_peek_ticker"] = new_ticker
                        st.rerun()

            with col_side_panel:
                with st.container(border=True):
                    peek_rows = scan_df[scan_df["티커"] == peek_ticker]
                    if not peek_rows.empty:
                        p_row = peek_rows.iloc[0]
                        p_name = p_row["종목명"]
                        p_anchor = p_row.get("개별앵커") or anchor_str
                    else:
                        p_name = get_stock_name(peek_ticker)
                        p_anchor = anchor_str

                    # Header Toolbar inside side panel
                    tb_col1, tb_col2, tb_col3, tb_col4 = st.columns([2.2, 1.1, 1.1, 0.5])
                    with tb_col1:
                        st.markdown(f"#### 🔎 **{p_name}** <small style='color:#94a3b8'>({peek_ticker})</small>", unsafe_allow_html=True)
                    with tb_col2:
                        if st.button("⛶ 모달 확대", key="btn_peek_modal", use_container_width=True, help="중앙 대형 모달 팝업으로 차트 확대"):
                            show_chart_modal(
                                target_ticker=peek_ticker,
                                target_name=p_name,
                                anchor_date=p_anchor,
                                days_cnt=days_lookback,
                                order_val=order_param,
                            )
                    with tb_col3:
                        if st.button("📊 상세 탭", key="btn_peek_to_tab", use_container_width=True, help="상세 차트 분석 탭으로 이동"):
                            st.session_state["selected_ticker"] = peek_ticker
                            st.session_state["active_tab"] = "📊 상세 차트 분석"
                            st.session_state["programmatic_ticker_change"] = True
                            st.rerun()
                    with tb_col4:
                        if st.button("✖", key="btn_peek_close", use_container_width=True, help="사이드 패널 닫기"):
                            st.session_state["scanner_peek_ticker"] = None
                            st.rerun()

                    st.markdown("---")

                    # Render compact chart inside right panel
                    render_stock_chart_view(
                        target_ticker=peek_ticker,
                        target_name=p_name,
                        anchor_date=p_anchor,
                        days_cnt=days_lookback,
                        order_val=order_param,
                        compact=True,
                    )

        else:
            # Full width table mode
            st.caption("💡 종목 행(체크박스)을 **클릭**하면 우측에 **상세 차트 사이드 패널**이 열립니다.")
            event = st.dataframe(
                table_df.style.map(style_diff, subset=["이격률(%)"]),
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
            )

            # Handle row selection → open side panel
            if event and event.selection and event.selection.rows:
                clicked_row_idx = event.selection.rows[0]
                clicked_ticker = scan_df.iloc[clicked_row_idx]["티커"]
                st.session_state["scanner_peek_ticker"] = clicked_ticker
                st.rerun()

    else:
        st.warning("스캔 데이터를 불러오지 못했습니다.")

# ==========================================
# TAB 3: Watchlist Management
# ==========================================
elif st.session_state["active_tab"] == "⚙️ 보유/관심 종목 관리":
    st.subheader("⚙️ 보유/관심 종목 관리 (`watchlist.json`)")
    st.caption("새로운 종목을 추가하거나 그룹(보유종목, 초관심종목, 관심종목)을 관리하고 그룹 간 이동/복사합니다.")

    # Form to add/update ticker
    with st.expander("➕ 새 종목 추가 / 수정", expanded=True):
        with st.form("add_stock_form"):
            fc1, fc2 = st.columns(2)
            with fc1:
                target_cat = st.selectbox("분류 그룹", options=available_categories + ["새 그룹 추가"])
                if target_cat == "새 그룹 추가":
                    target_cat = st.text_input("새 그룹 이름 입력", value="신규그룹")
                new_ticker = st.text_input("티커 / 종목코드", placeholder="예: 000660 또는 AAPL")
            with fc2:
                new_name = st.text_input("종목명 (선택)", placeholder="예: SK하이닉스 또는 애플")
                new_anchor = st.date_input("개별 앵커일자 (선택)", value=default_anchor).strftime("%Y-%m-%d")
                new_memo = st.text_input("메모 (선택)", placeholder="예: HBM 대장주, 매수평단 15만원 등")

            submit_btn = st.form_submit_button("💾 종목 저장하기", type="primary")
            if submit_btn and new_ticker:
                add_ticker_to_category(
                    category=target_cat,
                    ticker=new_ticker,
                    name=new_name if new_name else get_stock_name(new_ticker),
                    anchor=new_anchor,
                    memo=new_memo,
                )
                st.success(f"✅ '{target_cat}' 그룹에 [{new_ticker}] 종목이 저장되었습니다!")
                st.cache_data.clear()
                st.rerun()

    # Display, move, copy, and delete current stocks
    st.markdown("### 📋 현재 등록된 그룹별 종목 목록")
    current_wl = load_watchlist()

    for cat_name, items in current_wl.items():
        st.markdown(f"#### 📁 {cat_name} ({len(items)}개)")
        if items:
            c_cols = st.columns(3)
            other_cats = [c for c in available_categories if c != cat_name]

            for idx, it in enumerate(items):
                t_code = it["ticker"] if isinstance(it, dict) else str(it)
                t_name = it.get("name", t_code) if isinstance(it, dict) else t_code
                t_memo = it.get("memo", "") if isinstance(it, dict) else ""
                t_anchor = it.get("anchor", "") if isinstance(it, dict) else ""

                with c_cols[idx % 3]:
                    with st.container():
                        st.markdown(f"""
                        <div style="background-color: #1e293b; padding: 12px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 8px;">
                            <b>{t_name}</b> <span style="color:#94a3b8">({t_code})</span><br>
                            <small style="color:#64748b">앵커일: {t_anchor if t_anchor else '연초'}</small><br>
                            <small style="color:#38bdf8">{t_memo if t_memo else '메모 없음'}</small>
                        </div>
                        """, unsafe_allow_html=True)

                        # Quick chart view from watchlist tab
                        if st.button(f"📊 차트 보기", key=f"wl_chart_{cat_name}_{t_code}", use_container_width=True):
                            st.session_state["selected_ticker"] = t_code
                            st.session_state["active_tab"] = "📊 상세 차트 분석"
                            st.session_state["programmatic_ticker_change"] = True
                            st.rerun()

                        if other_cats:
                            sel_target = st.selectbox(
                                "대상 그룹",
                                options=other_cats,
                                key=f"target_grp_{cat_name}_{t_code}",
                                label_visibility="collapsed",
                            )
                            btn_col1, btn_col2, btn_col3 = st.columns(3)
                            with btn_col1:
                                if st.button(f"➡️ 이동", key=f"mov_{cat_name}_{t_code}", use_container_width=True):
                                    move_ticker_between_categories(cat_name, sel_target, t_code)
                                    st.success(f"'{sel_target}'(으)로 이동 완료!")
                                    st.cache_data.clear()
                                    st.rerun()
                            with btn_col2:
                                if st.button(f"📋 복사", key=f"cpy_{cat_name}_{t_code}", use_container_width=True):
                                    copy_ticker_between_categories(cat_name, sel_target, t_code)
                                    st.success(f"'{sel_target}'(으)로 복사 완료!")
                                    st.cache_data.clear()
                                    st.rerun()
                            with btn_col3:
                                if st.button(f"🗑️ 삭제", key=f"del_{cat_name}_{t_code}", use_container_width=True):
                                    remove_ticker_from_category(cat_name, t_code)
                                    st.cache_data.clear()
                                    st.rerun()
                        else:
                            if st.button(f"🗑️ 삭제: {t_code}", key=f"del_{cat_name}_{t_code}", use_container_width=True):
                                remove_ticker_from_category(cat_name, t_code)
                                st.cache_data.clear()
                                st.rerun()
        else:
            st.info("등록된 종목이 없습니다.")

# ==========================================
# TAB 4: Guide
# ==========================================
elif st.session_state["active_tab"] == "💡 수급 지표 활용 가이드":
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
