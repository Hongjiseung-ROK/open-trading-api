#!/usr/bin/env python3
"""Firecrawl 스크레이프 클라이언트 — 뉴스 기사 본문을 마크다운으로 추출.

사용: python firecrawl_fetch.py "https://..." --max-chars 4000
api.env 의 firecrawl_api_key 를 사용한다.
"""
from __future__ import annotations

import argparse
import json
import sys

import requests

from _common import load_env, require_key

V2_URL = "https://api.firecrawl.dev/v2/scrape"
V1_URL = "https://api.firecrawl.dev/v1/scrape"


def scrape(url: str, timeout: int = 60) -> dict:
    """주어진 URL 본문을 마크다운으로 추출. {url,title,markdown} 반환."""
    key = require_key(load_env(), "firecrawl_api_key")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {"url": url, "formats": ["markdown"], "onlyMainContent": True}
    resp = requests.post(V2_URL, headers=headers, json=body, timeout=timeout)
    if resp.status_code in (404, 405):  # v2 미지원 시 v1 폴백
        resp = requests.post(V1_URL, headers=headers, json=body, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()
    data = payload.get("data", payload)
    metadata = data.get("metadata") or {}
    return {
        "url": url,
        "title": metadata.get("title", ""),
        "markdown": data.get("markdown", ""),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Firecrawl로 기사 본문 추출")
    ap.add_argument("url")
    ap.add_argument("--max-chars", type=int, default=4000)
    args = ap.parse_args()
    try:
        out = scrape(args.url)
    except Exception as exc:  # noqa: BLE001
        print(f"[firecrawl_fetch] 오류: {exc}", file=sys.stderr)
        return 1
    out["markdown"] = out["markdown"][: args.max_chars]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
