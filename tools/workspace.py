#!/usr/bin/env python3
"""
Sisyphus Academica: paper run workspace and stage handoff contracts.

Each paper lives in out/papers/<slug>/. Every pipeline stage writes known
files there, and check_stage() validates them before the next stage starts,
so a malformed handoff fails loudly instead of degrading the paper.
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

try:
    from . import settings
except ImportError:  # run as a script
    import settings

ENGINES = (
    "contrarian",
    "cross-pollinator",
    "assumption-excavator",
    "counterfactual-generator",
    "paradox-sifter",
    "heretic",
)
PAPER_TYPES = ("empirical", "theoretical", "position", "survey")
MAX_REVIEW_ROUNDS = 4
SECTION_TITLES = {
    "abstract": "Abstract",
    "introduction": "Introduction",
    "related_work": "Related work",
    "background": "Background",
    "methods": "Methods",
    "method": "Method",
    "results": "Results",
    "experiments": "Experiments",
    "discussion": "Discussion",
    "conclusion": "Conclusion",
    "limitations": "Limitations",
    "data_availability": "Data availability",
}

# stage id -> (phase label, description)
STAGES = [
    ("voice", "0", "Voice calibration"),
    ("literature", "1", "Literature review"),
    ("gaps", "1", "Gap analysis"),
    ("novelty", "1.5", "Novelty generation"),
    ("hypothesis", "2", "Hypothesis selection"),
    ("methodology", "3", "Methodology design"),
    ("analysis", "4", "Data engineering"),
    ("references", "4", "Verified reference list"),
    ("outline", "5", "Paper outline"),
    ("draft", "5", "Parallel writing"),
    ("verification", "6", "Verification gates"),
    ("reviews", "7", "Adversarial review"),
    ("style", "9", "Style audit"),
    ("build", "10", "Formatting and PDF"),
]
STAGE_IDS = [s[0] for s in STAGES]


def papers_dir() -> Path:
    return settings.repo_dir() / "out" / "papers"


def slugify(topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return slug[:60].rstrip("-") or "paper"


def template_path(venue: str) -> Path:
    return settings.repo_dir() / "templates" / venue / "template.tex"


def venues() -> List[str]:
    root = settings.repo_dir() / "templates"
    return (
        sorted(p.name for p in root.iterdir() if (p / "template.tex").exists())
        if root.exists()
        else []
    )


def template_tokens(text: str) -> List[str]:
    """<<token>> placeholders in a template, ignoring LaTeX comments."""
    return re.findall(r"<<([a-z_]+)>>", re.sub(r"(?<!\\)%.*", "", text))


def template_sections(venue: str) -> List[str]:
    text = template_path(venue).read_text(encoding="utf-8")
    return [s for s in template_tokens(text) if s not in ("title", "authors")]


def new_run(topic: str, venue: Optional[str] = None, base: Optional[Path] = None) -> Path:
    venue = venue or settings.default_venue()
    if venue not in venues():
        raise ValueError(f"unknown venue {venue!r}; available: {', '.join(venues())}")
    base = base or papers_dir()
    slug = slugify(topic)
    run = base / slug
    n = 2
    while run.exists():
        run = base / f"{slug}-{n}"
        n += 1
    for sub in (
        "literature",
        "novelty",
        "analysis",
        "figures",
        "draft",
        "verification",
        "reviews",
        "revisions",
        "build",
    ):
        (run / sub).mkdir(parents=True, exist_ok=True)
    manifest = {
        "topic": topic,
        "slug": run.name,
        "venue": venue,
        "created": date.today().isoformat(),
        "sections": template_sections(venue),
        "max_review_rounds": MAX_REVIEW_ROUNDS,
    }
    write_json(run / "run.json", manifest)
    profile = settings.voice_profile_path()
    if profile.exists():
        (run / "voice-profile.json").write_text(
            profile.read_text(encoding="utf-8"), encoding="utf-8"
        )
    return run


def voice_profile(run: Path) -> Optional[Dict]:
    """The run's voice profile snapshot, else the repo profile, else None."""
    return load_json(Path(run) / "voice-profile.json") or load_json(settings.voice_profile_path())


def load_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def manifest(run: Path) -> Dict:
    data = load_json(Path(run) / "run.json")
    if data is None:
        raise FileNotFoundError(
            f'{run} is not a paper run (no run.json). Create one with: sisyphus new "topic"'
        )
    return data


def paper_type(run: Path) -> str:
    return (load_json(Path(run) / "hypothesis.json") or {}).get("paper_type", "empirical")


def references(run: Path) -> List[Dict]:
    data = load_json(Path(run) / "references.json") or {}
    return data.get("references", data) if isinstance(data, dict) else data


def draft_files(run: Path) -> Dict[str, Path]:
    run = Path(run)
    return {s: run / "draft" / f"{s}.tex" for s in manifest(run)["sections"]}


def section_title(section: str) -> str:
    return SECTION_TITLES.get(section, section.replace("_", " ").capitalize())


def paper_source(run: Path) -> str:
    """Concatenate the draft sections in venue order, with headings, for the gates."""
    parts = []
    for section, path in draft_files(run).items():
        body = path.read_text(encoding="utf-8") if path.exists() else ""
        if section == "abstract":
            parts.append("\\begin{abstract}\n" + body.strip() + "\n\\end{abstract}")
        else:
            parts.append(f"\\section{{{section_title(section)}}}\n" + body.strip())
    return "\n\n".join(parts) + "\n"


def cite_keys(text: str) -> List[str]:
    keys = []
    for m in re.finditer(r"\\(?:no)?cite[tpa-z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}", text):
        keys += [k.strip() for k in m.group(1).split(",") if k.strip()]
    return list(dict.fromkeys(keys))


# ---------------------------------------------------------------- contracts


def _need(cond: bool, problems: List[str], message: str) -> None:
    if not cond:
        problems.append(message)


def check_stage(run: Path, stage: str) -> List[str]:
    """Problems with the files a stage hands to the next one (empty list = OK)."""
    run = Path(run)
    p: List[str] = []
    if stage == "voice":
        profile = voice_profile(run)
        if profile is not None:
            _need(
                "features" in profile,
                p,
                "voice profile has no features; rebuild with sisyphus voice",
            )
    elif stage == "literature":
        corpus = load_json(run / "literature" / "corpus.json")
        _need(
            corpus is not None,
            p,
            "literature/corpus.json missing: run sisyphus search ... -o literature/<name>.json, "
            "then sisyphus corpus RUN",
        )
        if corpus is not None:
            papers = corpus.get("papers") or []
            _need(
                len(papers) >= 20,
                p,
                f"corpus has {len(papers)} papers; search more queries (need 20+)",
            )
            _need(
                all(x.get("id") and x.get("title") for x in papers),
                p,
                "every corpus paper needs id and title",
            )
    elif stage == "gaps":
        gaps = (load_json(run / "gaps.json") or {}).get("gaps")
        _need(bool(gaps), p, 'gaps.json missing or has no "gaps" list')
        for i, g in enumerate(gaps or []):
            _need(
                bool(g.get("gap")) and bool(g.get("evidence")),
                p,
                f'gaps[{i}] needs "gap" and "evidence" (corpus ids)',
            )
    elif stage == "novelty":
        for engine in ENGINES:
            data = load_json(run / "novelty" / f"{engine}.json")
            _need(data is not None, p, f"novelty/{engine}.json missing")
            if data is not None:
                _need(
                    bool(data.get("hypotheses")),
                    p,
                    f'novelty/{engine}.json has no "hypotheses" list',
                )
        _need(
            (run / "novelty" / "ranked.json").exists(),
            p,
            "novelty/ranked.json missing: run sisyphus novelty RUN",
        )
    elif stage == "hypothesis":
        h = load_json(run / "hypothesis.json")
        _need(h is not None, p, "hypothesis.json missing")
        if h:
            for field in (
                "primary_claim",
                "paper_type",
                "gap",
                "proposed_approach",
                "novelty_source",
            ):
                _need(bool(h.get(field)), p, f'hypothesis.json needs "{field}"')
            _need(
                h.get("paper_type") in PAPER_TYPES,
                p,
                f"paper_type must be one of {', '.join(PAPER_TYPES)}",
            )
    elif stage == "methodology":
        m = load_json(run / "methodology.json")
        _need(m is not None, p, "methodology.json missing")
        if m:
            for field in ("design", "statistical_tests", "threats_to_validity", "reproducibility"):
                _need(field in m, p, f'methodology.json needs "{field}"')
            if paper_type(run) == "empirical":
                _need(
                    bool(m.get("statistical_tests")),
                    p,
                    "empirical paper needs at least one planned statistical test",
                )
                _need(
                    bool(m.get("sample_size_justification")),
                    p,
                    'empirical paper needs "sample_size_justification"',
                )
    elif stage == "analysis":
        if paper_type(run) == "empirical":
            stats = load_json(run / "analysis" / "statistics.json")
            _need(stats is not None, p, "analysis/statistics.json missing (empirical paper)")
            _need((run / "analysis" / "analysis.py").exists(), p, "analysis/analysis.py missing")
            if stats is not None:
                tests = stats.get("tests")
                _need(isinstance(tests, list), p, 'statistics.json needs a "tests" list')
                for i, t in enumerate(tests or []):
                    _need(
                        "statistic" in t and "p_value" in t,
                        p,
                        f'tests[{i}] needs "statistic" and "p_value"',
                    )
                _need(
                    bool(stats.get("data_source")),
                    p,
                    'statistics.json needs "data_source" (where the data came from)',
                )
    elif stage == "references":
        refs = references(run)
        _need(bool(refs), p, "references.json missing or empty: run sisyphus refs RUN <corpus ids>")
        for r in refs:
            _need(
                bool((r.get("verification") or {}).get("verified")),
                p,
                f"reference {r.get('key')} is not verified in 2+ sources",
            )
    elif stage == "outline":
        o = load_json(run / "outline.json")
        _need(o is not None, p, "outline.json missing")
        if o:
            for field in ("title", "contributions", "terminology", "sections"):
                _need(bool(o.get(field)), p, f'outline.json needs "{field}"')
            missing = [s for s in manifest(run)["sections"] if s not in (o.get("sections") or {})]
            _need(not missing, p, f"outline.json has no plan for: {', '.join(missing)}")
            keys = {r.get("key") for r in references(run)}
            for name, plan in (o.get("sections") or {}).items():
                unknown = [k for k in plan.get("cites") or [] if k not in keys]
                _need(
                    not unknown,
                    p,
                    f"outline section {name} cites unknown keys: {', '.join(unknown)}",
                )
    elif stage == "draft":
        keys = {r.get("key") for r in references(run)}
        for section, path in draft_files(run).items():
            if not path.exists() or not path.read_text(encoding="utf-8").strip():
                p.append(f"draft/{section}.tex missing or empty")
                continue
            body = path.read_text(encoding="utf-8")
            _need(
                not re.search(r"\\(?:section|chapter)\*?\{", body),
                p,
                f"draft/{section}.tex must not contain \\section (the template adds it)",
            )
            unknown = [k for k in cite_keys(body) if k not in keys]
            _need(
                not unknown,
                p,
                f"draft/{section}.tex cites keys not in references.json: {', '.join(unknown)}",
            )
            for fig in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", body):
                _need((run / fig).exists(), p, f"draft/{section}.tex includes missing figure {fig}")
    elif stage in ("verification", "reviews", "style"):
        gate_names = {
            "verification": ("citations", "statistics", "patterns"),
            "reviews": ("reviews",),
            "style": ("style",),
        }[stage]
        gates = load_json(run / "gates.json") or {}
        for g in gate_names:
            _need(
                (gates.get(g) or {}).get("passed") is True,
                p,
                f"gate {g} has not passed: run sisyphus gate {g} RUN",
            )
    elif stage == "build":
        _need(
            (run / "build" / "paper.tex").exists(),
            p,
            "build/paper.tex missing: run sisyphus build RUN",
        )
    else:
        raise ValueError(f"unknown stage {stage!r}; stages: {', '.join(STAGE_IDS)}")
    return p


def status(run: Path) -> List[Dict]:
    out = []
    for sid, phase, label in STAGES:
        problems = check_stage(run, sid)
        out.append(
            {"stage": sid, "phase": phase, "label": label, "ok": not problems, "problems": problems}
        )
    return out
