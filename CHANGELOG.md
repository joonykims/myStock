# 📝 myStock 변경 및 개선 이력 (Changelog)

## [v1.8.0] - 2026-08-28
### ⚡ 증분 데이터 캐시(Incremental Cache) 시스템 도입 — 조회 속도 대폭 개선
- **신규 모듈 `mystock/stock_cache.py`**:
  - 종목별 OHLCV 데이터를 로컬 Parquet 파일(`.cache/{TICKER}.parquet`)에 자동 저장
  - 이미 캐시된 종목은 **마지막 거래일 이후 데이터만 증분 fetch**하여 병합 → API 호출 최소화
  - 캐시 파일 손상 시 자동 복구, 중복 데이터 자동 제거
  - `get_or_fetch()`, `invalidate_cache()`, `get_cache_info()` API 제공
- **`mystock/data_loader.py` 리팩터링**:
  - 기존 API 호출 로직을 `_raw_fetch_stock_data()`로 분리
  - `fetch_stock_data()`가 캐시 레이어를 자동 활용 (`use_cache=False`로 강제 갱신 가능)
- **대시보드 사이드바 캐시 상태 표시 (`app.py`)**:
  - 현재 캐시 종목 수, 용량 실시간 표시
  - `[🔄 현재 종목 갱신]` / `[🗑️ 전체 캐시 삭제]` 버튼 제공
- **단위 테스트 8건 추가 (`tests/test_mystock.py`)**:
  - 저장/로드, 개별·전체 삭제, 캐시 정보, 증분 fetch, 캐시 우선 사용, 중복 제거 검증

---

## [v1.7.0] - 2026-08-28
### 🎯 실시간 수급 스캐너 ➔ 상세 차트 원클릭 즉시 이동(Navigation) UI 구현
- **프로그래밍 방식 동적 탭 네비게이션 (`app.py`)**:
  - `st.session_state["active_tab"]` 및 상단 메뉴 바 연동으로 화면 간 상태 보존 이동 지원
- **스캐너 화면 내 원클릭 차트 이동 카드/버튼 추가**:
  - 탭 2(수급 스캐너)에서 스캔된 모든 종목 카드에 **`[ 📊 {종목명} 차트 보기 ]`** 버튼 배치
  - 버튼 클릭 시 해당 종목이 자동 선택되면서 **'📊 상세 차트 분석' 탭으로 즉시 화면 전환 및 차트 렌더링**
- **종목 관리 탭 내 빠른 차트 보기 버튼 추가**:
  - 탭 3(종목 관리)에서도 각 종목 카드에서 바로 상세 차트로 진입할 수 있도록 `[ 📊 차트 보기 ]` 버튼 지원

---

## [v1.6.0] - 2026-08-28

### 🚀 영문 혼합 KRX 특수 종목 코드(ETN/상품ETF 등) 데이터 수집 지원
- **종목 코드 판별 정규식 고도화 (`mystock/data_loader.py`)**:
  - `is_korean_ticker()` 정규식을 기존 순수 6자리 숫자(`^\d{6}$`)에서 영문이 포함된 KRX 표준 6자리 코드(`^\d[0-9A-Z]{5}$`, 예: `0072R0` TIGER KRX금현물) 및 `A` 접두사 코드까지 포괄하도록 확장
- **종목명 조회 다계층 폴백 구조 구축 (`get_stock_name`)**:
  - `watchlist.json` 사용자 정의 이름 ➔ `pykrx` 주식명 ➔ `pykrx` ETF명 ➔ 기본 티커 순차 조회로 영문 혼합 상품명 완벽 지원
- **데이터 로딩 검증**:
  - `0072R0` (TIGER KRX금현물) 365일 OHLCV 수집, AVWAP, OBV 및 다이버전스 분석 정상화 완료

---

## [v1.5.0] - 2026-08-28

### 🔄 종목 그룹 간 이동(Move) 및 복사(Copy) 기능 구현
- **종목 그룹 간 이동 및 복사 API (`mystock/watchlist.py`)**:
  - `move_ticker_between_categories(source, target, ticker)`: 원본 그룹에서 대상 그룹으로 종목 이전
  - `copy_ticker_between_categories(source, target, ticker)`: 원본 그룹 유지 상태로 대상 그룹에 종목 복제
- **웹 대시보드 인터랙티브 관리 UI 고도화 (`app.py`)**:
  - 탭 3(종목 관리)의 개별 종목 카드에 **[➡️ 이동]**, **[📋 복사]**, **[🗑️ 삭제]** 버튼 추가
  - 대상 그룹 선택 후 원클릭으로 이동/복사 즉시 반영 및 새로고침
- **단위 테스트 확장 (`tests/test_mystock.py`)**:
  - 그룹 간 복사 및 이동 기능에 대한 단위 테스트 추가 및 검증 완료

---

## [v1.4.0] - 2026-08-28

### 📁 보유종목 / 초관심종목 / 관심종목 그룹별 관리 기능 구축
- **독립 설정 파일 기반 종목 관리 (`watchlist.json`)**:
  - `보유종목`, `초관심종목`, `관심종목` 등 카테고리별 분리 관리 지원
  - 종목별 티커, 종목명, 개별 앵커일자(`anchor`), 메모(`memo`) 지정 기능 제공
- **종목 관리자 모듈 (`mystock/watchlist.py`)**:
  - `load_watchlist()`, `save_watchlist()`, `get_category_tickers()`, `get_all_tickers()` 제공
  - 대시보드 및 스크립트에서 동적으로 종목 추가/삭제/수정 API 구현
- **웹 대시보드 UI 고도화 (`app.py`)**:
  - 사이드바에서 그룹별(보유/초관심/관심/전체) 종목 필터링 선택 기능 추가
  - 탭 2(시장 수급 스캐너)에 카테고리별 탭 필터 적용
  - **'⚙️ 보유/관심 종목 관리' 탭 신설**: 웹 브라우저에서 직접 새 종목 추가 및 삭제 지원
- **CLI 및 스케줄러 그룹 필터 (`main.py`, `scheduler.py`)**:
  - `-g / --group` 옵션으로 특정 그룹만 타겟팅하여 스캔 및 알림 발송 가능 (예: `python main.py --scan -g 보유종목`)
- **단위 테스트 추가 (`tests/test_mystock.py`)**:
  - `test_watchlist` 테스트 케이스 추가 및 7개 단위 테스트 전원 정상 통과

---

## [v1.3.0] - 2026-08-27

### 🔔 자동화 알림 시스템 & 스케줄러 구축
- **다채널 알림 엔진 (`mystock/notifier.py`)**:
  - 텔레그램(Telegram Bot), 슬랙(Slack Webhook), 디스코드(Discord Webhook) 브로드캐스트 지원
  - 다이버전스 감지 시 현재가, AVWAP 대비 이격률, 분석 메시지 포맷팅 자동 전송
- **장 마감 자동 스케줄러 (`scheduler.py`)**:
  - 국내장 마감(매주 월~금 15:45 KST) 및 미국장 마감(매주 화~토 06:30 KST) 자동 스캔 및 발송 루프 지원
- **CLI 알림 옵션 추가 (`main.py`)**:
  - `--notify`: 전체 관심 종목 스캔 후 메신저 알림 1회 즉시 발송
  - `--scheduler`: 백그라운드 스케줄러 상시 실행
- **환경 설정 템플릿 (`.env.example`)**: 메신저 웹훅 및 봇 토큰 설정 안내
- **문서 보강 (`README.md`)**: 시장별 추천 조회 시간대 및 Windows 작업 스케줄러 등록 가이드 추가

---

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
