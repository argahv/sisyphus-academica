#!/usr/bin/env python3
"""
Sisyphus Academica: text helpers shared by the quality gates.

latex_to_text() turns LaTeX (or Markdown) into prose while keeping the
line count, so gate findings point at real source lines. Citations become
[CITE:key1,key2] tokens, references become [REF], headings become "## Title".
"""

import re
from typing import Dict, List, Tuple

DROP_ENVS = (
    "table",
    "table*",
    "tabular",
    "tabular*",
    "equation",
    "equation*",
    "align",
    "align*",
    "gather",
    "gather*",
    "multline",
    "algorithm",
    "algorithmic",
    "verbatim",
    "lstlisting",
    "thebibliography",
    "tikzpicture",
    "displaymath",
    "eqnarray",
    "eqnarray*",
)
DROP_WITH_ARG = (
    "label",
    "includegraphics",
    "vspace",
    "hspace",
    "bibliographystyle",
    "bibliography",
    "usepackage",
    "input",
    "include",
    "newcommand",
    "renewcommand",
    "setlength",
    "documentclass",
    "pagestyle",
    "thispagestyle",
    "newtheorem",
    "graphicspath",
)
HEADINGS = ("section", "subsection", "subsubsection", "paragraph", "chapter")
ABBREVIATIONS = (
    "et al.",
    "e.g.",
    "i.e.",
    "Fig.",
    "Figs.",
    "Eq.",
    "Eqs.",
    "vs.",
    "cf.",
    "etc.",
    "Sec.",
    "No.",
    "approx.",
    "resp.",
    "Dr.",
    "Prof.",
)
WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
TOKEN = re.compile(r"\[(?:CITE:[^\]]*|REF)\]")

MATH_SYMBOLS = [
    (r"\chi^2", "chi2"),
    (r"\chi^{2}", "chi2"),
    (r"\chi", "chi"),
    (r"\leq", "<="),
    (r"\le", "<="),
    (r"\geq", ">="),
    (r"\ge", ">="),
    (r"\times", "x"),
    (r"\pm", "±"),
    (r"\%", "%"),
    (r"\,", ""),
    (r"\;", " "),
    (r"\!", ""),
    (r"\eta^2", "eta2"),
    (r"\alpha", "alpha"),
    (r"\kappa", "kappa"),
    (r"\rho", "rho"),
    (r"\mathrm", ""),
    (r"\text", ""),
    (r"\textrm", ""),
    (r"\left", ""),
    (r"\right", ""),
    (r"\approx", "~"),
    (r"\sim", "~"),
]


def _blank(match: re.Match) -> str:
    return "\n" * match.group(0).count("\n")


def _heading(m: re.Match) -> str:
    level, title = m.group(1), m.group(2)
    if level == "paragraph":
        return title + " "
    return ("## " if level in ("section", "chapter") else "### ") + title


def is_latex(src: str) -> bool:
    """True when the source uses LaTeX markup (then % starts a comment)."""
    return bool(re.search(r"\\(?:[a-zA-Z]+\*?[{\[]|%|item\b|maketitle\b|\\)", src))


def strip_comment(line: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", line)


def _strip_comments(src: str) -> str:
    return strip_comment(src) if is_latex(src) else src


def _normalize_math(expr: str) -> str:
    for sym, repl in MATH_SYMBOLS:
        expr = expr.replace(sym, repl)
    expr = re.sub(r"[{}]", "", expr)
    return expr.replace("\\", "")


def _unwrap_commands(text: str) -> str:
    for _ in range(6):
        new = re.sub(
            r"\\(?:" + "|".join(DROP_WITH_ARG) + r")\*?(?:\[[^\]]*\])?\{[^{}]*\}", "", text
        )
        new = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", new)
        if new == text:
            break
        text = new
    text = re.sub(r"\\[a-zA-Z]+\*?", "", text)
    return text.replace("{", "").replace("}", "")


def latex_to_text(src: str, keep_math: bool = False) -> str:
    """Convert LaTeX or Markdown to prose. Keeps line breaks for line numbers.

    With keep_math=True, inline math is kept with common symbols normalized
    (\\chi^2 -> chi2, \\le -> <=) so statistics can be parsed.
    """
    if "\\begin{document}" in src:
        head, body = src.split("\\begin{document}", 1)
        src = "\n" * head.count("\n") + body
    src = re.sub(r"\\end\{document\}[\s\S]*", "", src)
    src = _strip_comments(src)
    for env in DROP_ENVS:
        e = re.escape(env)
        src = re.sub(r"\\begin\{" + e + r"\}[\s\S]*?\\end\{" + e + r"\}", _blank, src)
    src = re.sub(r"\\\[[\s\S]*?\\\]", _blank, src)
    src = re.sub(r"\$\$[\s\S]*?\$\$", _blank, src)
    if keep_math:
        src = re.sub(r"(?<!\\)\$([^$]*)\$", lambda m: _normalize_math(m.group(1)), src)
    else:
        src = re.sub(r"(?<!\\)\$[^$]*\$", "x", src)

    src = re.sub(
        r"\\(?:no)?cite[tpa-z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}",
        lambda m: "[CITE:" + ",".join(k.strip() for k in m.group(1).split(",")) + "]",
        src,
    )
    src = re.sub(r"(?:~|\s)?\\(?:eq|auto|c|C|page)?ref\{[^}]*\}", " [REF]", src)
    src = re.sub(r"\\(" + "|".join(HEADINGS) + r")\*?(?:\[[^\]]*\])?\{([^{}]*)\}", _heading, src)
    src = re.sub(r"\\begin\{abstract\}[ \t]*(?=\S)", "## Abstract\n", src)
    src = re.sub(r"\\begin\{abstract\}", "## Abstract", src)
    src = re.sub(r"\\end\{abstract\}", "", src)
    src = re.sub(r"\\item\b(?:\[[^\]]*\])?", "- ", src)
    src = re.sub(r"\\(?:begin|end)\{[^}]*\}(?:\[[^\]]*\])?", "", src)
    src = re.sub(r"\\caption\{", "Caption: {", src)
    src = src.replace("``", '"').replace("''", '"').replace("~", " ").replace("\\\\", " ")
    src = src.replace("\\%", "%").replace("\\&", "&").replace("\\_", "_").replace("\\#", "#")
    src = src.replace("\\$", "$")

    text = _unwrap_commands(src)
    # Markdown emphasis and links
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\((?:[^)]+)\)", r"\1", text)
    text = re.sub(r"^[ \t]*#{1,2}[ \t]+", "## ", text, flags=re.M)
    text = re.sub(r"^[ \t]*#{3,6}[ \t]+", "### ", text, flags=re.M)
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n"))


def words(text: str) -> List[str]:
    return WORD.findall(TOKEN.sub(" ", text))


def word_count(text: str) -> int:
    return len(words(text))


def _protect(text: str) -> str:
    for abbr in ABBREVIATIONS:
        text = text.replace(abbr, abbr.replace(".", "\u2024"))
    text = re.sub(r"(\d)\.(\d)", "\\1\u2024\\2", text)
    text = re.sub(r"(?<![\w.])\.(\d)", "\u2024\\1", text)
    return re.sub(r"\b([A-Z])\.(?=\s?[A-Z])", "\\1\u2024", text)


def sentences(text: str) -> List[Tuple[int, str]]:
    """Split prose into (line_number, sentence). Headings and list markers are skipped."""
    out: List[Tuple[int, str]] = []
    para: List[Tuple[int, str]] = []

    def flush():
        if not para:
            return
        start = para[0][0]
        joined = " ".join(t for _, t in para)
        offsets, pos = [], 0
        for ln, t in para:
            offsets.append((pos, ln))
            pos += len(t) + 1
        for m in re.finditer(r'[^.!?]+(?:[.!?]+["\')\]]*|$)', _protect(joined)):
            s = m.group(0).replace("\u2024", ".").strip()
            if len(WORD.findall(s)) < 2:
                continue
            line = start
            for off, ln in offsets:
                if off <= m.start():
                    line = ln
            out.append((line, s))
        para.clear()

    for i, raw in enumerate(text.split("\n"), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            flush()
            continue
        if line.startswith("- "):
            flush()
            line = line[2:]
        para.append((i, line))
    flush()
    return out


def headings(text: str) -> List[Tuple[int, str]]:
    return [
        (i, line.lstrip("#").strip())
        for i, line in enumerate(text.split("\n"), 1)
        if line.startswith("## ") or line.startswith("### ")
    ]


def split_sections(text: str) -> Dict[str, str]:
    """Map lowercased top-level heading -> prose under it. Text before any heading is 'preamble'."""
    sections: Dict[str, List[str]] = {"preamble": []}
    current = "preamble"
    for line in text.split("\n"):
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections.setdefault(current, [])
            continue
        sections[current].append(line)
    return {k: "\n".join(v) for k, v in sections.items()}
