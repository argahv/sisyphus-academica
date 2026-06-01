"""Tests for citation_verifier.py — all local logic, no network calls."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from citation_verifier import (
    format_authors_for_bibtex,
    verify_citation,
    verify_citations,
    generate_bibtex,
)


class TestVerifyCitation:
    """verify_citation() — local logic only (no mocked API)."""

    def test_returns_dict_with_required_keys(self):
        """Smoke: returns correct structure even when APIs fail (no mock)."""
        result = verify_citation("key", "some claim text here")
        assert "citation_key" in result
        assert "claim" in result
        assert "verified" in result
        assert "issues" in result
        assert isinstance(result["issues"], list)

    def test_citation_key_preserved(self):
        result = verify_citation("Smith2020", "Smith et al. demonstrated X")
        assert result["citation_key"] == "Smith2020"

    def test_claim_truncated_to_200_chars(self):
        long_claim = "A" * 500
        result = verify_citation("key", long_claim)
        assert len(result["claim"]) == 200

    def test_empty_citation_does_not_crash(self):
        result = verify_citation("", "")
        assert isinstance(result, dict)


class TestVerifyCitations:
    """verify_citations() — local text extraction logic."""

    def test_empty_findings_returns_zero_citations(self):
        result = verify_citations({})
        assert result["total_citations"] == 0
        assert result["verified"] == 0
        assert result["hallucinated_count"] == 0

    def test_findings_without_paper_key(self):
        result = verify_citations({"other": "data"})
        assert result["total_citations"] == 0

    def test_extracts_bracket_citations_from_text(self):
        findings = {"paper": "As shown in [Smith2020], the method works. See also [Jones2019]."}
        result = verify_citations(findings)
        # Both citations get extracted; each runs through verify_citation
        # which may or may not find them (we test structure only)
        assert result["total_citations"] == 2
        assert len(result["details"]) == 2

    def test_no_false_positives_on_text_without_brackets(self):
        findings = {"paper": "Smith et al. 2020 showed that learning works."}
        result = verify_citations(findings)
        assert result["total_citations"] == 0

    def test_result_structure(self):
        findings = {"paper": "See [Test2024]."}
        result = verify_citations(findings)
        assert "blocked" in result
        assert "hallucinated_citations" in result
        assert isinstance(result["blocked"], bool)
        assert isinstance(result["hallucinated_citations"], list)


class TestFormatAuthorsForBibtex:
    """format_authors_for_bibtex() — pure formatting."""

    def test_empty_list_returns_fallback(self):
        assert format_authors_for_bibtex([]) == "Author, A."

    def test_none_returns_fallback(self):
        assert format_authors_for_bibtex(None) == "Author, A."

    def test_non_list_returns_fallback(self):
        assert format_authors_for_bibtex("not a list") == "Author, A."

    def test_single_author_string(self):
        assert format_authors_for_bibtex(["John Smith"]) == "Smith, J."

    def test_multiple_authors_strings(self):
        result = format_authors_for_bibtex(["John Smith", "Jane Doe"])
        assert result == "Smith, J. and Doe, J."

    def test_author_dict_with_name_key(self):
        result = format_authors_for_bibtex([{"name": "John Smith"}])
        assert result == "Smith, J."

    def test_author_middle_name(self):
        result = format_authors_for_bibtex(["John A. Smith"])
        assert result == "Smith, J. A."

    def test_single_word_name_preserved(self):
        result = format_authors_for_bibtex(["Einstein"])
        assert result == "Einstein"

    def test_mixed_empty_and_valid(self):
        result = format_authors_for_bibtex(["", "John Smith", None])
        assert result == "Smith, J."


class TestGenerateBibtex:
    """generate_bibtex() — pure string formatting."""

    def test_returns_empty_for_no_doi(self):
        assert generate_bibtex({}) == ""

    def test_returns_empty_for_missing_doi_key(self):
        assert generate_bibtex({"title": "Test"}) == ""

    def test_returns_bibtex_string_without_authors(self):
        paper = {
            "doi": "10.1234/test.2024.001",
            "title": "A Test Paper",
            "year": 2024,
        }
        bib = generate_bibtex(paper)
        assert bib.startswith("@article{")
        assert "10.1234/test.2024.001" in bib
        assert "A Test Paper" in bib
        assert "Author, A." in bib
        assert bib.endswith("}")

    def test_bibtex_includes_year(self):
        paper = {"doi": "10.1/abc", "title": "T", "year": 2023}
        bib = generate_bibtex(paper)
        assert "2023" in bib

    def test_bibtex_with_string_authors(self):
        paper = {
            "doi": "10.1234/test.2024.001",
            "title": "A Test Paper",
            "year": 2024,
            "authors": ["John Smith", "Jane Doe"],
        }
        bib = generate_bibtex(paper)
        assert "Smith, J." in bib
        assert "Doe, J." in bib
        assert bib.split(",")[0].split("{")[-1] == "Smith2024"

    def test_bibtex_with_dict_authors(self):
        paper = {
            "doi": "10.1234/test.2024.001",
            "title": "A Test Paper",
            "year": 2024,
            "authors": [{"name": "John Smith"}, {"name": "Jane Doe"}],
        }
        bib = generate_bibtex(paper)
        assert "Smith, J." in bib
        assert "Doe, J." in bib
        assert bib.split(",")[0].split("{")[-1] == "Smith2024"

    def test_bibtex_with_single_author(self):
        paper = {
            "doi": "10.1/single.2023",
            "title": "Single Author",
            "year": 2023,
            "authors": ["Einstein"],
        }
        bib = generate_bibtex(paper)
        assert "Einstein" in bib
        assert "Einstein2023" in bib

    def test_bibtex_with_empty_authors_falls_back(self):
        paper = {"doi": "10.1/fallback", "title": "Fallback", "year": 2024, "authors": []}
        bib = generate_bibtex(paper)
        assert "Author, A." in bib
        assert "Authorn.d." not in bib

    def test_bibtex_key_uses_first_author_last_name(self):
        paper = {
            "doi": "10.1/keytest",
            "title": "Key Test",
            "year": 2023,
            "authors": ["Ada Lovelace", "Charles Babbage"],
        }
        bib = generate_bibtex(paper)
        assert bib.startswith("@article{Lovelace2023,")

    def test_bibtex_formats_and_separator(self):
        paper = {
            "doi": "10.1/andtest",
            "title": "And Test",
            "year": 2022,
            "authors": ["Alice Alpha", "Bob Beta"],
        }
        bib = generate_bibtex(paper)
        assert " and " in bib


