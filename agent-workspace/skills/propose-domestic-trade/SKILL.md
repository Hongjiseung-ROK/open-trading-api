---
name: propose-domestic-trade
description: 뉴스 다이제스트와 시세를 근거로 국내주식 매매안을 사람 승인 큐에 제출한다. 포트폴리오 매니저 전용 — 주문 실행은 하지 않는다.
---

# 스킬: 국내주식 매매안 제출

## 목적
정보(뉴스 + 시세)를 근거로 매수/매도 후보를 정하고 **매매안**을 제출한다.
실제 주문은 사람이 `approval_gate.py` 로 승인한 뒤에만 전송된다.

## 절차
1. 최신 다이제스트 확인:
   `ls -t ~/.agent-workspace/state/news/digest-*.md | head -1` → 읽기.
2. 시세·잔고 확인:
   `python agent-workspace/tools/kis_quote.py price <종목코드>`
   `python agent-workspace/tools/kis_quote.py balance`
3. 한도 확인: `agent-workspace/config/risk_limits.yaml`,
   대상 종목: `agent-workspace/config/watchlist.yaml`.
4. 판단: 뉴스 감성 + 가격 + 보유현황을 종합. **근거가 분명할 때만** 제안.
5. 제출:
   ```
   python agent-workspace/tools/propose.py --code 005930 --name 삼성전자 \
       --side buy --qty 3 --price 70000 --order-type limit \
       --reason "<구체적 근거>" --news-ref digest-<ts>.md
   ```
6. `propose.py` 가 리스크 한도를 검증한다. 거부되면 수량/가격을 줄여 재시도하거나
   포기한다. "기회 없음" 도 정상적인 결론이다.

## 매매안 근거 작성 원칙
- "어떤 뉴스/지표 때문에, 왜 지금" 인지 한 문장으로 분명히 적는다.
- 막연한 기대("오를 것 같다")는 근거가 아니다.
- 같은 종목에 모순되는 매매안을 동시에 내지 않는다.

## 절대 금지
- `approval_gate.py` 실행 금지 — 그건 사람의 몫이다.
- `kis_client` 의 `order_cash` 등 주문 API 직접 호출 금지.
- 우회 주문(직접 HTTP 호출, 별도 스크립트 작성) 금지.
- `risk_limits.yaml` 한도 초과 매매안 강행 금지.
- API 키·계좌번호·시크릿을 출력·로그·커밋에 포함 금지.
