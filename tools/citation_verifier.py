#!/usr/bin/env python3
"""
Sisyphus Academica: Citation Verifier
Verifies every reference against Semantic Scholar, CrossRef, OpenAlex and arXiv.
A reference is verified only when at least 2 independent sources return a
record whose title matches (and whose year and authors agree when known).
Flags hallucinations, misattributions and citation keys with no entry.
"""

import difflib
import json
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from . import literature_client as lit
    from . import net, settings
except ImportError:  # run as a script: python3 tools/citation_verifier.py
    import literature_client as lit
    import net
    import settings


SEMANTIC_SCHOLAR_API = lit.SEMANTIC_SCHOLAR_API
CROSSREF_API = lit.CROSSREF_API
OPENALEX_API = lit.OPENALEX_API
ARXIV_API = lit.ARXIV_API

MIN_SOURCES = 2
TITLE_THRESHOLD = 0.90
VERIFY_SOURCES = ("semantic_scholar", "crossref", "openalex", "arxiv")


# --------------------------------------------------------------- extraction


def _citation_like(key: str) -> bool:
    key = key.strip()
    return bool(
        re.fullmatch(r"\d+(?:\s*[,\-\u2013]\s*\d+)*", key)
        or re.fullmatch(r"[A-Za-z][\w:.\-+]*\d{2,4}[a-z]?", key)
    )


LATEX_CITE = re.compile(r"\\(?:no)?cite[tpa-z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}")


def extract_citations(text: str, latex_only: bool = False) -> List[Dict]:
    """Extract citations from paper text in several formats.

    Supports:
    - LaTeX: \\cite{smith2020}, \\citep{a,b}, \\citet[p. 3]{c}
    - [Bracket] notation: [Smith2020], [1], [JSM2020], [Smith2020; Jones2019]
    - Author (Year): 'Smith (2020) showed that...', 'Smith et al. (2020)'
    - (Author, Year): '(Smith, 2020)', '(Smith et al., 2020)'

    Returns list of dicts with 'key' (citation key) and 'claim' (surrounding context).
    Duplicate keys keep their first occurrence. With latex_only, only \\cite
    commands count (LaTeX sources use brackets for other things).
    """
    citations = []
    seen_keys = set()

    def add(key: str, start: int, end: int):
        key = key.strip()
        if key and key not in seen_keys:
            seen_keys.add(key)
            lo, hi = max(0, start - 40), min(len(text), end + 60)
            claim = text[lo:hi].strip()
            citations.append({"key": key, "claim": claim})

    for m in LATEX_CITE.finditer(text):
        for key in m.group(1).split(","):
            add(key, m.start(), m.end())
    if latex_only:
        return citations

    for m in re.finditer(r"(?<![\\\w])\[([^\]\n]+)\]", text):
        if re.search(r"\\[a-zA-Z]+\*?$", text[: m.start()]):
            continue  # LaTeX optional argument
        for key in re.split(r"\s*;\s*", m.group(1)):
            if _citation_like(key):
                add(key, m.start(), m.end())

    for m in re.finditer(r"([A-Z][a-z]+(?:\s+et\s+al\.?)?)\s*\((\d{4})\)", text):
        add(f"{m.group(1).strip()}{m.group(2)}", m.start(), m.end())

    for m in re.finditer(r"\(([A-Z][a-z]+(?:\s+et\s+al\.?)?),\s*(\d{4})\)", text):
        add(f"{m.group(1).strip()}{m.group(2)}", m.start(), m.end())

    return citations


# ------------------------------------------------------------- bibliography


def _read_bib_value(text: str, i: int) -> Tuple[str, int]:
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    if i < len(text) and text[i] == "{":
        depth, j = 0, i
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    return text[i:j][1:], j + 1
            j += 1
        return text[i:][1:], len(text)
    if i < len(text) and text[i] == '"':
        j = i + 1
        while j < len(text) and not (text[j] == '"' and text[j - 1] != "\\"):
            j += 1
        return text[i:j][1:], j + 1
    m = re.match(r"[^,}\s]+", text[i:])
    return (m.group(0), i + m.end()) if m else ("", i)


def _clean_bib(value: str) -> str:
    value = re.sub(r"\\[a-zA-Z]+\s*", "", value).replace("{", "").replace("}", "")
    return " ".join(value.replace("~", " ").split())


def _bib_authors(value: str) -> List[str]:
    names = []
    for part in re.split(r"\s+and\s+", _clean_bib(value)):
        if "," in part:
            last, first = [p.strip() for p in part.split(",", 1)]
            part = f"{first} {last}".strip()
        if part:
            names.append(part)
    return names


def parse_bibtex(text: str) -> List[Dict]:
    """Parse BibTeX entries into reference dicts."""
    refs = []
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        etype = m.group(1).lower()
        if etype in ("comment", "preamble", "string"):
            continue
        fields, i = {}, m.end()
        while i < len(text):
            fm = re.compile(r"\s*([A-Za-z][\w\-]*)\s*=\s*").match(text, i)
            if not fm:
                break
            value, i = _read_bib_value(text, fm.end())
            fields[fm.group(1).lower()] = value
            while i < len(text) and text[i] in " \t\r\n,":
                i += 1
            if i < len(text) and text[i] == "}":
                break
        year = re.search(r"\d{4}", fields.get("year", ""))
        refs.append(
            {
                "key": m.group(2),
                "type": etype,
                "title": _clean_bib(fields.get("title", "")),
                "authors": _bib_authors(fields.get("author", "")),
                "year": int(year.group(0)) if year else None,
                "doi": lit.normalize_doi(fields.get("doi")),
                "arxiv_id": (
                    lit.normalize_arxiv_id(fields.get("eprint"))
                    if "arxiv" in fields.get("archiveprefix", fields.get("eprinttype", "")).lower()
                    else ""
                ),
                "venue": _clean_bib(fields.get("journal") or fields.get("booktitle") or ""),
            }
        )
    return refs


def parse_thebibliography(text: str) -> List[Dict]:
    """Parse \\bibitem entries (authors, \\newblock title, \\newblock venue)."""
    env = re.search(r"\\begin\{thebibliography\}[\s\S]*?\\end\{thebibliography\}", text)
    if not env:
        return []
    refs = []
    for m in re.finditer(
        r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}([\s\S]*?)(?=\\bibitem|\\end\{thebibliography\})",
        env.group(0),
    ):
        parts = [_clean_bib(p).strip(" .") for p in re.split(r"\\newblock", m.group(2))]
        parts = [p for p in parts if p]
        if len(parts) >= 3:
            authors, title = parts[0], parts[1]
        elif parts:
            authors, title = "", parts[0]
        else:
            authors, title = "", ""
        raw = m.group(2)
        years = re.findall(r"\b(19\d{2}|20\d{2})\b", raw)
        arxiv = re.search(r"arXiv:(\d{4}\.\d{4,5})", raw)
        doi = re.search(r"\b(10\.\d{4,9}/[^\s}]+)", raw)
        refs.append(
            {
                "key": m.group(1).strip(),
                "title": title,
                "authors": [
                    a.strip()
                    for a in re.split(r",\s*(?:and\s+)?|\s+and\s+", authors)
                    if a.strip() and a.strip() != "et al."
                ],
                "year": int(years[-1]) if years else None,
                "doi": lit.normalize_doi(doi.group(1)) if doi else "",
                "arxiv_id": arxiv.group(1) if arxiv else "",
                "venue": parts[-1] if len(parts) >= 2 else "",
            }
        )
    return refs


def load_references(path: Path) -> Tuple[Optional[str], List[Dict]]:
    """Load (paper_text, references) from .json, .bib or .tex."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".bib":
        return None, parse_bibtex(text)
    if path.suffix == ".tex":
        refs = parse_thebibliography(text)
        for name in re.findall(r"\\bibliography\{([^}]+)\}", text):
            for part in name.split(","):
                bib = path.parent / (
                    part.strip() + ("" if part.strip().endswith(".bib") else ".bib")
                )
                if bib.exists():
                    refs += parse_bibtex(bib.read_text(encoding="utf-8"))
        return text, refs
    data = json.loads(text)
    if isinstance(data, list):
        return None, data
    return data.get("paper"), data.get("references") or []


# ------------------------------------------------------------------ lookups


def _s2(path: str) -> Optional[Dict]:
    return net.fetch_json(
        f"{SEMANTIC_SCHOLAR_API}/{path}",
        headers=settings.semantic_scholar_headers(),
        timeout=15,
        label="Semantic Scholar",
    )


def lookup_semantic_scholar(ref: Dict) -> List[Dict]:
    out = []
    fields = f"fields={lit.S2_FIELDS}"
    for ident in (
        f"DOI:{ref['doi']}" if ref.get("doi") else "",
        f"arXiv:{ref['arxiv_id']}" if ref.get("arxiv_id") else "",
    ):
        if ident:
            item = _s2(f"{urllib.parse.quote(ident, safe=':/')}?{fields}")
            if item and item.get("title"):
                out.append(lit.parse_semantic_scholar_item(item))
    if ref.get("title"):
        data = _s2(f"search?{urllib.parse.urlencode({'query': ref['title'], 'limit': 5})}&{fields}")
        out += lit.parse_semantic_scholar(data) if data else []
    return out


def lookup_crossref(ref: Dict) -> List[Dict]:
    out = []
    headers = lit.crossref_headers()
    if ref.get("doi"):
        data = net.fetch_json(
            f"{CROSSREF_API}/{urllib.parse.quote(ref['doi'], safe='/')}",
            headers=headers,
            timeout=15,
            label="CrossRef",
        )
        if data and data.get("message"):
            out.append(lit.parse_crossref_item(data["message"]))
    if ref.get("title"):
        params = urllib.parse.urlencode({"query.bibliographic": ref["title"], "rows": 5})
        data = net.fetch_json(
            f"{CROSSREF_API}?{params}", headers=headers, timeout=15, label="CrossRef"
        )
        out += lit.parse_crossref(data) if data else []
    return out


def lookup_openalex(ref: Dict) -> List[Dict]:
    out = []
    if ref.get("doi"):
        data = net.fetch_json(
            f"{OPENALEX_API}/https://doi.org/{ref['doi']}", timeout=15, label="OpenAlex"
        )
        if data and data.get("id"):
            out.append(lit.parse_openalex_item(data))
    if ref.get("title"):
        params = urllib.parse.urlencode({"search": ref["title"], "per_page": 5})
        data = net.fetch_json(f"{OPENALEX_API}?{params}", timeout=15, label="OpenAlex")
        out += lit.parse_openalex(data) if data else []
    return out


def lookup_arxiv(ref: Dict) -> List[Dict]:
    if ref.get("arxiv_id"):
        params = urllib.parse.urlencode({"id_list": ref["arxiv_id"]})
    elif ref.get("title"):
        title = re.sub(r"[^\w\s]", " ", ref["title"])
        params = urllib.parse.urlencode(
            {"search_query": f'ti:"{" ".join(title.split())}"', "max_results": 5}
        )
    else:
        return []
    body = net.fetch_text(f"{ARXIV_API}?{params}", timeout=15, label="arXiv")
    try:
        return lit.parse_arxiv(body) if body else []
    except Exception:
        return []


LOOKUPS = {
    "semantic_scholar": lookup_semantic_scholar,
    "crossref": lookup_crossref,
    "openalex": lookup_openalex,
    "arxiv": lookup_arxiv,
}


# ----------------------------------------------------------------- matching


def title_similarity(a: str, b: str) -> float:
    na, nb = lit._norm_title(a or ""), lit._norm_title(b or "")
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def _surnames(authors: List[str]) -> set:
    return {re.sub(r"[^a-z]", "", a.split()[-1].lower()) for a in authors or [] if a and a.split()}


def match_candidate(ref: Dict, cand: Dict) -> Tuple[bool, str]:
    """(is_match, reason). DOI equality or title similarity >= 0.90, then year and author checks."""
    same_doi = bool(ref.get("doi")) and ref["doi"] == cand.get("doi")
    same_arxiv = bool(ref.get("arxiv_id")) and ref["arxiv_id"] == cand.get("arxiv_id")
    sim = title_similarity(ref.get("title", ""), cand.get("title", ""))
    if (same_doi or same_arxiv) and ref.get("title") and sim < 0.6:
        return False, f"identifier resolves to a different title: {cand.get('title', '')[:80]!r}"
    if not (same_doi or same_arxiv) and sim < TITLE_THRESHOLD:
        return False, "title differs"
    ry, cy = ref.get("year"), cand.get("year")
    if ry and cy and abs(int(ry) - int(cy)) > 1:
        return False, f"year {ry} vs {cy}"
    rs, cs = _surnames(ref.get("authors")), _surnames(cand.get("authors"))
    if rs and cs and not rs & cs:
        return False, "no author surname in common"
    return True, "match"


def verify_reference(ref: Dict, sources=VERIFY_SOURCES) -> Dict:
    """Look a reference up in every source in parallel; verified when >= 2 sources match."""
    result = {
        "key": ref.get("key", ""),
        "title": ref.get("title", ""),
        "verified": False,
        "found_in": [],
        "matches": {},
        "issues": [],
    }
    if not ref.get("title") and not ref.get("doi") and not ref.get("arxiv_id"):
        result["issues"].append("No title, DOI or arXiv id: nothing to verify")
        return result

    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        found = dict(zip(sources, pool.map(lambda s: LOOKUPS[s](ref), sources)))

    near_misses = []
    for source, candidates in found.items():
        for cand in candidates:
            ok, reason = match_candidate(ref, cand)
            if ok:
                result["found_in"].append(source)
                result["matches"][source] = {
                    k: cand.get(k) for k in ("title", "year", "doi", "arxiv_id", "venue")
                }
                result["matches"][source]["authors"] = (cand.get("authors") or [])[:3]
                break
            if reason != "title differs":
                near_misses.append(f"{source}: {reason}")

    n = len(result["found_in"])
    result["verified"] = n >= MIN_SOURCES
    if n == 0:
        result["issues"].append("Not found in any source: may be hallucinated")
    elif n < MIN_SOURCES:
        result["issues"].append(
            f"Found only in {result['found_in'][0]}: needs {MIN_SOURCES}+ sources"
        )
    result["issues"] += near_misses
    if result["verified"]:
        dois = {m.get("doi") for m in result["matches"].values() if m.get("doi")}
        if ref.get("doi") and dois and ref["doi"] not in dois:
            result["issues"].append(
                f"DOI {ref['doi']} differs from sources: {', '.join(sorted(dois))}"
            )
    return result


def _fingerprint(ref: Dict) -> str:
    return "|".join([ref.get("key", ""), lit._norm_title(ref.get("title", "")), ref.get("doi", "")])


def verify_references(
    refs: List[Dict], cache: Optional[Dict[str, Dict]] = None, workers: int = 3
) -> List[Dict]:
    """Verify many references. Reuses verified results from `cache` (keyed by fingerprint)."""
    cache = cache if cache is not None else {}
    todo = [r for r in refs if not (cache.get(_fingerprint(r)) or {}).get("verified")]
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for ref, res in zip(todo, pool.map(verify_reference, todo)):
            cache[_fingerprint(ref)] = res
    return [cache[_fingerprint(r)] for r in refs]


def verify_citation(citation_key: str, claim: str) -> Dict:
    """Verify one citation given its title (or a claim containing the title)."""
    result = verify_reference({"key": citation_key, "title": claim})
    result["citation_key"] = citation_key
    result["claim"] = claim[:200]
    return result


def verify_citations(findings: Dict, cache: Optional[Dict[str, Dict]] = None) -> Dict:
    """Verify a paper: {'paper': text, 'references': [...]}.

    With paper text, every cited key must have a reference entry and every
    cited reference must be verified. Without paper text, every reference is
    checked. Uncited references are reported but do not block.
    """
    refs = findings.get("references") or []
    by_key = {r.get("key"): r for r in refs if r.get("key")}
    text = findings.get("paper")
    is_latex = bool(text and re.search(r"\\(?:begin|section|cite[tpa-z]*)\b", text))
    cited = (
        [c["key"] for c in extract_citations(text, latex_only=is_latex)]
        if text
        else [r.get("key", "") for r in refs]
    )

    to_check = [by_key[k] for k in cited if k in by_key]
    if not text:
        to_check = refs
    checked = {
        r.get("key", ""): res for r, res in zip(to_check, verify_references(to_check, cache))
    }

    details = []
    for key in cited:
        if key in checked:
            details.append(dict(checked[key], citation_key=key))
        else:
            details.append(
                {
                    "citation_key": key,
                    "key": key,
                    "verified": False,
                    "found_in": [],
                    "issues": ["No bibliography entry for this citation key"],
                }
            )

    unverified = [d for d in details if not d["verified"]]
    return {
        "total_citations": len(details),
        "verified": len(details) - len(unverified),
        "hallucinated_count": len(unverified),
        "issues_count": sum(len(d.get("issues", [])) for d in details),
        "hallucinated_citations": [d["citation_key"] for d in unverified],
        "missing_references": [k for k in cited if k not in by_key],
        "uncited_references": [k for k in by_key if text and k not in cited],
        "blocked": len(unverified) > 0,
        "details": details,
    }


# ------------------------------------------------------------------- BibTeX

BIB_TYPES = ("article", "inproceedings", "misc", "book", "incollection", "techreport", "phdthesis")


def _bib_escape(value) -> str:
    value = re.sub(r"<[^>]+>", "", str(value))
    return re.sub(r"(?<!\\)([&%$#_])", r"\\\1", value)


def _bib_name(name: str) -> str:
    parts = name.split()
    if len(parts) < 2 or "," in name:
        return name
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def bib_key(paper: Dict) -> str:
    if paper.get("key"):
        return paper["key"]
    authors = paper.get("authors") or []
    surname = (
        re.sub(r"[^a-z]", "", authors[0].split()[-1].lower())
        if authors and authors[0].split()
        else "anon"
    )
    word = next(
        (
            w
            for w in re.findall(r"[a-z]+", (paper.get("title") or "").lower())
            if w not in {"a", "an", "the", "on", "of", "for", "in", "to", "and"}
        ),
        "",
    )
    return f"{surname}{paper.get('year') or 'nd'}{word}"


def generate_bibtex(paper: Dict, require_id: bool = True) -> str:
    """Generate a BibTeX entry from verified paper metadata.

    Returns '' when require_id is set and the paper has no DOI or arXiv id.
    """
    doi = lit.normalize_doi(paper.get("doi"))
    arxiv_id = lit.normalize_arxiv_id(paper.get("arxiv_id"))
    if require_id and not (doi or arxiv_id):
        return ""
    venue = paper.get("venue") or paper.get("journal") or ""
    etype = (
        paper.get("type")
        if paper.get("type") in BIB_TYPES
        else ("article" if venue and venue != "arXiv" else "misc")
    )
    fields = []
    if paper.get("authors"):
        fields.append(("author", " and ".join(_bib_name(a) for a in paper["authors"])))
    fields.append(("title", "{" + (paper.get("title") or "Untitled") + "}"))
    if venue and venue != "arXiv":
        fields.append(
            (
                {"inproceedings": "booktitle", "incollection": "booktitle"}.get(etype, "journal"),
                venue,
            )
        )
    for name in ("volume", "number", "pages"):
        if paper.get(name):
            fields.append(
                (name, str(paper[name]).replace("-", "--") if name == "pages" else paper[name])
            )
    fields.append(("year", paper.get("year") or "n.d."))
    if doi:
        fields.append(("doi", doi))
    if arxiv_id:
        fields += [("eprint", arxiv_id), ("archivePrefix", "arXiv")]
    body = ",\n".join(
        f"  {k} = {{{_bib_escape(v) if k not in ('doi', 'eprint') else v}}}" for k, v in fields
    )
    return f"@{etype}{{{bib_key(paper)},\n{body}\n}}"


def fetch_doi_metadata(doi: str) -> Optional[Dict]:
    """Bibliographic metadata for a DOI from CrossRef, or None."""
    doi = lit.normalize_doi(doi)
    data = net.fetch_json(
        f"{CROSSREF_API}/{urllib.parse.quote(doi, safe='/')}",
        headers=lit.crossref_headers(),
        timeout=15,
        label="CrossRef",
    )
    if not data or not data.get("message"):
        return None
    paper = lit.parse_crossref_item(data["message"])
    issue = data["message"].get("issue")
    if issue:
        paper["number"] = issue
    return paper


def bibtex_from_doi(doi: str) -> Optional[str]:
    """BibTeX for a DOI: CrossRef metadata first, then doi.org content negotiation."""
    paper = fetch_doi_metadata(doi)
    if paper and paper.get("title"):
        return generate_bibtex(paper)
    text = net.fetch_text(
        f"https://doi.org/{lit.normalize_doi(doi)}",
        headers={"Accept": "application/x-bibtex"},
        timeout=15,
        label="doi.org",
    )
    return text.strip() if text and text.lstrip().startswith("@") else None


def summarize(result: Dict) -> str:
    if result["blocked"]:
        lines = [
            f"BLOCKED: {result['hallucinated_count']} of {result['total_citations']} citations "
            f"not verified "
            f"in {MIN_SOURCES}+ sources"
        ]
        lines += [
            f"  - {d['citation_key']}: {'; '.join(d.get('issues') or [])}"
            for d in result["details"]
            if not d["verified"]
        ]
        return "\n".join(lines)
    n, total = result["verified"], result["total_citations"]
    return f"All {n}/{total} citations verified in {MIN_SOURCES}+ sources"


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Sisyphus Academica Citation Verifier")
    parser.add_argument(
        "--findings", "-f", help='Paper JSON ({"paper", "references"}), .bib or .tex file'
    )
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument(
        "--citation", "-c", help="Verify a single paper title (overrides --findings)"
    )
    args = parser.parse_args(argv)

    if args.citation:
        result = verify_citation("manual", args.citation)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["verified"] else 1
    if not args.findings:
        parser.error("--findings or --citation is required")

    text, refs = load_references(Path(args.findings))
    result = verify_citations({"paper": text, "references": refs})
    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        print(f"Verification results written to {args.output}", file=sys.stderr)
    else:
        print(output)
    print(summarize(result), file=sys.stderr)
    return 1 if result["blocked"] else 0


if __name__ == "__main__":
    sys.exit(main())
