#!/usr/bin/env bash
# ============================================================================
# gitleaks 보조 스캔 — 설치돼 있을 때만 실행되는 2차 방어선.
# 미설치 시 통과(no-op). 도구 실행 오류는 차단하지 않고, 실제 유출 발견 시에만 차단.
# 설치:  brew install gitleaks
# ============================================================================
set -uo pipefail

command -v gitleaks >/dev/null 2>&1 || exit 0
[ "$#" -eq 0 ] && exit 0

cfg=()
[ -f .gitleaks.toml ] && cfg=(-c .gitleaks.toml)

gitleaks dir "$@" "${cfg[@]}" --no-banner --redact
rc=$?
# gitleaks: 0=clean, 1=leaks found, 그 외=도구 오류
if [ "$rc" -eq 1 ]; then
  echo "🚫 gitleaks가 시크릿을 탐지했습니다 — 커밋/푸시 차단." >&2
  exit 1
fi
exit 0
