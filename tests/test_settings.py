"""Tests for .env parsing and path resolution."""

from sisyphus.tools import settings


def test_parse_dotenv_handles_comments_quotes_export_and_defaults(monkeypatch):
    monkeypatch.setenv("HOME_X", "/home/x")
    text = (
        "# comment\n"
        "export A=1\n"
        "B='two words'\n"
        'C="${HOME_X}/data"\n'
        "D=${MISSING_VAR:-fallback}\n"
        "E=value # trailing comment\n"
        "F=\n"
        "not a pair\n"
    )
    values = settings.parse_dotenv(text)
    assert values == {
        "A": "1",
        "B": "two words",
        "C": "/home/x/data",
        "D": "fallback",
        "E": "value",
        "F": "",
    }


def test_load_dotenv_keeps_existing_environment(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("SEMANTIC_SCHOLAR_API_KEY=fromfile\nCROSSREF_EMAIL=a@b.org\n")
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "fromenv")
    settings.load_dotenv(env)
    assert settings.semantic_scholar_headers() == {"x-api-key": "fromenv"}
    assert settings.contact_email() == "a@b.org"


def test_repo_dir_and_resolve(isolated_repo):
    assert settings.repo_dir() == isolated_repo
    assert settings.resolve("data/voice-profile") == isolated_repo / "data" / "voice-profile"
    assert settings.voice_profile_path() == isolated_repo / "data" / "voice-profile.json"
