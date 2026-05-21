#!/usr/bin/env python3
"""KIS 국내주식 조회 CLI (읽기 전용) — 현재가 / 잔고.

포트폴리오 매니저가 매매안을 만들기 전 시세·보유현황을 확인할 때 사용한다.
실행 모드(paper/real)는 config/risk_limits.yaml 의 mode 를 따른다.

사용: python kis_quote.py price 005930
      python kis_quote.py balance
"""
from __future__ import annotations

import argparse
import json
import sys

import yaml

from _common import REPO_ROOT
from kis_client import KisClient

RISK = REPO_ROOT / "agent-workspace" / "config" / "risk_limits.yaml"


def _risk() -> dict:
    return yaml.safe_load(RISK.read_text(encoding="utf-8"))


def _mode(risk: dict) -> str:
    return "real" if risk.get("mode") == "live" else "paper"


def main() -> int:
    ap = argparse.ArgumentParser(description="KIS 국내주식 조회 (읽기 전용)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    price = sub.add_parser("price", help="현재가")
    price.add_argument("code")
    sub.add_parser("balance", help="잔고")
    args = ap.parse_args()

    try:
        risk = _risk()
        client = KisClient(_mode(risk))
        if args.cmd == "price":
            print(json.dumps(client.current_price(args.code),
                             ensure_ascii=False, indent=2))
        else:
            account = risk.get("account") or {}
            cano = account.get("cano") or client.cfg.get(
                "my_acct_stock" if client.mode == "real" else "my_paper_stock", "")
            prdt = account.get("acnt_prdt_cd") or "01"
            print(json.dumps(client.balance(cano, prdt),
                             ensure_ascii=False, indent=2))
    except Exception as exc:  # noqa: BLE001
        print(f"[kis_quote] 오류: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
