#!/usr/bin/env python3
"""
Sisyphus Academica: Literature API Client
Multi-source literature search: arXiv, Semantic Scholar, CrossRef, OpenAlex.
Queries run in parallel. Results are normalized and deduplicated, and each
record lists every source that returned it.
"""

import difflib
import html
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    from . import net, settings
except ImportError:  # run as a script: python3 tools/literature_client.py
    import net
    import settings


ARXIV_API = "https://export.arxiv.org/api/query"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper"
CROSSREF_API = "https://api.crossref.org/works"
OPENALEX_API = "https://api.openalex.org/works"

SOURCES = ("arxiv", "semantic_scholar", "crossref", "openalex")
DEFAULT_LIMITS = {"arxiv": 100, "semantic_scholar": 100, "crossref": 50, "openalex": 50}

ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

S2_FIELDS = "title,authors,year,abstract,citationCount,externalIds,venue,publicationVenue,url"


def _log(message: str) -> None:
    print(message, file=sys.stderr)


def normalize_doi(doi: Optional[str]) -> str:
    if not doi:
        return ""
    doi = doi.strip().lower()
    return re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", doi)


def normalize_arxiv_id(arxiv_id: Optional[str]) -> str:
    if not arxiv_id:
        return ""
    arxiv_id = re.sub(r"^(https?://arxiv\.org/abs/|arxiv:)", "", arxiv_id.strip(), flags=re.I)
    return re.sub(r"v\d+$", "", arxiv_id)


def _strip_tags(text: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text or "")).split())


def _record(source: str, **fields) -> Dict:
    paper = {
        "title": " ".join((fields.get("title") or "").split()),
        "authors": [a for a in fields.get("authors") or [] if a],
        "year": fields.get("year") or None,
        "abstract": fields.get("abstract") or "",
        "doi": normalize_doi(fields.get("doi")),
        "arxiv_id": normalize_arxiv_id(fields.get("arxiv_id")),
        "venue": fields.get("venue") or "",
        "citation_count": fields.get("citation_count") or 0,
        "url": fields.get("url") or "",
        "source": source,
        "sources": [source],
    }
    for extra in ("categories", "concepts", "open_access", "volume", "pages", "type"):
        if fields.get(extra):
            paper[extra] = fields[extra]
    return paper


# ---------------------------------------------------------------- arXiv


def arxiv_search_query(query: str) -> str:
    terms = [t for t in re.split(r"\s+", query.strip()) if t]
    return " AND ".join(f"all:{t}" for t in terms) if terms else "all:*"


def parse_arxiv(xml_text: str) -> List[Dict]:
    root = ET.fromstring(xml_text)
    papers = []
    for entry in root.findall("atom:entry", ARXIV_NS):

        def text(tag):
            node = entry.find(tag, ARXIV_NS)
            return (node.text or "") if node is not None else ""

        published = text("atom:published")
        doi = text("arxiv:doi")
        for link in entry.findall("atom:link", ARXIV_NS):
            if link.get("title") == "doi" and not doi:
                doi = link.get("href", "")
        papers.append(
            _record(
                "arxiv",
                title=text("atom:title"),
                authors=[
                    n.text for n in entry.findall("atom:author/atom:name", ARXIV_NS) if n.text
                ],
                year=int(published[:4]) if published[:4].isdigit() else None,
                abstract=" ".join(text("atom:summary").split()),
                doi=doi,
                arxiv_id=text("atom:id"),
                venue=text("arxiv:journal_ref") or "arXiv",
                url=text("atom:id"),
                categories=[
                    c.get("term") for c in entry.findall("atom:category", ARXIV_NS) if c.get("term")
                ],
            )
        )
    return papers


def search_arxiv(query: str, max_results: int = 100) -> List[Dict]:
    """Search arXiv via its REST API."""
    params = urllib.parse.urlencode(
        {
            "search_query": arxiv_search_query(query),
            "start": 0,
            "max_results": min(max_results, 200),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
    )
    body = net.fetch_text(f"{ARXIV_API}?{params}", label="arXiv")
    if body is None:
        return []
    try:
        return parse_arxiv(body)
    except ET.ParseError as e:
        _log(f"  arXiv: could not parse response ({e})")
        return []


# ------------------------------------------------------- Semantic Scholar


def parse_semantic_scholar_item(item: Dict) -> Dict:
    ids = item.get("externalIds") or {}
    venue = (item.get("publicationVenue") or {}).get("name") or item.get("venue") or ""
    return _record(
        "semantic_scholar",
        title=item.get("title"),
        authors=[a.get("name", "") for a in item.get("authors") or []],
        year=item.get("year"),
        abstract=item.get("abstract"),
        doi=ids.get("DOI"),
        arxiv_id=ids.get("ArXiv"),
        venue=venue,
        citation_count=item.get("citationCount"),
        url=item.get("url"),
    )


def parse_semantic_scholar(data: Dict) -> List[Dict]:
    return [parse_semantic_scholar_item(i) for i in (data or {}).get("data") or [] if i]


def search_semantic_scholar(query: str, limit: int = 100) -> List[Dict]:
    """Search Semantic Scholar. Uses SEMANTIC_SCHOLAR_API_KEY when set."""
    params = urllib.parse.urlencode({"query": query, "limit": min(limit, 100), "fields": S2_FIELDS})
    data = net.fetch_json(
        f"{SEMANTIC_SCHOLAR_API}/search?{params}",
        headers=settings.semantic_scholar_headers(),
        label="Semantic Scholar",
    )
    return parse_semantic_scholar(data) if data else []


# ---------------------------------------------------------------- CrossRef

CROSSREF_TYPES = {
    "journal-article": "article",
    "proceedings-article": "inproceedings",
    "posted-content": "misc",
    "book": "book",
    "book-chapter": "incollection",
    "report": "techreport",
    "dissertation": "phdthesis",
}


def _crossref_year(item: Dict) -> Optional[int]:
    for field in ("published-print", "published-online", "issued", "created"):
        parts = (item.get(field) or {}).get("date-parts") or [[None]]
        if parts and parts[0] and parts[0][0]:
            return int(parts[0][0])
    return None


def parse_crossref_item(item: Dict) -> Dict:
    authors = []
    for a in item.get("author") or []:
        name = " ".join(p for p in (a.get("given"), a.get("family")) if p) or a.get("name", "")
        authors.append(name)
    container = item.get("container-title") or []
    return _record(
        "crossref",
        title=" ".join(item.get("title") or []),
        authors=authors,
        year=_crossref_year(item),
        abstract=_strip_tags(item.get("abstract", "")),
        doi=item.get("DOI"),
        venue=container[0] if container else "",
        citation_count=item.get("is-referenced-by-count"),
        url=item.get("URL"),
        volume=item.get("volume"),
        pages=item.get("page"),
        type=CROSSREF_TYPES.get(item.get("type", ""), "misc"),
    )


def parse_crossref(data: Dict) -> List[Dict]:
    return [parse_crossref_item(i) for i in ((data or {}).get("message") or {}).get("items") or []]


def crossref_headers() -> Dict[str, str]:
    email = settings.contact_email()
    return {"User-Agent": f"{net.USER_AGENT} (mailto:{email})"} if email else {}


def search_crossref(query: str, rows: int = 50) -> List[Dict]:
    """Search CrossRef. Uses CROSSREF_EMAIL for the polite pool when set."""
    params = {"query.bibliographic": query, "rows": min(rows, 100)}
    email = settings.contact_email()
    if email:
        params["mailto"] = email
    data = net.fetch_json(
        f"{CROSSREF_API}?{urllib.parse.urlencode(params)}",
        headers=crossref_headers(),
        label="CrossRef",
    )
    return parse_crossref(data) if data else []


# ---------------------------------------------------------------- OpenAlex


def _openalex_abstract(inverted: Optional[Dict]) -> str:
    if not inverted:
        return ""
    positions = [(pos, word) for word, poss in inverted.items() for pos in poss]
    return " ".join(word for _, word in sorted(positions))


def parse_openalex_item(item: Dict) -> Dict:
    location = item.get("primary_location") or {}
    source = location.get("source") or {}
    ids = item.get("ids") or {}
    return _record(
        "openalex",
        title=item.get("title") or item.get("display_name"),
        authors=[
            (a.get("author") or {}).get("display_name", "") for a in item.get("authorships") or []
        ],
        year=item.get("publication_year"),
        abstract=_openalex_abstract(item.get("abstract_inverted_index")),
        doi=item.get("doi"),
        arxiv_id=ids.get("arxiv", ""),
        venue=source.get("display_name") or "",
        citation_count=item.get("cited_by_count"),
        url=item.get("id"),
        open_access=(item.get("open_access") or {}).get("is_oa", False),
        concepts=[c.get("display_name", "") for c in (item.get("concepts") or [])[:5]],
    )


def parse_openalex(data: Dict) -> List[Dict]:
    return [parse_openalex_item(i) for i in (data or {}).get("results") or []]


def search_openalex(query: str, per_page: int = 50) -> List[Dict]:
    """Search OpenAlex titles, abstracts and full text."""
    params = {"search": query, "per_page": min(per_page, 100)}
    email = settings.contact_email()
    if email:
        params["mailto"] = email
    data = net.fetch_json(f"{OPENALEX_API}?{urllib.parse.urlencode(params)}", label="OpenAlex")
    return parse_openalex(data) if data else []


SEARCHERS = {
    "arxiv": search_arxiv,
    "semantic_scholar": search_semantic_scholar,
    "crossref": search_crossref,
    "openalex": search_openalex,
}


# ------------------------------------------------------------ dedupe/merge


def _norm_title(title: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", title.lower()).split())


def _merge_into(kept: Dict, dup: Dict) -> None:
    for field in ("doi", "arxiv_id", "abstract", "year", "venue", "url"):
        if not kept.get(field) and dup.get(field):
            kept[field] = dup[field]
    if len(dup.get("authors") or []) > len(kept.get("authors") or []):
        kept["authors"] = list(dup["authors"])
    kept["citation_count"] = max(kept.get("citation_count") or 0, dup.get("citation_count") or 0)
    for src in dup.get("sources") or [dup.get("source")]:
        if src and src not in kept["sources"]:
            kept["sources"].append(src)


def deduplicate_papers(all_papers: List[Dict], fuzzy_threshold: float = 0.0) -> List[Dict]:
    """Remove duplicate papers across sources and merge their metadata.

    Two records are duplicates when their DOIs match, when the first 80
    characters of their normalized titles match, or (when fuzzy_threshold > 0)
    when difflib similarity of those prefixes reaches the threshold.
    Input dicts are not mutated.
    """
    unique: List[Dict] = []
    keys: List[str] = []
    by_doi: Dict[str, int] = {}

    for paper in all_papers:
        title = paper.get("title")
        if not title or not isinstance(title, str):
            continue
        key = _norm_title(title)[:80]
        if not key:
            continue

        match = None
        doi = normalize_doi(paper.get("doi"))
        if doi and doi in by_doi:
            match = by_doi[doi]
        elif key in keys:
            match = keys.index(key)
        elif fuzzy_threshold > 0.0:
            for i, seen in enumerate(keys):
                sm = difflib.SequenceMatcher(None, key, seen)
                if (
                    sm.real_quick_ratio() >= fuzzy_threshold
                    and sm.quick_ratio() >= fuzzy_threshold
                    and sm.ratio() >= fuzzy_threshold
                ):
                    match = i
                    break

        if match is not None:
            _merge_into(unique[match], paper)
            continue

        record = dict(paper)
        record["sources"] = list(
            paper.get("sources") or ([paper["source"]] if paper.get("source") else [])
        )
        if "authors" in record:
            record["authors"] = list(record["authors"] or [])
        unique.append(record)
        keys.append(key)
        if doi:
            by_doi[doi] = len(unique) - 1

    return unique


def _bib_key(paper: Dict, taken: set) -> str:
    authors = paper.get("authors") or ["anon"]
    surname = re.sub(r"[^a-z]", "", authors[0].split()[-1].lower()) if authors[0] else "anon"
    word = next(
        (
            w
            for w in re.findall(r"[a-z]+", (paper.get("title") or "").lower())
            if w not in {"a", "an", "the", "on", "of", "for", "in", "to", "and"}
        ),
        "paper",
    )
    base = f"{surname or 'anon'}{paper.get('year') or 'nd'}{word}"
    key, n = base, 2
    while key in taken:
        key, n = f"{base}{chr(ord('a') + n - 2)}", n + 1
    taken.add(key)
    return key


def assign_ids(papers: List[Dict]) -> List[Dict]:
    """Give each paper a stable corpus id (c0001...) and a suggested BibTeX key."""
    taken = {p["key"] for p in papers if p.get("key")}
    for i, paper in enumerate(papers, 1):
        paper.setdefault("id", f"c{i:04d}")
        if not paper.get("key"):
            paper["key"] = _bib_key(paper, taken)
    return papers


def rank_papers(papers: List[Dict]) -> List[Dict]:
    """Papers returned by more sources first, then by citation count."""
    return sorted(
        papers, key=lambda p: (-len(p.get("sources") or []), -(p.get("citation_count") or 0))
    )


def search_all(
    query: str, sources: Optional[Iterable[str]] = None, limits: Optional[Dict[str, int]] = None
) -> Dict:
    """Search the selected sources in parallel and merge the results."""
    selected = [s for s in (sources or SOURCES) if s in SEARCHERS]
    limits = {**DEFAULT_LIMITS, **(limits or {})}
    _log(f"  Searching {', '.join(selected)} for: {query}")

    with ThreadPoolExecutor(max_workers=max(1, len(selected))) as pool:
        futures = {s: pool.submit(SEARCHERS[s], query, limits[s]) for s in selected}
        results = {s: f.result() for s, f in futures.items()}

    for source, papers in results.items():
        _log(f"    {source}: {len(papers)} papers")

    all_papers = [p for papers in results.values() for p in papers]
    unique = rank_papers(deduplicate_papers(all_papers, fuzzy_threshold=0.85))
    return {
        "query": query,
        "total_raw": len(all_papers),
        "total_unique": len(unique),
        "by_source": {k: len(v) for k, v in results.items()},
        "papers": unique,
    }


def merge_corpus(result_files: List[Path]) -> Dict:
    """Merge several search outputs into one deduplicated corpus with ids and keys."""
    queries, papers = [], []
    for path in result_files:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("query"):
            queries.append(data["query"])
        papers.extend(data.get("papers") or [])
    unique = assign_ids(rank_papers(deduplicate_papers(papers, fuzzy_threshold=0.85)))
    return {"queries": queries, "total_unique": len(unique), "papers": unique}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Sisyphus Academica Literature Client")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument(
        "--sources",
        default=",".join(SOURCES),
        help=f'Comma-separated subset of: {", ".join(SOURCES)}',
    )
    parser.add_argument("--limit", type=int, help="Max results per source")
    args = parser.parse_args(argv)

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    unknown = [s for s in sources if s not in SEARCHERS]
    if unknown:
        parser.error(f"unknown source(s): {', '.join(unknown)}")
    limits = {s: args.limit for s in sources} if args.limit else None
    results = search_all(args.query, sources=sources, limits=limits)

    output = json.dumps(results, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        _log(f"Results written to {args.output}")
    else:
        print(output)
    return 0 if results["total_unique"] else 1


if __name__ == "__main__":
    sys.exit(main())
