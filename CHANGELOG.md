# 📝 myStock 변경 및 개선 이력 (Changelog)

## [v1.2.0] - 2026-08-27
### ⚡ 데이터 수집 안정성 및 응답 속도 대폭 개선
- **해외 주식(Yahoo Finance) 3단계 다중 폴백(Fallback) 구조 구축**:
  - `yf.download(start, end)` ➔ `yf.Ticker.history(period)` ➔ `yf.download(period)` 순차 시도로 특정 엔드포인트 지연 시 자동 대체
- **지수 백오프(Exponential Backoff) 기반 자동 재시도**:
  - 네트워크 타임아웃이나 일시적 패킷 유실 발생 시 최대 3회 자동 재시도 수행
- **타임존 정규화 (`tz_localize(None)`)**:
  - 해외 거래소(뉴욕/나스닥)와 국내 거래소 간 시차로 인한 DatetimeIndex 불일치 및 Plotly 렌더링 결함 방지
- **Streamlit 고속 메모리 캐싱 (`@st.cache_data(ttl=600)`)**:
  - 동일 종목 데이터를 10분 동안 캐시에 유지하여, 탭 이동 및 슬라이더 조절 시 0.1초 내 즉각적인 차트 렌더링 지원

---

## [v1.1.0] - 2026-08-27
### 🐛 웹 대시보드 스코프 버그 픽스
- **`NameError: name 'anchor_str' is not defined` 수정**:
  - 탭 1(차트 탭) 내부 로컬 스코프에 갇혀 있던 `anchor_str`을 사이드바 입력 직후 전역 스코프로 이동하여 전 탭(시장 스캐너, 가이드) 공유 지원
- **데이터 로딩 실패 시 안전한 예외 처리**:
  - `st.stop()`으로 인한 전체 대시보드 중단 방지 및 `st.warning()` 조건부 렌더링으로 개선

---

## [v1.0.0] - 2026-08-27
### 🎉 최초 릴리즈 (Initial Release)
- **AVWAP (고정형 거래량 가중 평균가) 연산 모듈 (`mystock/indicators.py`)**
- **OBV 및 OBV 20-EMA 연산 모듈**
- **Scipy 기반 극값(Peak/Trough) 탐색 및 강세/약세 다이버전스 자동 감지 엔진 (`mystock/divergence.py`)**
- **Plotly 3분할 반응형 인터랙티브 캔들스틱 차트 (`mystock/visualizer.py`)**
- **Streamlit 웹 인터랙티브 대시보드 (`app.py`)**
- **CLI 단일 종목 분석 및 전종목 시장 스캐너 (`main.py`)**
- **단위 테스트 슈트 구축 (`tests/test_mystock.py`)**
