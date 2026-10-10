"""Tests for the sisyphus CLI. Network calls are stubbed; files go to temporary directories."""

import json

import pytest

from sisyphus import cli
from sisyphus.tools import citation_verifier, literature_client


def run(argv, capsys):
    code = cli.main(argv)
    out = capsys.readouterr()
    return code, out.out, out.err


class TestEntryPoint:
    def test_no_args_shows_help(self, capsys):
        code, out, _ = run([], capsys)
        assert code == 0
        for command in ("demo", "search", "verify", "bibtex", "configure"):
            assert command in out

    def test_unknown_command_exits(self, capsys):
        with pytest.raises(SystemExit) as exc:
            cli.main(["nonexistent"])
        assert exc.value.code == 2

    def test_search_requires_query(self):
        with pytest.raises(SystemExit):
            cli.main(["search"])

    def test_bibtex_requires_doi(self):
        with pytest.raises(SystemExit):
            cli.main(["bibtex"])


class TestPublicCommands:
    def test_demo_passes_all_gates(self, capsys):
        code, out, _ = run(["demo"], capsys)
        assert code == 0
        assert out.count("PASS") == 5
        assert "paper.tex" in out

    def test_configure_writes_env_without_prompting(self, isolated_repo, capsys):
        code, out, _ = run(
            ["configure", "--semantic-scholar-key", "abc/123", "--crossref-email", "a@b.org"],
            capsys,
        )
        assert code == 0
        env = (isolated_repo / ".env").read_text()
        assert "SEMANTIC_SCHOLAR_API_KEY=abc/123" in env
        assert "CROSSREF_EMAIL=a@b.org" in env
        assert (isolated_repo / "data" / "voice-profile").is_dir()

    def test_search_prints_json(self, monkeypatch, capsys):
        monkeypatch.setattr(
            literature_client,
            "SEARCHERS",
            {
                "arxiv": lambda q, n: [{"title": "Paper A", "source": "arxiv"}],
                "crossref": lambda q, n: [{"title": "Paper A", "source": "crossref"}],
            },
        )
        code, out, err = run(
            ["search", "attention", "models", "--sources", "arxiv,crossref"], capsys
        )
        assert code == 0
        data = json.loads(out)
        assert data["query"] == "attention models"
        assert data["total_unique"] == 1
        assert "Searching" in err

    def test_search_writes_output_file(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            literature_client,
            "SEARCHERS",
            {"arxiv": lambda q, n: [{"title": "P", "source": "arxiv"}]},
        )
        target = tmp_path / "lit" / "q1.json"
        code, _, _ = run(["search", "q", "--sources", "arxiv", "-o", str(target)], capsys)
        assert code == 0 and json.loads(target.read_text())["total_unique"] == 1

    def test_verify_paper_json(self, monkeypatch, tmp_path, capsys):
        paper = tmp_path / "paper.json"
        paper.write_text(
            json.dumps({"paper": "See [A2020].", "references": [{"key": "A2020", "title": "Real"}]})
        )
        monkeypatch.setattr(
            citation_verifier,
            "verify_reference",
            lambda ref, sources=None: {
                "key": ref["key"],
                "verified": True,
                "found_in": ["crossref", "openalex"],
                "issues": [],
            },
        )
        code, out, err = run(["verify", str(paper)], capsys)
        assert code == 0
        assert json.loads(out)["verified"] == 1
        assert "verified in 2+ sources" in err

    def test_verify_blocks_unverified(self, tmp_path, capsys):
        paper = tmp_path / "paper.json"
        paper.write_text(json.dumps({"paper": "See [Ghost2024]."}))
        code, out, err = run(["verify", str(paper)], capsys)
        assert code == 1
        assert "BLOCKED" in err

    def test_verify_requires_target(self, capsys):
        code, _, err = run(["verify"], capsys)
        assert code == 1 and "Usage" in err

    def test_bibtex_success(self, monkeypatch, capsys):
        monkeypatch.setattr(
            citation_verifier, "bibtex_from_doi", lambda doi: "@article{x, doi={%s}}" % doi
        )
        code, out, _ = run(["bibtex", "10.1/abc"], capsys)
        assert code == 0 and "10.1/abc" in out

    def test_bibtex_unresolvable(self, capsys):
        code, _, err = run(["bibtex", "10.0000/none"], capsys)
        assert code == 1 and "Could not resolve" in err


class TestPipelineCommands:
    def test_new_status_check(self, isolated_repo, capsys):
        code, out, _ = run(["new", "Sparse", "attention", "--venue", "neurips"], capsys)
        assert code == 0
        run_dir = isolated_repo / "out" / "papers" / "sparse-attention"
        assert out.strip() == str(run_dir)
        manifest = json.loads((run_dir / "run.json").read_text())
        assert manifest["sections"][0] == "abstract" and "related_work" in manifest["sections"]
        code, out, _ = run(["status", str(run_dir)], capsys)
        assert code == 0 and "build: blocked" in out
        code, out, _ = run(["check", str(run_dir), "hypothesis"], capsys)
        assert code == 1 and "hypothesis.json missing" in out

    def test_new_rejects_unknown_venue(self, isolated_repo, capsys):
        code, _, err = run(["new", "x", "--venue", "acl"], capsys)
        assert code == 1 and "unknown venue" in err

    def test_gate_all_and_build_on_demo(self, demo_run, capsys):
        code, out, _ = run(["gate", "all", str(demo_run)], capsys)
        assert code == 0 and out.count("PASS") == 5
        code, out, _ = run(["build", str(demo_run), "--no-pdf"], capsys)
        assert code == 0 and json.loads(out)["references"] == 6

    def test_gate_on_file(self, tmp_path, capsys):
        f = tmp_path / "s.tex"
        f.write_text("We delve into a pivotal question — again.")
        code, out, err = run(["gate", "patterns", str(f)], capsys)
        assert code == 1 and json.loads(out)["details"]["em_dashes"] == 1 and "FAIL" in err

    def test_corpus_and_refs(self, isolated_repo, monkeypatch, capsys):
        run(["new", "topic"], capsys)
        run_dir = isolated_repo / "out" / "papers" / "topic"
        (run_dir / "literature" / "q1.json").write_text(
            json.dumps(
                {
                    "query": "q",
                    "papers": [
                        {
                            "title": "Attention Is All You Need",
                            "authors": ["Ashish Vaswani"],
                            "year": 2017,
                            "source": "arxiv",
                        },
                        {
                            "title": "Ghost paper",
                            "authors": ["No One"],
                            "year": 2024,
                            "source": "crossref",
                        },
                    ],
                }
            )
        )
        code, out, _ = run(["corpus", str(run_dir)], capsys)
        assert code == 0 and "2 unique papers" in out

        def fake_verify(ref, sources=None):
            ok = ref["title"].startswith("Attention")
            return {
                "key": ref["key"],
                "title": ref["title"],
                "verified": ok,
                "found_in": ["crossref", "openalex"] if ok else [],
                "issues": [] if ok else ["not found"],
            }

        monkeypatch.setattr(citation_verifier, "verify_reference", fake_verify)
        code, out, _ = run(["refs", str(run_dir), "c0001", "c0002", "c9999"], capsys)
        assert code == 1
        assert "1 verified" in out and "not in corpus" in out
        code, out, _ = run(["refs", str(run_dir), "--remove", "one2024ghost"], capsys)
        assert code == 0
        code, out, _ = run(["check", str(run_dir), "references"], capsys)
        assert code == 0
