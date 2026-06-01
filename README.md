# Sisyphus Academica — The Research Paper Writing Army

**Not a writing assistant. Not a chatbot with a LaTeX plugin. A self-coordinating swarm of 20+ specialized agents that produces publication-ready research papers with genuine novelty, zero hallucinated citations, and no detectable AI-written patterns.**

[![CI](https://github.com/argahv/sisyphus-academica/actions/workflows/ci.yml/badge.svg)](https://github.com/argahv/sisyphus-academica/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)

---

## What Makes This Different

| Capability | Every Other AI Paper Tool | Sisyphus Academica |
|---|---|---|
| Literature review | Searches 10-20 papers | **500+ papers via 5 parallel scouts** |
| Citation accuracy | ~60% (40% hallucination rate) | **100% verified against 2+ sources** |
| AI-sounding text | Post-hoc cleanup | **41 Humanizer patterns as generation constraints from token 1** |
| Voice calibration | None | **Learns author's voice from writing samples** |
| Novelty generation | "What's the gap?" (same as everyone) | **6 novelty engines × counterfactual history × cross-domain mining × assumption excavation** |
| Adversarial review | None | **10 distinct reviewer personas** |
| Thinking angles | 1 perspective | **Infinite parallel perspectives including the Heretic** |

---

## Architecture

```
                     ┌──────────────────────────────┐
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
   └─────────────────────────────────────────────────────────────┘
```

---

## The Novelty Engines (The Moat)

Six engines that think like no human can:

1. **The Contrarian** — Inverts every well-established claim in the field
2. **The Cross-Pollinator** — Imports solutions from 15 completely unrelated fields
3. **The Assumption Excavator** — Finds unstated assumptions and tests what breaks if they're false
4. **The Counterfactual Generator** — Rewrites the field's history without key papers
5. **The Paradox Sifter** — Cross-references every "Limitations" section to find ignored contradictions
6. **The Heretic** — **Crown jewel.** Generates 50 wild hypotheses from title+abstract alone, then scores them against the actual paper

---

## The Adversarial Reviewers

Each paper is independently reviewed by 10 distinct personas running in parallel:

| Persona | Focus |
|---------|-------|
| **Theorist** | Formal proofs, mathematical rigor |
| **Empiricist** | Experimental design, baselines |
| **Pragmatist** | Practical applicability |
| **Skeptic** | Default position: results are wrong |
| **Historian** | Prior art, citation accuracy |
| **Methodologist** | Statistical methodology |
| **Ethicist** | Societal implications |
| **Competitor** | Novelty relative to existing work |
| **Student** | Clarity and accessibility |
| **Dreamer** | "What if you went further?" |

All 10 must pass before the paper proceeds to formatting.

---

## Live Example: SIREN Paper

The pipeline was run to produce a full paper on **Intent-Based Blockchain Execution via Agentic RAG and Swarm Consensus**. The complete output is in [`examples/siren-paper/`](examples/siren-paper/):

| File | Description |
|------|-------------|
| `siren-paper.pdf` | 13-page compiled paper (PDF) |
| `siren-paper.tex` | LaTeX source (504 lines, 26 references, 2 algorithms, 3 tables) |
| `figures/*.pdf` | 3 publication-ready figures (Byzantine robustness, latency, architecture) |
| `README.md` | Pipeline summary with review scores |

**Pipeline stats:** 100+ papers surveyed, 6 novelty engines, 10 adversarial reviewers, 4 revision rounds, 0 AI-pattern violations, 0 em dashes.

---

## Quality Gates

1. **Citation Verification**: Every citation checked against 2+ sources (Semantic Scholar + CrossRef)
2. **Statistical Audit**: Every p-value, effect size, and sample size validated
3. **AI-Pattern Detection**: 41 Humanizer patterns scanned — density must be < 2/1000 words
4. **Style Audit**: Zero em dashes allowed — pattern density < 1/2000 words — voice must match author profile
5. **Adversarial Review**: All 10 reviewer personas must recommend acceptance

---

## Quick Start

### Prerequisites

- **OpenCode** (or compatible agent platform with task()/delegate_task support)
- **Python 3.10+** (for the CLI tools)
- **LaTeX** (pdflatex + bibtex) — optional, only for PDF generation
- **API keys** (free): Semantic Scholar, CrossRef polite pool email

### Install

```bash
git clone https://github.com/argahv/sisyphus-academica.git
cd sisyphus-academica

# Install agents into OpenCode
bash install.sh

# Configure API keys
cp .env.example .env
# Edit .env with your API keys
```

### Configure Your Model Provider

All agents in `config/agent-config.json` use `9router/opencode-free` by default.  
To use a different provider/LLM, edit `config/agent-config.json` and change the `model` field:

```json
{
  "agents": {
    "research-director": {
      "model": "anthropic/claude-opus-4",    // Change this
      "variant": "think",
      "fallback_models": [
        { "model": "anthropic/claude-sonnet-4" }
      ]
    }
  }
}
```

### Write a Paper

```bash
# Option A: Via OpenCode agent tab
#   Select "research-director" → type "write a paper about [topic]"

# Option B: Manual pipeline
python3 tools/literature_client.py "transformer efficiency" --output papers/literature.json
python3 tools/citation_verifier.py --findings papers/draft.json --output papers/verified.json
```

### Voice Calibration (Recommended)

Provide 2-3 paragraphs of your published writing to `data/voice-profile/`.  
The Research Director will learn your voice and calibrate all writer agents to match.

---

## Directory Structure

```
sisyphus-academica/
├── orchestrator/          # Research Director agent (the conductor)
├── subagents/             # Core writing pipeline agents
│   ├── writer.md          # Section writer (41 Humanizer constraints)
│   ├── verifier.md        # Citation/stats/AI-pattern verification
│   ├── style-auditor.md   # Final certification gate
│   ├── literature-scout.md # Multi-source literature search
│   ├── formatter.md       # LaTeX template + PDF compilation
│   ├── gap-analyzer.md    # Research gap identification
│   ├── methodology-designer.md  # Statistical test selection
│   └── data-engineer.md   # Python code + figure generation
├── novelty-engines/       # 6 novelty generation agents
├── reviewers/             # 10 adversarial reviewer personas
├── skills/                # Academic Humanizer skill
├── tools/                 # Python CLI toolchain
│   ├── literature_client.py   # Multi-source lit search
│   └── citation_verifier.py   # Citation verification + BibTeX
├── templates/             # LaTeX venue templates (add yours)
├── config/                # Agent configuration
├── data/                  # Research memory + voice profiles
├── out/                   # Generated papers and figures
├── tests/                 # Python tool tests
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Package metadata
├── docker-compose.yml     # LaTeX compilation environment
├── LICENSE                # MIT License
└── .env.example           # Configuration template
```

---

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Lint
flake8 tools/

# LaTeX compilation (via Docker)
docker compose --profile latex run latex pdflatex out/papers/paper.tex
```

---

## Docker

```bash
# LaTeX compilation environment
docker compose --profile latex up -d

# Full dev environment
docker compose --profile dev run dev
```

---

## FAQ

**Q: Does this require a specific LLM provider?**  
No. Edit `config/agent-config.json` to use any OpenAI-compatible or Anthropic API.  
The default uses 9router, but every agent's `model` field can be changed independently.

**Q: Can I add my own template?**  
Yes. Add a new folder under `templates/` with your `.tex`, `.sty`, and `.cls` files,  
then update `subagents/formatter.md` to reference it.

**Q: How long does a paper take?**  
The full pipeline takes 30 minutes to 4 hours depending on LLM speed,  
literature volume, and number of revision rounds.

**Q: The generated text sounds too AI-like. What can I do?**  
Provide a stronger voice sample (2-3 paragraphs of your published writing)  
in `data/voice-profile/`. The 41 Humanizer patterns are enforced as  
generation-time constraints, but the voice profile anchors the style.

---

## Acknowledgments

- **[Humanizer](https://github.com/blader/humanizer)** by blader — the 30-pattern AI-detection skill this system builds on 
- **[OpenCode](https://opencode.ai/)** + **[OhMyOpenAgent](https://omo.dev/)** — the agent orchestration platform
- All six novelty engines were inspired by cognitive diversity research

---

## License

MIT — see [LICENSE](LICENSE) for details.
