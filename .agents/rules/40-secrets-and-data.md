---
trigger: always_on
---

# 비밀정보와 데이터 파일 규칙 (myStock)

## .env / 비밀정보
- .env 파일은 열어보거나 내용을 출력하지 않는다. 필요한 변수 이름은 .env.example 에서 확인한다.
- 새 환경변수가 필요하면 .env.example 에 이름과 설명만 추가하고, 실제 값은 사용자에게 입력을 요청한다.
- GitHub Actions 의 비밀값은 Repository Secrets 를 사용한다. 워크플로 파일에 값을 쓰지 않는다.
- cron-job.org 가 GitHub API 를 호출할 때 쓰는 토큰(PAT)은 코드·문서·로그 어디에도 적지 않는다.
  문서에는 "토큰 종류, 권한 범위, 만료일 확인 필요" 수준까지만 기록한다.

## 알림 발송 (외부 전송)
- 다음 명령은 실제 텔레그램/슬랙/디스코드로 메시지를 보낸다. 실행 전 반드시 사용자 확인.
  - `python main.py --notify`, `python scheduler.py --now`, `python main.py --scheduler`
- 알림 실행 경로: cron-job.org(스케줄) → GitHub API dispatch 호출 → GitHub Actions 워크플로 실행 → 알림 발송
- .github/workflows/ 의 트리거(on:) 는 cron-job.org 가 호출하는 진입점이다.
  workflow_dispatch / repository_dispatch 설정, 워크플로 파일명, event_type, 입력값 이름을
  바꾸거나 지우면 외부 스케줄이 조용히 실패한다. 변경 전 반드시 사용자 확인을 받고,
  cron-job.org 쪽에서 함께 바꿔야 할 항목을 보고한다.
- 워크플로에 schedule(cron) 트리거를 다시 추가하지 않는다. (cron-job.org 와 중복 발송됨)
- 스케줄 시각 변경은 cron-job.org 에서 사용자가 직접 한다. 에이전트는 docs 의 스케줄 표 갱신만 한다.

## 사용자 데이터
- watchlist.json 은 사용자가 관리하는 관심종목 데이터다.
  코드 작업 중 내용을 임의로 바꾸거나 테스트 데이터로 덮어쓰지 않는다.
  구조(스키마) 변경이 필요하면 기존 데이터 이전 방법과 함께 먼저 제안한다.

## 캐시 (.cache/)
- .cache/*.parquet 은 재생성 가능한 시세 캐시다. 커밋하지 않는다.
- 캐시 형식(컬럼, 파일명 규칙)을 바꾸면 기존 캐시와의 호환 여부를 보고한다.
- 캐시 삭제는 사용자 확인 후 진행하고, 삭제 시 재수집에 걸리는 부담(API 호출량)을 함께 알린다.
