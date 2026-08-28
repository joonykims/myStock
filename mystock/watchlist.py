import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

DEFAULT_WATCHLIST_PATH = "watchlist.json"

DEFAULT_WATCHLIST_DATA = {
    "보유종목": [
        {"ticker": "005930", "name": "삼성전자", "anchor": "2026-01-02", "memo": "주력 핵심 보유"},
        {"ticker": "NVDA", "name": "엔비디아", "anchor": "2026-01-02", "memo": "AI 가속기 대장주"},
    ],
    "초관심종목": [
        {"ticker": "000660", "name": "SK하이닉스", "anchor": "2026-01-02", "memo": "HBM 실적 모멘텀"},
        {"ticker": "QQQ", "name": "나스닥 100 ETF", "anchor": "2026-01-02", "memo": "미국 기술주 지수 추종"},
        {"ticker": "TSLA", "name": "테슬라", "anchor": "2026-01-02", "memo": "자율주행 및 로보택시"},
    ],
    "관심종목": [
        {"ticker": "005380", "name": "현대차", "anchor": "2026-01-02", "memo": "주주환원 및 친환경차"},
        {"ticker": "373220", "name": "LG에너지솔루션", "anchor": "2026-01-02", "memo": "2차전지"},
        {"ticker": "035420", "name": "NAVER", "anchor": "2026-01-02", "memo": "플랫폼 및 AI 서비스"},
        {"ticker": "035720", "name": "카카오", "anchor": "2026-01-02", "memo": "바닥권 수급 턴어라운드"},
        {"ticker": "AAPL", "name": "애플", "anchor": "2026-01-02", "memo": "온디바이스 AI"},
        {"ticker": "MSFT", "name": "마이크로소프트", "anchor": "2026-01-02", "memo": "클라우드 및 생성형 AI"},
        {"ticker": "SPY", "name": "S&P 500 ETF", "anchor": "2026-01-02", "memo": "미국 대형주 시장 지수"},
    ],
}


def get_watchlist_file_path(custom_path: Optional[str] = None) -> Path:
    """Resolve the absolute path to watchlist.json."""
    if custom_path:
        return Path(custom_path)
    # Check current directory or project root
    curr = Path.cwd() / DEFAULT_WATCHLIST_PATH
    if curr.exists():
        return curr
    pkg_root = Path(__file__).resolve().parent.parent / DEFAULT_WATCHLIST_PATH
    return pkg_root


def load_watchlist(file_path: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Load stock watchlist categories from JSON file.
    If the file does not exist, creates it with default data.
    """
    path = get_watchlist_file_path(file_path)
    if not path.exists():
        save_watchlist(DEFAULT_WATCHLIST_DATA, str(path))
        return DEFAULT_WATCHLIST_DATA

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception as e:
        print(f"[Watchlist Warning] Failed to read {path} ({e}), using default watchlist.")
    return DEFAULT_WATCHLIST_DATA


def save_watchlist(data: Dict[str, List[Dict[str, Any]]], file_path: Optional[str] = None) -> bool:
    """Save stock watchlist to JSON file."""
    path = get_watchlist_file_path(file_path)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[Watchlist Error] Failed to save {path}: {e}")
        return False


def get_category_tickers(category: str, file_path: Optional[str] = None) -> List[str]:
    """Get list of ticker strings for a specific category."""
    watchlist = load_watchlist(file_path)
    items = watchlist.get(category, [])
    return [item["ticker"] if isinstance(item, dict) else str(item) for item in items]


def get_all_tickers(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get all tickers across all categories with category tag.
    Returns list of dicts: [{'ticker': ..., 'name': ..., 'category': ..., 'anchor': ..., 'memo': ...}]
    """
    watchlist = load_watchlist(file_path)
    all_list = []
    seen = set()

    for cat, items in watchlist.items():
        for item in items:
            if isinstance(item, dict):
                t = item.get("ticker", "")
                if t and t not in seen:
                    seen.add(t)
                    all_list.append({
                        "ticker": t,
                        "name": item.get("name", t),
                        "category": cat,
                        "anchor": item.get("anchor"),
                        "memo": item.get("memo", ""),
                    })
            elif isinstance(item, str) and item not in seen:
                seen.add(item)
                all_list.append({
                    "ticker": item,
                    "name": item,
                    "category": cat,
                    "anchor": None,
                    "memo": "",
                })

    return all_list


def add_ticker_to_category(
    category: str,
    ticker: str,
    name: Optional[str] = None,
    anchor: Optional[str] = None,
    memo: str = "",
    file_path: Optional[str] = None,
) -> bool:
    """Add or update a ticker in a category."""
    watchlist = load_watchlist(file_path)
    if category not in watchlist:
        watchlist[category] = []

    # Remove existing if already present in this category
    clean_ticker = ticker.strip().upper()
    watchlist[category] = [
        item for item in watchlist[category]
        if (item.get("ticker", "").strip().upper() if isinstance(item, dict) else str(item).strip().upper()) != clean_ticker
    ]

    watchlist[category].append({
        "ticker": clean_ticker,
        "name": name or clean_ticker,
        "anchor": anchor,
        "memo": memo,
    })

    return save_watchlist(watchlist, file_path)


def remove_ticker_from_category(
    category: str,
    ticker: str,
    file_path: Optional[str] = None,
) -> bool:
    """Remove a ticker from a category."""
    watchlist = load_watchlist(file_path)
    if category not in watchlist:
        return False

    clean_ticker = ticker.strip().upper()
    watchlist[category] = [
        item for item in watchlist[category]
        if (item.get("ticker", "").strip().upper() if isinstance(item, dict) else str(item).strip().upper()) != clean_ticker
    ]

    return save_watchlist(watchlist, file_path)


def move_ticker_between_categories(
    source_category: str,
    target_category: str,
    ticker: str,
    file_path: Optional[str] = None,
) -> bool:
    """Move a ticker from source_category to target_category."""
    watchlist = load_watchlist(file_path)
    if source_category not in watchlist:
        return False

    clean_ticker = ticker.strip().upper()
    found_item = None
    new_source_list = []

    for item in watchlist[source_category]:
        t = item.get("ticker", "").strip().upper() if isinstance(item, dict) else str(item).strip().upper()
        if t == clean_ticker:
            found_item = item
        else:
            new_source_list.append(item)

    if not found_item:
        return False

    watchlist[source_category] = new_source_list

    if target_category not in watchlist:
        watchlist[target_category] = []

    # Remove from target if already there before adding
    watchlist[target_category] = [
        item for item in watchlist[target_category]
        if (item.get("ticker", "").strip().upper() if isinstance(item, dict) else str(item).strip().upper()) != clean_ticker
    ]
    watchlist[target_category].append(found_item)

    return save_watchlist(watchlist, file_path)


def copy_ticker_between_categories(
    source_category: str,
    target_category: str,
    ticker: str,
    file_path: Optional[str] = None,
) -> bool:
    """Copy a ticker from source_category to target_category (preserves in source)."""
    watchlist = load_watchlist(file_path)
    if source_category not in watchlist:
        return False

    clean_ticker = ticker.strip().upper()
    found_item = None

    for item in watchlist[source_category]:
        t = item.get("ticker", "").strip().upper() if isinstance(item, dict) else str(item).strip().upper()
        if t == clean_ticker:
            found_item = dict(item) if isinstance(item, dict) else {"ticker": str(item), "name": str(item)}
            break

    if not found_item:
        return False

    if target_category not in watchlist:
        watchlist[target_category] = []

    # Replace or add in target
    watchlist[target_category] = [
        item for item in watchlist[target_category]
        if (item.get("ticker", "").strip().upper() if isinstance(item, dict) else str(item).strip().upper()) != clean_ticker
    ]
    watchlist[target_category].append(found_item)

    return save_watchlist(watchlist, file_path)

