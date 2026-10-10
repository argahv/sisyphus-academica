"""Tests for literature_client.py and net.py: parsing, merging, retries. No network."""

import io
import json
import urllib.error

from sisyphus.tools import literature_client as lit
from sisyphus.tools import net

ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v7</id>
    <published>2017-06-12T17:57:34Z</published>
    <title>Attention Is All
      You Need</title>
    <summary>The dominant sequence transduction models...</summary>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <arxiv:doi>10.48550/arXiv.1706.03762</arxiv:doi>
    <category term="cs.CL"/>
  </entry>
</feed>"""

S2_PAYLOAD = {
    "data": [
        {
            "title": "Attention is All you Need",
            "year": 2017,
            "abstract": "abc",
            "citationCount": 100000,
            "authors": [{"name": "Ashish Vaswani"}],
            "externalIds": {"ArXiv": "1706.03762"},
            "publicationVenue": None,
            "venue": "NeurIPS",
            "url": "https://s2/x",
        }
    ]
}

CROSSREF_PAYLOAD = {
    "message": {
        "items": [
            {
                "DOI": "10.5555/3295222.3295349",
                "title": ["Attention is all you need"],
                "author": [{"given": "Ashish", "family": "Vaswani"}],
                "issued": {"date-parts": [[2017, 12]]},
                "container-title": ["NeurIPS"],
                "type": "proceedings-article",
                "abstract": "<jats:p>abc</jats:p>",
            }
        ]
    }
}

OPENALEX_PAYLOAD = {
    "results": [
        {
            "title": "Attention Is All You Need",
            "doi": "https://doi.org/10.5555/3295222.3295349",
            "publication_year": 2017,
            "cited_by_count": 5000,
            "authorships": [{"author": {"display_name": "Ashish Vaswani"}}],
            "abstract_inverted_index": {"dominant": [1], "The": [0]},
            "primary_location": {"source": {"display_name": "NeurIPS"}},
        }
    ]
}


class TestDeduplicatePapers:
    def test_empty_list(self):
        assert lit.deduplicate_papers([]) == []

    def test_identical_titles_deduplicated(self):
        papers = [
            {"title": "Same Title", "source": "arxiv"},
            {"title": "Same Title", "source": "crossref"},
        ]
        result = lit.deduplicate_papers(papers)
        assert len(result) == 1
        assert result[0]["sources"] == ["arxiv", "crossref"]

    def test_case_and_whitespace_normalized(self):
        papers = [
            {"title": "  Machine Learning  ", "source": "arxiv"},
            {"title": "machine learning", "source": "x"},
        ]
        assert len(lit.deduplicate_papers(papers)) == 1

    def test_different_titles_preserved(self):
        papers = [{"title": "Paper One"}, {"title": "Paper Two"}]
        assert len(lit.deduplicate_papers(papers)) == 2

    def test_long_titles_truncated_to_80_chars(self):
        papers = [{"title": "A" * 100}, {"title": "A" * 80 + "B" * 20}]
        assert len(lit.deduplicate_papers(papers)) == 1

    def test_none_or_empty_title_skipped(self):
        papers = [{"title": None}, {"title": ""}, {"title": "Real Paper"}]
        result = lit.deduplicate_papers(papers)
        assert [p["title"] for p in result] == ["Real Paper"]

    def test_does_not_mutate_input(self):
        papers = [
            {"title": "Test", "source": "arxiv", "authors": ["A"]},
            {"title": "Test", "source": "crossref", "authors": ["A", "B"], "doi": "10.1/x"},
        ]
        snapshot = json.loads(json.dumps(papers))
        lit.deduplicate_papers(papers)
        assert papers == snapshot

    def test_merge_fills_missing_fields(self):
        papers = [
            {"title": "Test", "source": "arxiv", "authors": ["A"], "doi": ""},
            {
                "title": "Test",
                "source": "crossref",
                "authors": ["A", "B"],
                "doi": "10.1/x",
                "citation_count": 9,
            },
        ]
        merged = lit.deduplicate_papers(papers)[0]
        assert merged["doi"] == "10.1/x"
        assert merged["authors"] == ["A", "B"]
        assert merged["citation_count"] == 9

    def test_same_doi_deduplicated_despite_title(self):
        papers = [
            {"title": "Short title", "doi": "10.1/X"},
            {"title": "Completely different", "doi": "10.1/x"},
        ]
        assert len(lit.deduplicate_papers(papers)) == 1

    def test_fuzzy_dedup_with_threshold(self):
        papers = [{"title": "Attention Is All You Need"}, {"title": "Attention is All you Need."}]
        assert len(lit.deduplicate_papers(papers, fuzzy_threshold=0.85)) == 1

    def test_fuzzy_keeps_distinct_titles(self):
        papers = [{"title": "Deep Learning"}, {"title": "Reinforcement Learning"}]
        assert len(lit.deduplicate_papers(papers, fuzzy_threshold=0.85)) == 2

    def test_fuzzy_threshold_zero_disabled(self):
        papers = [
            {"title": "A Novel Approach to Neural Machine Translation"},
            {"title": "A Novel Approach to Neural Machine Translation NIPS 2017"},
        ]
        assert len(lit.deduplicate_papers(papers, fuzzy_threshold=0.0)) == 2


class TestParsers:
    def test_parse_arxiv(self):
        [p] = lit.parse_arxiv(ARXIV_XML)
        assert p["title"] == "Attention Is All You Need"
        assert p["authors"] == ["Ashish Vaswani", "Noam Shazeer"]
        assert p["year"] == 2017
        assert p["arxiv_id"] == "1706.03762"
        assert p["doi"] == "10.48550/arxiv.1706.03762"

    def test_parse_semantic_scholar_handles_null_venue(self):
        [p] = lit.parse_semantic_scholar(S2_PAYLOAD)
        assert p["venue"] == "NeurIPS"
        assert p["arxiv_id"] == "1706.03762"
        assert p["citation_count"] == 100000

    def test_parse_crossref_full_names_year_and_abstract(self):
        [p] = lit.parse_crossref(CROSSREF_PAYLOAD)
        assert p["authors"] == ["Ashish Vaswani"]
        assert p["year"] == 2017
        assert p["abstract"] == "abc"
        assert p["type"] == "inproceedings"

    def test_parse_openalex_rebuilds_abstract(self):
        [p] = lit.parse_openalex(OPENALEX_PAYLOAD)
        assert p["abstract"] == "The dominant"
        assert p["doi"] == "10.5555/3295222.3295349"

    def test_arxiv_query_joins_terms(self):
        assert lit.arxiv_search_query("sparse attention") == "all:sparse AND all:attention"


class TestSearchAll:
    def test_merges_sources_and_ranks_multi_source_first(self, fake_api):
        fake_api.text("export.arxiv.org", ARXIV_XML)
        fake_api.json("semanticscholar", S2_PAYLOAD)
        fake_api.json("crossref", CROSSREF_PAYLOAD)
        fake_api.json("openalex", OPENALEX_PAYLOAD)
        result = lit.search_all("attention")
        assert result["by_source"] == {
            "arxiv": 1,
            "semantic_scholar": 1,
            "crossref": 1,
            "openalex": 1,
        }
        assert result["total_unique"] == 1
        assert sorted(result["papers"][0]["sources"]) == sorted(lit.SOURCES)

    def test_failed_source_degrades_gracefully(self, fake_api):
        fake_api.json("crossref", CROSSREF_PAYLOAD)
        result = lit.search_all("attention", sources=["crossref", "openalex"])
        assert result["by_source"] == {"crossref": 1, "openalex": 0}

    def test_api_key_and_email_are_sent(self, fake_api, monkeypatch):
        seen = {}
        monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "k123")
        monkeypatch.setenv("CROSSREF_EMAIL", "me@example.org")

        def capture(url, headers=None, **kw):
            seen[url.split("/")[2]] = (url, headers or {})
            return None

        monkeypatch.setattr(net, "fetch_json", capture)
        lit.search_semantic_scholar("x")
        lit.search_crossref("x")
        assert seen["api.semanticscholar.org"][1] == {"x-api-key": "k123"}
        assert "mailto=me%40example.org" in seen["api.crossref.org"][0]

    def test_merge_corpus_assigns_ids_and_keys(self, tmp_path):
        a = tmp_path / "a.json"
        a.write_text(
            json.dumps(
                {
                    "query": "q1",
                    "papers": [
                        {
                            "title": "Attention Is All You Need",
                            "authors": ["Ashish Vaswani"],
                            "year": 2017,
                            "source": "arxiv",
                        }
                    ],
                }
            )
        )
        b = tmp_path / "b.json"
        b.write_text(
            json.dumps(
                {
                    "query": "q2",
                    "papers": [
                        {
                            "title": "attention is all you need",
                            "source": "crossref",
                            "doi": "10.1/x",
                        },
                        {
                            "title": "BERT",
                            "authors": ["Jacob Devlin"],
                            "year": 2019,
                            "source": "crossref",
                        },
                    ],
                }
            )
        )
        corpus = lit.merge_corpus([a, b])
        assert corpus["total_unique"] == 2
        ids = {p["id"] for p in corpus["papers"]}
        assert ids == {"c0001", "c0002"}
        assert any(p["key"] == "vaswani2017attention" for p in corpus["papers"])


class TestNetRetry:
    def test_retries_then_succeeds(self, monkeypatch):
        calls = []

        def flaky(req, timeout=0):
            calls.append(1)
            if len(calls) < 3:
                raise urllib.error.HTTPError(req.full_url, 503, "busy", {}, None)
            return io.BytesIO(b'{"ok": true}')

        monkeypatch.setattr(net.urllib.request, "urlopen", flaky)
        assert net.fetch_json("https://x") == {"ok": True}
        assert len(calls) == 3

    def test_gives_up_after_max_retries(self, monkeypatch):
        calls = []

        def down(req, timeout=0):
            calls.append(1)
            raise urllib.error.URLError("down")

        monkeypatch.setattr(net.urllib.request, "urlopen", down)
        assert net.fetch("https://x", max_retries=2) is None
        assert len(calls) == 2

    def test_404_is_not_retried(self, monkeypatch):
        calls = []

        def missing(req, timeout=0):
            calls.append(1)
            raise urllib.error.HTTPError(req.full_url, 404, "nf", {}, None)

        monkeypatch.setattr(net.urllib.request, "urlopen", missing)
        assert net.fetch("https://x") is None
        assert len(calls) == 1
