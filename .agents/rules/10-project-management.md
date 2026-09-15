---
trigger: always_on
---

# 프로젝트 관리 규칙

## 기록 시스템 (docs/ 가 유일한 진실)
- 대화 내용은 세션이 끝나면 사라진다. 남겨야 할 것은 반드시 docs/ 에 파일로 남긴다.
- docs/PROGRESS.md : 현재 상태, 진행 중, 다음 할 일, 막힌 점
- docs/plans/YYYYMMDD-작업명.md : 중 규모 이상 작업의 계획서
- docs/DECISIONS.md : 설계 결정 기록 (ADR 요약형)
- docs/LESSONS.md : 에이전트가 틀렸던 것과 교정 내용

## 세션 시작 시
1. docs/PROGRESS.md 를 읽는다.
2. 진행 중인 계획서가 있으면 docs/plans/ 에서 읽는다.
3. 현재 요청이 기존 계획과 어떻게 연결되는지 한 줄로 요약한 뒤 시작한다.

## 작업 중
- 계획서의 체크박스를 단계가 끝날 때마다 갱신한다.
- 계획과 다르게 진행해야 하면 멈추고 이유와 대안을 보고한 뒤 승인받는다.
- 같은 오류로 2회 이상 수정에 실패하면 멈추고, 시도한 내용과 가설을 보고한다.

## 세션 종료 시
- session-handoff 스킬을 사용해 PROGRESS.md 를 갱신한다.

## 커밋
- 형식: `type(scope): summary` (feat, fix, refactor, test, docs, chore)
- 커밋 단위는 계획서의 단계 단위와 맞춘다.
- 사용자가 요청하지 않으면 push 하지 않는다.
