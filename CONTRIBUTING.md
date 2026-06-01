# Contributing to Sisyphus Academica

First off — thanks for being here. This project needs people who can write, review, test, template, and document as much as it needs people who can code.

## Table of Contents

- [First-Time Contributors](#first-time-contributors)
- [Code of Conduct](#code-of-conduct)
- [What Kind of Contributions We Need](#what-kind-of-contributions-we-need)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [How to Contribute](#how-to-contribute)
  - [Adding a Venue Template](#adding-a-venue-template)
  - [Adding a Novelty Engine](#adding-a-novelty-engine)
  - [Adding a Reviewer Persona](#adding-a-reviewer-persona)
  - [Improving Python Tools](#improving-python-tools)
  - [Improving Agent Prompts](#improving-agent-prompts)
- [Testing](#testing)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)
- [The Quality Gates](#the-quality-gates)

## First-Time Contributors

Never contributed to open source before? Start with the **[First-Contributor Guide](docs/first-contributor.md)** — it covers every step from forking the repo to getting your PR merged, with no assumed experience.

Looking for something to work on? Filter issues by [`good-first-issue`](https://github.com/argahv/sisyphus-academica/labels/good-first-issue) or [`help-wanted`](https://github.com/argahv/sisyphus-academica/labels/help-wanted).

---

## Code of Conduct

Be respectful. This project spans ML, stats, LaTeX, and agent orchestration — everyone comes from a different background. Assume good intent. No gatekeeping.

## What Kind of Contributions We Need

| Area | Examples | Skill Level |
|------|----------|-------------|
| **LaTeX templates** | Add NeurIPS/ICML/ICLR/Nature/arXiv templates | Beginner |
| **Documentation** | CONTRIBUTING.md, template guides, FAQ updates | Beginner |
| **Python tools** | Better API pagination, rate limiting, retry logic | Intermediate |
| **Agent prompts** | Sharper reviewer personas, better novelty engine instructions | Intermediate |
| **Tests** | More unit tests, mock API tests, edge cases | Beginner–Intermediate |
| **CI/CD** | Pre-commit hooks, linting, additional checks | Intermediate |
| **Docker** | Dev container, smaller images, compose fixes | Intermediate |
| **Bug fixes** | Things that break or produce wrong results | Any |

No contribution is too small. Fixing a typo, adding a test, or writing docs counts.

## Getting Started

```bash
# Clone
git clone https://github.com/argahv/sisyphus-academica.git
cd sisyphus-academica

# Install Python deps
pip install -r requirements.txt

# Run the tests
python -m pytest tests/ -v

# Install agents (optional — needed to run the paper pipeline)
bash install.sh
```

You do not need to run the full paper pipeline to contribute. Most contributions are to the Python tools, agent prompts, templates, or docs.

## Development Setup

### Minimal (for tools/tests/docs)

```bash
pip install -r requirements.txt
python -m pytest tests/ -v   # should pass
flake8 tools/ --max-line-length=100   # should pass
```

### Full (for running the pipeline)

```bash
bash install.sh --dev --latex
cp .env.example .env
# Edit .env with your API keys (Semantic Scholar, CrossRef email)
```

### Docker (for LaTeX compilation)

```bash
docker compose --profile latex up -d
docker compose run latex pdflatex out/papers/paper.tex
```

## Project Structure

```
sisyphus-academica/
├── orchestrator/          # Research Director agent (the conductor)
├── subagents/             # Core writing pipeline agents (8 agents)
├── novelty-engines/       # 6 novelty generation agents
├── reviewers/             # 10 adversarial reviewer personas
├── skills/                # Academic Humanizer skill
├── tools/                 # Python CLI toolchain
│   ├── literature_client.py    # Multi-source lit search (arXiv, S2, CrossRef, OpenAlex)
│   └── citation_verifier.py    # Citation verification + BibTeX
├── templates/             # LaTeX venue templates (stubs — need filling!)
│   ├── neurips/
│   ├── iclr/
│   ├── icml/
│   ├── nature/
│   └── arxiv/
├── config/                # Agent configuration (agent-config.json)
├── data/                  # Research memory + voice profiles
├── out/                   # Generated papers and figures
├── tests/                 # Python tool tests
├── hooks/                 # Git hooks (optional)
├── examples/              # Pipeline output examples
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Package metadata
├── docker-compose.yml     # LaTeX + dev environments
└── install.sh             # Agent installation script
```

## How to Contribute

### Adding a Venue Template

This is the most common beginner contribution. All 5 template directories are currently stubs.

1. Create a new directory under `templates/<venue>/`
2. Add the official template files (`.sty`, `.cls`, `.tex`) from the venue's website
3. Add a `README.md` explaining the template version and any quirks
4. Update `subagents/formatter.md` to reference the new template
5. Test compilation:
   ```bash
   docker compose --profile latex run latex pdflatex templates/<venue>/sample.tex
   ```

**Required files per venue:**
- `sample.tex` — minimal working example showing the template builds
- `references.bib` — sample bibliography
- Figures directory if needed

### Adding a Novelty Engine

Novelty engines are the heart of the system. Each is a single markdown file.

1. Create `novelty-engines/your-engine.md`
2. Follow the existing pattern: frontmatter + method + output format
3. The frontmatter must include:
   ```yaml
   ---
   mode: subagent
   description: "Your engine — what makes it unique"
   skills:
     - skill-academic-humanizer
   permission:
     "*": deny
     read: { "*": allow }
     write: { /root/sisyphus-academica/out/papers/*: allow }
     bash: deny
     webfetch: allow
     task: deny
     call_omo_agent: deny
   ---
   ```
4. Add the engine to the workflow in `orchestrator/research-director.md`
5. Add it to `config/agent-config.json`

### Adding a Reviewer Persona

Reviewers are single markdown files with a defined persona and evaluation criteria.

1. Create `reviewers/your-persona.md`
2. Follow the existing pattern: frontmatter + persona description + questions + rating dimensions
3. Keep it to 25-30 lines — concise, sharp, opinionated
4. Add it to the orchestrator workflow and agent-config.json

### Improving Python Tools

The two Python tools (`literature_client.py` and `citation_verifier.py`) are self-contained CLI scripts using only the stdlib.

**Common improvements:**
- Add `requests` library for cleaner HTTP calls
- Implement API pagination (each source returns multiple pages)
- Add exponential backoff retry for rate limits
- Expand citation format extraction beyond `[bracket]` syntax
- Parallelize API calls instead of sequential `time.sleep`
- Improve `deduplicate_papers` with fuzzy matching

**Guidelines:**
- Keep the CLI interface (argparse) backward-compatible
- Add tests for any new logic
- Run `flake8 tools/ --max-line-length=100` before committing

### Improving Agent Prompts

Each agent is a markdown file. The prompt quality determines output quality.

**What makes a good agent prompt:**
- Clear, specific instructions (not vague goals)
- Concrete output format examples (JSON schemas)
- Boundary conditions (what to do when APIs fail, data is missing, etc.)
- Constraints that prevent hallucinations and AI-isms

**Best practice:** Include example I/O at the bottom of the file so the agent can pattern-match.

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_literature_client.py -v

# Run with coverage (if pytest-cov installed)
python -m pytest tests/ --cov=tools
```

**Test philosophy:**
- Tests should not require network access (mock external APIs)
- Pure logic functions (dedup, bibtex generation, citation extraction) should have thorough tests
- Each bug fix should include a test that would have caught it

**Current test gaps (good first PRs):**
- No tests for API pagination logic
- No tests for rate limit handling
- No tests for `search_all()` merge logic
- No integration tests (end-to-end with mocked APIs)

## Code Style

```bash
# Python
flake8 tools/ --max-line-length=100 --ignore=E501,W291

# Markdown
# - One sentence per line in agent prompts (easier to diff)
# - No trailing whitespace
# - Use fenced code blocks with language tags
```

**Python conventions:**
- Type hints on all function signatures
- Docstrings on all public functions (Google style)
- `raise` on errors, not silent `try/except pass`
- Prefer `requests` over `urllib` for new code

## Pull Request Process

> New to pull requests? See the [First-Contributor Guide](docs/first-contributor.md) for a full walkthrough.

1. **Fork the repo** and create your branch from `main`
2. **If adding code, add tests first** (or at minimum verify existing tests pass)
3. **Run flake8** — the CI will reject anything that doesn't pass
4. **Open a draft PR early** — get feedback before investing too much
5. **Update the PR** — address review comments, keep the branch updated with `main`
6. **Merge** — a maintainer will squash-merge when everything is green

**PR title format:** `type(scope): brief description`

Examples:
- `feat(templates): add NeurIPS 2025 template`
- `fix(tools): handle rate limit 429 in literature_client`
- `docs: add CONTRIBUTING.md`
- `test(citation): add tests for Author (Year) pattern extraction`
- `refactor(tools): replace urllib with requests`

**Checklist for every PR:**
- [ ] Tests pass (`python -m pytest tests/ -v`)
- [ ] Flake8 passes (`flake8 tools/ --max-line-length=100`)
- [ ] New functions have type hints and docstrings
- [ ] Agent prompt changes preserve existing output format
- [ ] Python tools remain backward-compatible (argparse unchanged)

## The Quality Gates

The whole system is built around these five gates. Any contribution that weakens them will be rejected:

1. **Citation Verification** — every citation checked against 2+ sources
2. **Statistical Audit** — every p-value, effect size, and sample size validated
3. **AI-Pattern Detection** — 41 Humanizer patterns scanned, density < 2/1000 words
4. **Style Audit** — zero em dashes, density < 1/2000 words, voice consistent
5. **Adversarial Review** — all 10 reviewer personas must pass

If you're working on the pipeline itself, make sure your changes don't bypass or weaken these gates.

---

**Still not sure where to start?** Look for issues labeled `good-first-issue` or `help-wanted`. Or just pick a stub template directory and fill it in. Every template matters.
