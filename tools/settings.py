#!/usr/bin/env python3
"""
Sisyphus Academica: repository paths, .env loading and agent config.

Paths resolve from SISYPHUS_ACADEMICA_DIR when set, otherwise from the
checkout this file lives in, otherwise from the current directory.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, Optional

_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")
_LOADED = False


def repo_dir() -> Path:
    """Root of the Sisyphus Academica checkout."""
    env = os.environ.get("SISYPHUS_ACADEMICA_DIR")
    if env and env != ".":
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve().parent.parent
    if (here / "config" / "agent-config.json").exists():
        return here
    return Path.cwd()


def resolve(path: str) -> Path:
    """Resolve a path from config or .env relative to the repo root."""
    p = Path(os.path.expandvars(path)).expanduser()
    return p if p.is_absolute() else repo_dir() / p


def _expand(value: str, scope: Dict[str, str]) -> str:
    def sub(m):
        name, default = m.group(1), m.group(2)
        found = os.environ.get(name) or scope.get(name)
        return found if found else (default or "")

    return _VAR.sub(sub, value)


def parse_dotenv(text: str) -> Dict[str, str]:
    """Parse .env text. Supports comments, `export`, quotes and ${VAR:-default}."""
    values: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line.split(" ", 1)[1]
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        values[key] = _expand(value, values)
    return values


def load_dotenv(path: Optional[Path] = None, override: bool = False) -> Dict[str, str]:
    """Load the repo .env into os.environ. Existing variables win unless override."""
    global _LOADED
    env_file = path or repo_dir() / ".env"
    if not env_file.exists():
        return {}
    values = parse_dotenv(env_file.read_text(encoding="utf-8"))
    for key, value in values.items():
        if override or key not in os.environ:
            os.environ[key] = value
    _LOADED = True
    return values


def ensure_env() -> None:
    """Load .env once per process."""
    if not _LOADED:
        load_dotenv()


def semantic_scholar_headers() -> Dict[str, str]:
    ensure_env()
    key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    return {"x-api-key": key} if key else {}


def contact_email() -> str:
    """Email for the CrossRef and OpenAlex polite pools (empty when unset)."""
    ensure_env()
    return os.environ.get("CROSSREF_EMAIL", "").strip()


def default_venue() -> str:
    ensure_env()
    return os.environ.get("DEFAULT_VENUE", "arxiv").strip() or "arxiv"


def voice_sample_path() -> Path:
    ensure_env()
    return resolve(os.environ.get("VOICE_SAMPLE_PATH") or "data/voice-profile")


def voice_profile_path() -> Path:
    return repo_dir() / "data" / "voice-profile.json"


def load_agent_config(path: Optional[Path] = None) -> Dict:
    cfg = path or repo_dir() / "config" / "agent-config.json"
    with open(cfg, encoding="utf-8") as f:
        return json.load(f)
