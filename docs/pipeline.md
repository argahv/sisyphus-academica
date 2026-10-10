---
layout: default
title: Pipeline Phases
---

# Pipeline Phases

The paper pipeline runs 10 sequential phases. Verification and review phases can loop back for revision. The entire cycle takes 30 minutes to 4 hours depending on model speed and revision depth.

## Agent Action Timeline

<div class="timeline">
  <span class="timeline-pill pill-read">Literature Scout</span>
  <span class="timeline-pill pill-thinking">Novelty Engines</span>
  <span class="timeline-pill pill-grep">Methodology</span>
  <span class="timeline-pill pill-edit">Data Engineer</span>
  <span class="timeline-pill pill-edit">Writer</span>
  <span class="timeline-pill pill-grep">Verifier</span>
  <span class="timeline-pill pill-thinking">Reviewers</span>
  <span class="timeline-pill pill-done">Formatter</span>
</div>

## Handoffs

Each paper lives in <code>out/papers/&lt;slug&gt;/</code> (created by <code>sisyphus new</code>). Every stage writes known files there, and <code>sisyphus check RUN STAGE</code> validates them before the next stage starts.

| Phase | Writes | Checked by |
|-------|--------|------------|
| 0 | <code>data/voice-profile.json</code> | <code>sisyphus voice</code> |
| 1 | <code>literature/*.json</code>, <code>literature/corpus.json</code>, <code>gaps.json</code> | <code>check literature</code>, <code>check gaps</code> |
| 1.5 | <code>novelty/&lt;engine&gt;.json</code>, <code>novelty/ranked.json</code> | <code>sisyphus novelty</code> (flags evidence not in the corpus) |
| 2-4 | <code>hypothesis.json</code>, <code>methodology.json</code>, <code>analysis/statistics.json</code>, <code>references.json</code> | <code>check hypothesis</code> ... <code>check references</code> (every reference verified in 2+ APIs) |
| 5 | <code>outline.json</code>, <code>draft/&lt;section&gt;.tex</code> | <code>check outline</code>, <code>check draft</code> (only verified cite keys) |
| 6, 9 | <code>verification/*.json</code> | <code>sisyphus gate verify</code>, <code>sisyphus gate style</code> |
| 7 | <code>reviews/&lt;persona&gt;.json</code> | <code>sisyphus gate reviews</code> |
| 10 | <code>build/paper.tex</code>, <code>references.bib</code>, <code>paper.pdf</code> | <code>sisyphus build</code> (refuses unless all gates passed on this draft) |

## Phase 0: Voice Calibration

**Input:** 2-3 paragraphs of the author's published writing
**Output:** Voice style profile (sentence length, vocabulary, paragraph patterns, punctuation)

The profile is loaded by every Writer agent. Writers match the author's voice at the sentence level, not just the topic level.

## Phase 1: Literature Review

5 parallel scouts hit different sources:

| Scout | Source | Max Results |
|-------|--------|-------------|
| 1 | arXiv REST API | 100 |
| 2 | Semantic Scholar | 100 |
| 3 | CrossRef | 50 |
| 4 | OpenAlex | 50 |
| 5 | Field-specific (NCBI, etc.) | varies |

Results are deduplicated by title similarity. The orchestrator builds a master literature graph from all discovered papers.

## Phase 1.5: Novelty Generation

All 6 novelty engines run in parallel, generating 50+ hypotheses scored by novelty &times; tractability. Top 3 become the paper's contribution.

| Engine | Angle | Output |
|--------|-------|--------|
| Contrarian | Invert field claims | 10 counter-hypotheses |
| Cross-Pollinator | Import from distant fields | Top 5 analogies |
| Assumption Excavator | Find unstated assumptions | 5 testable assumptions |
| Counterfactual Generator | Rewrite field history | 5 counterfactual histories |
| Paradox Sifter | Cross-reference limitations | Paradoxes + elephants |
| Heretic | 50 wild guesses from title alone | 50 hypotheses + haunting idea |

## Phase 2: Hypothesis Selection

Top hypotheses are presented to the user (if connected) or selected automatically. Each includes: primary claim, evidence base, gap filled, proposed approach.

## Phase 3: Methodology Design

Recommends correct statistical tests, performs power analysis, designs experimental protocol, flags confounds. Outputs a reproducible analysis plan.

## Phase 4: Data Engineering

Writes Python analysis code, generates publication-ready figures (SciencePlots, 300 DPI, colorblind-safe), computes all statistics with correct reporting.

## Phase 5: Parallel Writing

5 Writer subagents write simultaneously:

| Writer | Section |
|--------|---------|
| Writer 1 | Abstract |
| Writer 2 | Introduction |
| Writer 3 | Methods |
| Writer 4 | Results |
| Writer 5 | Related Work + Discussion |

All 41 Humanizer patterns are hard constraints during generation, not post-hoc fixes.

## Phase 6: Verification

3 parallel verification modules:

1. **Citation Verifier** — Every citation checked against Semantic Scholar + CrossRef. Must be found in 2+ sources.
2. **Statistical Auditor** — Validates p-values, effect sizes, sample sizes, test selection. Flags p-hacking and multiple comparison errors.
3. **AI-Pattern Detector** — Scans for all 41 Humanizer patterns. Density must be &lt; 2/1000 words.

All 3 must pass. If any fails, the section goes back to the Writer with annotations.

## Phase 7: Adversarial Review

10 reviewer personas (Theorist, Empiricist, Pragmatist, Skeptic, Historian, Methodologist, Ethicist, Competitor, Student, Dreamer) review independently. All 10 must recommend acceptance.

## Phase 8: Revision

Writers receive annotated critiques and revise. The loop continues until all 10 reviewers accept or the orchestrator determines a critique has been adequately addressed.

## Phase 9: Style Audit

Complete paper scanned for all 41 patterns:
- Pattern density &lt; 1 per 2000 words
- Em dash count: **ZERO**
- Voice must match author profile

**PASS** &rarr; Proceed to formatting. **FAIL** &rarr; Back to Writer with line-level annotations.

## Phase 10: Formatting &rarr; Submission

Formatter loads venue-specific LaTeX template, generates BibTeX from verified citations, embeds figures, compiles PDF. Outputs: <code>paper.tex</code>, <code>references.bib</code>, <code>paper.pdf</code>.

Supported venue templates: NeurIPS, ICML, ICLR, Nature/Springer, arXiv.

<div class="button-group">
  <a href="{{ '/architecture' | relative_url }}" class="btn-secondary">Architecture</a>
  <a href="{{ '/novelty-engines' | relative_url }}" class="btn-secondary">Novelty Engines</a>
</div>
