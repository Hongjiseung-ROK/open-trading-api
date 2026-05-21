#!/usr/bin/env python3
"""매매안(주문 제안)을 사람 승인 대기 큐에 기록한다 — 포트폴리오 매니저 전용.

이 스크립트는 KIS 주문 API를 호출하지 않는다. 제안 JSON 파일만 만든다.
실제 주문은 approval_gate.py 에서 사람이 승인한 뒤에만 전송된다.
모든 매매안은 config/risk_limits.yaml 의 하드 한도로 검증된다.

사용:
  python propose.py --code 005930 --name 삼성전자 --side buy \\
      --qty 5 --price 70000 --reason "호실적 뉴스, 외국인 순매수" \\
      --news-ref raw-20260521-1530.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import uuid
from pathlib import Path

import yaml

from _common import REPO_ROOT, state_dir

RISK = REPO_ROOT / "agent-workspace" / "config" / "risk_limits.yaml"
WATCHLIST = REPO_ROOT / "agent-workspace" / "config" / "watchlist.yaml"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate(code: str, side: str, qty: int, price: int,
             risk: dict, watch: dict) -> list[str]:
    """리스크 한도 위반 사유 목록을 반환한다 (빈 리스트면 통과)."""
    errors: list[str] = []
    limits = risk.get("limits", {})
    value = qty * price
    if side not in limits.get("allowed_sides", ["buy", "sell"]):
        errors.append(f"허용되지 않은 매매구분: {side}")
    if qty <= 0 or price <= 0:
        errors.append("수량/가격은 양수여야 합니다")
    if qty > limits.get("max_qty_per_order", 10 ** 9):
        errors.append(f"수량 한도 초과: {qty} > {limits['max_qty_per_order']}")
    if value > limits.get("max_order_value_krw", 10 ** 18):
        errors.append(
            f"주문금액 한도 초과: {value:,}원 > {limits['max_order_value_krw']:,}원")
    if limits.get("watchlist_only", True):
        codes = {s["code"] for s in watch.get("stocks", [])}
        if code not in codes:
            errors.append(f"관심종목(watchlist) 외 종목입니다: {code}")
    pending = list(state_dir("orders", "pending").glob("*.json"))
    if len(pending) >= limits.get("max_open_proposals", 10):
        errors.append(f"대기 매매안 수 한도 초과: {len(pending)}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="매매안을 승인 대기 큐에 기록")
    ap.add_argument("--code", required=True, help="종목코드 6자리")
    ap.add_argument("--name", default="", help="종목명")
    ap.add_argument("--side", required=True, choices=["buy", "sell"])
    ap.add_argument("--qty", required=True, type=int, help="주문수량")
    ap.add_argument("--price", required=True, type=int, help="주문단가(원)")
    ap.add_argument("--order-type", default="limit", choices=["limit", "market"])
    ap.add_argument("--reason", required=True, help="매매 근거 (뉴스/분석)")
    ap.add_argument("--news-ref", default="", help="참고한 뉴스 raw/digest 파일명")
    args = ap.parse_args()

    risk, watch = _load(RISK), _load(WATCHLIST)
    errors = validate(args.code, args.side, args.qty, args.price, risk, watch)
    if errors:
        print("❌ 매매안 거부 — 리스크 한도 위반:", file=sys.stderr)
        for err in errors:
            print(f"   - {err}", file=sys.stderr)
        return 1

    proposal_id = (datetime.datetime.now().strftime("%Y%m%d-%H%M%S-")
                   + uuid.uuid4().hex[:6])
    proposal = {
        "id": proposal_id,
        "status": "pending_approval",
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "code": args.code,
        "name": args.name,
        "side": args.side,
        "qty": args.qty,
        "price": args.price,
        "order_type": args.order_type,
        "est_value_krw": args.qty * args.price,
        "reason": args.reason,
        "news_ref": args.news_ref,
        "mode": "live" if risk.get("mode") == "live" else "paper",
    }
    path = state_dir("orders", "pending") / f"{proposal_id}.json"
    path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    print(f"✅ 매매안 기록: {path}")
    print(f"   {args.side.upper()} {args.name}({args.code}) "
          f"{args.qty}주 @ {args.price:,}원 = {proposal['est_value_krw']:,}원")
    print("   → 사람 승인 대기. approval_gate.py 로 검토하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
