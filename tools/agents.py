#!/usr/bin/env python3
"""
Sisyphus Academica: render and install the 25 OpenCode agents.

Model selection comes from config/agent-config.json: each agent's "model",
else "default_model". --default-model (set by the install.sh interview)
replaces the default and keeps per-agent customizations. LLM_PROVIDER (from
.env or the environment) or --model overrides every agent at once. Model strings
use the provider/model form, so any provider OpenCode knows works: anthropic/..., openai/..., or an
OpenAI-compatible endpoint configured in opencode.json.

Placeholders {{SISYPHUS_DIR}}, {{OPENCODE_CONFIG}} and {{OPENCODE_DATA}} in the
agent files are replaced with real paths at install time.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

try:
    from . import settings
except ImportError:  # run as a script: python3 tools/agents.py
    import settings

AGENT_DIRS = ("orchestrator", "subagents", "novelty-engines", "reviewers")
EXPECTED_AGENTS = 25


def agent_files(repo: Optional[Path] = None) -> List[Path]:
    repo = repo or settings.repo_dir()
    return [f for d in AGENT_DIRS for f in sorted((repo / d).glob("*.md"))]


def model_for(
    name: str, config: Dict, override: Optional[str] = None, default_model: Optional[str] = None
) -> str:
    """Model for one agent: override > agent model > default.

    default_model replaces config's default_model, including agents whose
    model equals the old default, so per-agent customizations survive.
    """
    if override:
        return override
    agent = (config.get("agents") or {}).get(name) or {}
    old_default = config.get("default_model")
    model = agent.get("model") or old_default
    if default_model and model == old_default:
        model = default_model
    if not model:
        raise ValueError(
            f"no model for agent {name!r}: set agents.{name}.model or default_model "
            "in config/agent-config.json"
        )
    return model


def render(text: str, model: str, paths: Dict[str, str]) -> str:
    for placeholder, value in paths.items():
        text = text.replace("{{" + placeholder + "}}", value)
    if not text.startswith("---\n"):
        raise ValueError("agent file must start with YAML frontmatter")
    end = text.index("\n---", 4)
    front, body = text[4:end], text[end:]
    front = re.sub(r"^model:.*\n?", "", front, flags=re.M).rstrip("\n")
    return f"---\n{front}\nmodel: {model}{body}"


def install(
    dest: Path,
    override: Optional[str] = None,
    opencode_config: Optional[Path] = None,
    config_path: Optional[Path] = None,
    default_model: Optional[str] = None,
) -> List[Path]:
    settings.ensure_env()
    override = override or os.environ.get("LLM_PROVIDER") or None
    config = settings.load_agent_config(config_path)
    home = Path.home()
    paths = {
        "SISYPHUS_DIR": str(settings.repo_dir()),
        "OPENCODE_CONFIG": str(opencode_config or home / ".config" / "opencode"),
        "OPENCODE_DATA": str(home / ".local" / "share" / "opencode"),
    }
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    for src in agent_files():
        name = src.stem
        out = dest / src.name
        model = model_for(name, config, override, default_model)
        out.write_text(render(src.read_text(encoding="utf-8"), model, paths), encoding="utf-8")
        written.append(out)
    return written


def check(dest: Path) -> List[str]:
    """Problems with an installed agent directory."""
    problems = []
    for src in agent_files():
        out = dest / src.name
        if not out.exists():
            problems.append(f"missing {out}")
            continue
        text = out.read_text(encoding="utf-8")
        if "{{" in text:
            problems.append(f"{out.name}: unreplaced placeholder")
        if not re.search(r"^model: \S+", text, re.M):
            problems.append(f"{out.name}: no model line")
    return problems


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Install Sisyphus Academica agents into OpenCode")
    parser.add_argument("--dest", default=str(Path.home() / ".config" / "opencode" / "agents"))
    parser.add_argument(
        "--opencode-config", help="OpenCode config dir (default ~/.config/opencode)"
    )
    parser.add_argument("--model", help="Use this provider/model for every agent")
    parser.add_argument(
        "--default-model", help="Replace default_model (agents with custom models keep them)"
    )
    parser.add_argument("--check", action="store_true", help="Validate an existing install")
    args = parser.parse_args(argv)
    dest = Path(args.dest).expanduser()
    if not args.check:
        written = install(
            dest,
            args.model,
            Path(args.opencode_config) if args.opencode_config else None,
            default_model=args.default_model,
        )
        print(f"  Installed {len(written)} agents into {dest}")
    problems = check(dest)
    count = len(agent_files())
    if count != EXPECTED_AGENTS:
        problems.append(f"repo has {count} agent files, expected {EXPECTED_AGENTS}")
    for p in problems:
        print(f"  ! {p}")
    if not problems:
        print(f"  All {count} agents present with models")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
