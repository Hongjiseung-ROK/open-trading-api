---
name: scan-stock-news
description: Brave Web Search와 Firecrawl로 국내주식 증권 뉴스를 스캔하고 종목별 감성 다이제스트를 작성한다. 뉴스 스캐너 에이전트가 사용.
---

# 스킬: 증권 뉴스 스캔

## 목적
관심종목과 시황 뉴스를 수집해, 포트폴리오 매니저가 매매 판단에 쓸 수 있는
구조화된 **뉴스 다이제스트**를 만든다.

## 사전 조건
- `~/.agent-workspace/api.env` 에 `brave_search_api_key`, `firecrawl_api_key` 존재.
- 의존성: `requests`, `pyyaml` (저장소 requirements.txt 에 포함).

## 절차
1. **수집**: `python agent-workspace/tools/scan_news.py --freshness pd --per-query 6`
   → `~/.agent-workspace/state/news/raw-<ts>.json` 생성.
2. **본문 확인**: raw JSON 헤드라인 중 중요해 보이는 것만
   `python agent-workspace/tools/firecrawl_fetch.py "<url>" --max-chars 3000`
   으로 기사 본문을 읽는다. (모든 기사를 긁지 말 것 — API 비용)
3. **분석**: 종목별 감성을 분류한다.
   - 긍정: 실적 호조, 수주, 자사주 매입, 목표가 상향 등
   - 부정: 실적 부진, 규제·소송, 목표가 하향, 대량매도 등
   - 중립: 영향 불명확
4. **다이제스트 작성** → `~/.agent-workspace/state/news/digest-<ts>.md` 저장.

## 다이제스트 형식
```
# 뉴스 다이제스트 — <날짜 시각>

## 시장 요약
<코스피/코스닥 시황 2~3줄>

## 종목별
### 삼성전자 (005930) — 감성: 긍정
- <헤드라인 요약> (출처: <url>)
- 핵심 이벤트: <실적/수주/규제 등>
- 코멘트: <한 줄, 불확실하면 '불확실' 명시>
```

## 하지 말 것
- 매매안 작성·주문 금지. 이 스킬은 정보 수집·정리까지만.
- 한 건의 자극적 헤드라인 과대해석 금지 — 복수 출처로 교차검증.
- API 키·시크릿을 출력·로그·커밋에 포함 금지.
