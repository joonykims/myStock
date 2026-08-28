# myStock - 주식 수급 지표 분석 & 다이버전스 자동 알림 시스템

이 프로젝트는 **AVWAP (Anchored VWAP, 고정형 거래량 가중 평균가)**과 **OBV (On-Balance Volume) 다이버전스 탐지 알고리즘**을 활용하여 스마트 머니의 매집/분산 수급 궤적과 가격 변곡점을 정밀하게 추적하는 주식 분석 및 자동 알림 도구입니다.

---

## 📌 주요 기능

1. **AVWAP (고정형 거래량 가중 평균가) 추적**
   - 특정 기준일(Anchor Date, 예: 분기 실적 발표일, 신저가/신고가, 연초 등) 이후 유입된 자금의 실제 평균 단가를 산출하여 지지/저항 라인으로 활용.
2. **OBV (거래량 누적 지표) & 20-EMA**
   - 가격 등락에 따른 거래량 누적 에너지를 추적하고 단기 수급 우위 판별.
3. **OBV 다이버전스 자동 감지 엔진 (`scipy` 기반)**
   - **★ 강세 다이버전스 (Bullish)**: 주가 저점 갱신/횡보 vs OBV 저점 상승 ➔ 바닥권 스마트머니 매집 신호 (매수)
   - **⚠️ 약세 다이버전스 (Bearish)**: 주가 고점 갱신 vs OBV 고점 하락 ➔ 고점 물량 분산/차익실현 경고 신호 (매도)
4. **인터랙티브 웹 대시보드 (`Streamlit` & `Plotly`)**
   - 브라우저에서 실시간 차트 분석, 전종목 수급 스캐너, 지표 전략 가이드 제공.
5. **다채널 자동 알림 봇 (`Telegram`, `Slack`, `Discord`)**
   - 장 마감 시간에 맞춰 신규 발생한 강세/약세 다이버전스 시그널을 자동으로 분석하여 메신저로 발송.

---

## 🕒 시장별 추천 조회 시간대

OBV 다이버전스는 **하루 동안의 모든 매수/매도 공방이 끝난 '최종 종가'를 기준**으로 계산할 때 가장 높은 신뢰도를 발휘합니다 (장중 분봉 노이즈 방지).

| 대상 시장 | 추천 조회 주기 | 최적의 확인 시간대 (KST) | 목적 및 활용법 |
| :--- | :---: | :---: | :--- |
| **국내 주식 (KOSPI / KOSDAQ)** | **매일 1회 (월~금)** | **오후 3:45 ~ 4:30**<br>(정규장 마감 및 데이터 정산 직후) | 당일 종가 확정 후 **세력 매집(강세) / 분산(약세) 신호 포착**, 다음 날 시초가 매매 전략 수립 |
| **미국 주식 / ETF (나스닥 등)** | **매일 1회 (화~토)** | **아침 6:30 ~ 7:30**<br>(미국장 마감 직후) | 미국 장 마감 결과 반영 및 **출근 전 모닝 브리핑**, 보유 종목 수급 상태 점검 |
| **장중 수급 확인 (선택)** | **장중 1~2회** | **오후 2:00 ~ 2:30** | 주가가 **AVWAP(세력 평단가)** 지지선에 터치하고 반등하는지 장중 타점 점검 |

---

## 🚀 설치 및 환경 설정

```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. (선택) 알림 메신저 환경 변수 설정
cp .env.example .env
```

`.env` 파일에 텔레그램, 슬랙, 또는 디스코드 웹훅 정보를 입력하면 자동으로 알림이 발송됩니다:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

## 💻 사용법

### 1. 🌐 웹 인터랙티브 대시보드 실행

```bash
# 방법 1: main.py를 통한 실행
python main.py --dashboard

# 방법 2: streamlit 직접 실행
streamlit run app.py
```

---

### 2. 🔔 자동 알림 발송 및 스케줄러 실행

```bash
# [즉시 알림] 현재 시점 기준 전체 관심 종목 스캔 후 메신저 알림 1회 즉시 발송
python main.py --notify
# 또는
python scheduler.py --now

# [백그라운드 스케줄러] 국내장(15:45) 및 미국장(06:30) 마감 시간에 자동 실행 유지
python main.py --scheduler
# 또는
python scheduler.py
```

---

### 3. 단일 종목 분석 (기본: 삼성전자 `005930`)

```bash
# 콘솔 요약 리포트
python main.py -t 005930

# 특정 앵커일 지정 및 인터랙티브 차트 생성 후 브라우저 열기
python main.py -t 005930 -a 2026-01-02 -c --open

# 미국 주식(엔비디아 NVDA, QQQ ETF) 분석
python main.py -t NVDA -c --open
python main.py -t QQQ -c --open
```

---

### 4. 보유/관심 종목 그룹별 스캐너 모드

`watchlist.json`에 등록된 그룹별(보유종목, 초관심종목, 관심종목)로 선별 스캔하거나 알림을 보낼 수 있습니다:

```bash
# 전체 등록 종목 일괄 스캔
python main.py --scan

# '보유종목' 그룹만 선별 스캔
python main.py --scan -g 보유종목

# '초관심종목' 그룹만 선별 스캔 및 텔레그램 알림 발송
python main.py --scan -g 초관심종목
python main.py --notify -g 초관심종목
```

---

### 5. 📁 종목 목록 관리 (`watchlist.json`)

프로젝트 루트의 `watchlist.json` 파일을 직접 수정하거나, **웹 대시보드의 [⚙️ 종목 관리] 탭**에서 마우스 클릭으로 간편하게 종목을 추가/수정/삭제할 수 있습니다:

```json
{
  "보유종목": [
    { "ticker": "005930", "name": "삼성전자", "anchor": "2026-01-02", "memo": "주력 핵심 보유" },
    { "ticker": "NVDA", "name": "엔비디아", "anchor": "2026-01-02", "memo": "AI 가속기 대장주" }
  ],
  "초관심종목": [
    { "ticker": "000660", "name": "SK하이닉스", "anchor": "2026-01-02", "memo": "HBM 실적 모멘텀" },
    { "ticker": "QQQ", "name": "나스닥 100 ETF", "anchor": "2026-01-02", "memo": "미국 기술주 지수 추종" }
  ],
  "관심종목": [
    { "ticker": "005380", "name": "현대차", "anchor": "2026-01-02", "memo": "주주환원 및 친환경차" }
  ]
}
```


---

## ⏰ OS 스케줄러 등록 방법 (무중단 자동화)

### Windows 작업 스케줄러 (Task Scheduler) 등록
1. `Win + R` ➔ `taskschd.msc` 실행
2. **기본 작업 만들기** 클릭
3. **트리거**: 매일 (월~금 오후 3시 45분 / 화~토 아침 6시 30분)
4. **동작**: 프로그램 시작
   - 프로그램/스크립트: `python.exe` 절대 경로
   - 인수 추가: `main.py --notify`
   - 시작 위치: `G:\Dev\myStock`

### Linux / macOS Crontab 등록
```bash
# crontab -e
# 국내장 마감 알림: 매주 월~금 15:45
45 15 * * 1-5 cd /path/to/myStock && python3 main.py --notify >> notify.log 2>&1

# 미국장 마감 알림: 매주 화~토 06:30
30 6 * * 2-6 cd /path/to/myStock && python3 main.py --notify >> notify.log 2>&1
```

---

## 📂 프로젝트 구조

```
myStock/
├── app.py                # Streamlit 인터랙티브 웹 대시보드
├── scheduler.py          # 자동 스케줄러 및 알림 발송 엔진
├── mystock/
│   ├── __init__.py       # 모듈 진입점
│   ├── data_loader.py    # 3단계 폴백 + 지수 백오프 데이터 수집기
│   ├── indicators.py     # AVWAP, OBV, SMA 연산 모듈
│   ├── divergence.py     # Scipy 기반 다이버전스 자동 감지 엔진
│   ├── visualizer.py     # Plotly 인터랙티브 차트 생성기
│   └── notifier.py       # Telegram/Slack/Discord 알림 매니저
├── main.py               # 메인 통합 CLI 엔트리포인트
├── tests/
│   └── test_mystock.py   # 단위 테스트 슈트
├── .env.example          # 알림 메신저 환경 변수 템플릿
├── CHANGELOG.md          # 버전별 상세 변경 및 개선 이력
├── requirements.txt      # 의존성 패키지 목록
└── README.md             # 프로젝트 설명서
```
