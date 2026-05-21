"""agent-workspace 공용 유틸 — 경로 해석, api.env 로더, state 디렉터리.

코드는 저장소에 추적되지만 런타임 데이터(api.env, state/)는 모든 worktree가
공유하는 ~/.agent-workspace 에 둔다. 그래야 ao spawn 으로 띄운 워커들이
같은 뉴스·매매안·주문 큐를 본다.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def workspace_home() -> Path:
    """런타임 데이터(api.env, state/)가 있는 공유 디렉터리."""
    return Path(os.environ.get("AGENT_WORKSPACE_HOME", "~/.agent-workspace")).expanduser()


def state_dir(*parts: str) -> Path:
    """~/.agent-workspace/state/<parts...> 를 만들고 경로를 반환한다."""
    d = workspace_home() / "state"
    for p in parts:
        d = d / p
    d.mkdir(parents=True, exist_ok=True)
    return d


def _env_candidates() -> list[Path]:
    cands: list[Path] = []
    if os.environ.get("AGENT_API_ENV"):
        cands.append(Path(os.environ["AGENT_API_ENV"]).expanduser())
    cands.append(workspace_home() / "api.env")
    cands.append(REPO_ROOT / "api.env")
    return cands


def _parse_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            out[key] = val
    return out


def load_env() -> dict[str, str]:
    """api.env 를 읽어 dict로 반환 ('key = value' / 'key=value', 따옴표·# 주석 처리)."""
    for path in _env_candidates():
        if path.is_file():
            return _parse_env(path)
    raise FileNotFoundError(
        "api.env 를 찾을 수 없습니다. 다음 위치 중 하나에 두세요: "
        + ", ".join(str(p) for p in _env_candidates())
    )


def require_key(env: dict[str, str], *names: str) -> str:
    """주어진 후보 키 이름(대소문자 무시) 중 첫 번째로 존재하는 값을 반환한다."""
    for n in names:
        for k, v in env.items():
            if k.lower() == n.lower() and v:
                return v
    raise KeyError(f"api.env 에 키가 없습니다: {names}")
