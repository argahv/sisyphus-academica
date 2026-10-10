#!/usr/bin/env python3
"""sisyphus: command line for the Sisyphus Academica research pipeline."""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from sisyphus.tools import settings

PIPELINE_HELP = """\
pipeline (run in this order; RUN is the directory printed by `sisyphus new`):
  new TOPIC              create out/papers/<slug>/ for a paper
  voice                  build data/voice-profile.json from your writing samples
  search QUERY -o FILE   search arXiv, Semantic Scholar, CrossRef, OpenAlex in parallel
  corpus RUN             merge RUN/literature/*.json into a deduplicated corpus
  novelty RUN            rank the six novelty engines' hypotheses
  refs RUN ID...         add corpus papers to references.json and verify them
  check RUN STAGE        validate a stage's handoff files
  gate GATE RUN          run a quality gate (citations, statistics, patterns, style,
                         reviews, verify = first three, all = all five)
  status RUN             show every stage and gate
  build RUN              LaTeX + BibTeX + PDF (only after all five gates pass)
"""


def _print_json(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_demo(args) -> int:
    from sisyphus.demo import run_demo

    return run_demo()


def cmd_configure(args) -> int:
    from sisyphus.configure import run_configure

    return run_configure(args.semantic_scholar_key, args.crossref_email)


def cmd_search(args) -> int:
    from sisyphus.tools import literature_client

    argv = [" ".join(args.query), "--sources", args.sources]
    if args.output:
        argv += ["--output", args.output]
    if args.limit:
        argv += ["--limit", str(args.limit)]
    return literature_client.main(argv)


def cmd_verify(args) -> int:
    from sisyphus.tools import citation_verifier, gates

    if args.citation:
        result = citation_verifier.verify_citation("manual", " ".join(args.citation))
        _print_json(result)
        return 0 if result["verified"] else 1
    if not args.target:
        print("Usage: sisyphus verify FILE|RUN (or --citation TITLE)", file=sys.stderr)
        return 1
    target = Path(args.target)
    if (target / "run.json").exists():
        result = gates.run_gate(target, "citations", refresh=args.refresh)
        print(result["summary"])
        return 0 if result["passed"] else 1
    text, refs = citation_verifier.load_references(target)
    result = citation_verifier.verify_citations({"paper": text, "references": refs})
    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    print(citation_verifier.summarize(result), file=sys.stderr)
    return 1 if result["blocked"] else 0


def cmd_bibtex(args) -> int:
    from sisyphus.tools import citation_verifier

    bib = citation_verifier.bibtex_from_doi(args.doi)
    if not bib:
        print(f"Could not resolve DOI {args.doi} via CrossRef or doi.org", file=sys.stderr)
        return 1
    print(bib)
    return 0


def cmd_new(args) -> int:
    from sisyphus.tools import workspace

    try:
        run = workspace.new_run(" ".join(args.topic), args.venue)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    print(run)
    return 0


def cmd_corpus(args) -> int:
    from sisyphus.tools import literature_client, workspace

    run = Path(args.run)
    files = sorted(p for p in (run / "literature").glob("*.json") if p.name != "corpus.json")
    if not files:
        print(
            f"No search results in {run}/literature/. Run: "
            f"sisyphus search QUERY -o {run}/literature/q1.json",
            file=sys.stderr,
        )
        return 1
    corpus = literature_client.merge_corpus(files)
    workspace.write_json(run / "literature" / "corpus.json", corpus)
    print(
        f"{corpus['total_unique']} unique papers from {len(files)} searches "
        f"-> {run}/literature/corpus.json"
    )
    return 0


def cmd_refs(args) -> int:
    from sisyphus.tools import citation_verifier, workspace

    run = Path(args.run)
    corpus = workspace.load_json(run / "literature" / "corpus.json") or {}
    index = {}
    for p in corpus.get("papers") or []:
        for ident in (p.get("id"), p.get("key"), p.get("doi")):
            if ident:
                index[ident] = p
    refs = {r["key"]: r for r in workspace.references(run)}
    for key in args.remove or []:
        refs.pop(key, None)
    unknown = []
    for ident in args.ids:
        paper = index.get(ident) or index.get(ident.lower())
        if paper is None:
            unknown.append(ident)
            continue
        ref = {
            k: paper.get(k)
            for k in (
                "key",
                "title",
                "authors",
                "year",
                "doi",
                "arxiv_id",
                "venue",
                "type",
                "volume",
                "pages",
                "abstract",
            )
            if paper.get(k)
        }
        ref["corpus_id"] = paper.get("id")
        refs.setdefault(ref["key"], ref)
    ref_list = list(refs.values())
    if not args.no_verify:
        todo = [r for r in ref_list if not (r.get("verification") or {}).get("verified")]
        for r, res in zip(todo, citation_verifier.verify_references(todo)):
            r["verification"] = dict(res, fingerprint=citation_verifier._fingerprint(r))
    workspace.write_json(run / "references.json", {"references": ref_list})
    bad = [r["key"] for r in ref_list if not (r.get("verification") or {}).get("verified")]
    print(f"{len(ref_list)} references, {len(ref_list) - len(bad)} verified in 2+ sources")
    for key in bad:
        issues = "; ".join((refs[key].get("verification") or {}).get("issues") or ["not checked"])
        print(f"  ! {key}: {issues}")
    for ident in unknown:
        print(f"  ! {ident}: not in corpus (search for it first)")
    return 1 if bad or unknown else 0


def cmd_voice(args) -> int:
    from sisyphus.tools import voice

    argv = list(args.samples)
    if args.check:
        argv += ["--check", args.check]
    return voice.main(argv)


def cmd_novelty(args) -> int:
    from sisyphus.tools import novelty

    return novelty.main([args.run])


def cmd_check(args) -> int:
    from sisyphus.tools import workspace

    problems = workspace.check_stage(Path(args.run), args.stage)
    for p in problems:
        print(f"  ! {p}")
    if not problems:
        print(f"  {args.stage}: OK")
    return 1 if problems else 0


def cmd_gate(args) -> int:
    from sisyphus.tools import gates

    target = Path(args.target)
    is_run = (target / "run.json").exists()
    if args.gate in ("verify", "all") and not is_run:
        print(f"gate {args.gate} needs a paper run directory", file=sys.stderr)
        return 1
    if is_run:
        if args.gate == "verify":
            report = gates.run_verification(target, refresh=args.refresh)
            for name, g in report["gates"].items():
                print(f"  {'PASS' if g['passed'] else 'FAIL'} {name}: {g['summary']}")
            print(f"  annotations: {target}/verification/report.json")
            return 0 if report["ready_for_review"] else 1
        names = gates.GATES if args.gate == "all" else [args.gate]
        ok = True
        for name in names:
            result = gates.run_gate(target, name, refresh=args.refresh)
            ok &= result["passed"]
            print(f"  {'PASS' if result['passed'] else 'FAIL'} {name}: {result['summary']}")
        return 0 if ok else 1
    result = gates.run_on_file(args.gate, target, refresh=args.refresh)
    _print_json(result)
    print(
        f"{'PASS' if result['passed'] else 'FAIL'} {args.gate}: {result['summary']}",
        file=sys.stderr,
    )
    return 0 if result["passed"] else 1


def cmd_status(args) -> int:
    from sisyphus.tools import gates, workspace

    run = Path(args.run)
    meta = workspace.manifest(run)
    print(f"{meta['topic']} ({meta['venue']}) at {run}")
    for s in workspace.status(run):
        mark = "ok " if s["ok"] else "..."
        print(f"  [{mark}] phase {s['phase']:>4}  {s['label']}")
        for p in s["problems"][:3]:
            print(f"           {p}")
    blockers = gates.build_ready(run) if (run / "gates.json").exists() else ["no gates run yet"]
    print("  build: " + ("ready" if not blockers else "blocked (" + blockers[0] + ")"))
    return 0


def cmd_build(args) -> int:
    from sisyphus.tools import build

    try:
        result = build.build(
            Path(args.run), venue=args.venue, pdf=not args.no_pdf, docker=args.docker
        )
    except build.BuildError as e:
        print(f"Build refused: {e}", file=sys.stderr)
        return 1
    _print_json(result)
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sisyphus",
        description="Sisyphus Academica research pipeline tools.",
        epilog=PIPELINE_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("demo", help="run the gates on a bundled example paper (offline, no API keys)")

    s = sub.add_parser("configure", help="set API keys in .env and create data directories")
    s.add_argument("--semantic-scholar-key")
    s.add_argument("--crossref-email")

    s = sub.add_parser("search", help="search 4 academic APIs in parallel")
    s.add_argument("query", nargs="+")
    s.add_argument("--output", "-o")
    s.add_argument("--sources", default="arxiv,semantic_scholar,crossref,openalex")
    s.add_argument("--limit", type=int)

    s = sub.add_parser(
        "verify", help="verify citations in a paper JSON, .bib, .tex or run directory"
    )
    s.add_argument("target", nargs="?")
    s.add_argument("--citation", nargs="+", help="verify one paper title")
    s.add_argument("--output", "-o")
    s.add_argument("--refresh", action="store_true", help="ignore cached verification results")

    s = sub.add_parser("bibtex", help="BibTeX entry for a DOI")
    s.add_argument("doi")

    s = sub.add_parser("new", help="create a paper run directory")
    s.add_argument("topic", nargs="+")
    s.add_argument("--venue", help="template under templates/ (default: DEFAULT_VENUE or arxiv)")

    s = sub.add_parser("corpus", help="merge search results into literature/corpus.json")
    s.add_argument("run")

    s = sub.add_parser("refs", help="add corpus papers to references.json and verify them")
    s.add_argument("run")
    s.add_argument("ids", nargs="*", help="corpus ids (c0001), keys or DOIs")
    s.add_argument("--remove", nargs="+", metavar="KEY")
    s.add_argument("--no-verify", action="store_true")

    s = sub.add_parser("voice", help="build or check the author voice profile")
    s.add_argument("samples", nargs="*")
    s.add_argument("--check", metavar="FILE")

    s = sub.add_parser("novelty", help="rank novelty engine hypotheses")
    s.add_argument("run")

    s = sub.add_parser("check", help="validate a stage's handoff files")
    s.add_argument("run")
    s.add_argument("stage")

    s = sub.add_parser("gate", help="run a quality gate on a run directory or a file")
    s.add_argument(
        "gate", choices=["citations", "statistics", "patterns", "style", "reviews", "verify", "all"]
    )
    s.add_argument("target")
    s.add_argument("--refresh", action="store_true")

    s = sub.add_parser("status", help="show pipeline progress for a run")
    s.add_argument("run")

    s = sub.add_parser("build", help="format the paper: LaTeX, BibTeX, PDF")
    s.add_argument("run")
    s.add_argument("--venue")
    s.add_argument("--no-pdf", action="store_true")
    s.add_argument("--docker", action="store_true", help="compile with the texlive Docker image")
    return p


COMMANDS = {
    "demo": cmd_demo,
    "configure": cmd_configure,
    "search": cmd_search,
    "verify": cmd_verify,
    "bibtex": cmd_bibtex,
    "new": cmd_new,
    "corpus": cmd_corpus,
    "refs": cmd_refs,
    "voice": cmd_voice,
    "novelty": cmd_novelty,
    "check": cmd_check,
    "gate": cmd_gate,
    "status": cmd_status,
    "build": cmd_build,
}


def main(argv: Optional[List[str]] = None) -> int:
    settings.ensure_env()
    p = parser()
    args = p.parse_args(sys.argv[1:] if argv is None else argv)
    if not args.command:
        p.print_help()
        return 0
    try:
        return COMMANDS[args.command](args)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1


def entrypoint() -> None:
    sys.exit(main())


if __name__ == "__main__":
    entrypoint()
