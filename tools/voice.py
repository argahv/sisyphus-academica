#!/usr/bin/env python3
"""
Sisyphus Academica: voice calibration.

build_profile() measures an author's writing samples (data/voice-profile/*.txt
or *.md, or VOICE_SAMPLE_PATH) and writes data/voice-profile.json. The profile
holds numeric features plus plain-language guidance for the writer agents.
compare() checks a draft against the profile and lists the features that
drift outside tolerance. These are stylometric measures: they catch drift in
rhythm and register, not word choice.
"""

import json
import re
import statistics
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

try:
    from . import settings, textutil
except ImportError:  # run as a script
    import settings
    import textutil

MIN_SAMPLE_WORDS = 150
PASSIVE = re.compile(r"\b(?:is|are|was|were|be|been|being)\s+(?:\w+ly\s+)?\w+(?:ed|en)\b", re.I)
HEDGE = re.compile(
    r"\b(?:may|might|could|possibly|perhaps|likely|suggests?|appears?|seems?)\b", re.I
)

# feature: (relative tolerance, absolute tolerance, label, unit)
TOLERANCES = {
    "sentence_length_mean": (0.30, 3.0, "average sentence length", "words"),
    "sentence_length_sd": (0.50, 3.0, "sentence length variation (sd)", "words"),
    "word_length_mean": (0.10, 0.3, "average word length", "letters"),
    "long_word_ratio": (0.30, 0.05, "share of words with 7+ letters", ""),
    "commas_per_sentence": (0.50, 0.5, "commas per sentence", ""),
    "semicolons_per_1000": (1.00, 2.0, "semicolons per 1000 words", ""),
    "parentheses_per_1000": (1.00, 4.0, "parentheticals per 1000 words", ""),
    "first_person_plural_per_1000": (0.60, 6.0, "'we/our/us' per 1000 words", ""),
    "passive_per_sentence": (0.60, 0.10, "passive constructions per sentence", ""),
    "hedges_per_1000": (0.80, 4.0, "hedges per 1000 words", ""),
}
CORE = ("sentence_length_mean", "word_length_mean")


def features(text: str) -> Dict[str, float]:
    sents = [s for _, s in textutil.sentences(text)]
    words = textutil.words(text)
    n_words = max(len(words), 1)
    n_sents = max(len(sents), 1)
    lengths = [len(textutil.words(s)) for s in sents] or [0]
    per_k = 1000.0 / n_words
    return {
        "sentence_length_mean": round(statistics.mean(lengths), 2),
        "sentence_length_sd": round(statistics.pstdev(lengths), 2),
        "word_length_mean": round(sum(len(w) for w in words) / n_words, 2),
        "long_word_ratio": round(sum(1 for w in words if len(w) >= 7) / n_words, 3),
        "commas_per_sentence": round(text.count(",") / n_sents, 2),
        "semicolons_per_1000": round(text.count(";") * per_k, 2),
        "parentheses_per_1000": round(text.count("(") * per_k, 2),
        "first_person_plural_per_1000": round(
            sum(1 for w in words if w.lower() in ("we", "our", "us", "ours")) * per_k, 2
        ),
        "passive_per_sentence": round(sum(len(PASSIVE.findall(s)) for s in sents) / n_sents, 3),
        "hedges_per_1000": round(len(HEDGE.findall(text)) * per_k, 2),
    }


def _guidance(f: Dict[str, float]) -> List[str]:
    lo = max(5, round(f["sentence_length_mean"] - f["sentence_length_sd"]))
    hi = round(f["sentence_length_mean"] + f["sentence_length_sd"])
    lines = [
        f"Sentences average {f['sentence_length_mean']:.0f} words; most fall between {lo} and "
        f"{hi}. Vary length the same way.",
        f"Average word length is {f['word_length_mean']:.1f} letters; "
        f"{f['long_word_ratio'] * 100:.0f}% of words have 7+ letters.",
        f"About {f['commas_per_sentence']:.1f} commas per sentence.",
        "Semicolons are "
        + ("common" if f["semicolons_per_1000"] >= 3 else "rare")
        + f" ({f['semicolons_per_1000']:.1f} per 1000 words).",
        "Parentheticals are "
        + ("common" if f["parentheses_per_1000"] >= 8 else "occasional")
        + f" ({f['parentheses_per_1000']:.1f} per 1000 words).",
        f"First person plural ('we', 'our') appears {f['first_person_plural_per_1000']:.1f} "
        "times per 1000 words.",
        "Passive voice is "
        + ("frequent" if f["passive_per_sentence"] >= 0.4 else "limited")
        + f" ({f['passive_per_sentence']:.2f} per sentence).",
        f"Hedges ('may', 'suggests') appear {f['hedges_per_1000']:.1f} times per 1000 words.",
    ]
    return lines


def sample_files(path: Optional[Path] = None) -> List[Path]:
    path = path or settings.voice_sample_path()
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(
            p
            for p in path.iterdir()
            if p.suffix in (".txt", ".md", ".tex") and p.name != "README.md"
        )
    return []


def build_profile(files: List[Path]) -> Dict:
    texts = []
    for p in files:
        raw = p.read_text(encoding="utf-8")
        texts.append(textutil.latex_to_text(raw) if p.suffix in (".tex", ".md") else raw)
    text = "\n\n".join(texts)
    n_words = textutil.word_count(text)
    if n_words < MIN_SAMPLE_WORDS:
        raise ValueError(
            f"voice samples contain {n_words} words; provide at least {MIN_SAMPLE_WORDS} "
            "(2-3 paragraphs of published writing)"
        )
    f = features(text)
    return {
        "created": date.today().isoformat(),
        "source_files": [str(p) for p in files],
        "sample_words": n_words,
        "features": f,
        "guidance": _guidance(f),
    }


def compare(text: str, profile: Dict) -> Dict:
    """Check prose against a profile. consistent=True when both core features and
    at least 80% of all features fall inside tolerance."""
    target = profile["features"]
    got = features(text)
    deviations = []
    inside = 0
    for name, (rel, abs_tol, label, unit) in TOLERANCES.items():
        want, have = target.get(name), got.get(name)
        if want is None or have is None:
            continue
        tol = max(abs(want) * rel, abs_tol)
        if abs(have - want) <= tol:
            inside += 1
            continue
        direction = "higher" if have > want else "lower"
        deviations.append(
            {
                "feature": name,
                "profile": want,
                "draft": have,
                "message": " ".join(
                    f"{label} is {have} {unit} vs {want} in the profile ({direction})".split()
                ),
            }
        )
    total = inside + len(deviations)
    core_ok = all(d["feature"] not in CORE for d in deviations)
    share = inside / total if total else 1.0
    return {
        "consistent": core_ok and share >= 0.8,
        "features_within_tolerance": f"{inside}/{total}",
        "deviations": deviations,
        "draft_features": got,
    }


def load_profile(path: Optional[Path] = None) -> Optional[Dict]:
    path = path or settings.voice_profile_path()
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build or check an author voice profile")
    parser.add_argument(
        "samples",
        nargs="*",
        help="Sample files (default: data/voice-profile/ or VOICE_SAMPLE_PATH)",
    )
    parser.add_argument("--output", "-o", help="Profile path (default: data/voice-profile.json)")
    parser.add_argument(
        "--check", metavar="FILE", help="Compare a draft against the existing profile"
    )
    args = parser.parse_args(argv)

    out = Path(args.output) if args.output else settings.voice_profile_path()
    if args.check:
        profile = load_profile(out)
        if profile is None:
            print(f"No voice profile at {out}. Build one first.")
            return 1
        raw = Path(args.check).read_text(encoding="utf-8")
        result = compare(textutil.latex_to_text(raw), profile)
        print(json.dumps(result, indent=2))
        return 0 if result["consistent"] else 1

    files = [Path(s) for s in args.samples] or sample_files()
    if not files:
        print(
            f"No voice samples found in {settings.voice_sample_path()}. Add 2-3 paragraphs of your "
            "published writing as .txt files, or skip voice calibration."
        )
        return 1
    try:
        profile = build_profile(files)
    except ValueError as e:
        print(str(e))
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    print(f"Voice profile written to {out}")
    for line in profile["guidance"]:
        print(f"  - {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
