---
trigger: glob
globs: **/*.py, requirements*.txt, .github/workflows/*.yml, .devcontainer/**
---

# Python 코딩 규칙 (myStock)

## 구조와 의존 방향
- 진입점: app.py(Streamlit UI), main.py(CLI), scheduler.py(스케줄/알림 실행)
- 핵심 로직은 mystock/ 패키지에 둔다. 진입점 파일에는 화면·인자 처리·호출 조합만 둔다.
- mystock/ 안에서는 streamlit 을 import 하지 않는다. (UI 의존은 app.py 에만)
- 모듈 역할을 섞지 않는다.
  - 데이터 수집: data_loader.py / 캐시: stock_cache.py
  - 지표: indicators.py / 다이버전스: divergence.py / 스캐너: scanner.py
  - 차트: visualizer.py / 관심종목: watchlist.py / 알림: notifier.py
- 새 외부 API 호출은 data_loader.py(시세) 또는 notifier.py(알림)를 통해서만 한다.
- app.py(1,000줄 이상)를 쪼개는 리팩터링은 기능 변경과 섞지 말고 plan-task 로 따로 계획한다.

## 코드 스타일
- 새 함수·수정한 함수에는 타입 힌트를 붙인다.
- 지표 계산 함수는 입력 DataFrame 을 직접 변경하지 않고 새 결과를 반환한다.
- DataFrame 컬럼명은 기존 코드의 명칭을 따른다. 임의로 바꾸지 않는다.
- 날짜·시간은 한국 시장 기준 Asia/Seoul 로 다룬다.
- 실행 스케줄은 저장소가 아니라 외부 서비스 cron-job.org 에 있다.
  코드에서 "몇 시에 실행되는지"를 가정하지 말고, 필요하면 docs/ARCHITECTURE.md 의 스케줄 표를 참고한다.
  실행 시각이 조금 늦거나 같은 트리거가 두 번 올 수 있으므로, 알림 로직은 중복 실행에 안전해야 한다.
- 로그·알림 메시지에 토큰, Chat ID, Webhook URL 을 출력하지 않는다.

## 의존성
- 라이브러리 추가·버전 변경은 사용자 확인 후 requirements.txt 에 반영한다.
- Python 버전 기준: {{확인 필요 — docs/DECISIONS.md 의 Python 버전 결정 참고}}
  로컬(3.14)과 CI·devcontainer(3.11)가 다르므로, 새 문법·라이브러리를 쓸 때는
  기준 버전에서 동작하는지 확인하고 보고한다.

## 테스트
- 테스트 러너는 unittest 로 통일한다: `python -m unittest discover tests`
- 지표·다이버전스·스캐너 로직을 바꾸면 tests/ 에 테스트를 추가하거나 수정한다.
- 단위 테스트는 실제 네트워크를 호출하지 않는다. 고정 DataFrame 이나 mock 을 사용한다.
- 실제 시세 API 확인은 smoke-test 스킬로 별도 수행한다.
