#!/usr/bin/env python3
"""증권 뉴스 스캔 오케스트레이션 — 관심종목+시황을 Brave로 검색해 raw 데이터 저장.

뉴스 스캐너 페르소나가 실행한다. 이 스크립트는 데이터 수집만 하며,
요약·감성분석은 LLM 에이전트가 raw JSON을 보고 digest 로 작성한다.

사용: python scan_news.py --freshness pd --per-query 6
출력: ~/.agent-workspace/state/news/raw-<timestamp>.json
"""
from __future__ import annotations

import argparse
import datetime
import json

import yaml

from _common import REPO_ROOT, state_dir
from brave_news import search

WATCHLIST = REPO_ROOT / "agent-workspace" / "config" / "watchlist.yaml"


def load_watchlist() -> dict:
    return yaml.safe_load(WATCHLIST.read_text(encoding="utf-8"))


def collect(freshness: str = "pd", per_query: int = 6) -> dict:
    """관심종목별 + 시황 쿼리별로 Brave 검색 결과를 모은다."""
    watch = load_watchlist()
    out: dict = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "freshness": freshness,
        "stocks": [],
        "market": [],
    }
    for stock in watch.get("stocks", []):
        query = f"{stock['name']} 주가 뉴스"
        try:
            headlines = search(query, per_query, freshness)
        except Exception as exc:  # noqa: BLE001
            headlines = [{"error": str(exc)}]
        out["stocks"].append({
            "code": stock["code"], "name": stock["name"],
            "query": query, "headlines": headlines,
        })
    for query in watch.get("market_queries", []):
        try:
            headlines = search(query, per_query, freshness)
        except Exception as exc:  # noqa: BLE001
            headlines = [{"error": str(exc)}]
        out["market"].append({"query": query, "headlines": headlines})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="관심종목 증권 뉴스 스캔")
    ap.add_argument("--freshness", default="pd", choices=["pd", "pw", "pm"])
    ap.add_argument("--per-query", type=int, default=6)
    args = ap.parse_args()

    data = collect(args.freshness, args.per_query)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = state_dir("news") / f"raw-{ts}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"뉴스 raw 데이터 저장: {path}")
    print(f"종목 {len(data['stocks'])}개, 시황쿼리 {len(data['market'])}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
