#!/usr/bin/env python3
"""
Sisyphus Academica: formatter. Turns a gated paper run into LaTeX and PDF.

  1. refuses to run unless all five gates passed on the current draft
  2. fills templates/<venue>/template.tex (<<title>>, <<authors>>, <<section>>)
  3. writes references.bib with only the cited, verified references
  4. copies style files and figures, then compiles with latexmk, pdflatex +
     bibtex, or the texlive Docker image (--docker)
  5. fails on undefined citations or references in the LaTeX log
"""

import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

try:
    from . import citation_verifier, gates, settings, workspace
except ImportError:  # run as a script
    import citation_verifier
    import gates
    import settings
    import workspace

DOCKER_IMAGE = "texlive/texlive:latest"


class BuildError(Exception):
    pass


def _latex_escape(text: str) -> str:
    return re.sub(r"(?<!\\)([&%$#_])", r"\\\1", text)


def render_tex(run: Path, venue: str) -> str:
    template = workspace.template_path(venue)
    if not template.exists():
        raise BuildError(
            f"no template for venue {venue!r}; available: {', '.join(workspace.venues())}"
        )
    tex = template.read_text(encoding="utf-8")
    outline = workspace.load_json(run / "outline.json") or {}
    meta = workspace.manifest(run)
    title = outline.get("title") or meta["topic"]
    authors = outline.get("authors") or meta.get("authors") or ["Anonymous"]
    tex = tex.replace("<<title>>", _latex_escape(title))
    tex = tex.replace("<<authors>>", " \\and ".join(_latex_escape(a) for a in authors))
    missing = []
    for section in workspace.template_tokens(tex):
        path = run / "draft" / f"{section}.tex"
        if not path.exists():
            missing.append(section)
            continue
        tex = tex.replace(f"<<{section}>>", path.read_text(encoding="utf-8").strip())
    if missing:
        raise BuildError(f"draft sections missing for {venue}: {', '.join(missing)}")
    return tex


def write_bibliography(run: Path, tex: str) -> List[str]:
    cited = workspace.cite_keys(tex)
    refs = {r["key"]: r for r in workspace.references(run)}
    unknown = [k for k in cited if k not in refs]
    if unknown:
        raise BuildError(f"cited keys missing from references.json: {', '.join(unknown)}")
    entries = [citation_verifier.generate_bibtex(refs[k], require_id=False) for k in cited]
    (run / "build" / "references.bib").write_text("\n\n".join(entries) + "\n", encoding="utf-8")
    return cited


def _copy_assets(run: Path, venue: str) -> None:
    build = run / "build"
    for f in workspace.template_path(venue).parent.iterdir():
        if f.suffix in (".sty", ".cls", ".bst") and f.is_file():
            shutil.copy(f, build / f.name)
    figures = run / "figures"
    if figures.exists():
        shutil.copytree(figures, build / "figures", dirs_exist_ok=True)


def latex_command() -> Optional[List[List[str]]]:
    if shutil.which("latexmk"):
        return [["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"]]
    if shutil.which("pdflatex") and shutil.which("bibtex"):
        pdf = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"]
        return [pdf, ["bibtex", "paper"], pdf, pdf]
    return None


def compile_pdf(build: Path, docker: bool = False) -> Dict:
    steps = latex_command()
    if steps is None and docker:
        if not shutil.which("docker"):
            raise BuildError("--docker given but docker is not installed")
        steps = [
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{build.resolve()}:/work",
                "-w",
                "/work",
                DOCKER_IMAGE,
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "paper.tex",
            ]
        ]
    if steps is None:
        return {
            "pdf": None,
            "message": "No LaTeX found (latexmk or pdflatex + bibtex). Wrote paper.tex and "
            "references.bib; install TeX Live or rerun with --docker to get a PDF.",
        }
    for cmd in steps:
        proc = subprocess.run(cmd, cwd=build, capture_output=True, text=True)
        if proc.returncode != 0 and cmd[0] != "bibtex":
            tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-20:])
            raise BuildError(f"{' '.join(cmd[:2])} failed:\n{tail}")
    log = (
        (build / "paper.log").read_text(encoding="utf-8", errors="replace")
        if (build / "paper.log").exists()
        else ""
    )
    undefined = sorted(
        set(re.findall(r"(?:Citation|Reference) `([^']+)' on page \d+ undefined", log))
    )
    if undefined:
        raise BuildError(f"undefined citations or references in the PDF: {', '.join(undefined)}")
    pages = re.search(r"Output written on paper\.pdf \((\d+) pages?", log)
    return {
        "pdf": str(build / "paper.pdf"),
        "pages": int(pages.group(1)) if pages else None,
        "warnings": len(re.findall(r"^LaTeX Warning", log, re.M)),
    }


def build(run: Path, venue: Optional[str] = None, pdf: bool = True, docker: bool = False) -> Dict:
    run = Path(run)
    blockers = gates.build_ready(run)
    if blockers:
        raise BuildError("quality gates not satisfied:\n  - " + "\n  - ".join(blockers))
    venue = venue or workspace.manifest(run).get("venue") or settings.default_venue()
    tex = render_tex(run, venue)
    (run / "build").mkdir(exist_ok=True)
    (run / "build" / "paper.tex").write_text(tex, encoding="utf-8")
    cited = write_bibliography(run, tex)
    _copy_assets(run, venue)
    result = {
        "venue": venue,
        "tex": str(run / "build" / "paper.tex"),
        "bib": str(run / "build" / "references.bib"),
        "references": len(cited),
    }
    if pdf:
        result.update(compile_pdf(run / "build", docker=docker))
    return result
