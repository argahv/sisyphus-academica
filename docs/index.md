---
layout: default
title: Home
---

<div class="hero">
  <h1>Open-source research pipeline</h1>
  <p class="subhead">Literature review, novelty generation, citation verification, and adversarial review. A self-coordinating pipeline of 20+ specialized agents for researchers.</p>
  <div class="button-group">
    <a href="https://github.com/argahv/sisyphus-academica" class="btn-primary btn-large">View on GitHub</a>
    <a href="https://github.com/argahv/novelty-skills" class="btn-secondary btn-large">Novelty Skills</a>
  </div>
</div>

## Quick Start

<div class="install-tabs">
  <div class="tab-content">

<p class="demo-label"><strong>Python CLI tools:</strong></p>
<div class="demo-block">
  <div class="cmd"><span class="prompt">$</span> <span class="input">git clone https://github.com/argahv/sisyphus-academica.git</span></div>
  <div class="cmd"><span class="prompt">$</span> <span class="input">cd sisyphus-academica && pip install -e .</span></div>
  <div class="cmd"><span class="prompt">$</span> <span class="input">sisyphus demo</span></div>
  <div class="output">Running pipeline on example topic: 'Transformer Efficiency' ...</div>
</div>

<p class="demo-label"><strong>Install skills via npx (any agent):</strong></p>
<div class="demo-block">
  <div class="cmd"><span class="prompt">$</span> <span class="input">npx skills add argahv/sisyphus-academica -s contrarian</span></div>
  <div class="cmd"><span class="prompt">$</span> <span class="input">npx skills add argahv/novelty-skills -s heretic</span></div>
  <div class="output">Installed to Claude Code, Cursor, Copilot, Hermes Agent, OpenCode</div>
</div>

<p class="demo-label"><strong>Full pipeline (requires OpenCode):</strong></p>
<div class="demo-block">
  <div class="cmd"><span class="prompt">$</span> <span class="input">git clone https://github.com/argahv/sisyphus-academica.git && cd sisyphus-academica</span></div>
  <div class="cmd"><span class="prompt">$</span> <span class="input">bash install.sh</span></div>
  <div class="output">25 agents deployed → select "research-director" → "write a paper about [topic]"</div>
</div>

  </div>
</div>

---

## What Makes This Different

<div class="comparison-wrap">
<table>
  <thead>
    <tr><th>Capability</th><th>Other AI Paper Tools</th><th>Sisyphus Academica</th></tr>
  </thead>
  <tbody>
    <tr><td>Literature review</td><td>10-20 papers</td><td><strong>500+ papers via 5 parallel scouts</strong></td></tr>
    <tr><td>Citation accuracy</td><td>~60% (40% hallucination)</td><td><strong>100% verified against 2+ sources</strong> <a href="https://github.com/argahv/sisyphus-academica/blob/main/examples/siren-paper/siren-paper.pdf" class="proof-link">[view proof]</a></td></tr>
    <tr><td>AI-sounding text</td><td>Post-hoc cleanup</td><td><strong>41 Humanizer patterns as generation constraints</strong></td></tr>
    <tr><td>Voice calibration</td><td>None</td><td><strong>Learns author's voice from writing samples</strong></td></tr>
    <tr><td>Novelty generation</td><td>"What's the gap?"</td><td><strong>6 novelty engines × 50+ hypotheses</strong></td></tr>
    <tr><td>Adversarial review</td><td>None</td><td><strong>10 distinct reviewer personas</strong></td></tr>
  </tbody>
</table>
</div>

<div class="proof-bar">
  <span class="proof-badge">SIREN paper</span>
  <span>13-page PDF · 20 cited references · 2 figures · <a href="https://github.com/argahv/sisyphus-academica/blob/main/examples/siren-paper/README.md">what the current gates flag</a> · <a href="https://github.com/argahv/sisyphus-academica/blob/main/examples/siren-paper/siren-paper.pdf">download PDF</a></span>
</div>

---

## What You Get

### 17 Portable Agent Skills

Install any skill in one command — works with Claude Code, Codex, Cursor, Gemini CLI, OpenCode:

```bash
npx skills add argahv/sisyphus-academica     # Browse all 17 interactively
npx skills add argahv/novelty-skills           # Standalone thinking tools pack
```

Invoke directly in your agent:

```
/contrarian "The claim: 'Attention is all you need'"
/heretic "Paper: 'Scaling Laws for Neural Language Models'"
```

### 6 Novelty Engines

<div class="engine-grid">
  <div class="engine-card">
    <div class="engine-icon">C</div>
    <h3>Contrarian</h3>
    <p class="tagline">Invert every well-established claim</p>
    <p>Generates 10 counter-hypotheses by inverting claims across 6 axes: polarity, direction, scope, relevance, existence, priority.</p>
  </div>
  <div class="engine-card">
    <div class="engine-icon">X</div>
    <h3>Cross-Pollinator</h3>
    <p class="tagline">Solutions from 15 distant fields</p>
    <p>Maps concepts from astrodynamics onto biology, from monetary policy onto ML. Extract the mechanism, not the metaphor.</p>
  </div>
  <div class="engine-card">
    <div class="engine-icon">A</div>
    <h3>Assumption Excavator</h3>
    <p class="tagline">Find what everyone assumed</p>
    <p>Surfaces resource, behavioral, environmental, temporal, and causal assumptions. Tests what breaks if each is false.</p>
  </div>
  <div class="engine-card">
    <div class="engine-icon">G</div>
    <h3>Counterfactual Generator</h3>
    <p class="tagline">The field without its key papers</p>
    <p>Removes the most-cited papers from history. Traces ripple effects. Finds suppressed alternatives that deserve a second look.</p>
  </div>
  <div class="engine-card">
    <div class="engine-icon">P</div>
    <h3>Paradox Sifter</h3>
    <p class="tagline">Contradictions everyone ignores</p>
    <p>Cross-references Limitations sections across papers. Finds direct contradictions, mutual ignorance, hidden dependencies, and escalations.</p>
  </div>
  <div class="engine-card">
    <div class="engine-icon">H</div>
    <h3>Heretic</h3>
    <p class="tagline">50 wild hypotheses from any abstract</p>
    <p>The crown jewel. Generates 50 hypotheses from title+abstract alone, scores against the actual paper, finds the haunting idea.</p>
  </div>
</div>

---

## The Quality Gates

<div class="gate-list">
  <div class="gate-item">
    <span class="gate-icon">✓</span>
    <div><strong>Citation Verification</strong> — Every reference checked against Semantic Scholar + CrossRef. Must be found in 2+ sources. No exceptions.</div>
  </div>
  <div class="gate-item">
    <span class="gate-icon">✓</span>
    <div><strong>Statistical Audit</strong> — Every p-value, effect size, sample size, and test selection validated. No p-hacking, no multiple comparison errors.</div>
  </div>
  <div class="gate-item">
    <span class="gate-icon">✓</span>
    <div><strong>AI-Pattern Detection</strong> — 41 Humanizer patterns scanned (30 base + 11 academic). Density must be &lt; 2 violations per 1000 words.</div>
  </div>
  <div class="gate-item">
    <span class="gate-icon">✓</span>
    <div><strong>Style Audit</strong> — Zero em dashes. Voice must match the author's writing profile.</div>
  </div>
  <div class="gate-item">
    <span class="gate-icon">✓</span>
    <div><strong>Adversarial Review</strong> — All 10 reviewer personas must recommend acceptance. Not a subset. All 10.</div>
  </div>
</div>

---

## Pipeline Overview

<div class="arch-wrapper">
<div class="arch-diagram">                     ┌──────────────────────────────┐
                     │  Research Director            │
                     │  (orchestrator)               │
                     └────────┬─────────────────────┘
                              │
         ┌────────────────────┼─────────────────────────┐
         ▼                    ▼                          ▼
   ┌───────────┐    ┌────────────────┐    ┌──────────────────────┐
   │ Literature│    │ 6 Novelty      │    │ Gap Analyzer         │
   │ Scout ×5  │    │ Engines        │    │ + Methodology        │
   └───────────┘    └────────────────┘    └──────────────────────┘
                              │
         ┌────────────────────┼─────────────────────────┐
         ▼                    ▼                          ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  Parallel Writing Swarm (5 agents + 41 Humanizer patterns)   │
   └──────────────────────────┬──────────────────────────────────┘
                              │
   ┌─────────────────────────────────────────────────────────────┐
   │  Verifier: Citations × Statistics × AI-Pattern Detection    │
   └──────────────────────────┬──────────────────────────────────┘
                              │
   ┌─────────────────────────────────────────────────────────────┐
   │  Adversarial Review: 10 reviewer personas (parallel)        │
   └──────────────────────────┬──────────────────────────────────┘
                              │
   ┌─────────────────────────────────────────────────────────────┐
   │  Style Auditor: Humanizer certification, em dash zero check │
   └──────────────────────────┬──────────────────────────────────┘
                              │
   ┌─────────────────────────────────────────────────────────────┐
   │  Formatter: LaTeX template, BibTeX, figures, PDF            │
   └──────────────┬───────────────────────────┬──────────────────┘
                  │                           │
                  ▼                           ▼
            ┌──────────┐              ┌──────────────┐
            │  Paper   │              │   Citation   │
            │  PDF     │              │   Report     │
            └──────────┘              └──────────────┘</div>
</div>

---

## Project Structure

```
sisyphus-academica/
├── orchestrator/          # Research Director agent
├── subagents/             # Writing pipeline agents (writer, verifier, etc.)
├── novelty-engines/       # 6 novelty generation agents
├── reviewers/             # 10 adversarial reviewer personas
├── skills/                # 17 portable skill files (SKILL.md format)
├── tools/                 # Python CLI toolchain
├── templates/             # LaTeX venue templates
├── config/                # Agent configuration
├── examples/siren-paper/  # Full pipeline output (13-page paper)
├── tests/                 # Python unit tests
└── docs/                  # This documentation site
```

<div class="button-group">
  <a href="{{ '/guide/installation' | relative_url }}" class="btn-primary">Installation Guide</a>
  <a href="{{ '/architecture' | relative_url }}" class="btn-secondary">Architecture</a>
  <a href="{{ '/novelty-engines' | relative_url }}" class="btn-secondary">Novelty Engines</a>
</div>
