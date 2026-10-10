"""Tests for the run workspace, handoff checks, novelty ranking, gates and the formatter."""

import json

import pytest

from sisyphus.tools import build, gates, novelty, workspace


def test_demo_run_passes_all_gates(demo_run):
    for gate in gates.GATES:
        assert gates.run_gate(demo_run, gate)["passed"], gate
    assert gates.build_ready(demo_run) == []


def test_rerunning_citation_gate_keeps_other_gates_current(demo_run):
    for gate in ("statistics", "patterns", "style", "reviews", "citations"):
        gates.run_gate(demo_run, gate)
    gates.run_gate(demo_run, "citations")
    assert gates.build_ready(demo_run) == []


def test_build_refuses_before_gates(demo_run):
    with pytest.raises(build.BuildError, match="has not been run"):
        build.build(demo_run, pdf=False)


def test_build_refuses_when_draft_changes_after_gates(demo_run):
    for gate in gates.GATES:
        gates.run_gate(demo_run, gate)
    conclusion = demo_run / "draft" / "conclusion.tex"
    conclusion.write_text(conclusion.read_text() + "\nWelch's test is the safer default.\n")
    problems = gates.build_ready(demo_run)
    assert any("earlier draft" in p for p in problems)
    assert not any(p.startswith("gate reviews") or "reviewers accepted" in p for p in problems)


def test_large_post_review_change_needs_new_review(demo_run):
    for gate in gates.GATES:
        gates.run_gate(demo_run, gate)
    (demo_run / "draft" / "discussion.tex").write_text("A different discussion. " * 80)
    for gate in ("citations", "statistics", "patterns", "style"):
        gates.run_gate(demo_run, gate)
    assert any("since all 10 reviewers accepted" in p for p in gates.build_ready(demo_run))


def test_failing_gate_blocks_build(demo_run):
    (demo_run / "draft" / "results.tex").write_text(
        (demo_run / "draft" / "results.tex").read_text().replace("$z = 1.16$", "$z = 3.16$")
    )
    result = gates.run_gate(demo_run, "statistics")
    assert not result["passed"]
    assert any(i["check"] == "p_mismatch" for i in result["details"]["issues"])


def test_build_writes_tex_and_bib(demo_run):
    for gate in gates.GATES:
        gates.run_gate(demo_run, gate)
    result = build.build(demo_run, pdf=False)
    tex = (demo_run / "build" / "paper.tex").read_text()
    bib = (demo_run / "build" / "references.bib").read_text()
    assert "<<" not in tex
    assert "\\section{Results}" in tex and "\\bibliography{references}" in tex
    assert result["references"] == 6 and bib.count("@article{") == 6


def test_build_without_latex_reports_message(demo_run, monkeypatch):
    for gate in gates.GATES:
        gates.run_gate(demo_run, gate)
    monkeypatch.setattr(build, "latex_command", lambda: None)
    result = build.build(demo_run)
    assert result["pdf"] is None and "No LaTeX found" in result["message"]


def test_verification_report_has_annotations(demo_run):
    (demo_run / "draft" / "discussion.tex").write_text(
        "We delve into a pivotal question \u2014 again.\n"
    )
    report = gates.run_verification(demo_run)
    assert not report["ready_for_review"]
    assert {a["gate"] for a in report["annotations"]} >= {"patterns"}
    assert (demo_run / "verification" / "report.json").exists()


def test_reviews_round_limit_message(demo_run):
    (demo_run / "reviews" / "skeptic.json").write_text(
        json.dumps(
            {
                "reviewer": "skeptic",
                "score": 4,
                "strengths": [],
                "weaknesses": ["x"],
                "recommendation": "reject",
                "must_fix": [{"issue": "a", "required_change": "b"}],
            }
        )
    )
    for _ in range(workspace.MAX_REVIEW_ROUNDS):
        result = gates.run_gate(demo_run, "reviews")
    assert "stop and report" in result["summary"]


class TestHandoffChecks:
    def test_demo_stages(self, demo_run):
        for stage in ("hypothesis", "methodology", "analysis", "references", "outline", "draft"):
            assert workspace.check_stage(demo_run, stage) == [], stage

    def test_draft_with_unknown_cite_and_section(self, demo_run):
        (demo_run / "draft" / "methods.tex").write_text(
            "\\section{Methods}\nAs in \\citep{ghost2024}.\n"
        )
        problems = workspace.check_stage(demo_run, "draft")
        assert any("must not contain \\section" in p for p in problems)
        assert any("ghost2024" in p for p in problems)

    def test_empirical_paper_needs_analysis(self, demo_run):
        (demo_run / "analysis" / "statistics.json").unlink()
        assert any(
            "statistics.json missing" in p for p in workspace.check_stage(demo_run, "analysis")
        )

    def test_unknown_stage(self, demo_run):
        with pytest.raises(ValueError):
            workspace.check_stage(demo_run, "nope")


class TestNovelty:
    def _engine(self, run, name, items):
        (run / "novelty").mkdir(exist_ok=True)
        (run / "novelty" / f"{name}.json").write_text(
            json.dumps({"engine": name, "hypotheses": items})
        )

    def test_rank_normalizes_aliases_and_flags_unsupported(self, demo_run):
        (demo_run / "literature").mkdir()
        (demo_run / "literature" / "corpus.json").write_text(
            json.dumps({"papers": [{"id": "c0001", "key": "ruxton2006unequal", "title": "t"}]})
        )
        for engine in workspace.ENGINES:
            self._engine(demo_run, engine, [])
        self._engine(
            demo_run,
            "contrarian",
            [
                {
                    "id": "CT-1",
                    "inverted_hypothesis": "Real idea",
                    "novelty_score": 8,
                    "plausibility": 7,
                    "impact_if_true": 9,
                    "evidence_that_supports_inversion": ["c0001 shows inflation"],
                },
                {
                    "id": "CT-2",
                    "inverted_hypothesis": "Made-up support",
                    "novelty_score": 9,
                    "plausibility": 9,
                    "impact_if_true": 9,
                    "evidence_that_supports_inversion": ["Paper A shows X"],
                },
            ],
        )
        self._engine(
            demo_run,
            "heretic",
            [
                {
                    "id": "H-1",
                    "hypothesis": "Wild",
                    "novelty_gap": 10,
                    "tractability": 3,
                    "potential_impact": 10,
                    "evidence": ["c0001"],
                }
            ],
        )
        result = novelty.rank(demo_run)
        assert result["by_engine"]["contrarian"] == 2
        assert [h["id"] for h in result["top"]] == ["CT-1"]
        unsupported = [h for h in result["all"] if not h["supported"]]
        assert [h["id"] for h in unsupported] == ["CT-2"]
        assert (demo_run / "novelty" / "ranked.json").exists()

    def test_no_novel_angle(self, demo_run):
        for engine in workspace.ENGINES:
            self._engine(
                demo_run,
                engine,
                [
                    {
                        "hypothesis": "weak",
                        "novelty": 3,
                        "tractability": 9,
                        "impact": 2,
                        "evidence": [],
                    }
                ],
            )
        assert novelty.rank(demo_run)["no_novel_angle"] is True


def test_templates_have_matching_sections():
    for venue in workspace.venues():
        sections = workspace.template_sections(venue)
        assert sections[0] == "abstract", venue
        assert "introduction" in sections and "results" in sections, venue
    assert set(workspace.venues()) == {"arxiv", "neurips", "icml", "iclr", "nature"}


@pytest.mark.skipif(build.latex_command() is None, reason="LaTeX not installed")
def test_pdf_compiles_without_undefined_citations(demo_run):
    for gate in gates.GATES:
        gates.run_gate(demo_run, gate)
    result = build.build(demo_run)
    assert result["pdf"] and result["pages"] >= 2
