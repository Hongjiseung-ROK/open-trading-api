---
name: review-and-approve-orders
description: 사람이 대기 중인 매매안을 검토하고 승인/거부하는 절차. 승인된 주문만 KIS로 전송된다. 사람이 직접 수행하며 에이전트는 실행하지 않는다.
---

# 스킬: 매매안 검토·승인 (사람 전용)

⚠️ 이 절차는 **사람이 직접** 터미널에서 수행한다. 에이전트는 실행하지 않는다.

## 목적
포트폴리오 매니저가 제출한 매매안을 사람이 검토하고, 승인한 것만 실제 주문으로
KIS 에 전송한다. **이것이 자금이 움직이는 유일한 지점이다.**

## 절차
1. 대기 목록 확인:
   `python agent-workspace/tools/approval_gate.py list`
2. 대화형 검토·승인:
   `python agent-workspace/tools/approval_gate.py review`
   - 매매안마다 `[a]승인 / [r]거부 / [s]건너뛰기` 선택.
   - `mode: live`(실거래)면 승인 시 `CONFIRM` 을 직접 입력해야 주문이 나간다.
   - 실행 직전 일일 한도가 재검증된다.
3. 결과는 `~/.agent-workspace/state/orders/{executed,rejected}/` 에 기록된다.

## 검토 체크리스트
- 매매안 근거가 납득되는가? 인용한 뉴스가 실제로 그런 내용인가?
- 금액·수량이 감당 가능한가? (`risk_limits.yaml` 한도 안인가)
- 제안 이후 가격이 급변하지 않았는가? 지금도 유효한가?
- 같은 종목에 중복·모순 주문이 없는가?
- 의심스러우면 거부한다. 거부는 비용이 들지 않는다.

## 모의 → 실거래 전환
1. 모의투자(`mode: paper`)로 충분히 검증한다.
2. `agent-workspace/config/risk_limits.yaml` 의 `mode` 를 `live` 로 바꾼다.
3. `~/KIS/config/kis_devlp.yaml` 의 실전 앱키(`my_app`, `my_sec`)와
   계좌번호가 정확한지 확인한다.
4. `limits` 를 본인 자금규모에 맞게 보수적으로 설정한다.
