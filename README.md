<div align="center">

# Sisyphus Academica — The Research Paper Writing Army

**20+ specialized agents. 6 novelty engines. 10 adversarial reviewers. Zero hallucinated citations. Zero AI-isms.**

⭐ **If you write research papers, star this repo — it will save you weeks of work.**

[![CI](https://github.com/argahv/sisyphus-academica/actions/workflows/ci.yml/badge.svg)](https://github.com/argahv/sisyphus-academica/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![GitHub Stars](https://img.shields.io/github/stars/argahv/sisyphus-academica?style=social)](https://github.com/argahv/sisyphus-academica)
[![Star History](https://api.star-history.com/svg?repos=argahv/sisyphus-academica&type=Date)](https://star-history.com/#argahv/sisyphus-academica)

</div>

Not a writing assistant. Not a chatbot with a LaTeX plugin. A **self-coordinating swarm** of 20+ specialized agents that produces publication-ready research papers with **genuine novelty, zero hallucinated citations, and no detectable AI-written patterns.**

```bash
git clone https://github.com/argahv/sisyphus-academica.git && cd sisyphus-academica
bash install.sh
# Select "research-director" → "write a paper about [topic]"
```

---

## CLI Tools (No Agent Required)

The Python CLI works standalone — no OpenCode or agent platform needed:

```bash
git clone https://github.com/argahv/sisyphus-academica.git && cd sisyphus-academica
pip install -e .

sisyphus demo              # Interactive pipeline demo (no API keys)
sisyphus search QUERY      # Search 4 academic APIs in parallel
sisyphus verify FILE       # Verify citations in a paper JSON
sisyphus bibtex DOI        # Generate BibTeX from a DOI
sisyphus configure         # Set up API keys interactively
```

---

## Portable Agent Skills (Works with Any Agent)

The novelty engines and reviewer personas are packaged as **standalone agent skills** — drop them into any agent that reads SKILL.md (Claude Code, Codex, Cursor, Gemini CLI, OpenCode, and more):

```bash
git clone https://github.com/argahv/sisyphus-academica.git
# Manual: copy individual skill directories
cp -r skills/contrarian ~/.claude/skills/
# Or use npx (see below)
```

Or install any skill with a single command:

```bash
npx skills add argahv/sisyphus-academica          # Browse and select interactively
npx skills add argahv/sisyphus-academica -s '*'   # Install all 17 skills
npx skills add argahv/sisyphus-academica -s contrarian  # Install one skill
```

Then invoke directly in your agent:

```
/contrarian "The claim: 'Attention is all you need'"
/cross-pollinator "Problem: How to reduce LLM hallucination"
/heretic "Paper: 'Scaling Laws for Neural Language Models'"
```

**6 novelty engines + 10 reviewers + academic humanizer = 17 portable skills**.

> 💡 **Prefer a standalone repo?** The 6 novelty engines and 5 reviewer personas are also available as a dedicated skill pack at **[argahv/novelty-skills](https://github.com/argahv/novelty-skills)** — install via `npx skills add argahv/novelty-skills`.

---

## For Humans

**Strongly recommended: let an LLM agent install this for you.** The setup involves API key configuration, agent deployment across 25 specialized agents, voice profile calibration, and provider selection — humans fat-finger these. An LLM agent reads the full guide and walks every step correctly.

The agent will greet you with `oMoMoMoMo...` and ask **one question at a time**:
1. Which platform? (OpenCode recommended)
2. Do you have oh-my-openagent?
3. Claude subscription? (Pro / Max 20x / None)
4. OpenAI subscription? (Plus / None)
5. Semantic Scholar API key? (free — boosts rate limits)
6. LaTeX for PDF? (or Docker / skip for .tex only)
7. Writing sample for voice calibration? (optional)

Then it installs, configures, and verifies everything automatically.

Paste this prompt into Claude Code, AmpCode, Cursor, or any agent:

```
Install and configure Sisyphus Academica by following the instructions here:
https://raw.githubusercontent.com/argahv/sisyphus-academica/main/docs/guide/installation.md
```

### Manual install — one line, no agent needed

If you prefer to run the installer yourself:

```bash
git clone https://github.com/argahv/sisyphus-academica.git && cd sisyphus-academica
bash install.sh
```

The installer will ask you the same 6 questions and configure everything automatically. Run with `--yes` to skip all prompts and use defaults:

```bash
bash install.sh --yes
```

---

## The Numbers (Not Claims)

| Metric | GPT-4 / NotebookLM | Sisyphus Academica |
|---|---|---|
| Papers surveyed per run | 10-50 | **500+** (5 parallel scouts) |
| Citation hallucination rate | ~30-40% | **0%** (verified against 2+ APIs) |
| Novelty generation | None ("what's the gap?") | **6 engines × 50+ hypotheses** |
| Adversarial review | None | **10 distinct personas** |
| AI-text detection | Post-hoc (chatgpt.com paste) | **Generation-time (41 patterns)** |
| Voice calibration | None | **Learns from your writing samples** |
| Output format | Raw text / Google Doc | **LaTeX PDF with verified BibTeX** |
| Time to first draft | 5-20 min | **30 min - 4 hours** (reviewed) |

**Pipeline stats from our SIREN paper** ([view output](examples/siren-paper/)):
100+ papers surveyed → 6 novelty engines → 50+ hypotheses → 10 adversarial reviewers → 4 revision rounds → **13-page PDF, 26 verified citations, 3 publication-ready figures, 0 AI-pattern violations, 0 em dashes, 0 hallucinated references.**

---

## Quick Start

```bash
# 1. Clone + install
git clone https://github.com/argahv/sisyphus-academica.git
cd sisyphus-academica
bash install.sh

# 2. Configure API keys (free)
cp .env.example .env
# Add your Semantic Scholar API key + CrossRef email

# 3. Write a paper
# OpenCode → agent tab → select "research-director"
# → type: "write a paper about transformer efficiency"
```

**Prerequisites:** OpenCode (or compatible agent platform), Python 3.10+, LaTeX (optional, for PDF).

**Provider-agnostic** — works with any OpenAI-compatible or Anthropic API. Edit `config/agent-config.json` to switch models:

```json
{
  "agents": {
    "research-director": {
      "model": "anthropic/claude-opus-4",
      "fallback_models": [{"model": "anthropic/claude-sonnet-4"}]
    }
  }
}
```

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

1. **The Contrarian** — Inverts every well-established claim in the field. Generates 10 counter-hypotheses.
2. **The Cross-Pollinator** — Imports solutions from 15 distant fields (astrodynamics, epidemiology, music theory, immunology, 15th-century shipbuilding...).
3. **The Assumption Excavator** — Finds unstated assumptions and tests what breaks if they're false.
4. **The Counterfactual Generator** — Rewrites the field's history without the most-cited papers.
5. **The Paradox Sifter** — Cross-references every "Limitations" section to find ignored contradictions.
6. **The Heretic** — **Crown jewel.** Generates 50 wild hypotheses from title+abstract alone, scores each against the actual paper, and finds the "haunting idea" — what the paper *should have been*.

---

## The Adversarial Reviewers

Each paper is independently reviewed by 10 distinct personas running in parallel. All 10 must pass before formatting.

| Persona | Focus | Typical Critique |
|---------|-------|-----------------|
| **Theorist** | Formal proofs, mathematical rigor | "Where's the formal proof?" |
| **Empiricist** | Experimental design, baselines | "Your baseline is wrong" |
| **Pragmatist** | Practical applicability | "Does this matter in practice?" |
| **Skeptic** | Default: results are wrong | "Show me error bars" |
| **Historian** | Prior art, citation accuracy | "This was done in 1972" |
| **Methodologist** | Statistical methodology | "Your test assumes normality" |
| **Ethicist** | Societal implications | "What are the downsides?" |
| **Competitor** | Novelty relative to existing work | "Minor mod of our 2023 paper" |
| **Student** | Clarity and accessibility | "I don't understand section 3" |
| **Dreamer** | "What if you went further?" | "You stopped too early" |

---

## Quality Gates

Every paper passes through 5 hard gates. **If any gate fails, the paper goes back to revision.**

1. **Citation Verification** — Every reference checked against Semantic Scholar + CrossRef APIs. Must be found in 2+ sources. No exceptions.
2. **Statistical Audit** — Every p-value, effect size, sample size, and test selection validated. No p-hacking, no multiple comparison errors.
3. **AI-Pattern Detection** — 41 Humanizer patterns scanned. Density must be < 2 violations per 1000 words.
4. **Style Audit** — Zero em dashes. Pattern density < 1/2000 words. Voice must match the author's writing profile.
5. **Adversarial Review** — All 10 reviewer personas must recommend acceptance. Not a subset. All 10.

---

## Live Example: SIREN Paper

The pipeline was run to produce a full paper on **Intent-Based Blockchain Execution via Agentic RAG and Swarm Consensus**. Complete output in [`examples/siren-paper/`](examples/siren-paper/):

| File | Description |
|------|-------------|
| `siren-paper.pdf` | 13-page compiled paper |
| `siren-paper.tex` | LaTeX source (504 lines, 26 references) |
| `figures/*.pdf` | 3 publication-ready figures |
| `README.md` | Pipeline summary with review scores |

**Review scores progressed from Avg 4.6/10 → 8/10 across 4 revision rounds.**

---

## FAQ

**Q: Does this require a specific LLM provider?**
No. Edit `config/agent-config.json` to use any OpenAI-compatible or Anthropic API.

**Q: Can I add my own LaTeX template?**
Yes. Add a folder under `templates/` with `.tex`, `.sty`, and `.cls` files, then update `subagents/formatter.md`.

**Q: How long does a paper take?**
30 minutes to 4 hours depending on LLM speed, literature volume, and revision rounds.

**Q: The output sounds too AI-like. What do I do?**
Provide 2-3 paragraphs of your published writing in `data/voice-profile/`. The writers will match your voice at the sentence level.

**Q: Can I use this without OpenCode?**
The agents are OpenCode-compatible, but the Python CLI tools (`tools/literature_client.py`, `tools/citation_verifier.py`) work standalone.

**Q: How do I contribute?**
See [CONTRIBUTING.md](CONTRIBUTING.md). Good first issues are tagged. Template stubs need filling, the PyPI package needs publishing, and more reviewer personas are welcome.

---

## Directory Structure

```
sisyphus-academica/
├── orchestrator/          # Research Director agent (the conductor)
├── subagents/             # Core writing pipeline agents (writer, verifier, etc.)
├── novelty-engines/       # 6 novelty generation agents
├── reviewers/             # 10 adversarial reviewer personas
├── skills/                # 17 portable skill files (also available as standalone [novelty-skills](https://github.com/argahv/novelty-skills) repo)
├── tools/                 # Python CLI toolchain
│   ├── literature_client.py    # Multi-source lit search
│   └── citation_verifier.py    # Citation verification + BibTeX
├── templates/             # LaTeX venue templates (add yours)
├── config/                # Agent configuration
├── examples/siren-paper/  # Full pipeline output (13-page paper)
├── data/                  # Research memory + voice profiles
├── tests/                 # Python unit tests
├── docs/                  # GitHub Pages documentation
├── docker-compose.yml     # LaTeX + dev environments
└── pyproject.toml         # Package metadata
```

---

## Development

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
flake8 tools/ --max-line-length=100

# LaTeX via Docker
docker compose --profile latex run latex pdflatex out/papers/paper.tex
```
---

## Docker

Run the CLI without installing anything locally.

### Demo

```bash
docker run --rm ghcr.io/argahv/sisyphus-academica:latest demo
```

### Help

```bash
docker run --rm ghcr.io/argahv/sisyphus-academica:latest --help
```

### Run Pipeline

Requires an Anthropic API key:

```bash
export ANTHROPIC_API_KEY=your_key_here

docker run --rm \
  -e ANTHROPIC_API_KEY \
  -v $(pwd)/out:/app/out \
  ghcr.io/argahv/sisyphus-academica:latest \
  write "your research topic"
```

Generated files will be saved to `./out`.

---

## Acknowledgments

- **[Humanizer](https://github.com/blader/humanizer)** by blader — the 30-pattern AI-detection skill this system builds on
- **[Novelty Skills](https://github.com/argahv/novelty-skills)** — standalone thinking tools for AI agents (separate repo)
- **[OpenCode](https://opencode.ai/)** + **[OhMyOpenAgent](https://omo.dev/)** — agent orchestration platform
- All six novelty engines were inspired by cognitive diversity research

---

## License

MIT — see [LICENSE](LICENSE) for details.

⭐ **Star this repo if you write research papers — it helps others find it.**
