"""
mystock/universe.py
───────────────────
Curated market universe presets for leading stock scanning.
Filters out low-liquidity penny stocks / speculative small caps,
focusing on high-liquidity, mega-trend aligned industry leaders.
"""

from typing import List, Dict, Optional

# KOSPI / KOSDAQ representative industry leaders across mega-trends:
# AI/Semiconductor, Power/Infrastructure, Defense, Bio, Automotive, Finance/Value-up, Platform
KOREA_LEADERS: List[Dict[str, str]] = [
    # 반도체 & AI 인프라
    {"ticker": "005930", "name": "삼성전자", "sector": "반도체"},
    {"ticker": "000660", "name": "SK하이닉스", "sector": "반도체/HBM"},
    {"ticker": "042700", "name": "한미반도체", "sector": "반도체장비"},
    {"ticker": "009150", "name": "삼성전기", "sector": "전자부품/MLCC"},
    {"ticker": "278280", "name": "천보", "sector": "반도체/2차전지소재"},
    {"ticker": "005290", "name": "동진쎄미켐", "sector": "반도체소재"},
    {"ticker": "039030", "name": "이오테크닉스", "sector": "반도체장비"},
    {"ticker": "058470", "name": "리노공업", "sector": "반도체테스트"},
    # 전력설비 & 원전 & 인프라
    {"ticker": "267260", "name": "HD현대일렉트릭", "sector": "전력기기"},
    {"ticker": "010120", "name": "LS ELECTRIC", "sector": "전력기기"},
    {"ticker": "006260", "name": "LS", "sector": "지주/전선"},
    {"ticker": "103140", "name": "풍산", "sector": "방산/동제품"},
    {"ticker": "034020", "name": "두산에너빌리티", "sector": "원전/에너지"},
    {"ticker": "015760", "name": "한국전력", "sector": "전력/유틸리티"},
    # 방위산업 & 조선 & 우주항공
    {"ticker": "012450", "name": "한화에어로스페이스", "sector": "방산/우주"},
    {"ticker": "079550", "name": "LIG넥스원", "sector": "방위산업"},
    {"ticker": "042660", "name": "한화오션", "sector": "조선/방산"},
    {"ticker": "329180", "name": "HD현대중공업", "sector": "조선"},
    {"ticker": "010140", "name": "삼성중공업", "sector": "조선"},
    {"ticker": "005380", "name": "현대차", "sector": "자동차"},
    {"ticker": "000270", "name": "기아", "sector": "자동차"},
    {"ticker": "012330", "name": "현대모비스", "sector": "자동차부품"},
    # 2차전지 & 친환경
    {"ticker": "373220", "name": "LG에너지솔루션", "sector": "2차전지"},
    {"ticker": "006400", "name": "삼성SDI", "sector": "2차전지"},
    {"ticker": "051910", "name": "LG화학", "sector": "화학/소재"},
    {"ticker": "005490", "name": "POSCO홀딩스", "sector": "철강/2차전지"},
    {"ticker": "247540", "name": "에코프로비엠", "sector": "양극재"},
    {"ticker": "086520", "name": "에코프로", "sector": "2차전지지주"},
    # 바이오 & 헬스케어
    {"ticker": "207940", "name": "삼성바이오로직스", "sector": "바이오CDMO"},
    {"ticker": "068270", "name": "셀트리온", "sector": "바이오시밀러"},
    {"ticker": "000100", "name": "유한양행", "sector": "신약개발"},
    {"ticker": "196170", "name": "알테오젠", "sector": "바이오플랫폼"},
    {"ticker": "141080", "name": "레고켐바이오", "sector": "ADC신약"},
    # 플랫폼 & 인터넷 & IT
    {"ticker": "035420", "name": "NAVER", "sector": "인터넷플랫폼"},
    {"ticker": "035720", "name": "카카오", "sector": "인터넷/컨텐츠"},
    {"ticker": "259960", "name": "크래프톤", "sector": "게임"},
    # 금융 & 주주환원 밸류업
    {"ticker": "105560", "name": "KB금융", "sector": "은행/금융"},
    {"ticker": "055550", "name": "신한지주", "sector": "은행/금융"},
    {"ticker": "086790", "name": "하나금융지주", "sector": "은행/금융"},
    {"ticker": "000810", "name": "삼성화재", "sector": "보험"},
    {"ticker": "017670", "name": "SK텔레콤", "sector": "통신/고배당"},
]

# US Mega-Cap Leaders & Benchmark ETFs
US_LEADERS: List[Dict[str, str]] = [
    {"ticker": "NVDA", "name": "엔비디아 (NVIDIA)", "sector": "AI가속기/반도체"},
    {"ticker": "MSFT", "name": "마이크로소프트 (Microsoft)", "sector": "AI/클라우드"},
    {"ticker": "AAPL", "name": "애플 (Apple)", "sector": "온디바이스AI/빅테크"},
    {"ticker": "GOOGL", "name": "알파벳 Class A (Google)", "sector": "AI/검색플랫폼"},
    {"ticker": "AMZN", "name": "아마존 (Amazon)", "sector": "클라우드/이커머스"},
    {"ticker": "META", "name": "메타 (Meta)", "sector": "AI/소셜미디어"},
    {"ticker": "TSLA", "name": "테슬라 (Tesla)", "sector": "자율주행/전기차"},
    {"ticker": "AVGO", "name": "브로드컴 (Broadcom)", "sector": "네트워킹/ASIC"},
    {"ticker": "TSM", "name": "TSMC (ADR)", "sector": "파운드리"},
    {"ticker": "AMD", "name": "AMD", "sector": "CPU/AI칩"},
    {"ticker": "QCOM", "name": "퀄컴 (Qualcomm)", "sector": "모바일/NPU"},
    {"ticker": "ARM", "name": "ARM 홀딩스", "sector": "반도체IP"},
    {"ticker": "ASML", "name": "ASML (ADR)", "sector": "반도체노광장비"},
    {"ticker": "PLTR", "name": "팔란티어 (Palantir)", "sector": "엔터프라이즈AI"},
    {"ticker": "LLY", "name": "일라이릴리 (Eli Lilly)", "sector": "비만치료제/헬스케어"},
    {"ticker": "SPY", "name": "SPDR S&P 500 ETF", "sector": "미국시장지수"},
    {"ticker": "QQQ", "name": "Invesco QQQ (나스닥 100)", "sector": "기술주지수"},
]

def get_universe_items(universe_name: str = "korea") -> List[Dict[str, str]]:
    key = (universe_name or "").strip().lower()
    if key in ["korea", "kr", "국내", "국내대표", "국내주도주"]:
        return list(KOREA_LEADERS)
    elif key in ["us", "usa", "미국", "미국대표", "미국주도주"]:
        return list(US_LEADERS)
    elif key in ["all", "전체", "글로벌"]:
        return list(KOREA_LEADERS) + list(US_LEADERS)
    else:
        return list(KOREA_LEADERS)
