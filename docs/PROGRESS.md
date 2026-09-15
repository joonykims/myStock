# 진행 현황

_마지막 갱신: 2026-09-15_

## 현재 목표
- 에이전트 하네스(AGENTS.md, docs/, .agents/) 템플릿을 myStock 실제 구조·규칙에 맞게 채우기

## 진행 중
- (없음)

## 다음 할 일 (우선순위 순)
1. D-002 Python 버전 결정 (로컬 3.14 vs CI·devcontainer 3.11) — docs/DECISIONS.md 참고
2. GitHub Actions(market_scheduler.yml)에 unittest 실행 스텝 추가 검토
3. 스케줄 표 기입 (cron-job.org 실행 시각 확인) — docs/ARCHITECTURE.md "알림 실행 경로" 절의 표

## 막힌 점 / 확인 필요
- Python 버전 기준 미확정 (D-002, 사용자 확인 필요)

## 최근 완료
- 2026-09-15: AGENTS.md / docs/ARCHITECTURE.md / docs/DECISIONS.md 를 실제 프로젝트 내용으로 채우고, `.agents/rules/20-java-spring.md`(무관한 Java 규칙) 삭제
