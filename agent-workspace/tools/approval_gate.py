#!/usr/bin/env python3
"""사람 승인 게이트 — 대기 매매안을 검토하고 승인 시에만 실주문을 전송한다.

⚠️ 이 스크립트만 KIS 주문 API를 호출한다. 반드시 사람이 터미널에서 실행할 것.
에이전트(뉴스 스캐너 / 포트폴리오 매니저)는 이 스크립트를 실행하지 않는다.

사용:
  python approval_gate.py list      # 대기 매매안 보기
  python approval_gate.py review    # 대화형 검토·승인 (실주문 전송)
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

import yaml

from _common import REPO_ROOT, state_dir
from kis_client import KisClient

RISK = REPO_ROOT / "agent-workspace" / "config" / "risk_limits.yaml"


def _risk() -> dict:
    return yaml.safe_load(RISK.read_text(encoding="utf-8"))


def _pending() -> list[Path]:
    return sorted(state_dir("orders", "pending").glob("*.json"))


def _show(p: dict) -> None:
    print("─" * 64)
    print(f"  ID      : {p['id']}")
    print(f"  종목    : {p.get('name', '')} ({p['code']})")
    print(f"  주문    : {p['side'].upper()}  {p['qty']}주 @ {p['price']:,}원  "
          f"({p.get('order_type', 'limit')})")
    print(f"  예상금액: {p['est_value_krw']:,}원      제안모드: {p.get('mode')}")
    print(f"  근거    : {p.get('reason', '')}")
    if p.get("news_ref"):
        print(f"  뉴스참고: {p['news_ref']}")
    print("─" * 64)


def _daily_executed_value() -> int:
    total = 0
    today = datetime.date.today().isoformat()
    for f in state_dir("orders", "executed").glob("*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        if str(data.get("executed_at", "")).startswith(today):
            total += data.get("est_value_krw", 0)
    return total


def cmd_list() -> int:
    items = _pending()
    if not items:
        print("대기 중인 매매안이 없습니다.")
        return 0
    print(f"대기 매매안 {len(items)}건:\n")
    for f in items:
        _show(json.loads(f.read_text(encoding="utf-8")))
    return 0


def cmd_review() -> int:
    risk = _risk()
    mode = "real" if risk.get("mode") == "live" else "paper"
    limits = risk.get("limits", {})
    items = _pending()
    if not items:
        print("대기 중인 매매안이 없습니다.")
        return 0

    label = "⚠️  실제 자금 (실거래)" if mode == "real" else "모의투자 (paper)"
    print(f"실행 모드: {mode.upper()}  —  {label}\n")
    client: KisClient | None = None

    for f in items:
        proposal = json.loads(f.read_text(encoding="utf-8"))
        _show(proposal)
        choice = input("  [a]승인  [r]거부  [s]건너뛰기  ? ").strip().lower()
        if choice not in ("a", "r"):
            print("  → 건너뜀.\n")
            continue
        if choice == "r":
            f.rename(state_dir("orders", "rejected") / f.name)
            print("  → 거부. rejected/ 로 이동.\n")
            continue

        # --- 승인 경로: 실행 직전 한도 재검증 ---
        if (_daily_executed_value() + proposal["est_value_krw"]
                > limits.get("daily_order_value_krw", 10 ** 18)):
            print("  ❌ 일일 누적 주문금액 한도 초과 — 실행 취소.\n")
            continue
        if mode == "real":
            print("  ⚠️  실거래 주문입니다. 진행하려면 정확히 'CONFIRM' 을 입력하세요.")
            if input("  > ").strip() != "CONFIRM":
                print("  → 취소됨.\n")
                continue

        # --- 실제 주문 전송 ---
        try:
            if client is None:
                client = KisClient(mode)
            account = risk.get("account") or {}
            cano = account.get("cano") or client.cfg.get(
                "my_acct_stock" if mode == "real" else "my_paper_stock", "")
            prdt = account.get("acnt_prdt_cd") or "01"
            order_type = "01" if proposal.get("order_type") == "market" else "00"
            result = client.order_cash(
                cano, prdt, proposal["code"], proposal["side"],
                proposal["qty"], proposal["price"], order_type)
        except Exception as exc:  # noqa: BLE001
            print(f"  ❌ 주문 전송 실패: {exc}\n")
            proposal["status"] = "execution_failed"
            proposal["error"] = str(exc)
            f.write_text(json.dumps(proposal, ensure_ascii=False, indent=2),
                         encoding="utf-8")
            continue

        ok = result.get("rt_cd") == "0"
        proposal["status"] = "executed" if ok else "rejected_by_broker"
        proposal["executed_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        proposal["broker_result"] = result
        dest = "executed" if ok else "rejected"
        (state_dir("orders", dest) / f.name).write_text(
            json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
        f.unlink()
        print(f"  → {proposal['status']}  주문번호={result.get('order_no', '')}  "
              f"{result.get('msg', '')}\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="매매안 사람 승인 게이트")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="대기 매매안 보기")
    sub.add_parser("review", help="대화형 검토·승인 (실주문 전송)")
    args = ap.parse_args()
    return cmd_list() if args.cmd == "list" else cmd_review()


if __name__ == "__main__":
    raise SystemExit(main())
