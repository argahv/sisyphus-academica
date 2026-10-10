#!/usr/bin/env python3
"""
Sisyphus Academica: statistical audit.

Deterministic checks on statistics reported in a paper:
  - recompute p from t, F, chi-square, z and r statistics and compare with the
    reported p (allowing for rounding), in the style of statcheck
  - "significant" claimed with p > .05
  - impossible values (p outside [0, 1], p = 0, |r| > 1, CI bounds reversed,
    point estimate outside its CI)
  - five or more tests with no multiple-comparison correction mentioned
  - Bonferroni-adjusted alpha that does not equal alpha / k
  - decimals and percentages in the abstract or conclusion that do not appear
    in the body
  - with an analysis output (statistics.json), test statistics in the text
    that the analysis never produced

Errors block the gate. Warnings go to the verifier agent for judgment.
"""

import json
import math
import re
from typing import Dict, List, Optional, Tuple

try:
    from . import textutil
except ImportError:  # run as a script
    import textutil

NUM = r"(-?\d+(?:\.\d+)?)"
P_RX = re.compile(r"\bp\s*(=|<|>|<=|>=|≤|≥)\s*(\d*\.?\d+(?:e-?\d+)?)", re.I)
TESTS = [
    ("t", re.compile(r"\bt\s*\(\s*" + NUM + r"\s*\)\s*=\s*" + NUM)),
    ("F", re.compile(r"\bF\s*\(\s*" + NUM + r"\s*,\s*" + NUM + r"\s*\)\s*=\s*" + NUM)),
    (
        "chi2",
        re.compile(
            r"(?:chi2|χ2|χ²|chi-squared?)\s*(?:\(\s*(\d+)(?:\s*,\s*N\s*=\s*\d+)?\s*\))?\s*=\s*"
            + NUM,
            re.I,
        ),
    ),
    ("r", re.compile(r"\br\s*\(\s*" + NUM + r"\s*\)\s*=\s*(-?\.?\d+(?:\.\d+)?)")),
    ("z", re.compile(r"\b[zZ]\s*=\s*" + NUM)),
]
CORRECTION = re.compile(
    r"bonferroni|holm|benjamini|hochberg|false discovery|\bfdr\b|tukey|šidák|sidak|scheff|"
    r"(?:corrected|adjusted) (?:for )?(?:multiple|p|alpha|α)|multiple[- ]comparison",
    re.I,
)
EXACT_TESTS = re.compile(
    r"fisher|binomial|permutation|bootstrap|exact test|mcnemar|wilcoxon|mann[- ]whitney|"
    r"kruskal|log[- ]rank|likelihood[- ]ratio",
    re.I,
)
NOT_SIG = re.compile(
    r"\b(?:not|non-?|in)\s*significant|\bno significant|\bfailed to reach significance", re.I
)
SIG = re.compile(r"\bsignificant(?:ly)?\b", re.I)
CI_RX = re.compile(
    r"(?:\bCI\b|confidence interval)[^\[\d]{0,20}\[\s*"
    + NUM
    + r"\s*%?\s*,\s*"
    + NUM
    + r"\s*%?\s*\]",
    re.I,
)
BONF = re.compile(
    r"bonferroni[^.]{0,80}?(\d+)\s+(?:comparisons|tests)[^.]{0,60}?(?:alpha|α)\s*=\s*(\d*\.\d+)",
    re.I,
)


# ------------------------------------------------------------ distributions


def _betacf(a: float, b: float, x: float) -> float:
    tiny, qab, qap, qam = 1e-300, a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c if abs(1.0 + aa / c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c if abs(1.0 + aa / c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbt = (
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    )
    if x < (a + 1) / (a + b + 2):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * _betacf(b, a, 1 - x) / b


def gammaincc(s: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(s, x)."""
    if x <= 0:
        return 1.0
    if x < s + 1:
        term = total = 1.0 / s
        n = s
        for _ in range(500):
            n += 1
            term *= x / n
            total += term
            if abs(term) < abs(total) * 1e-14:
                break
        return 1.0 - total * math.exp(-x + s * math.log(x) - math.lgamma(s))
    tiny = 1e-300
    b = x + 1 - s
    c, d = 1 / tiny, 1 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - s)
        b += 2
        d = an * d + b
        d = 1 / (d if abs(d) > tiny else tiny)
        c = b + an / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-14:
            break
    return math.exp(-x + s * math.log(x) - math.lgamma(s)) * h


def p_value(
    test: str, stat: float, df1: Optional[float] = None, df2: Optional[float] = None
) -> float:
    """Two-tailed p for t, z and r; upper-tail p for F and chi-square."""
    if test == "t":
        return betainc(df1 / 2, 0.5, df1 / (df1 + stat * stat))
    if test == "z":
        return math.erfc(abs(stat) / math.sqrt(2))
    if test == "r":
        if abs(stat) >= 1:
            return 0.0
        t = stat * math.sqrt(df1 / (1 - stat * stat))
        return p_value("t", t, df1)
    if test == "F":
        return betainc(df2 / 2, df1 / 2, df2 / (df2 + df1 * stat)) if stat > 0 else 1.0
    if test == "chi2":
        return gammaincc(df1 / 2, stat / 2)
    raise ValueError(test)


# ------------------------------------------------------------------ checks


def _decimals(s: str) -> int:
    return len(s.split(".")[1]) if "." in s else 0


def _p_range(test: str, stat_s: str, df1, df2) -> Tuple[float, float]:
    """p-values reachable given rounding of the reported statistic."""
    stat = float(stat_s)
    half = 0.5 * 10 ** (-_decimals(stat_s))
    lo_stat, hi_stat = abs(stat) - half, abs(stat) + half
    if test in ("F", "chi2"):
        lo_stat = max(lo_stat, 1e-12)
    if test == "r":
        hi_stat = min(hi_stat, 0.999999)
    p_hi = p_value(test, max(lo_stat, 0.0), df1, df2)
    p_lo = p_value(test, hi_stat, df1, df2)
    return min(p_lo, p_hi), max(p_lo, p_hi)


def _consistent(op: str, p_s: str, lo: float, hi: float, one_tailed: bool) -> bool:
    if one_tailed:
        lo, hi = lo / 2, hi / 2
    p = float(p_s)
    if op in ("<", "<=", "≤"):
        return lo < p or (op != "<" and lo <= p)
    if op in (">", ">=", "≥"):
        return hi > p or (op != ">" and hi >= p)
    tol = 0.5 * 10 ** (-_decimals(p_s)) if "." in p_s else 0.5
    return lo - tol <= p <= hi + tol


def _issue(level: str, kind: str, line: int, text: str, message: str) -> Dict:
    return {
        "level": level,
        "check": kind,
        "line": line,
        "text": " ".join(text.split())[:200],
        "message": message,
    }


def _numbers(text: str) -> List[str]:
    return re.findall(r"(?<![\w.])(\d+\.\d+|\d+(?=\s*%|\s*pp\b))", text)


def _matches_any(value: str, body_values: List[float]) -> bool:
    v, d = float(value), _decimals(value)
    return any(round(b, d) == v or abs(b - v) < 1e-9 for b in body_values)


def _traceable(test: str, stat: float, analysis: List[Dict]) -> bool:
    for t in analysis:
        try:
            other = float(t.get("statistic"))
        except (TypeError, ValueError):
            continue
        if abs(abs(other) - abs(stat)) <= max(0.0051, abs(stat) * 0.005):
            return True
    return False


def audit_text(src: str, analysis: Optional[Dict] = None) -> Dict:
    """Audit LaTeX or Markdown source. `analysis` is the parsed statistics.json, if any."""
    text = textutil.latex_to_text(src, keep_math=True)
    sents = textutil.sentences(text)
    issues: List[Dict] = []
    tests_found: List[Dict] = []
    p_count = 0
    analysis_tests = (analysis or {}).get("tests") or (analysis or {}).get("tests_performed") or []

    for line, s in sents:
        one_tailed = bool(re.search(r"one[- ](?:tailed|sided)", s, re.I))
        ps = list(P_RX.finditer(s))
        p_count += len(ps)
        stats_here = []
        for name, rx in TESTS:
            for m in rx.finditer(s):
                g = m.groups()
                if name == "t":
                    df1, df2, stat_s = float(g[0]), None, g[1]
                elif name == "F":
                    df1, df2, stat_s = float(g[0]), float(g[1]), g[2]
                elif name == "chi2":
                    df1 = float(g[0]) if g[0] else (1.0 if re.search(r"mcnemar", s, re.I) else None)
                    df2, stat_s = None, g[1]
                elif name == "r":
                    df1, df2, stat_s = float(g[0]), None, g[1]
                else:
                    df1, df2, stat_s = None, None, g[0]
                stats_here.append((name, m, df1, df2, stat_s))

        for name, m, df1, df2, stat_s in stats_here:
            stat = float(stat_s)
            entry = {
                "test": name,
                "statistic": stat,
                "df": [d for d in (df1, df2) if d is not None],
                "line": line,
            }
            tests_found.append(entry)
            if name == "r" and abs(stat) > 1:
                issues.append(
                    _issue("error", "impossible_value", line, s, f"|r| = {abs(stat)} > 1")
                )
                continue
            if name == "chi2" and df1 is None:
                issues.append(
                    _issue(
                        "warning",
                        "missing_df",
                        line,
                        s,
                        "chi-square reported without degrees of freedom",
                    )
                )
                continue
            following = [p for p in ps if p.start() >= m.end()]
            if not following:
                continue
            pm = following[0]
            lo, hi = _p_range(name, stat_s, df1, df2)
            entry["p_recomputed"] = round((lo + hi) / 2, 6)
            if not _consistent(pm.group(1), pm.group(2), lo, hi, one_tailed):
                exact = p_value(name, stat, df1, df2) / (2 if one_tailed else 1)
                issues.append(
                    _issue(
                        "error",
                        "p_mismatch",
                        line,
                        s,
                        f"{name} = {stat_s} gives p = {exact:.4g}, but the text reports "
                        f"p {pm.group(1)} {pm.group(2)}",
                    )
                )
            if analysis is not None and not _traceable(name, stat, analysis_tests):
                issues.append(
                    _issue(
                        "error",
                        "untraceable",
                        line,
                        s,
                        f"{name} = {stat_s} does not appear in the analysis output "
                        "(statistics.json)",
                    )
                )

        for pm in ps:
            p = float(pm.group(2))
            if p > 1 or p < 0:
                issues.append(
                    _issue("error", "impossible_value", line, s, f"p = {p} is outside [0, 1]")
                )
            elif p == 0 and pm.group(1) == "=":
                issues.append(
                    _issue(
                        "error",
                        "impossible_value",
                        line,
                        s,
                        "p = 0 is impossible; report p < 0.001",
                    )
                )
            if pm.group(1) == "=" and 0.04 <= p < 0.05:
                issues.append(
                    _issue(
                        "warning",
                        "p_hacking_signal",
                        line,
                        s,
                        f"p = {p} sits just below .05; report the exact test, n and effect size",
                    )
                )
            if (
                SIG.search(s)
                and not NOT_SIG.search(s)
                and (
                    (pm.group(1) == "=" and p > 0.05)
                    or (pm.group(1) in (">", ">=", "≥") and p >= 0.05)
                )
            ):
                issues.append(
                    _issue(
                        "error",
                        "significance_claim",
                        line,
                        s,
                        f'"significant" claimed with p {pm.group(1)} {p}',
                    )
                )
        if ps and not stats_here and not EXACT_TESTS.search(s):
            issues.append(
                _issue(
                    "warning",
                    "p_without_statistic",
                    line,
                    s,
                    "p-value reported without a test statistic or named exact test",
                )
            )

        for m in CI_RX.finditer(s):
            lo_s, hi_s = m.group(1), m.group(2)
            if float(lo_s) > float(hi_s):
                issues.append(
                    _issue(
                        "error",
                        "impossible_value",
                        line,
                        s,
                        f"CI lower bound {lo_s} > upper bound {hi_s}",
                    )
                )
                continue
            before = re.sub(
                r"\d+(?:\.\d+)?\s*%?\s*(?:Wilson |bootstrap |exact )?$", "", s[: m.start()].rstrip()
            )
            nums = re.findall(r"(\d+(?:\.\d+)?)\s*%?", before)
            if nums:
                est = float(nums[-1])
                if not float(lo_s) <= est <= float(hi_s):
                    issues.append(
                        _issue(
                            "error",
                            "estimate_outside_ci",
                            line,
                            s,
                            f"estimate {nums[-1]} lies outside [{lo_s}, {hi_s}]",
                        )
                    )

        for m in BONF.finditer(s):
            k, adj = int(m.group(1)), float(m.group(2))
            alpha_m = re.search(r"(?:alpha|α)\s*=\s*(0?\.\d+)(?![^.]*adjusted)", s, re.I)
            alpha = (
                0.05 if not alpha_m or float(alpha_m.group(1)) == adj else float(alpha_m.group(1))
            )
            if k and abs(adj - alpha / k) > 0.5 * 10 ** (-_decimals(m.group(2))) + 1e-12:
                issues.append(
                    _issue(
                        "error",
                        "bonferroni_arithmetic",
                        line,
                        s,
                        f"{alpha}/{k} = {alpha / k:.4g}, not {adj}",
                    )
                )

    if p_count >= 5 and not CORRECTION.search(text):
        issues.append(
            _issue(
                "error",
                "multiple_comparisons",
                1,
                "",
                f"{p_count} p-values reported and no multiple-comparison correction is mentioned",
            )
        )

    sections = textutil.split_sections(text)
    summary_names = [n for n in sections if n in ("abstract", "conclusion", "conclusions")]
    body = "\n".join(v for k, v in sections.items() if k not in summary_names)
    body_values = [float(n) for n in _numbers(body)]
    lines = text.split("\n")
    for name in summary_names:
        for value in dict.fromkeys(_numbers(sections[name])):
            if not _matches_any(value, body_values):
                line = next((i for i, ln in enumerate(lines, 1) if value in ln), 1)
                issues.append(
                    _issue(
                        "error",
                        "summary_number_not_in_body",
                        line,
                        lines[line - 1],
                        f"{value} appears in the {name} but nowhere in the body",
                    )
                )

    errors = [i for i in issues if i["level"] == "error"]
    return {
        "tests_found": len(tests_found),
        "p_values_found": p_count,
        "errors": len(errors),
        "warnings": len(issues) - len(errors),
        "passed": not errors,
        "issues": issues,
        "tests": tests_found,
    }


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Statistical audit of a LaTeX or Markdown paper")
    parser.add_argument("file")
    parser.add_argument("--analysis", help="statistics.json from the data engineer")
    args = parser.parse_args(argv)
    with open(args.file, encoding="utf-8") as f:
        src = f.read()
    analysis = None
    if args.analysis:
        with open(args.analysis, encoding="utf-8") as f:
            analysis = json.load(f)
    result = audit_text(src, analysis)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
