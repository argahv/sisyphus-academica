"""Tests for citation_verifier.py: extraction, parsing, 2-source checks, BibTeX. No network."""

import json

from sisyphus.tools import citation_verifier as cv

WELCH = {
    "key": "welch1947generalization",
    "title": "The generalization of Student's problem when several different population "
    "variances are involved",
    "authors": ["B. L. Welch"],
    "year": 1947,
    "doi": "10.1093/biomet/34.1-2.28",
}

S2_HIT = {
    "data": [
        {
            "title": WELCH["title"],
            "year": 1947,
            "authors": [{"name": "B. L. Welch"}],
            "externalIds": {"DOI": "10.1093/biomet/34.1-2.28"},
        }
    ]
}
CROSSREF_HIT = {
    "message": {
        "DOI": "10.1093/biomet/34.1-2.28",
        "title": [WELCH["title"]],
        "author": [{"given": "B. L.", "family": "Welch"}],
        "issued": {"date-parts": [[1947]]},
        "container-title": ["Biometrika"],
        "type": "journal-article",
        "volume": "34",
        "page": "28-35",
        "issue": "1-2",
    }
}
WRONG_PAPER = {
    "data": [
        {
            "title": "Something else entirely about neural networks",
            "year": 2019,
            "authors": [{"name": "Someone Else"}],
        }
    ]
}


class TestExtractCitations:
    def test_empty_text(self):
        assert cv.extract_citations("") == []

    def test_no_citations(self):
        assert cv.extract_citations("Plain text without references.") == []

    def test_bracket_citation(self):
        assert [c["key"] for c in cv.extract_citations("As shown in [Smith2020].")] == ["Smith2020"]

    def test_bracket_semicolon_list(self):
        keys = [c["key"] for c in cv.extract_citations("See [Smith2020; Jones2019].")]
        assert keys == ["Smith2020", "Jones2019"]

    def test_author_year_and_et_al(self):
        assert cv.extract_citations("Smith (2020) showed X.")[0]["key"] == "Smith2020"
        assert cv.extract_citations("Smith et al. (2020) showed Y.")[0]["key"] == "Smith et al.2020"

    def test_parenthetical(self):
        assert cv.extract_citations("Confirmed (Smith, 2020).")[0]["key"] == "Smith2020"
        assert (
            cv.extract_citations("Proposed in (Smith et al., 2020).")[0]["key"]
            == "Smith et al.2020"
        )

    def test_mixed_formats(self):
        text = "[Jones2019] was early work, but Smith (2020) improved it (Lee, 2021)."
        assert len(cv.extract_citations(text)) == 3

    def test_latex_cite_commands(self):
        text = r"As \citet{a2020} and \citep[p.~3]{b2021, c2022} show, \cite{a2020} again."
        assert [c["key"] for c in cv.extract_citations(text)] == ["a2020", "b2021", "c2022"]

    def test_latex_only_ignores_brackets_and_optional_args(self):
        text = r"\includegraphics[width=0.5]{f.pdf} CI [92.6, 96.0] \cite{x2020}"
        assert [c["key"] for c in cv.extract_citations(text, latex_only=True)] == ["x2020"]

    def test_numeric_intervals_are_not_citations(self):
        assert cv.extract_citations("The interval [0.6, 1.2] is narrow.") == []

    def test_claim_includes_context(self):
        result = cv.extract_citations("Prior research by Smith (2020) established the foundation.")
        assert "Smith (2020)" in result[0]["claim"]


class TestBibliographyParsing:
    def test_parse_bibtex(self):
        bib = """@article{welch1947,
          author = {Welch, B. L. and Student},
          title = {The generalization of {Student's} problem},
          journal = "Biometrika", year = 1947, doi = {10.1093/biomet/34.1-2.28}
        }
        @misc{vaswani2017, title={Attention is all you need}, eprint={1706.03762},
              archivePrefix={arXiv}, year={2017}}"""
        refs = cv.parse_bibtex(bib)
        assert [r["key"] for r in refs] == ["welch1947", "vaswani2017"]
        assert refs[0]["authors"] == ["B. L. Welch", "Student"]
        assert refs[0]["title"] == "The generalization of Student's problem"
        assert refs[0]["year"] == 1947
        assert refs[1]["arxiv_id"] == "1706.03762"

    def test_parse_thebibliography(self):
        tex = r"""\begin{thebibliography}{9}
\bibitem{dls1988}
C.~Dwork, N.~Lynch, and L.~Stockmeyer.
\newblock Consensus in the presence of partial synchrony.
\newblock \textit{JACM}, 1988.

\bibitem{survey}
Autonomous agents on blockchains.
\newblock \textit{arXiv:2601.04583}, 2026.
\end{thebibliography}"""
        refs = cv.parse_thebibliography(tex)
        assert refs[0]["title"] == "Consensus in the presence of partial synchrony"
        assert refs[0]["authors"] == ["C. Dwork", "N. Lynch", "L. Stockmeyer"]
        assert refs[0]["year"] == 1988
        assert refs[1]["arxiv_id"] == "2601.04583"

    def test_load_references_json(self, tmp_path):
        f = tmp_path / "paper.json"
        f.write_text(
            json.dumps({"paper": "See [A2020].", "references": [{"key": "A2020", "title": "T"}]})
        )
        text, refs = cv.load_references(f)
        assert text == "See [A2020]." and refs[0]["key"] == "A2020"


class TestVerification:
    def test_verified_when_two_sources_match(self, fake_api):
        fake_api.json("semanticscholar", S2_HIT)
        fake_api.json("api.crossref.org/works/10.1093", CROSSREF_HIT)
        result = cv.verify_reference(WELCH)
        assert result["verified"] is True
        assert set(result["found_in"]) == {"semantic_scholar", "crossref"}

    def test_single_source_is_not_verified(self, fake_api):
        fake_api.json("semanticscholar", S2_HIT)
        result = cv.verify_reference(WELCH)
        assert result["verified"] is False
        assert "needs 2+ sources" in result["issues"][0]

    def test_not_found_is_flagged_as_hallucination(self, fake_api):
        result = cv.verify_reference({"key": "fake2024", "title": "A paper that does not exist"})
        assert result["verified"] is False
        assert "hallucinated" in result["issues"][0]

    def test_wrong_title_does_not_count(self, fake_api):
        fake_api.json("semanticscholar", WRONG_PAPER)
        fake_api.json(
            "api.crossref.org/works?",
            {"message": {"items": [{"title": ["Unrelated"], "DOI": "10.9/z"}]}},
        )
        assert cv.verify_reference(WELCH)["verified"] is False

    def test_year_mismatch_rejected(self):
        cand = {"title": WELCH["title"], "year": 1990, "authors": ["B. L. Welch"]}
        ok, reason = cv.match_candidate(WELCH, cand)
        assert not ok and "year" in reason

    def test_author_mismatch_rejected(self):
        cand = {"title": WELCH["title"], "year": 1947, "authors": ["Someone Else"]}
        assert cv.match_candidate(WELCH, cand)[0] is False

    def test_doi_pointing_to_other_paper_rejected(self):
        cand = {"title": "Totally unrelated title", "doi": WELCH["doi"], "year": 1947}
        ok, reason = cv.match_candidate(WELCH, cand)
        assert not ok and "different title" in reason

    def test_verify_citations_blocks_missing_entries(self):
        result = cv.verify_citations({"paper": "As shown in [Smith2020], see also [Jones2019]."})
        assert result["total_citations"] == 2
        assert result["blocked"] is True
        assert result["missing_references"] == ["Smith2020", "Jones2019"]

    def test_verify_citations_uses_cache_and_reports_uncited(self):
        fp = cv._fingerprint(WELCH)
        cache = {
            fp: {
                "key": WELCH["key"],
                "verified": True,
                "found_in": ["crossref", "openalex"],
                "issues": [],
            }
        }
        other = {"key": "unused2020", "title": "Unused"}
        result = cv.verify_citations(
            {
                "paper": r"Welch's test \citep{welch1947generalization}.",
                "references": [WELCH, other],
            },
            cache=cache,
        )
        assert result["blocked"] is False
        assert result["verified"] == 1
        assert result["uncited_references"] == ["unused2020"]

    def test_empty_findings(self):
        result = cv.verify_citations({})
        assert result["total_citations"] == 0 and result["blocked"] is False

    def test_verify_citation_backward_compatible_shape(self):
        result = cv.verify_citation("Smith2020", "A" * 500)
        assert result["citation_key"] == "Smith2020"
        assert len(result["claim"]) == 200
        assert isinstance(result["issues"], list)


class TestBibtex:
    def test_returns_empty_without_identifier(self):
        assert cv.generate_bibtex({}) == ""
        assert cv.generate_bibtex({"title": "Test"}) == ""

    def test_full_entry(self):
        bib = cv.generate_bibtex(
            {**WELCH, "venue": "Biometrika", "type": "article", "volume": "34", "pages": "28-35"}
        )
        assert bib.startswith("@article{welch1947generalization,")
        assert "author = {Welch, B. L.}" in bib
        assert "journal = {Biometrika}" in bib
        assert "pages = {28--35}" in bib
        assert "doi = {10.1093/biomet/34.1-2.28}" in bib
        assert bib.endswith("}")

    def test_arxiv_only_entry_and_escaping(self):
        bib = cv.generate_bibtex(
            {
                "title": "Questions & answers at 50% scale",
                "arxiv_id": "1706.03762v2",
                "year": 2017,
                "authors": ["Ada Lovelace"],
            }
        )
        assert bib.startswith("@misc{lovelace2017questions,")
        assert "Questions \\& answers at 50\\% scale" in bib
        assert "eprint = {1706.03762}" in bib

    def test_bibtex_from_doi_uses_crossref(self, fake_api):
        fake_api.json("api.crossref.org/works/10.1093", CROSSREF_HIT)
        bib = cv.bibtex_from_doi("https://doi.org/10.1093/biomet/34.1-2.28")
        assert "Welch, B. L." in bib and "number = {1-2}" in bib and "year = {1947}" in bib

    def test_bibtex_from_doi_falls_back_to_doi_org(self, fake_api):
        fake_api.text("doi.org/10.48550", "@misc{x, title={From DataCite}}")
        assert cv.bibtex_from_doi("10.48550/arXiv.1706.03762").startswith("@misc{x")

    def test_bibtex_from_unknown_doi_returns_none(self, fake_api):
        assert cv.bibtex_from_doi("10.0000/none") is None
