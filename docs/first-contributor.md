# Your First Contribution to Sisyphus Academica

Welcome! This guide walks you through making your first contribution — from forking the repo to getting your PR merged. No prior open-source experience needed.

---

## Prerequisites

- A [GitHub account](https://github.com/join)
- Git installed locally (`git --version` should print something)
- Python 3.10+ (`python --version` or `python3 --version`)

---

## Step 1: Fork the Repository

A fork is your personal copy of the project on GitHub. You make changes there, then propose them back via a pull request.

1. Go to [github.com/argahv/sisyphus-academica](https://github.com/argahv/sisyphus-academica)
2. Click the **Fork** button (top-right corner)
3. GitHub creates `https://github.com/YOUR_USERNAME/sisyphus-academica`

---

## Step 2: Clone Your Fork

Download your fork to your local machine.

```bash
git clone https://github.com/YOUR_USERNAME/sisyphus-academica.git
cd sisyphus-academica
```

Then add the original repo as `upstream` so you can stay in sync with future changes:

```bash
git remote add upstream https://github.com/argahv/sisyphus-academica.git
```

Verify both remotes exist:

```bash
git remote -v
# origin    https://github.com/YOUR_USERNAME/sisyphus-academica.git (fetch)
# upstream  https://github.com/argahv/sisyphus-academica.git (fetch)
```

---

## Step 3: Set Up Your Environment

Install the Python dependencies so tests and linting work:

```bash
pip install -e ".[dev]"
```

Verify everything is working:

```bash
python -m pytest tests/ -v      # all tests should pass
flake8 tools/ --max-line-length=100 --ignore=E501,W291   # should produce no output
```

---

## Step 4: Create a Branch

Never work directly on `main`. Create a descriptive branch for your change:

```bash
git checkout -b docs/improve-faq
```

Branch naming conventions used in this project:

| Type | Example |
|------|---------|
| Feature | `feat/add-neurips-template` |
| Bug fix | `fix/citation-regex-edge-case` |
| Docs | `docs/first-contributor-guide` |
| Tests | `test/search-all-merge-logic` |

---

## Step 5: Make Your Changes

Pick something from the issues labeled [`good-first-issue`](https://github.com/argahv/sisyphus-academica/labels/good-first-issue) or [`help-wanted`](https://github.com/argahv/sisyphus-academica/labels/help-wanted).

**Good starting points with no code required:**

- Fill in a stub LaTeX template under `templates/` (neurips, iclr, icml, nature, arxiv)
- Improve or expand a doc file under `docs/`
- Fix a typo or clarify wording in an agent prompt under `subagents/` or `reviewers/`

**If your change touches Python tools:**

- Add or update tests in `tests/`
- Run `flake8` after every edit — the CI will reject lint failures

---

## Step 6: Commit Your Changes

Stage and commit with a clear message:

```bash
git add docs/first-contributor.md        # stage specific files, not "git add ."
git commit -m "docs: add first-contributor onboarding guide"
```

Commit message format: `type(scope): brief description`

Examples:
- `docs: clarify FAQ entry on API keys`
- `fix(tools): handle empty title in deduplicate_papers`
- `feat(templates): add NeurIPS 2025 sample.tex`

---

## Step 7: Sync with Upstream (Optional but Recommended)

If the project moved forward while you were working, pull in those changes before pushing:

```bash
git fetch upstream
git rebase upstream/main
```

Resolve any conflicts, then continue:

```bash
git rebase --continue
```

---

## Step 8: Push Your Branch

```bash
git push origin docs/improve-faq
```

---

## Step 9: Open a Pull Request

1. Go to `https://github.com/YOUR_USERNAME/sisyphus-academica`
2. GitHub shows a **"Compare & pull request"** banner — click it
3. Set the base branch to `main` on `argahv/sisyphus-academica`
4. Fill in the PR title and description:
   - **Title:** follows the `type(scope): description` format
   - **Description:** what you changed, why, and how to test it
5. Click **"Create pull request"**

**Open a draft PR early** if you want feedback before the work is complete — maintainers are happy to review in-progress work.

---

## PR Checklist

Before marking your PR as ready for review:

- [ ] `python -m pytest tests/ -v` passes
- [ ] `flake8 tools/ --max-line-length=100 --ignore=E501,W291` produces no output
- [ ] New Python functions have type hints and docstrings
- [ ] Agent prompt changes preserve the existing JSON output format
- [ ] Python tool changes keep the `argparse` CLI interface backward-compatible

---

## What Happens Next

A maintainer will review your PR, leave comments, and either request changes or approve. Respond to comments, push new commits, and the branch will be squash-merged once everything is green.

---

## Still Stuck?

- Browse the existing [pull requests](https://github.com/argahv/sisyphus-academica/pulls?q=is%3Amerged) to see what accepted contributions look like
- Open a [blank issue](https://github.com/argahv/sisyphus-academica/issues/new) and ask — no question is too small
- Read [CONTRIBUTING.md](../CONTRIBUTING.md) for deeper detail on each contribution type
