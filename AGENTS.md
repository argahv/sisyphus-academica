# Sisyphus Academica — Agent Onboarding

You are working on an open-source research pipeline. This AGENTS.md helps AI coding agents understand the repo structure and conventions.

## Quick Start

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## Key Files

| File | Purpose |
|------|---------|
| `orchestrator/research-director.md` | Primary orchestrator agent |
| `subagents/writer.md` | Paper section writer with Humanizer constraints |
| `novelty-engines/heretic.md` | Crown jewel novelty engine |
| `tools/literature_client.py` | Multi-source literature search |
| `tools/citation_verifier.py` | Citation verification + BibTeX |
| `skills/contrarian/SKILL.md` | Portable contrarian skill |
| `tools/gates.py` | The five quality gates, enforced in code |
| `src/sisyphus/cli.py` | `sisyphus` command line |
| `pyproject.toml` | Package config for pip install |

## Conventions

- Python tools use stdlib-only (urllib, json, xml) for zero-dependency CLI usage
- Agent prompts have YAML frontmatter with mode, description, skills, permissions
- Tests mock all network calls — never hit real APIs
- `pip install -e ".[dev]"` for development
- NO em dashes in generated text (this is a quality gate)
