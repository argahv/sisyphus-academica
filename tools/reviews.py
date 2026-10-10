#!/usr/bin/env python3
"""
Sisyphus Academica: adversarial review gate.

Reads one JSON review per persona from a reviews/ directory and passes only
when all 10 personas are present and each one accepts:
  recommendation is "accept" or "minor_revision", score >= 6 and must_fix is empty.
It also merges the must_fix items into a revision plan for the writer.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

PERSONAS = (
    "theorist",
    "empiricist",
    "pragmatist",
    "skeptic",
    "historian",
    "methodologist",
    "ethicist",
    "competitor",
    "student",
    "dreamer",
)
RECOMMENDATIONS = ("accept", "minor_revision", "major_revision", "reject")
PASSING = ("accept", "minor_revision")
MIN_SCORE = 6

_ALIASES = {
    "accept with minor revisions": "minor_revision",
    "minor revisions": "minor_revision",
    "minor revision": "minor_revision",
    "weak accept": "minor_revision",
    "major revisions": "major_revision",
    "major revision": "major_revision",
    "weak reject": "major_revision",
    "strong accept": "accept",
    "strong reject": "reject",
}


def normalize_recommendation(value: str) -> str:
    v = (value or "").strip().lower()
    v = _ALIASES.get(v, v)
    return v.replace(" ", "_").replace("-", "_")


def validate_review(review: Dict, persona: Optional[str] = None) -> List[str]:
    """Return schema problems for one review."""
    problems = []
    name = (review.get("reviewer") or "").lower()
    if name not in PERSONAS:
        problems.append(
            f"reviewer must be one of {', '.join(PERSONAS)} (got {review.get('reviewer')!r})"
        )
    elif persona and name != persona:
        problems.append(f"file is for {persona} but reviewer field says {name}")
    score = review.get("score")
    if not isinstance(score, (int, float)) or not 1 <= score <= 10:
        problems.append("score must be a number from 1 to 10")
    if normalize_recommendation(review.get("recommendation", "")) not in RECOMMENDATIONS:
        problems.append(f"recommendation must be one of {', '.join(RECOMMENDATIONS)}")
    for field in ("strengths", "weaknesses", "must_fix"):
        if not isinstance(review.get(field), list):
            problems.append(f"{field} must be a list")
    must_fix = review.get("must_fix") if isinstance(review.get("must_fix"), list) else []
    for i, item in enumerate(must_fix):
        if not isinstance(item, dict) or not item.get("issue") or not item.get("required_change"):
            problems.append(
                f'must_fix[{i}] needs "issue" and "required_change" (and ideally "location")'
            )
    return problems


def reviewer_passes(review: Dict) -> bool:
    return (
        normalize_recommendation(review.get("recommendation", "")) in PASSING
        and (review.get("score") or 0) >= MIN_SCORE
        and not review.get("must_fix")
    )


def load_reviews(reviews_dir: Path) -> Dict[str, Optional[Dict]]:
    found: Dict[str, Optional[Dict]] = {p: None for p in PERSONAS}
    for persona in PERSONAS:
        path = reviews_dir / f"{persona}.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                found[persona] = json.load(f)
    return found


def evaluate(reviews_dir: Path) -> Dict:
    reviews = load_reviews(Path(reviews_dir))
    per = {}
    plan: List[Dict] = []
    for persona, review in reviews.items():
        if review is None:
            per[persona] = {"status": "missing"}
            continue
        problems = validate_review(review, persona)
        if problems:
            per[persona] = {"status": "invalid", "problems": problems}
            continue
        ok = reviewer_passes(review)
        per[persona] = {
            "status": "accept" if ok else "not_accepted",
            "score": review["score"],
            "recommendation": normalize_recommendation(review["recommendation"]),
            "must_fix": len(review.get("must_fix") or []),
        }
        for item in review.get("must_fix") or []:
            plan.append(
                {
                    "reviewer": persona,
                    "location": item.get("location", "unspecified"),
                    "issue": item["issue"],
                    "required_change": item["required_change"],
                }
            )
    plan.sort(key=lambda x: (x["location"], x["reviewer"]))
    accepted = [p for p, v in per.items() if v["status"] == "accept"]
    scores = [v["score"] for v in per.values() if "score" in v]
    return {
        "passed": len(accepted) == len(PERSONAS),
        "accepted": f"{len(accepted)}/{len(PERSONAS)}",
        "average_score": round(sum(scores) / len(scores), 2) if scores else None,
        "reviewers": per,
        "revision_plan": plan,
    }


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Check that all 10 adversarial reviewers accept")
    parser.add_argument("reviews_dir")
    args = parser.parse_args(argv)
    result = evaluate(Path(args.reviews_dir))
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
