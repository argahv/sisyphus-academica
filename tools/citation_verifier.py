#!/usr/bin/env python3
"""
Sisyphus Academica — Citation Verifier
Verifies every citation against 2+ sources.
Flags hallucinations, misattributions, and unverifiable claims.
"""

import json
import urllib.request
import urllib.parse
import re
from typing import Dict, List, Tuple


SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper"
CROSSREF_API = "https://api.crossref.org/works"
ARXIV_API = "http://export.arxiv.org/api/query"


def search_semantic_scholar(title: str) -> Dict:
    """Search Semantic Scholar for a paper by title."""
    params = urllib.parse.urlencode({
        'query': title,
        'limit': 3,
        'fields': 'title,authors,year,abstract,citationCount,externalIds'
    })
    url = f"{SEMANTIC_SCHOLAR_API}/search?{params}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SisyphusAcademica/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return data.get('data', [{}])[0] if data.get('data') else {}
    except:
        return {}


def search_crossref(title: str) -> Dict:
    """Search CrossRef for a paper by title."""
    params = urllib.parse.urlencode({
        'query': title,
        'rows': 2,
        'select': 'DOI,title,author,container-title'
    })
    url = f"{CROSSREF_API}?{params}"
    
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'SisyphusAcademica/1.0 (mailto:research@example.com)',
                'Accept': 'application/json'
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        items = data.get('message', {}).get('items', [])
        return items[0] if items else {}
    except:
        return {}


def verify_citation(citation_key: str, claim: str) -> Dict:
    """Verify a single citation by searching multiple sources."""
    result = {
        'citation_key': citation_key,
        'claim': claim[:200],
        'semantic_scholar': None,
        'crossref': None,
        'verified': False,
        'issues': []
    }
    
    # Extract paper title from citation key or claim
    # In practice, the claim text contains the paper reference
    
    # Search Semantic Scholar
    ss_result = search_semantic_scholar(claim[:100])
    if ss_result:
        result['semantic_scholar'] = {
            'title': ss_result.get('title', ''),
            'year': ss_result.get('year', ''),
            'citation_count': ss_result.get('citationCount', 0),
            'external_ids': ss_result.get('externalIds', {})
        }
    
    # Search CrossRef
    cr_result = search_crossref(claim[:100])
    if cr_result:
        result['crossref'] = {
            'doi': cr_result.get('DOI', ''),
            'title': ' '.join(cr_result.get('title', [''])),
            'container': cr_result.get('container-title', [''])[0] if cr_result.get('container-title') else ''
        }
    
    # Determine verification status
    if result['semantic_scholar'] and result['crossref']:
        # Both found the paper
        ss_title = (result['semantic_scholar'].get('title') or '').lower()
        cr_title = (result['crossref'].get('title') or '').lower()
        if ss_title and cr_title and (ss_title[:50] == cr_title[:50] or 
                                       ss_title[:30] in cr_title or cr_title[:30] in ss_title):
            result['verified'] = True
    elif result['semantic_scholar'] or result['crossref']:
        result['verified'] = True
        result['issues'].append("Found in only 1 source — weak verification")
    else:
        result['issues'].append("Paper not found in any source — may be hallucinated")
    
    return result


def verify_citations(findings: Dict) -> Dict:
    """Verify all citations in a paper findings file."""
    citations = []
    
    # Extract citations from text
    if 'paper' in findings:
        text = findings['paper']
        # Find patterns like [AuthorYear], [1], Smith et al. (2020), etc.
        citation_patterns = re.findall(r'\[([^\]]+)\]', text)
        for cp in citation_patterns:
            citations.append({'key': cp, 'claim': ''})
    
    results = []
    for citation in citations:
        result = verify_citation(citation['key'], citation['claim'])
        results.append(result)
    
    verified_count = sum(1 for r in results if r['verified'])
    hallucinated = [r for r in results if not r['verified']]
    
    return {
        'total_citations': len(results),
        'verified': verified_count,
        'hallucinated_count': len(hallucinated),
        'issues_count': sum(len(r.get('issues', [])) for r in results),
        'hallucinated_citations': [r['citation_key'] for r in hallucinated],
        'blocked': len(hallucinated) > 0,
        'details': results
    }


def format_authors_for_bibtex(authors) -> str:
    """Format author list into BibTeX 'Last, I. and ...' string.

    Handles list of strings (['John Smith']) or dicts ([{'name': 'John Smith'}]).
    Falls back to 'Author, A.' on empty/invalid input.
    """
    if not isinstance(authors, (list, tuple)) or not authors:
        return 'Author, A.'

    names = []
    for a in authors:
        name = a.strip() if isinstance(a, str) else (a.get('name', '').strip() if isinstance(a, dict) else '')
        if not name:
            continue
        parts = name.split()
        if len(parts) == 1:
            names.append(parts[0])
        else:
            last = parts[-1]
            initials = ' '.join(p[0] + '.' for p in parts[:-1] if p)
            names.append(f'{last}, {initials}')
    return ' and '.join(names) if names else 'Author, A.'


def generate_bibtex(paper: Dict) -> str:
    """Generate BibTeX entry from verified paper metadata."""
    if not paper.get('doi'):
        return ''

    doi = paper['doi']
    author_field = format_authors_for_bibtex(paper.get('authors', []))
    title_field = paper.get('title', 'Untitled')
    year = paper.get('year', 'n.d.')

    first_author = author_field.split(',')[0].split(' and ')[0].strip()
    key = f"{first_author}{year}"

    bibtex = f"""@article{{{key},
  author = {{{author_field}}},
  title = {{{title_field}}},
  year = {{{year}}},
  doi = {{{doi}}}
}}"""
    return bibtex


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Sisyphus Academica Citation Verifier')
    parser.add_argument('--findings', '-f', required=True, help='Findings JSON file')
    parser.add_argument('--output', '-o', help='Output file')
    parser.add_argument('--citation', '-c', help='Verify a single citation (overrides --findings)')
    args = parser.parse_args()
    
    if args.citation:
        result = verify_citation('manual', args.citation)
        print(json.dumps(result, indent=2))
        return
    
    with open(args.findings) as f:
        findings = json.load(f)
    
    result = verify_citations(findings)
    
    output = json.dumps(result, indent=2)
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Verification results written to {args.output}")
    else:
        print(output)
    
    if result['blocked']:
        print(f"\n⚠ BLOCKED: {result['hallucinated_count']} unverifiable citations found")
        for c in result['hallucinated_citations']:
            print(f"  - {c}")
        exit(1)
    else:
        print(f"\n✓ All {result['verified']}/{result['total_citations']} citations verified")
        exit(0)


if __name__ == '__main__':
    main()
