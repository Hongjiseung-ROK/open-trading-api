#!/usr/bin/env bash
# ============================================================================
# KIS open-trading-api — 시크릿 커밋/푸시 차단 가드
# ----------------------------------------------------------------------------
# pre-commit / pre-push 양 단계에서 호출된다. 인자로 검사 대상 파일 경로를 받는다.
#  1) 민감 설정 파일명은 무조건 차단 (git add -f 강제 추가도 봉쇄)
#  2) 파일 내용에서 KIS 앱키/앱시크릿/토큰으로 보이는 값을 차단
# 발견 시 0이 아닌 코드로 종료하여 커밋/푸시를 막는다.
# ============================================================================
set -uo pipefail

# 가드 자체 파일 — 정규식 패턴 문자열이 오탐될 수 있어 검사 제외
self_allow_re='scripts/check-kis-secrets\.sh$|scripts/run-gitleaks\.sh$|(^|/)\.gitleaks\.toml$'

# 추적 금지 민감 파일명 (실제 자격증명 파일. *.example 템플릿만 추적할 것)
deny_path_re='(^|/)(kis_devlp\.yaml|kisdev_vi\.yaml)$|(^|/)legacy/rest/config\.yaml$|(^|/)\.kis_token[^/]*$|(^|/)(api\.env|\.env)$|\.pem$'

# 내용 패턴 — 자격증명 키 뒤에 20자 이상의 키처럼 보이는 값
cred_re='(my_app|my_sec|paper_app|paper_sec|app_?key|app_?secret|APP_KEY|APP_SECRET|secret_?key|api[_-]?key|apikey)["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9/+_=-]{20,}'
# 알려진 접두사 키 (OpenAI sk-, Firecrawl fc-)
generic_re='(sk-[A-Za-z0-9_-]{20,}|fc-[A-Za-z0-9]{20,})'
# JWT
jwt_re='eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}'
# 접근토큰 / 승인키 / Bearer
token_re='(my_token|access_token|approval_key|[Bb]earer)["'"'"']?[[:space:]]*[:=[:space:]]["'"'"']?[A-Za-z0-9._-]{24,}'

# 명백한 플레이스홀더 — 문서/예제의 가짜 값은 차단 대상에서 제외
placeholder_re='(your[_-]|[_-]here|YOUR[_-]|example|placeholder|change[_-]?me|dummy|sample|xxxx|XXXX|<[A-Za-z_-]|\.\.\.|발급|앱키|시크릿|토큰값|계좌)'

fail=0
for f in "$@"; do
  [ -f "$f" ] || continue

  # 가드 자체 파일은 통과
  if printf '%s\n' "$f" | grep -Eq "$self_allow_re"; then
    continue
  fi

  # 1) 민감 파일명 차단
  if printf '%s\n' "$f" | grep -Eq "$deny_path_re"; then
    echo "🚫 차단: 민감 설정 파일은 커밋/푸시할 수 없습니다 → $f" >&2
    echo "   실제 자격증명 파일입니다. *.example 템플릿만 추적하세요." >&2
    fail=1
    continue
  fi

  # 2) 내용 스캔 (명백한 플레이스홀더 라인은 제외)
  hit=$(grep -nEH "$cred_re" "$f" 2>/dev/null | grep -Ev "$placeholder_re" | head -3 || true)
  [ -z "$hit" ] && hit=$(grep -nEH "$jwt_re" "$f" 2>/dev/null | grep -Ev "$placeholder_re" | head -3 || true)
  [ -z "$hit" ] && hit=$(grep -nEH "$token_re" "$f" 2>/dev/null | grep -Ev "$placeholder_re" | head -3 || true)
  [ -z "$hit" ] && hit=$(grep -nEH "$generic_re" "$f" 2>/dev/null | grep -Ev "$placeholder_re" | head -3 || true)
  if [ -n "$hit" ]; then
    echo "🚫 차단: 실제 자격증명/토큰으로 보이는 값이 포함됨 → $f" >&2
    printf '%s\n' "$hit" | sed -E 's/([:=][[:space:]]*["'"'"']?)[A-Za-z0-9/+_=.-]{8,}/\1<REDACTED>/' >&2
    fail=1
  fi
done

if [ "$fail" -ne 0 ]; then
  echo "" >&2
  echo "커밋/푸시가 차단되었습니다. KIS 앱키·앱시크릿·토큰·계좌정보를 제거한 뒤 다시 시도하세요." >&2
  echo "--no-verify 우회는 금지입니다 (정책 위반)." >&2
fi
exit "$fail"
