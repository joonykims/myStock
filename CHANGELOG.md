# 📝 myStock 변경 및 개선 이력 (Changelog)

## [v1.9.3] - 2026-09-02
### ⏰ GitHub Actions 24시간 완전 자동 시장 알림 스케줄러 구축
- **클라우드 무중단 스케줄러 (`.github/workflows/market_scheduler.yml`)**:
  - 내 PC를 켜둘 필요 없이 GitHub 무료 크론 서버를 통해 정시 자동 스캔 & 텔레그램 리포트 발송
  - **아침 개장 전 모닝 브리핑**: 매주 월~금 **07:50 KST** (UTC 일~목 22:50)
  - **국내장 마감 알림**: 매주 월~금 **15:45 KST** (UTC 06:45)
  - **미국장 마감 알림**: 매주 화~토 **06:30 KST** (UTC 월~금 21:30)
  - **수동 즉시 실행 지원 (`workflow_dispatch`)**: GitHub Actions 웹 콘솔에서 버튼 클릭 한 번으로 언제든 테스트 발송 가능
- **보안 비밀키(`GitHub Secrets`) 연동**:
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`를 안전하게 주입받아 동작

---

## [v1.9.2] - 2026-09-01
### 🔄 평일 당일 종가(Today's Close) 증분 갱신 판정 로직 수정
- **캐시 신선도(Freshness) 판정 로직 개선 (`mystock/stock_cache.py`)**:
  - 기존: 캐시에 '어제 날짜'까지만 있어도 Fresh로 판정되어 평일 장마감 후에도 당일 종가를 가져오지 않던 버그 해결
  - 개선: 평일(월~금) 장마감/장중에는 캐시 마지막 날짜가 당일(Today)이 아닌 경우 **당일치 델타 증분 fetch를 반드시 실행**하여 오늘 종가를 즉시 반영
- **주말/휴일 처리 최적화**:
  - 주말(토/일)에는 직전 금요일 종가가 있으면 불필요한 API 요청 없이 캐시 우선 사용

---

## [v1.9.1] - 2026-09-01
### ⚡ 해외 주식(미국 주식) 데이터 수집 지연 및 `download failed` 오류 완벽 해결
- **초고속 Direct Yahoo Finance v8 Chart API 도입**:
  - 기존 `yfinance`의 쿠키/크럼(Crumb) 인증 및 멀티스레딩 타임아웃으로 인한 10~30초 지연 및 `download failed` 오류 제거
  - 브라우저 표준 User-Agent 헤더 세션 기반의 **Direct Chart API 1순위 파이프라인** 구축 ➔ 해외 종목 수집 속도 **0.2초대**로 100배 이상 대폭 단축
- **3단계 폴백(Fallback) 안정성 파이프라인**:
  1. Direct Yahoo v8 API (< 0.5s)
  2. `yf.Ticker(session=custom_session).history()`
  3. `yf.download(session=custom_session)`
- **증분 Parquet 캐시 연동 극대화**:
  - 최초 1회만 초고속 수집 후 로컬 Parquet 캐시에 저장되어 이후 조회 시 0.01초 내 즉시 로드

---

## [v1.9.0] - 2026-08-28
### 🪟 노션 스타일 플로팅 사이드 뷰(Side Peek Drawer) & 모달 팝업(Center Peek) 차트 연동
- **독립 레이어 우측 플로팅 사이드 드로어 (Floating Side Peek Drawer)**:
  - 수급 스캐너 테이블에서 종목 체크 시 표 영역을 밀어내지 않고 **화면 우측에 별도 오버레이 레이어로 차트 패널이 겹쳐서 표시**
  - **표 레이아웃 보존**: 메인 테이블이 100% 전체 너비로 유지되어 표의 내용이 찌그러지거나 숨겨지지 않음
  - **상단 헤더 레벨 배치**: 상단 제목 라인 부근(`top: 55px`)부터 화면 전체 높이로 시원하게 배치
  - **시각적 구분 강화**: 딥 네이비 배경(`#0b1329`), 블루 포인트 보더(`border-left: 2px solid #3b82f6`), 입체 그림자 오버레이(`box-shadow`) 적용
  - 테이블에서 다른 종목 클릭 시 사이드 뷰의 차트/지표가 **실시간으로 즉시 전환**
- **중앙 대형 모달 팝업 (Center Peek)**:
  - 사이드 패널 상단 `[⛶ 모달 확대]` 클릭 시 `@st.dialog`를 활용한 대형 팝업으로 차트 및 세부 지표를 크게 확장하여 집중 분석
- **상세 탭 이동 및 닫기 제어**:
  - `[📊 상세 탭 이동]` 버튼을 통해 필요 시 언제든지 전체 차트 분석 탭으로 이동 가능
  - `[✖]` 버튼 클릭 시 사이드 패널을 닫고 100% 전체 테이블 뷰로 복귀
- **차트 렌더링 컴포넌트 모듈화**:
  - `render_stock_chart_view()`를 정의하여 메인 탭, 사이드 패널, 모달 팝업에서 동일한 차트/지표 UI 재사용

---

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
