#!/usr/bin/env python3
"""
Sisyphus Academica: the five quality gates.

  1. citations   every cited reference found in 2+ APIs (citation_verifier)
  2. statistics  statistical audit has zero errors (stats_audit)
  3. patterns    AI-pattern density < 2 per 1000 words and zero em dashes
  4. style       zero em dashes, density < 1 per 2000 words, voice matches profile
  5. reviews     all 10 reviewer personas accept (reviews)

On a paper run directory each result is recorded in gates.json together with
a hash of the draft it was computed on. build_ready() refuses to format a
draft unless every gate passed on that exact draft. Reviews tolerate small
post-review edits (style fixes) up to REVIEW_DRIFT_LIMIT of changed words.
"""

import difflib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    from . import citation_verifier, patterns, reviews, stats_audit, textutil, voice, workspace
except ImportError:  # run as a script
    import citation_verifier
    import patterns
    import reviews
    import stats_audit
    import textutil
    import voice
    import workspace

GATES = ("citations", "statistics", "patterns", "style", "reviews")
VERIFICATION_GATES = ("citations", "statistics", "patterns")
PATTERN_MAX_PER_1000 = 2.0
STYLE_MAX_PER_2000 = 1.0
REVIEW_DRIFT_LIMIT = 0.05


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def draft_hash(run: Path) -> str:
    """Hash of the draft text and the bibliographic fields of its references.

    Verification results stored in references.json are left out, so rerunning
    the citation gate does not make the other gates stale.
    """
    refs = [{k: v for k, v in r.items() if k != "verification"} for r in workspace.references(run)]
    h = hashlib.sha256(workspace.paper_source(run).encode("utf-8"))
    h.update(json.dumps(refs, sort_keys=True, default=str).encode("utf-8"))
    return h.hexdigest()[:16]


# ------------------------------------------------------------- gate bodies


def check_citations(text: Optional[str], refs: List[Dict], refresh: bool = False) -> Dict:
    cache = (
        {}
        if refresh
        else {
            r["verification"]["fingerprint"]: r["verification"]
            for r in refs
            if (r.get("verification") or {}).get("fingerprint")
        }
    )
    result = citation_verifier.verify_citations({"paper": text, "references": refs}, cache=cache)
    for r in refs:
        fp = citation_verifier._fingerprint(r)
        if fp in cache:
            r["verification"] = dict(cache[fp], fingerprint=fp)
    passed = not result["blocked"] and result["total_citations"] > 0
    summary = (
        citation_verifier.summarize(result) if result["total_citations"] else "No citations found"
    )
    return {"passed": passed, "summary": summary, "details": result}


def check_statistics(src: str, analysis: Optional[Dict], require_analysis: bool = False) -> Dict:
    result = stats_audit.audit_text(src, analysis)
    if require_analysis and analysis is None and result["tests_found"]:
        result["issues"].append(
            {
                "level": "error",
                "check": "untraceable",
                "line": 1,
                "text": "",
                "message": "paper reports statistical tests but analysis/statistics.json "
                "is missing",
            }
        )
        result["errors"] += 1
        result["passed"] = False
    summary = (
        f"{result['errors']} errors, {result['warnings']} warnings "
        f"across {result['tests_found']} tests"
    )
    return {"passed": result["passed"], "summary": summary, "details": result}


def check_patterns(src: str) -> Dict:
    scan = patterns.scan(src)
    passed = scan["em_dashes"] == 0 and scan["density_per_1000"] < PATTERN_MAX_PER_1000
    summary = (
        f"{scan['violations']} pattern hits in {scan['words']} words "
        f"({scan['density_per_1000']}/1000, limit < {PATTERN_MAX_PER_1000}); "
        f"em dashes: {scan['em_dashes']}"
    )
    return {"passed": passed, "summary": summary, "details": scan}


def check_style(src: str, profile: Optional[Dict]) -> Dict:
    scan = patterns.scan(src)
    voice_result = voice.compare(textutil.latex_to_text(src), profile) if profile else None
    voice_ok = voice_result["consistent"] if voice_result else True
    passed = scan["em_dashes"] == 0 and scan["density_per_2000"] < STYLE_MAX_PER_2000 and voice_ok
    voice_note = (
        "voice: no profile (skipped)"
        if voice_result is None
        else f"voice: {'consistent' if voice_ok else 'drifted'} "
        f"({voice_result['features_within_tolerance']})"
    )
    summary = (
        f"em dashes: {scan['em_dashes']}; {scan['density_per_2000']}/2000 words "
        f"(limit < {STYLE_MAX_PER_2000}); {voice_note}"
    )
    return {
        "passed": passed,
        "summary": summary,
        "details": {"patterns": scan, "voice": voice_result},
    }


def check_reviews(reviews_dir: Path) -> Dict:
    result = reviews.evaluate(reviews_dir)
    summary = f"{result['accepted']} reviewers accept (average score {result['average_score']})"
    return {"passed": result["passed"], "summary": summary, "details": result}


# ---------------------------------------------------------------- run mode


def _record(run: Path, gate: str, result: Dict) -> Dict:
    path = run / "gates.json"
    state = workspace.load_json(path) or {}
    entry = {
        "passed": result["passed"],
        "summary": result["summary"],
        "draft_hash": draft_hash(run),
        "checked_at": _now(),
    }
    if gate == "reviews":
        history = (state.get("reviews") or {}).get("history", [])
        history.append(
            {
                "checked_at": entry["checked_at"],
                "accepted": result["details"]["accepted"],
                "passed": result["passed"],
            }
        )
        entry["history"] = history
        entry["round"] = len(history)
        if result["passed"]:
            (run / "verification").mkdir(exist_ok=True)
            (run / "verification" / "reviewed-draft.tex").write_text(
                workspace.paper_source(run), encoding="utf-8"
            )
    state[gate] = entry
    workspace.write_json(path, state)
    return entry


def run_gate(run: Path, gate: str, refresh: bool = False) -> Dict:
    """Run one gate on a paper run directory and record the result."""
    run = Path(run)
    src = workspace.paper_source(run)
    if gate == "citations":
        refs = workspace.references(run)
        result = check_citations(src, refs, refresh=refresh)
        workspace.write_json(run / "references.json", {"references": refs})
    elif gate == "statistics":
        analysis = workspace.load_json(run / "analysis" / "statistics.json")
        result = check_statistics(
            src, analysis, require_analysis=workspace.paper_type(run) == "empirical"
        )
    elif gate == "patterns":
        result = check_patterns(src)
    elif gate == "style":
        result = check_style(src, workspace.voice_profile(run))
    elif gate == "reviews":
        result = check_reviews(run / "reviews")
        rounds = len(
            ((workspace.load_json(run / "gates.json") or {}).get("reviews") or {}).get(
                "history", []
            )
        )
        if not result["passed"] and rounds + 1 >= workspace.MAX_REVIEW_ROUNDS:
            result["summary"] += (
                f"; review round {rounds + 1} of {workspace.MAX_REVIEW_ROUNDS}: stop and report "
                "the open must-fix items instead of formatting"
            )
    else:
        raise ValueError(f"unknown gate {gate!r}; gates: {', '.join(GATES)}")
    result["record"] = _record(run, gate, result)
    workspace.write_json(run / "verification" / f"{gate}.json", result)
    return result


def run_verification(run: Path, refresh: bool = False) -> Dict:
    """Phase 6: citations, statistics and AI patterns. Writes verification/report.json."""
    results = {g: run_gate(run, g, refresh=refresh) for g in VERIFICATION_GATES}
    annotations = []
    for f in results["patterns"]["details"]["findings"]:
        annotations.append(
            {
                "gate": "patterns",
                "line": f["line"],
                "issue": f"{f['pattern']}. {f['name']}",
                "text": f["text"],
                "fix": f["fix"],
            }
        )
    for i in results["statistics"]["details"]["issues"]:
        annotations.append(
            {
                "gate": "statistics",
                "line": i["line"],
                "issue": f"{i['level']}: {i['check']}",
                "text": i["text"],
                "fix": i["message"],
            }
        )
    for d in results["citations"]["details"]["details"]:
        if not d["verified"]:
            annotations.append(
                {
                    "gate": "citations",
                    "line": None,
                    "issue": d["citation_key"],
                    "text": "; ".join(d.get("issues") or []),
                    "fix": "Replace with a verified reference from the corpus or remove the claim",
                }
            )
    report = {
        "ready_for_review": all(r["passed"] for r in results.values()),
        "gates": {g: {"passed": r["passed"], "summary": r["summary"]} for g, r in results.items()},
        "annotations": annotations,
        "note": "Line numbers refer to the draft sections concatenated in run.json order.",
    }
    workspace.write_json(run / "verification" / "report.json", report)
    return report


def build_ready(run: Path) -> List[str]:
    """Reasons the run cannot be formatted. Empty list means every gate passed on this draft."""
    run = Path(run)
    state = workspace.load_json(run / "gates.json") or {}
    current = draft_hash(run)
    problems = []
    for gate in GATES:
        entry = state.get(gate)
        if not entry:
            problems.append(f"gate {gate} has not been run")
            continue
        if not entry.get("passed"):
            problems.append(f"gate {gate} failed: {entry.get('summary')}")
            continue
        if gate == "reviews":
            reviewed = run / "verification" / "reviewed-draft.tex"
            if entry.get("draft_hash") != current and reviewed.exists():
                drift = (
                    1
                    - difflib.SequenceMatcher(
                        None,
                        textutil.words(reviewed.read_text(encoding="utf-8")),
                        textutil.words(workspace.paper_source(run)),
                    ).ratio()
                )
                if drift > REVIEW_DRIFT_LIMIT:
                    problems.append(
                        f"draft changed {drift:.0%} since all 10 reviewers accepted "
                        f"(limit {REVIEW_DRIFT_LIMIT:.0%}); run another review round"
                    )
            continue
        if entry.get("draft_hash") != current:
            problems.append(
                f"gate {gate} passed on an earlier draft; re-run sisyphus gate {gate} RUN"
            )
    return problems


# --------------------------------------------------------------- file mode


def run_on_file(gate: str, target: Path, refresh: bool = False) -> Dict:
    """Run a gate on a standalone file (.tex, .md, .json, .bib) or a reviews directory."""
    target = Path(target)
    if gate == "reviews":
        return check_reviews(target)
    if gate == "citations":
        text, refs = citation_verifier.load_references(target)
        return check_citations(text, refs, refresh=True)
    src = target.read_text(encoding="utf-8")
    if gate == "statistics":
        return check_statistics(src, None)
    if gate == "patterns":
        return check_patterns(src)
    if gate == "style":
        return check_style(src, voice.load_profile())
    raise ValueError(f"unknown gate {gate!r}; gates: {', '.join(GATES)}")
