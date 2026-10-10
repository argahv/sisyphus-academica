"""Tests for the agent definitions, model config, installer rendering and portable skills."""

import json
import re
from pathlib import Path

import pytest

from sisyphus.tools import agents, reviews, workspace

REPO = Path(__file__).resolve().parent.parent
NOVELTY = [
    "assumption-excavator",
    "contrarian",
    "counterfactual-generator",
    "cross-pollinator",
    "heretic",
    "paradox-sifter",
]


def body(path: Path) -> str:
    text = path.read_text()
    return text.split("\n---", 1)[1].split("\n", 1)[1].strip()


def test_there_are_25_agents_and_all_are_configured():
    files = agents.agent_files(REPO)
    assert len(files) == agents.EXPECTED_AGENTS
    config = json.loads((REPO / "config" / "agent-config.json").read_text())
    assert {f.stem for f in files} == set(config["agents"])
    assert config["default_model"]


@pytest.mark.parametrize("path", agents.agent_files(REPO), ids=lambda p: p.stem)
def test_agent_frontmatter(path):
    text = path.read_text()
    assert text.startswith("---\n")
    front = text.split("\n---", 1)[0]
    assert re.search(r'^description: ".+"$', front, re.M)
    assert "\nmodel:" not in front, "model comes from config/agent-config.json"
    assert "/root/" not in text, "use {{SISYPHUS_DIR}} placeholders, not hardcoded paths"


def test_reviewers_and_engines_match_their_portable_skills():
    for name in list(reviews.PERSONAS) + NOVELTY:
        folder = "reviewers" if name in reviews.PERSONAS else "novelty-engines"
        assert body(REPO / folder / f"{name}.md") == body(REPO / "skills" / name / "SKILL.md"), name


def test_skills_are_standalone():
    for skill in (REPO / "skills").glob("*/SKILL.md"):
        text = skill.read_text()
        assert re.search(rf'^name: "?{skill.parent.name}"?$', text, re.M), skill
        assert "{{" not in text and "sisyphus " not in text and "out/papers" not in text, skill


def test_reviewer_prompts_define_the_gate_schema():
    for persona in reviews.PERSONAS:
        text = (REPO / "reviewers" / f"{persona}.md").read_text()
        example = json.loads(re.search(r"```json\n(.*?)```", text, re.S).group(1))
        assert reviews.validate_review(example, persona) == []


def test_novelty_prompts_define_shared_fields():
    for engine in workspace.ENGINES:
        text = (REPO / "novelty-engines" / f"{engine}.md").read_text()
        for field in ("`novelty`", "`tractability`", "`impact`", "`evidence`"):
            assert field in text, (engine, field)


def test_prompts_contain_no_em_dashes():
    for path in agents.agent_files(REPO) + list((REPO / "skills").glob("*/SKILL.md")):
        assert "—" not in path.read_text(), path


def test_render_sets_model_and_paths():
    src = (
        '---\nmode: subagent\ndescription: "x"\npermission:\n  write:\n'
        '    "{{SISYPHUS_DIR}}/out/*": allow\n---\nBody\n'
    )
    out = agents.render(src, "anthropic/claude-sonnet-4", {"SISYPHUS_DIR": "/opt/sa"})
    assert '"/opt/sa/out/*": allow' in out
    assert "\nmodel: anthropic/claude-sonnet-4\n---\nBody" in out


def test_model_selection():
    config = {
        "default_model": "router/free",
        "agents": {
            "writer": {"model": "anthropic/claude-opus-4"},
            "skeptic": {"model": "router/free"},
        },
    }
    assert agents.model_for("writer", config) == "anthropic/claude-opus-4"
    assert agents.model_for("verifier", config) == "router/free"
    assert agents.model_for("skeptic", config, default_model="openai/gpt-4o") == "openai/gpt-4o"
    assert (
        agents.model_for("writer", config, default_model="openai/gpt-4o")
        == "anthropic/claude-opus-4"
    )
    assert agents.model_for("writer", config, override="openai/gpt-4o") == "openai/gpt-4o"


def test_install_and_check(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai/gpt-4o")
    written = agents.install(tmp_path / "agents", opencode_config=tmp_path / "oc")
    assert len(written) == 25
    assert agents.check(tmp_path / "agents") == []
    text = (tmp_path / "agents" / "writer.md").read_text()
    assert "model: openai/gpt-4o" in text and "{{" not in text
    assert str(REPO) in text


def test_director_uses_existing_commands_and_stages():
    text = (REPO / "orchestrator" / "research-director.md").read_text()
    from sisyphus.cli import COMMANDS

    for command in re.findall(r"\$S ([a-z]+)", text):
        assert command in COMMANDS, command
    for stage in re.findall(r"\$S check RUN ([a-z]+)", text):
        assert stage in workspace.STAGE_IDS, stage
