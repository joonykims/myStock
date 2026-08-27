# myStock - 주식 수급 지표 분석 & 다이버전스 감지 시스템

이 프로젝트는 **AVWAP (Anchored VWAP, 고정형 거래량 가중 평균가)**과 **OBV (On-Balance Volume) 다이버전스 탐지 알고리즘**을 활용하여 스마트 머니의 매집/분산 수급 궤적과 가격 변곡점을 정밀하게 추적하는 주식 분석 도구입니다.

---

## 📌 주요 기능

1. **AVWAP (고정형 거래량 가중 평균가) 추적**
   - 특정 기준일(Anchor Date, 예: 분기 실적 발표일, 신저가/신고가, 연초 등) 이후 유입된 자금의 실제 평균 단가를 산출하여 지지/저항 라인으로 활용.
2. **OBV (거래량 누적 지표) & 20-EMA**
   - 가격 등락에 따른 거래량 누적 에너지를 추적하고 단기 수급 우위 판별.
3. **OBV 다이버전스 자동 감지 엔진 (`scipy` 기반)**
   - **★ 강세 다이버전스 (Bullish)**: 주가 저점 갱신/횡보 vs OBV 저점 상승 ➔ 바닥권 스마트머니 매집 신호
   - **⚠️ 약세 다이버전스 (Bearish)**: 주가 고점 갱신 vs OBV 고점 하락 ➔ 고점 물량 분산/차익실현 경고 신호
4. **인터랙티브 Plotly 차트 리포트 (HTML)**
   - 캔들스틱 + AVWAP + 이동평균선(SMA 20/60) + 거래량 + OBV + 매수/매도 시그널 화살표 및 추세선을 포함한 HTML 차트 생성.
5. **다중 종목 일괄 스캐너 (Market Scanner)**
   - 국내외 주요 종목들의 현재가, AVWAP 이격률, 최근 30일 내 발생한 다이버전스 신호를 한눈에 요약.

---

## 🚀 설치 및 요구사항

```bash
pip install -r requirements.txt
```

---

## 💻 사용법

### 1. 단일 종목 분석 (기본: 삼성전자 `005930`)

```bash
# 기본 분석 (콘솔 요약 리포트)
python main.py -t 005930

# 특정 앵커일(예: 2026년 1월 2일) 지정 및 인터랙티브 차트 생성
python main.py -t 005930 -a 2026-01-02 -c

# 차트 생성 후 웹 브라우저에서 자동 열기
python main.py -t 005930 -c --open
```

### 2. 해외 주식 (미국 기술주 / ETF) 분석

```bash
# 엔비디아(NVDA) 분석 및 차트 생성
python main.py -t NVDA -a 2026-01-02 -c

# 애플(AAPL), 나스닥 100 ETF(QQQ)
python main.py -t AAPL -c
python main.py -t QQQ -c
```

### 3. 관심 종목 일괄 스캐너 모드

```bash
python main.py --scan
```

### 4. 옵션 설명

| 옵션 | 설명 | 기본값 |
| :--- | :--- | :--- |
| `-t`, `--ticker` | 종목 코드 또는 티커 (예: `005930`, `000660`, `NVDA`, `AAPL`) | `005930` |
| `-a`, `--anchor` | AVWAP 앵커 기준일 (`YYYY-MM-DD`) | 당해년도 1월 2일 |
| `-d`, `--days` | 데이터 조회 기간 (일 단위) | `365` |
| `-o`, `--order` | 극값(Peak/Trough) 탐색 윈도우 크기 | `5` |
| `-c`, `--chart` | 인터랙티브 Plotly HTML 차트 생성 | `False` |
| `--open` | 차트 생성 후 브라우저에서 바로 열기 | `False` |
| `--out` | 차트 HTML 저장 경로 지정 | `chart_<ticker>.html` |
| `--scan` | 주요 관심 종목 일괄 스캔 모드 | `False` |

---

## 📂 프로젝트 구조

```
myStock/
├── mystock/
│   ├── __init__.py
│   ├── data_loader.py    # pykrx 및 yfinance 연동 데이터 로더
│   ├── indicators.py     # AVWAP, OBV, 이동평균선 연산
│   ├── divergence.py     # 국소 극값 추출 및 다이버전스 판별 엔진
│   └── visualizer.py     # Plotly 인터랙티브 3분할 차트 생성기
├── main.py               # 메인 CLI 및 스캐너 엔트리포인트
├── requirements.txt      # 의존성 패키지 목록
└── README.md             # 프로젝트 설명서
```
