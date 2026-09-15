---
name: verify-change
description: 코드 변경 후 "완료"라고 보고하기 전에 테스트, 문법 점검, 범위 점검을 실제로 수행한다. 구현을 마쳤을 때, 커밋 전, 사용자가 "확인해줘/검증해줘"라고 할 때 사용.
---

# 변경 검증 (myStock / Python)

## 절차
1. 문법 점검
   ```bash
   python -m compileall -q app.py main.py scheduler.py mystock
   ```
2. 단위 테스트
   ```bash
   python -m unittest discover tests -v
   ```
   - 기존 18개 테스트 + 새로 추가한 테스트가 모두 통과해야 한다.
   - 실패하면 원인을 수정한 뒤 재실행. 같은 원인으로 2회 실패하면 멈추고 보고한다.
3. 의존성을 바꿨다면 `pip install -r requirements.txt` 가 오류 없이 끝나는지 확인한다.
4. UI(app.py)를 바꿨다면 사용자에게 `streamlit run app.py` 로 화면 확인을 요청한다.
   (에이전트가 확인하지 못했으면 "화면 미검증"으로 보고)
5. 시세 수집·지표·스캐너 로직을 바꿨다면 smoke-test 스킬도 실행한다.
6. `git status`, `git diff --stat` 으로 변경 범위를 확인한다.
   watchlist.json, .env, .cache/ 가 변경 목록에 있으면 즉시 보고한다.

## 체크리스트
- [ ] compileall 통과
- [ ] unittest 전체 통과 (skip 없음)
- [ ] 새/변경 로직에 테스트 있음
- [ ] mystock/ 에 streamlit import 없음
- [ ] 비밀정보·watchlist.json·캐시 변경 없음
- [ ] 계획서 체크박스, 필요 시 DECISIONS.md / CHANGELOG.md 갱신

## 보고 형식
```
## 검증 결과
- 문법: 통과/실패
- 테스트: N개 통과 / N개 실패
- 스모크 테스트: 실행함/해당 없음/실패
- 변경 파일: N개 (목록)
- 미검증 항목: (없으면 "없음")
```
