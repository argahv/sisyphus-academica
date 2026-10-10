"""Sisyphus Academica: research paper pipeline CLI and quality gates."""

from pathlib import Path

__version__ = "0.3.0"

# pip maps the repo's tools/ directory to sisyphus.tools. In a plain source
# checkout (no install), let sisyphus.tools resolve to <repo>/tools as well.
_repo = Path(__file__).resolve().parents[2]
if (_repo / "tools" / "literature_client.py").exists() and str(_repo) not in __path__:
    __path__.append(str(_repo))
