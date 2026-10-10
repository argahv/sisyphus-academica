---
layout: default
title: Tool Reference
---

# Tool Reference

## sisyphus CLI

The <code>sisyphus</code> command runs every deterministic part of the pipeline. It uses only the Python standard library. Install it with <code>pip install -e .</code>, or run <code>bin/sisyphus</code> from a checkout. API keys are optional and read from <code>.env</code>.

| Command | Description |
|---------|-------------|
| <code>sisyphus demo</code> | Run all five gates and the formatter on a bundled example paper (offline) |
| <code>sisyphus configure</code> | Write API keys to <code>.env</code> and create data directories |
| <code>sisyphus search QUERY</code> | Search arXiv, Semantic Scholar, CrossRef and OpenAlex in parallel |
| <code>sisyphus verify FILE</code> | Verify citations in a paper JSON, <code>.bib</code>, <code>.tex</code> or run directory |
| <code>sisyphus bibtex DOI</code> | BibTeX entry for a DOI (CrossRef, then doi.org) |
| <code>sisyphus new TOPIC</code> | Create a paper run in <code>out/papers/&lt;slug&gt;/</code> |
| <code>sisyphus corpus RUN</code> | Merge the run's search results into a deduplicated corpus |
| <code>sisyphus refs RUN ID...</code> | Copy corpus papers into <code>references.json</code> and verify them |
| <code>sisyphus voice</code> | Build the author voice profile from <code>data/voice-profile/*.txt</code> |
| <code>sisyphus novelty RUN</code> | Rank the six novelty engines' hypotheses |
| <code>sisyphus check RUN STAGE</code> | Validate one stage's handoff files |
| <code>sisyphus gate GATE TARGET</code> | Run a quality gate on a run or a file |
| <code>sisyphus status RUN</code> | Show every stage and gate |
| <code>sisyphus build RUN</code> | LaTeX, BibTeX and PDF; refused until every gate passes |

## Literature search

```bash
sisyphus search "transformer efficiency" -o out/papers/demo/literature/q1.json
sisyphus search "sparse attention" --sources arxiv,openalex --limit 50
```

| Source | Default results | API |
|--------|-----------------|-----|
| arXiv | 100 (max 200) | REST (Atom) |
| Semantic Scholar | 100 | Graph API; uses <code>SEMANTIC_SCHOLAR_API_KEY</code> when set |
| CrossRef | 50 | REST; uses <code>CROSSREF_EMAIL</code> for the polite pool |
| OpenAlex | 50 | REST |

Sources are queried in parallel with retries and exponential backoff. Results are normalized (full author names, year, DOI, arXiv id, abstract), deduplicated by DOI and title, and each record lists every source that returned it. A failed source returns no papers and the others continue. JSON goes to stdout or <code>-o</code>; progress goes to stderr.

## Citation verification

```bash
sisyphus verify paper.json          # {"paper": "...text...", "references": [{"key", "title", "authors", "year", "doi"}]}
sisyphus verify references.bib
sisyphus verify paper.tex           # \cite keys + thebibliography or \bibliography{...}
sisyphus verify --citation "Attention is all you need"
```

1. Extract citation keys (<code>\cite</code> variants in LaTeX; brackets, Author (Year) and (Author, Year) in plain text)
2. Look each reference up in Semantic Scholar, CrossRef, OpenAlex and arXiv (by DOI or arXiv id, then by title)
3. A source counts when the title matches (similarity of 0.90 or more, or the same identifier with a similar title) and the year and author surnames agree
4. **Verified** means 2 or more sources. One source is not enough, and a cited key with no bibliography entry fails

Exit code 0 when every citation is verified, 1 otherwise.

## Quality gates

```bash
sisyphus gate patterns draft/introduction.tex   # 41 AI-writing patterns, em dashes
sisyphus gate statistics paper.tex              # statistical audit
sisyphus gate style paper.tex                   # em dashes, density per 2000 words, voice profile
sisyphus gate reviews out/papers/demo/reviews   # all 10 reviewers accept?
sisyphus gate verify RUN                        # citations + statistics + patterns, with annotations
sisyphus gate all RUN                           # all five; results recorded in RUN/gates.json
```

| Gate | Passes when |
|------|-------------|
| citations | every cited reference is verified in 2+ sources |
| statistics | no errors: p-values match their test statistics, no "significant" with p > .05, no impossible values or estimates outside their CI, a multiple-comparison correction when 5+ tests are reported, abstract and conclusion numbers appear in the body, and (in a run) every test appears in <code>analysis/statistics.json</code> |
| patterns | under 2 pattern hits per 1000 words and zero em dashes |
| style | zero em dashes, under 1 hit per 2000 words, voice within the profile's tolerance |
| reviews | all 10 personas present, each with recommendation accept or minor_revision, score 6 or more and no must-fix items |

On a run directory, each result is stored with a hash of the draft. <code>sisyphus build</code> refuses to run if any gate failed or ran on an earlier draft. After all 10 reviewers accept, small style edits (up to 5% of words) are allowed without another review round.

Patterns 10, 11, 15, 17, 24, 29 and 35 are structural heuristics; the rest are phrase and regex rules. The style-auditor agent reads the full paper for what the detector misses.
