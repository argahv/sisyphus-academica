#!/usr/bin/env python3
"""
Sisyphus Academica: merge and rank novelty engine output.

Each engine keeps its own JSON shape. This module reads the shared fields
(with the aliases each engine already uses), checks that cited evidence exists
in the literature corpus, and ranks every hypothesis on one scale:

  score = 0.4 * novelty + 0.35 * tractability + 0.25 * impact     (0-10)

Hypotheses whose evidence is not in the corpus are kept but marked
unsupported and ranked last, so a hallucinated "Paper A shows X" cannot
become the paper's contribution.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    from . import workspace
except ImportError:  # run as a script
    import workspace

ALIASES = {
    "hypothesis": (
        "hypothesis",
        "inverted_hypothesis",
        "imported_solution",
        "counterfactual",
        "resolution_hypothesis",
        "paradox",
        "assumption",
        "gap",
    ),
    "novelty": ("novelty", "novelty_score", "novelty_gap"),
    "tractability": (
        "tractability",
        "tractability_score",
        "transferability",
        "plausibility",
        "plausibility_of_falseness",
    ),
    "impact": (
        "impact",
        "impact_if_true",
        "potential_impact",
        "impact_if_false",
        "impact_on_current_field",
    ),
    "evidence": (
        "evidence",
        "evidence_base",
        "evidence_that_supports_inversion",
        "evidence_it_may_be_false",
    ),
    "test": ("test", "what_would_prove_it", "proposed_test", "testability"),
}
MIN_NOVELTY = 7
MIN_TRACTABILITY = 5


def _pick(item: Dict, field: str):
    for name in ALIASES[field]:
        if item.get(name) not in (None, "", []):
            return item[name]
    return None


def _num(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if 0 <= f <= 10 else None


def normalize(engine: str, data: Dict) -> List[Dict]:
    out = []
    for i, item in enumerate(data.get("hypotheses") or []):
        evidence = _pick(item, "evidence") or []
        if isinstance(evidence, str):
            evidence = [evidence]
        out.append(
            {
                "engine": engine,
                "id": item.get("id") or f"{engine}-{i + 1:03d}",
                "hypothesis": _pick(item, "hypothesis") or "",
                "novelty": _num(_pick(item, "novelty")),
                "tractability": _num(_pick(item, "tractability")),
                "impact": _num(_pick(item, "impact")),
                "evidence": evidence,
                "test": _pick(item, "test") or "",
            }
        )
    return out


def _known_ids(run: Path) -> set:
    corpus = workspace.load_json(run / "literature" / "corpus.json") or {}
    ids = set()
    for p in corpus.get("papers") or []:
        ids.update(x for x in (p.get("id"), p.get("key"), p.get("doi")) if x)
    return ids


def rank(run: Path) -> Dict:
    run = Path(run)
    known = _known_ids(run)
    problems, merged = [], []
    for engine in workspace.ENGINES:
        data = workspace.load_json(run / "novelty" / f"{engine}.json")
        if data is None:
            problems.append(f"novelty/{engine}.json missing")
            continue
        items = normalize(engine, data)
        if not items:
            problems.append(f'novelty/{engine}.json has no "hypotheses" list')
        merged += items

    for h in merged:
        missing = [f for f in ("novelty", "tractability", "impact") if h[f] is None]
        if missing or not h["hypothesis"]:
            h["problems"] = [f"missing or out-of-range {f} (1-10)" for f in missing] + (
                [] if h["hypothesis"] else ["missing hypothesis text"]
            )
        cited = [e for e in h["evidence"] if isinstance(e, str)]
        h["supported"] = bool(cited) and all(any(k in e for k in known) for e in cited)
        h["score"] = round(
            0.4 * (h["novelty"] or 0) + 0.35 * (h["tractability"] or 0) + 0.25 * (h["impact"] or 0),
            2,
        )

    merged.sort(key=lambda h: (not h["supported"], bool(h.get("problems")), -h["score"]))
    viable = [
        h
        for h in merged
        if h["supported"]
        and not h.get("problems")
        and h["novelty"] >= MIN_NOVELTY
        and h["tractability"] >= MIN_TRACTABILITY
    ]
    result = {
        "total_hypotheses": len(merged),
        "by_engine": {e: sum(1 for h in merged if h["engine"] == e) for e in workspace.ENGINES},
        "viable": len(viable),
        "no_novel_angle": not viable,
        "top": viable[:10],
        "problems": problems,
        "all": merged,
    }
    workspace.write_json(run / "novelty" / "ranked.json", result)
    return result


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Rank novelty engine hypotheses for a paper run")
    parser.add_argument("run")
    args = parser.parse_args(argv)
    result = rank(Path(args.run))
    print(json.dumps({k: v for k, v in result.items() if k != "all"}, indent=2, ensure_ascii=False))
    return 0 if not result["no_novel_angle"] and not result["problems"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
