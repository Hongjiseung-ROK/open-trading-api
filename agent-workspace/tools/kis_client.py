#!/usr/bin/env python3
"""KIS 국내주식 최소 클라이언트 — 토큰 / 현재가 / 잔고 / 현금주문.

⚠️ order_cash() 는 실제 주문을 전송한다. 이 메서드는 approval_gate.py(사람 승인
게이트)에서만 호출되어야 한다. 뉴스 스캐너·포트폴리오 매니저 에이전트는 호출 금지.

자격증명 우선순위:
  $KIS_DEVLP_YAML > ~/KIS/config/kis_devlp.yaml > <repo>/kis_devlp.yaml
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests
import yaml

from _common import REPO_ROOT, state_dir

DOMAINS = {
    "real": "https://openapi.koreainvestment.com:9443",
    "paper": "https://openapivts.koreainvestment.com:29443",
}
# tr_id 매핑: 현재가 / 잔고 / 매수 / 매도
TR = {
    "real": {"price": "FHKST01010100", "balance": "TTTC8434R",
             "buy": "TTTC0012U", "sell": "TTTC0011U"},
    "paper": {"price": "FHKST01010100", "balance": "VTTC8434R",
              "buy": "VTTC0012U", "sell": "VTTC0011U"},
}


def _find_creds() -> Path:
    cands: list[Path] = []
    if os.environ.get("KIS_DEVLP_YAML"):
        cands.append(Path(os.environ["KIS_DEVLP_YAML"]).expanduser())
    cands.append(Path("~/KIS/config/kis_devlp.yaml").expanduser())
    cands.append(REPO_ROOT / "kis_devlp.yaml")
    for c in cands:
        if c.is_file():
            return c
    raise FileNotFoundError(
        "kis_devlp.yaml 을 찾을 수 없습니다. ~/KIS/config/kis_devlp.yaml 에 "
        "실제 KIS 앱키/계좌번호를 채우세요 (kis_devlp.yaml.example 참고)."
    )


class KisClient:
    """KIS 국내주식 클라이언트. mode: 'paper'(모의) | 'real'(실거래)."""

    def __init__(self, mode: str = "paper") -> None:
        if mode not in DOMAINS:
            raise ValueError("mode 는 'paper' 또는 'real' 이어야 합니다")
        self.mode = mode
        self.base = DOMAINS[mode]
        self.cfg = yaml.safe_load(_find_creds().read_text(encoding="utf-8"))
        if mode == "real":
            self.app = self.cfg["my_app"]
            self.sec = self.cfg["my_sec"]
        else:
            self.app = self.cfg["paper_app"]
            self.sec = self.cfg["paper_sec"]
        self._token: str | None = None

    # ------------------------------------------------------------------ 토큰
    def _token_cache(self) -> Path:
        return state_dir() / f".kis_token_{self.mode}.json"

    def token(self) -> str:
        """접근토큰 (캐시 사용 — KIS는 토큰 발급을 분당 1회로 제한)."""
        if self._token:
            return self._token
        cache = self._token_cache()
        if cache.is_file():
            cached = json.loads(cache.read_text())
            if cached.get("expires_at", 0) > time.time() + 600:
                self._token = cached["access_token"]
                return self._token
        resp = requests.post(
            f"{self.base}/oauth2/tokenP",
            json={"grant_type": "client_credentials",
                  "appkey": self.app, "appsecret": self.sec},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        cache.write_text(json.dumps({
            "access_token": self._token,
            "expires_at": time.time() + int(data.get("expires_in", 86400)),
        }))
        try:
            cache.chmod(0o600)
        except OSError:
            pass
        return self._token

    def _headers(self, tr_id: str, extra: dict | None = None) -> dict:
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.token()}",
            "appkey": self.app,
            "appsecret": self.sec,
            "tr_id": tr_id,
        }
        if extra:
            headers.update(extra)
        return headers

    # ------------------------------------------------------- 조회 (읽기 전용)
    def current_price(self, code: str) -> dict:
        """국내주식 현재가."""
        resp = requests.get(
            f"{self.base}/uapi/domestic-stock/v1/quotations/inquire-price",
            headers=self._headers(TR[self.mode]["price"]),
            params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code},
            timeout=20,
        )
        resp.raise_for_status()
        out = resp.json().get("output", {})
        return {
            "code": code,
            "price": int(out.get("stck_prpr", 0) or 0),
            "change_rate": out.get("prdy_ctrt", ""),
            "volume": out.get("acml_vol", ""),
        }

    def balance(self, cano: str, prdt: str = "01") -> dict:
        """국내주식 잔고 — 보유종목과 예수금."""
        resp = requests.get(
            f"{self.base}/uapi/domestic-stock/v1/trading/inquire-balance",
            headers=self._headers(TR[self.mode]["balance"]),
            params={
                "CANO": cano, "ACNT_PRDT_CD": prdt, "AFHR_FLPR_YN": "N",
                "OFL_YN": "", "INQR_DVSN": "02", "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "00", "CTX_AREA_FK100": "", "CTX_AREA_NK100": "",
            },
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
        holdings = [
            {
                "code": h.get("pdno"), "name": h.get("prdt_name"),
                "qty": int(h.get("hldg_qty", 0) or 0),
                "avg_price": h.get("pchs_avg_pric"),
                "eval_profit": h.get("evlu_pfls_amt"),
            }
            for h in payload.get("output1", [])
            if int(h.get("hldg_qty", 0) or 0) > 0
        ]
        summary = (payload.get("output2") or [{}])[0]
        return {
            "holdings": holdings,
            "cash": int(summary.get("dnca_tot_amt", 0) or 0),
            "total_eval": int(summary.get("tot_evlu_amt", 0) or 0),
        }

    # -------------------------------------- 주문 (실행) — approval_gate 전용
    def _hashkey(self, body: dict) -> str:
        resp = requests.post(
            f"{self.base}/uapi/hashkey",
            headers={"content-type": "application/json; charset=utf-8",
                     "appkey": self.app, "appsecret": self.sec},
            json=body, timeout=20,
        )
        resp.raise_for_status()
        return resp.json().get("HASH", "")

    def order_cash(self, cano: str, prdt: str, code: str, side: str,
                   qty: int, price: int, order_type: str = "00") -> dict:
        """현금 매수/매도 주문을 전송한다.

        ⚠️ 실제 주문. approval_gate.py 의 사람 승인 후에만 호출할 것.
        side: 'buy'|'sell'. order_type: '00'=지정가, '01'=시장가.
        """
        if side not in ("buy", "sell"):
            raise ValueError("side 는 'buy' 또는 'sell'")
        body = {
            "CANO": cano, "ACNT_PRDT_CD": prdt, "PDNO": code,
            "ORD_DVSN": order_type, "ORD_QTY": str(int(qty)),
            "ORD_UNPR": str(int(price)) if order_type == "00" else "0",
            "EXCG_ID_DVSN_CD": "KRX",
        }
        headers = self._headers(TR[self.mode][side], {"hashkey": self._hashkey(body)})
        resp = requests.post(
            f"{self.base}/uapi/domestic-stock/v1/trading/order-cash",
            headers=headers, json=body, timeout=20,
        )
        resp.raise_for_status()
        result = resp.json()
        return {
            "rt_cd": result.get("rt_cd"),
            "msg": result.get("msg1", ""),
            "order_no": (result.get("output") or {}).get("ODNO", ""),
            "raw": result,
        }
