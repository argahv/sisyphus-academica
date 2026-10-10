"""Shared fixtures. Every test runs offline: real network access raises."""

import json
import shutil
import sys
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from sisyphus.tools import net, settings  # noqa: E402

DEMO_RUN = REPO / "src" / "sisyphus" / "demo_run"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """Block real HTTP, make retries instant and ignore local configuration."""

    def refuse(*args, **kwargs):
        raise OSError("network disabled in tests")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    monkeypatch.setattr(net.time, "sleep", lambda s: None)
    # Ignore a developer's .env so results do not depend on local keys or overrides.
    monkeypatch.setattr(settings, "_LOADED", True)
    for var in (
        "SEMANTIC_SCHOLAR_API_KEY",
        "CROSSREF_EMAIL",
        "LLM_PROVIDER",
        "DEFAULT_VENUE",
        "VOICE_SAMPLE_PATH",
        "SISYPHUS_ACADEMICA_DIR",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def isolated_repo(monkeypatch, tmp_path):
    """Point settings at a temporary repo root with config and templates."""
    root = tmp_path / "repo"
    (root / "config").mkdir(parents=True)
    shutil.copy(REPO / "config" / "agent-config.json", root / "config")
    shutil.copytree(REPO / "templates", root / "templates")
    shutil.copy(REPO / ".env.example", root / ".env.example")
    monkeypatch.setenv("SISYPHUS_ACADEMICA_DIR", str(root))
    return root


@pytest.fixture
def demo_run(tmp_path):
    """A complete paper run that passes every gate (citation results are cached)."""
    run = tmp_path / "demo"
    shutil.copytree(DEMO_RUN, run)
    return run


class FakeAPI:
    """Route net.fetch_json / fetch_text by URL substring to canned payloads."""

    def __init__(self):
        self.json_routes = []
        self.text_routes = []
        self.calls = []

    def json(self, fragment, payload):
        self.json_routes.append((fragment, payload))

    def text(self, fragment, payload):
        self.text_routes.append((fragment, payload))

    def fetch_json(self, url, headers=None, **kwargs):
        self.calls.append(url)
        for fragment, payload in self.json_routes:
            if fragment in url:
                return json.loads(json.dumps(payload))
        return None

    def fetch_text(self, url, headers=None, **kwargs):
        self.calls.append(url)
        for fragment, payload in self.text_routes:
            if fragment in url:
                return payload
        return None


@pytest.fixture
def fake_api(monkeypatch):
    api = FakeAPI()
    monkeypatch.setattr(net, "fetch_json", api.fetch_json)
    monkeypatch.setattr(net, "fetch_text", api.fetch_text)
    return api
