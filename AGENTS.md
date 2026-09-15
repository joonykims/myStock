# AGENTS.md — 에이전트용 프로젝트 지도

> 이 파일은 "백과사전"이 아니라 "목차"다. 자세한 내용은 docs/ 로 안내한다.
> 여기 적힌 규칙은 짧고 중요한 것만. 상세 규칙은 .agents/rules/ 에 있다.

## 1. 프로젝트 개요
- 이름: myStock
- 목적: AVWAP(고정형 거래량 가중 평균가)과 OBV 다이버전스 탐지로 종목 수급 흐름을 분석하고, 신호 발생 시 텔레그램/슬랙/디스코드로 자동 알림하는 개인용 주식 분석 도구
- 스택: Python, Streamlit(웹 대시보드), pandas/numpy/scipy(지표·다이버전스 연산), pykrx/yfinance(시세 수집), Parquet(로컬 캐시)
- 상세 아키텍처: docs/ARCHITECTURE.md

## 2. 빠른 시작
```bash
pip install -r requirements.txt        # 의존성 설치
python -m unittest discover tests -v   # 테스트 실행 (18개)
streamlit run app.py                   # 웹 대시보드 실행 (또는: python main.py --dashboard)
python main.py -t 005930               # 단일 종목 콘솔 분석 (기본값: 삼성전자)
python main.py -l                      # 이광수식 주도주 스캐너 실행

# 아래는 실제 전송됨 — 실행 전 확인
python main.py --notify                # (실제 전송됨 — 실행 전 확인) 전체 관심종목 스캔 후 메신저 알림 1회 발송
python scheduler.py --now              # (실제 전송됨 — 실행 전 확인) 위와 동일한 경로의 즉시 알림
python main.py --scheduler             # (실제 전송됨 — 실행 전 확인) 장마감 시간대 자동 알림 백그라운드 루프
```

## 3. 디렉터리 구조
```
app.py               # Streamlit 웹 대시보드 (UI 진입점)
main.py              # CLI 진입점 (분석/스캔/알림/스케줄러 인자 처리)
scheduler.py         # 알림 실행 엔진 (--now 1회 실행 및 로컬 대기 루프)
mystock/             # 핵심 로직 패키지 (UI 비의존)
  ├── data_loader.py   # 시세 수집 (pykrx/Yahoo, 3단계 폴백 + 지수 백오프)
  ├── stock_cache.py   # Parquet 기반 증분 캐시
  ├── indicators.py    # AVWAP, OBV 계산
  ├── divergence.py    # OBV 다이버전스 탐지 (scipy)
  ├── scanner.py        # 이광수식 주도주 상대강도(RS) 스캐너
  ├── universe.py        # 스캔 대상 종목 유니버스 프리셋
  ├── visualizer.py       # Plotly 인터랙티브 차트 생성
  ├── watchlist.py         # watchlist.json 관심종목 CRUD
  └── notifier.py           # 텔레그램/슬랙/디스코드 알림 발송
tests/                # unittest 테스트 (18개)
.github/workflows/    # market_scheduler.yml — cron-job.org 웹훅으로 트리거되는 알림 워크플로
docs/                 # 기록 시스템 (아래 문서 지도 참고)
.agents/rules/        # 항상/조건부 적용 규칙
.agents/skills/       # 필요할 때 불러오는 작업 절차
watchlist.json        # 사용자 관심종목 데이터 (보유종목/초관심종목/관심종목 그룹)
.env                  # 알림 봇 토큰/웹훅 (git 무시 — 절대 열람 금지, 40-secrets-and-data.md 참고)
.cache/               # 시세 Parquet 캐시 (git 무시, 재생성 가능)
```

## 4. 핵심 규칙 (반드시 지킬 것)
1. 작업 시작 전 docs/PROGRESS.md 를 읽고 현재 상태를 파악한다.
2. 3개 이상 파일을 바꾸는 작업은 먼저 계획을 세우고 승인받는다 (plan-task 스킬).
3. "완료"라고 말하기 전에 테스트를 실제로 실행해 통과를 확인한다 (verify-change 스킬).
4. 요청 범위 밖의 파일은 수정하지 않는다. 필요하면 먼저 묻는다.
5. 설계 결정이 생기면 docs/DECISIONS.md 에 기록한다.
6. 세션 종료 전 docs/PROGRESS.md 를 갱신한다 (session-handoff 스킬).
7. mystock/ 안에서는 streamlit 을 import 하지 않는다 (UI 의존은 app.py 에만 — 20-python.md).
8. .env 는 열어보지 않는다. 비밀정보·실제 알림 발송 관련 규칙은 40-secrets-and-data.md 를 따른다.

## 5. 문서 지도
| 알고 싶은 것 | 볼 곳 |
|---|---|
| 전체 구조, 레이어/의존 규칙, 외부 연동 | docs/ARCHITECTURE.md |
| 알림이 실제로 어떻게 발송되는지 (cron-job.org → GitHub Actions → notifier.py) | docs/ARCHITECTURE.md "알림 실행 경로" 절 |
| 지금 진행 상황, 다음 할 일 | docs/PROGRESS.md |
| 진행 중인 작업 계획 | docs/plans/ |
| 과거 설계 결정과 이유 | docs/DECISIONS.md |
| 에이전트가 반복한 실수 | docs/LESSONS.md |

## 6. 자주 하는 작업
| 작업 | 참고 |
|---|---|
| 지표/다이버전스/스캐너 로직 수정 | mystock/ 내 해당 모듈만 수정, tests/ 에 테스트 추가·수정, 실데이터 확인은 smoke-test 스킬 |
| 알림 채널 로직 수정 | mystock/notifier.py 수정, 실제 발송 명령 실행 전 사용자 확인 필수 |
| 워크플로/스케줄 변경 | .agents/rules/40-secrets-and-data.md 확인 후 사용자 승인 필수 (cron-job.org 쪽 설정도 함께 바뀌어야 함) |
| 관심종목 데이터 구조 변경 | watchlist.json 스키마 변경 시 기존 데이터 이전 방법을 함께 제안 |
