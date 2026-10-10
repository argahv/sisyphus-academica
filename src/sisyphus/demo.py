#!/usr/bin/env python3
"""Sisyphus Academica: offline demo of the quality gates. No API keys or network.

Copies the bundled example run (a small Student vs Welch t-test simulation) to a
temporary directory, shows the AI-pattern detector on a deliberately bad
paragraph, runs all five gates on the example paper, and formats it.
"""

import shutil
import tempfile
import textwrap
from collections import Counter
from pathlib import Path

from sisyphus.tools import build, gates, patterns

DEMO_RUN = Path(__file__).resolve().parent / "demo_run"

BAD_PARAGRAPH = (
    "In this paper, we delve into the pivotal role of attention. Moreover, our groundbreaking "
    "framework achieves state-of-the-art results, showcasing its robust design — a testament "
    "to the power of data-driven methods. Further research is needed."
)


def _line(passed: bool, name: str, summary: str) -> str:
    return f"  {'PASS' if passed else 'FAIL'}  {name:<11} {summary}"


def run_demo() -> int:
    print("Sisyphus Academica demo (offline)")
    print()
    print("1. AI-pattern detector on a deliberately bad paragraph:")
    print(textwrap.indent(textwrap.fill(BAD_PARAGRAPH, 88), "     > "))
    scan = patterns.scan(BAD_PARAGRAPH)
    for (pid, name), n in sorted(
        Counter((f["pattern"], f["name"]) for f in scan["findings"]).items()
    ):
        print(f"     {n} x pattern {pid:>2}: {name}")
    print(
        f"     {scan['violations']} hits in {scan['words']} words; "
        "the gate allows fewer than 2 per 1000."
    )
    print()

    tmp = Path(tempfile.mkdtemp(prefix="sisyphus-demo-"))
    run = tmp / "demo-welch-vs-student"
    shutil.copytree(DEMO_RUN, run)
    print("2. Five quality gates on the example paper")
    print("   (Student's vs Welch's t-test under unequal variances, 850 words, simulated data):")
    ok = True
    for gate in gates.GATES:
        result = gates.run_gate(run, gate)
        ok &= result["passed"]
        print(_line(result["passed"], gate, result["summary"]))
    print("   Citation results come from the cached verification in references.json;")
    print(f"   check them live with: sisyphus gate citations {run} --refresh")
    print()

    print("3. Formatter (refuses to run unless every gate passed on this exact draft):")
    try:
        result = build.build(run)
        print(f"     LaTeX: {result['tex']}")
        print(f"     BibTeX: {result['bib']} ({result['references']} verified references)")
        print(f"     PDF: {result.get('pdf') or result.get('message')}")
    except build.BuildError as e:
        ok = False
        print(f"     build refused: {e}")
    print()
    print("Next steps:")
    print("  sisyphus configure                 API keys (optional, raise rate limits)")
    print('  sisyphus new "your topic"          start a paper run')
    print('  OpenCode -> research-director -> "write a paper about [topic]"')
    print(f"Demo files: {run}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run_demo())
