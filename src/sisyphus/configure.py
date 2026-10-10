#!/usr/bin/env python3
"""Sisyphus Academica: configuration of .env and data directories."""

import shutil
import sys
from pathlib import Path
from typing import Optional

from sisyphus.tools import settings


def _ask(prompt: str) -> str:
    if not sys.stdin.isatty():
        return ""
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def run_configure(
    semantic_scholar_key: Optional[str] = None, crossref_email: Optional[str] = None
) -> int:
    """Create .env from .env.example, store API keys, and create data/output directories.

    Prompts only when stdin is a terminal and a value was not passed as a flag.
    """
    repo_dir = settings.repo_dir()
    env_example = repo_dir / ".env.example"
    env_file = repo_dir / ".env"

    print("Sisyphus Academica: configuration")
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print(f"  Created {env_file} from .env.example")
    elif env_file.exists():
        print(f"  Using existing {env_file}")

    ss_key = semantic_scholar_key or _ask(
        "  Semantic Scholar API key (free, semanticscholar.org/product/api) [enter to skip]: "
    )
    if ss_key:
        set_env(env_file, "SEMANTIC_SCHOLAR_API_KEY", ss_key)
        print("  Saved SEMANTIC_SCHOLAR_API_KEY")

    email = crossref_email or _ask(
        "  Email for the CrossRef/OpenAlex polite pool [enter to skip]: "
    )
    if email:
        set_env(env_file, "CROSSREF_EMAIL", email)
        print("  Saved CROSSREF_EMAIL")

    for d in ("out/papers", "data/voice-profile"):
        (repo_dir / d).mkdir(parents=True, exist_ok=True)
    print("  Voice calibration (optional): put 2-3 paragraphs of your published writing in")
    print(f"    {repo_dir / 'data' / 'voice-profile'}/*.txt, then run: sisyphus voice")
    print("  Next: sisyphus demo")
    return 0


def set_env(env_file: Path, key: str, value: str) -> None:
    """Set key=value in .env, preserving other lines."""
    lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.exists() else []
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(run_configure())
