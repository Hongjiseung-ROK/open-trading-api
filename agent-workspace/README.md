# agent-workspace — 정보기반 국내주식 투자 에이전트 시스템

`ao spawn` 으로 띄운 Claude Code / Codex 에이전트가 **전문가 페르소나**로 협업해
증권 뉴스를 스캔하고 매매안을 만든다. **모든 실주문은 사람 승인을 거친다.**

## 안전 모델 (핵심)
- 실행 모드: **실거래 + 매 주문 사람 승인**. 출고 기본값은 안전을 위해
  `mode: paper`(모의투자) — 검증 후 `risk_limits.yaml` 에서 `live` 로 전환한다.
- 에이전트는 **주문을 실행할 수 없다.** 포트폴리오 매니저는 `propose.py` 로
  매매안 파일만 만든다. 실주문은 사람이 `approval_gate.py` 로 승인할 때만 전송된다.
- 다층 한도: `risk_limits.yaml` 을 제안 시(`propose.py`)와 실행 직전
  (`approval_gate.py`) 양쪽에서 강제. 관심종목 외 종목 차단, 주문/일일 금액 상한.
- 시크릿: `api.env`·`kis_devlp.yaml` 은 git 추적 차단(pre-commit 스캐너 + .gitignore).

## 구조
| 경로 | 내용 |
|---|---|
| `agent-workspace/tools/` | 도구 스크립트 (저장소에 추적) |
| `agent-workspace/config/` | `risk_limits.yaml`, `watchlist.yaml` |
| `agent-workspace/personas/` | `ao spawn` 페르소나 프롬프트 |
| `agent-workspace/skills/` | `SKILL.md` 3종 |
| `~/.agent-workspace/api.env` | API 키 (Brave/Firecrawl) — git 밖, 모든 worktree 공유 |
| `~/.agent-workspace/state/` | 뉴스 다이제스트·매매안·주문 큐 — 공유 런타임 데이터 |

코드는 저장소에 추적되어 모든 `ao spawn` worktree 가 갖고, 런타임 데이터는
`~/.agent-workspace` 에 공유되어 워커들이 같은 뉴스·주문 큐를 본다.

## 페르소나
- **뉴스 스캐너**: Brave + Firecrawl 로 뉴스 스캔 → 다이제스트 작성. 읽기 전용.
- **포트폴리오 매니저**: 다이제스트 + 시세 → 매매안 제출(`propose.py`). 주문 실행 안 함.
- **사람**: `approval_gate.py` 로 검토·승인. 자금이 움직이는 유일한 지점.

## 도구
| 스크립트 | 역할 |
|---|---|
| `tools/scan_news.py` | 관심종목·시황 뉴스 수집 → raw JSON |
| `tools/brave_news.py` | Brave 웹검색 클라이언트 |
| `tools/firecrawl_fetch.py` | Firecrawl 기사 본문 추출 |
| `tools/kis_quote.py` | 국내주식 현재가·잔고 조회 (읽기 전용) |
| `tools/kis_client.py` | KIS 최소 클라이언트 (주문은 approval_gate 전용) |
| `tools/propose.py` | 매매안을 승인 대기 큐에 기록 (한도 검증) |
| `tools/approval_gate.py` | 사람 승인 게이트 — 승인 시에만 실주문 전송 |

## 사전 준비
1. `~/.agent-workspace/api.env` 에 키 입력 (`api.env.example` 참고).
2. `~/KIS/config/kis_devlp.yaml` 에 KIS 앱키·계좌 입력 (`kis_devlp.yaml.example` 참고).
3. 의존성: `pip install -r requirements.txt` (requests, pyyaml 포함).

## 실행
```bash
# 오케스트레이터가 페르소나 워커를 띄운다
ao spawn --agent codex \
  --prompt "당신은 뉴스 스캐너입니다. agent-workspace/personas/news-scanner.md 를 읽고 그대로 수행하세요."
ao spawn \
  --prompt "당신은 포트폴리오 매니저입니다. agent-workspace/personas/portfolio-manager.md 를 읽고 그대로 수행하세요."

# 사람: 매매안 검토·승인
python agent-workspace/tools/approval_gate.py list
python agent-workspace/tools/approval_gate.py review
```

## 모의 → 실거래 전환
`config/risk_limits.yaml` 의 `mode: paper` → `live`. 그 전에 모의투자로 충분히 검증할 것.

## 한계 (반드시 인지)
LLM 의 뉴스 기반 매매 판단은 환각·오해·과적합 위험이 있다. 이 시스템은
**투자 자문이 아니며 수익을 보장하지 않는다.** 사람 승인 게이트는 생략 불가한
안전장치다. 손실은 전적으로 사용자 책임이다.
