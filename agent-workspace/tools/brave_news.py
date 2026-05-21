#!/usr/bin/env python3
"""Brave Web Search 클라이언트 — 증권 뉴스/시황 검색.

사용: python brave_news.py "삼성전자 주가 뉴스" --count 8 --freshness pd
api.env 의 brave_search_api_key 를 사용한다.
"""
from __future__ import annotations

import argparse
import json
import sys

import requests

from _common import load_env, require_key

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"


def search(query: str, count: int = 10, freshness: str = "pw",
           country: str = "KR") -> list[dict]:
    """Brave 웹검색. freshness: pd(1일)/pw(1주)/pm(1달). list[{title,url,description,age}]."""
    key = require_key(load_env(), "brave_search_api_key", "brave_api_key")
    headers = {"Accept": "application/json", "X-Subscription-Token": key}
    params = {
        "q": query,
        "count": min(count, 20),
        "freshness": freshness,
        "country": country,
        "search_lang": "ko",
        "ui_lang": "ko-KR",  # Brave는 <lang>-<COUNTRY> 형식을 요구
    }
    resp = requests.get(BRAVE_URL, headers=headers, params=params, timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"Brave API {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    results: list[dict] = []
    for item in data.get("web", {}).get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": item.get("description", ""),
            "age": item.get("age") or item.get("page_age", ""),
        })
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Brave 웹검색으로 증권 뉴스 검색")
    ap.add_argument("query")
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--freshness", default="pw", choices=["pd", "pw", "pm"])
    args = ap.parse_args()
    try:
        results = search(args.query, args.count, args.freshness)
    except Exception as exc:  # noqa: BLE001
        print(f"[brave_news] 오류: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
