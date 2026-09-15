# 설계 결정 기록

새 결정은 맨 위에 추가한다. 결정을 뒤집을 때는 기존 항목을 지우지 말고 상태를 "대체됨"으로 바꾼다.

---

## D-001: 스케줄 트리거를 GitHub Actions schedule(cron)에서 cron-job.org로 이전
- 날짜: 2026-09-04
- 상태: 채택
- 배경: GitHub Actions 자체 `schedule:` 크론은 대기열 지연(15~60분)이 발생해 국내장(15:45)·미국장(06:30) 마감 직후 정시 알림이 불가능했다. (CHANGELOG v1.9.4 참고)
- 결정: 내부 `schedule:` 트리거를 제거하고, 외부 정밀 크론 서비스(cron-job.org)가 `workflow_dispatch`/`repository_dispatch` 웹훅으로 GitHub Actions를 초 단위로 정확히 트리거하도록 전환했다.
- 대안: GitHub Actions 자체 `schedule:` 유지 — 대기열 지연으로 정시성 요구를 충족하지 못해 기각.
- 영향: `.github/workflows/market_scheduler.yml`에 `schedule:` 트리거를 재추가하지 않는다 (cron-job.org와 중복 발송 위험). 정시 실행 책임은 cron-job.org 설정(및 그곳에 저장된 GitHub PAT)에 있으며, 세부 스케줄과 PAT 관리는 사용자가 직접 확인·관리한다. 상세 흐름은 docs/ARCHITECTURE.md "알림 실행 경로" 참고.

---

## D-002: Python 버전 기준 (로컬 3.14 vs CI·devcontainer 3.11)
- 날짜: 2026-09-15
- 상태: 검토 중
- 배경: 로컬 개발 환경은 Python 3.14.6이지만, `.github/workflows/market_scheduler.yml`은 `python-version: '3.11'`을, `.devcontainer/`도 3.11 계열을 지정하고 있다. `requirements.txt`에는 버전 제약이 없어 어느 쪽이 기준인지 문서상 정해진 바가 없다.
- 결정: (미정 — 사용자 확인 필요)
- 대안: 기록 없음
- 영향: 기준이 정해지기 전까지는 새 문법·라이브러리 사용 시 3.11 기준으로도 동작하는지 확인하고 보고한다 (.agents/rules/20-python.md 참고).

---

## D-003: Parquet 기반 증분 시세 캐시 도입
- 날짜: 2026-08-28 (CHANGELOG v1.8.0)
- 상태: 채택
- 배경: 매 조회마다 외부 시세 API를 다시 호출하면 응답이 느리고 호출량이 늘어난다.
- 결정: 종목별 OHLCV를 로컬 Parquet 파일(`.cache/{TICKER}.parquet`)에 저장하고, 마지막 거래일 이후 데이터만 증분 fetch하여 병합하는 `mystock/stock_cache.py`를 도입했다.
- 대안: 기록 없음
- 영향: `.cache/`는 재생성 가능한 캐시이므로 커밋하지 않는다. 캐시 형식(컬럼, 파일명 규칙) 변경 시 기존 캐시와의 호환 여부를 보고한다 (40-secrets-and-data.md 참고).

---

## D-004: 해외 시세 수집에 Direct Yahoo Chart API 우선 + 다단계 폴백 적용
- 날짜: 2026-09-01 (CHANGELOG v1.9.1)
- 상태: 채택
- 배경: 기존 `yfinance`의 쿠키/크럼(Crumb) 인증과 멀티스레딩 처리에서 10~30초 지연 및 `download failed` 오류가 발생했다.
- 결정: 브라우저 표준 User-Agent 세션 기반의 Direct Yahoo Finance v8 Chart API를 1순위로 사용하고, 실패 시 `yf.Ticker(session=...).history()` → `yf.download(session=...)` 순으로 폴백하는 3단계 파이프라인을 `mystock/data_loader.py`에 구성했다.
- 대안: 기록 없음
- 영향: 해외 티커 수집 로직을 바꿀 때는 이 3단계 폴백 순서를 유지하거나, 변경 시 사유를 함께 기록한다.

---

## D-005: 이광수식 주도주 스캐너 — RS 점수·등급 체계 및 기계적 손절선 도입
- 날짜: 2026-09-08 (CHANGELOG v2.0.0)
- 상태: 채택
- 배경: 지수 급락(-1% 이상) 구간에서도 버티거나 양봉 마감하는 차기 주도주를 식별하려는 요구가 있었다.
- 결정: 지수 대비 상대강도(RS Spread), 양봉 마감 강도, 거래량 폭발(20일 MA 대비), AVWAP 지지 여부를 종합한 0~100점 점수와 S/A/B/C/D 등급 체계를 `mystock/scanner.py`에 도입하고, 매수가 대비 -10% 기계적 손절선과 5종목 이내 압축 투자 원칙을 자동 산출하도록 했다.
- 대안: 기록 없음
- 영향: 점수 산식이나 등급 기준(구간값)을 바꾸면 `tests/test_scanner.py`의 관련 단위 테스트도 함께 갱신한다.

---

## D-006: watchlist.json 을 카테고리(보유/초관심/관심종목)로 구분 관리
- 날짜: 2026-08-28 (CHANGELOG v1.4.0)
- 상태: 채택
- 배경: 관심종목을 중요도/관심도에 따라 구분해서 스캔·알림 대상을 좁힐 필요가 있었다.
- 결정: `watchlist.json`을 `보유종목`/`초관심종목`/`관심종목` 등 카테고리 키로 나누고, 종목별로 티커·이름·개별 앵커일자(`anchor`)·메모(`memo`)를 갖는 스키마로 `mystock/watchlist.py`를 통해 CRUD하도록 했다.
- 대안: 기록 없음
- 영향: watchlist.json 은 사용자가 직접 관리하는 데이터다. 코드 작업 중 임의로 값을 바꾸지 않으며, 스키마 변경 시 기존 데이터 이전 방법을 함께 제안한다 (40-secrets-and-data.md 참고).
