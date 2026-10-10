#!/usr/bin/env python3
"""
Sisyphus Academica: AI-writing pattern detector (41 Humanizer patterns).

Patterns 1-30 are the general list in subagents/style-auditor.md and
subagents/writer.md, taken from blader/humanizer when this project adopted it
(upstream has since renumbered). Patterns 31-41 are the academic extensions
in skills/skill-academic-humanizer/SKILL.md. Most patterns are
phrase or regex rules. Patterns 10, 11, 15, 17, 24, 29 and 35 are structural
heuristics, so a pass here is necessary but not sufficient: the style
auditor agent still reads the paper.

Em dashes count as pattern 14 and are also reported separately because the
gates require exactly zero. Spaced en dashes and spaced LaTeX `--` count as
em dash substitutes. Numeric ranges such as 0.6--1.2 do not.
"""

import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

try:
    from . import textutil
except ImportError:  # run as a script
    import textutil

PATTERN_NAMES = {
    1: "significance inflation",
    2: "notability name-dropping",
    3: "superficial -ing analysis",
    4: "promotional language",
    5: "vague attribution",
    6: "formulaic challenges",
    7: "AI vocabulary",
    8: "copula avoidance",
    9: "negative parallelism",
    10: "rule of three",
    11: "synonym cycling",
    12: "false range",
    13: "agentless passive / subjectless fragment",
    14: "em dash",
    15: "boldface overuse",
    16: "inline-header list",
    17: "title case heading",
    18: "emoji",
    19: "curly quotes",
    20: "collaborative artifact",
    21: "cutoff disclaimer",
    22: "sycophantic tone",
    23: "filler phrase",
    24: "excessive hedging",
    25: "generic conclusion",
    26: "hyphenated pair overuse",
    27: "persuasive authority trope",
    28: "signposting announcement",
    29: "fragmented header",
    30: "diff-anchored writing",
    31: "state-of-the-art inflation",
    32: "'to the best of our knowledge' overuse",
    33: "'further research is needed' filler",
    34: "'recent advances' vagueness",
    35: "formulaic related work",
    36: "table/figure shows without interpretation",
    37: "'despite these limitations' formula",
    38: "'in this paper, we' overuse",
    39: "self-citation promotion",
    40: "citation stacking",
    41: "'this paper proposes' opener",
}

FIXES = {
    1: "State the measured effect instead of calling it important.",
    2: "Drop the prestige marker; say what the cited work found.",
    3: "End the sentence; give the consequence its own sentence with evidence.",
    4: "Replace the adjective with a number or a concrete property.",
    5: "Name and cite the source.",
    6: "Name the specific obstacle and what it costs.",
    7: "Use a plain word (examine, show, use, area).",
    8: "Use 'is' or 'has'.",
    9: "State the claim directly.",
    10: "Keep the items you have evidence for; do not pad to three.",
    11: "Pick one term for this concept and use it throughout.",
    12: "List the actual items.",
    13: "Name who did it.",
    14: "Use a comma, colon, parentheses or a new sentence.",
    15: "Remove bold from running prose.",
    16: "Write the list as prose or plain items.",
    17: "Use sentence case.",
    18: "Remove the emoji.",
    19: "Use straight quotes or LaTeX ``quotes''.",
    20: "Delete the chat artifact.",
    21: "Delete the disclaimer or cite a dated source.",
    22: "Delete the flattery.",
    23: "Cut the filler.",
    24: "Keep one hedge, tied to the source of uncertainty.",
    25: "Name the next experiment and what it would show.",
    26: "Use a plain phrase.",
    27: "State the point without the framing.",
    28: "Start with the content.",
    29: "Merge into the next paragraph or delete.",
    30: "Describe the current state, not the change history.",
    31: "Name the benchmark, the previous best and the margin.",
    32: "Keep one novelty hedge at most.",
    33: "Say which study, on what data, would answer which question.",
    34: "Cite the specific papers and what they showed.",
    35: "Group related work by theme, not one citation per sentence.",
    36: "Say what the reader should see in the table or figure, with numbers.",
    37: "Name the limitation and its effect on the conclusion.",
    38: "Vary the opening; drop 'In this paper, we'.",
    39: "Cite prior work only where it carries the argument.",
    40: "Cite the two or three sources that support the claim.",
    41: "Open with the problem or the finding.",
}


def _rx(*phrases: str) -> re.Pattern:
    return re.compile(r"\b(?:" + "|".join(phrases) + r")\b", re.I)


PHRASES: Dict[int, re.Pattern] = {
    1: _rx(
        r"pivotal",
        r"transformative",
        r"landmark",
        r"groundbreaking",
        r"revolutioni[sz](?:e|es|ed|ing)",
        r"paradigm[- ]shift(?:ing)?",
        r"game[- ]chang(?:er|ing)",
        r"testament to",
        r"monumental",
        r"(?:plays?|played) an? (?:crucial|pivotal|key|vital|critical|central) role",
        r"(?:crucial|vital) role",
        r"(?:marks?|marked|represents?) an? (?:significant|major|important) "
        r"(?:step|milestone|advance(?:ment)?)",
        r"significant step forward",
        r"unprecedented",
    ),
    2: _rx(
        r"(?:world-)?renowned",
        r"prestigious",
        r"leading experts?",
        r"widely acclaimed",
        r"highly (?:respected|influential|acclaimed)",
        r"featured (?:in|by) (?:major|leading|top)",
    ),
    3: re.compile(
        r",\s+(?:highlighting|underscoring|showcasing|emphasizing|emphasising|reflecting|"
        r"signaling|signalling|symbolizing|illustrating|cementing|solidifying|demonstrating) "
        r"(?:the|its|their|how|that|a|an|our)\b",
        re.I,
    ),
    4: _rx(
        r"boasts?",
        r"vibrant",
        r"nestled",
        r"breathtaking",
        r"stunning",
        r"seamless(?:ly)?",
        r"cutting[- ]edge",
        r"unparalleled",
        r"remarkabl[ey]",
        r"impressive(?:ly)?",
        r"world[- ]class",
        r"best[- ]in[- ]class",
        r"rich (?:history|tapestry|heritage|landscape)",
        r"innovative",
        r"exceptional(?:ly)?",
        r"unmatched",
        r"powerful new",
    ),
    6: _rx(
        r"despite (?:these|its|their|the|such|many|numerous) "
        r"(?:challenges|obstacles|setbacks|hurdles|difficulties)",
        r"continues? to (?:thrive|flourish|evolve|grow)",
        r"faces? (?:several|many|numerous|significant) challenges",
        r"challenges remain",
        r"not without (?:its|their) challenges",
    ),
    7: _rx(
        r"delv(?:e|es|ed|ing)",
        r"tapestry",
        r"intricac(?:y|ies)",
        r"intricate(?:ly)?",
        r"showcas(?:e|es|ed|ing)",
        r"underscor(?:e|es|ed|ing)",
        r"realm",
        r"foster(?:s|ed|ing)?",
        r"garner(?:s|ed|ing)?",
        r"interplay",
        r"multifaceted",
        r"embark(?:s|ed|ing)?",
        r"unlock(?:s|ed|ing)? (?:the|new|its)",
        r"harness(?:es|ed|ing)?",
        r"elevat(?:e|es|ed|ing) (?:the|our|your)",
        r"commendabl[ey]",
        r"meticulous(?:ly)?",
        r"unpack(?:s|ed|ing)?",
        r"navigat(?:e|es|ing) the (?:complexit|landscape|challenge)\w*",
        r"(?:the|this|evolving|changing) landscape of",
        r"ever[- ](?:evolving|changing|growing)",
        r"leverag(?:e|es|ed|ing)",
        r"in the realm of",
        r"a myriad of",
        r"plethora",
        r"holistic",
        r"synerg(?:y|ies|istic)",
        r"paramount",
        r"bustling",
        r"invaluable",
    ),
    8: _rx(
        r"serv(?:e|es|ed|ing) as (?:a|an|the)",
        r"stand(?:s|ing)? as (?:a|an|the)",
        r"act(?:s|ed)? as a (?:testament|cornerstone|bridge|catalyst)",
        r"function(?:s|ed)? as a (?:cornerstone|testament)",
        r"boasts? an?",
        r"features? an? (?:robust|rich|wide|comprehensive)",
        r"represents? an? (?:significant|major|novel|new|key|crucial|important|promising)",
    ),
    9: re.compile(
        r"\b(?:not (?:just|only|merely|simply)\b[^.;]{1,80}?\bbut(?: also)?\b|"
        r"it(?:'s| is) not [^.;,]{1,50}, it(?:'s| is)\b|"
        r"is(?:n't| not) about [^.;,]{1,50}, (?:it's|it is) about\b|"
        r"\bno [^.;,]{1,30}, no [^.;,]{1,30}, just\b)",
        re.I,
    ),
    12: re.compile(
        r"\b(?:everything|anything) from\b|\branging from [a-z ]{3,40} to [a-z ]{3,40} (?:and|to) |"
        r"\bfrom (?:the )?[a-z]+(?: [a-z]+)? to (?:the )?[a-z]+(?: [a-z]+)?, (?:and )?from\b",
        re.I,
    ),
    13: re.compile(
        r"^(?:No|Zero) [a-z]+(?: [a-z]+)? (?:needed|required|necessary)\b|"
        r"\bit (?:is|was|has been) "
        r"(?:shown|found|observed|demonstrated|noted|believed|argued|suggested) that\b",
        re.I,
    ),
    20: _rx(
        r"i hope this helps",
        r"let me know if",
        r"feel free to",
        r"happy to help",
        r"as an ai",
        r"here is (?:the|a|an) (?:revised|updated|rewritten|improved)",
        r"certainly[!,]",
        r"of course[!,]",
        r"i can help",
        r"would you like me to",
    ),
    21: _rx(
        r"as of my (?:last|latest|knowledge)",
        r"knowledge cut-?off",
        r"training (?:data )?cut-?off",
        r"while (?:specific )?details are (?:limited|scarce)",
        r"based on (?:the )?available information",
        r"up to my last (?:training|update)",
    ),
    22: _rx(
        r"great question",
        r"you(?:'re| are) (?:absolutely )?right",
        r"excellent (?:point|question)",
        r"what a (?:fascinating|great|wonderful)",
    ),
    23: _rx(
        r"in order to",
        r"due to the fact that",
        r"it is (?:important|worth|interesting) to note that",
        r"it should be noted that",
        r"it is worth (?:noting|mentioning) that",
        r"at this point in time",
        r"in the event that",
        r"for the purpose of",
        r"has the ability to",
        r"needless to say",
        r"essentially",
        r"basically",
        r"actually",
        r"in terms of",
        r"the fact that",
        r"it goes without saying",
    ),
    25: _rx(
        r"the future (?:looks|is) bright",
        r"exciting times (?:lie|are) ahead",
        r"only time will tell",
        r"opens? (?:up )?(?:new|exciting) (?:avenues|possibilities|doors|horizons)",
        r"pav(?:e|es|ed|ing) the way",
        r"a step in the right direction",
        r"holds? (?:great|significant|immense|tremendous) (?:promise|potential)",
        r"remains? to be seen",
    ),
    26: _rx(
        r"data[- ]driven",
        r"cutting[- ]edge",
        r"high[- ]quality",
        r"well[- ]known",
        r"game[- ]changing",
        r"thought[- ]provoking",
        r"user[- ]friendly",
        r"forward[- ]thinking",
        r"fast[- ]paced",
        r"cross[- ]functional",
        r"one[- ]of[- ]a[- ]kind",
        r"next[- ]generation",
        r"mission[- ]critical",
        r"value[- ]added",
        r"far[- ]reaching",
        r"wide[- ]ranging",
    ),
    27: _rx(
        r"at its core",
        r"the real question is",
        r"make no mistake",
        r"the truth is",
        r"in reality,",
        r"here's the thing",
        r"what really matters",
        r"the key insight (?:here )?is",
        r"the bottom line",
        r"fundamentally,",
        r"let(?: u|\')s be clear",
    ),
    28: _rx(
        r"let(?:'s| us) "
        r"(?:dive|delve|explore|take a (?:closer )?look|unpack|break (?:it|this) down)",
        r"here(?:'s| is) what you need to know",
        r"in this section,? we will",
        r"we will now (?:discuss|turn|explore)",
        r"without further ado",
        r"(?:it's|it is) time to",
        r"in conclusion",
        r"to sum (?:it )?up",
        r"as we will see",
        r"buckle up",
    ),
    30: _rx(
        r"(?:in response to|as (?:suggested|requested|noted|recommended) by) "
        r"(?:the )?(?:reviewers?|reviewer \d+|r\d)",
        r"we have (?:now )?(?:added|revised|updated|clarified|expanded|rewritten)",
        r"this revised (?:version|manuscript|draft)",
        r"(?:the|our) (?:previous|earlier|original|prior) (?:version|draft|submission)",
        r"in this revision",
        r"(?:now|newly) (?:supports?|includes?|uses?)",
        r"was (?:changed|updated|revised) (?:from|to)",
    ),
    33: _rx(
        r"(?:further|more|additional|future) (?:research|work|study|studies|investigation) "
        r"(?:is|are|will be) "
        r"(?:needed|required|warranted|necessary)",
        r"warrants? further (?:investigation|research|study)",
    ),
    37: _rx(
        r"despite (?:these|its|their|our|the) limitations",
        r"notwithstanding (?:these|its|their) limitations",
        r"(?:these|its|their) limitations notwithstanding",
    ),
}

TRANSITION = re.compile(
    r"^(?:Moreover|Furthermore|Additionally|Notably|Crucially|Importantly|In addition),"
)
HEDGES = re.compile(
    r"\b(?:may|might|could|possibly|potentially|perhaps|likely|somewhat|arguably|seemingly|"
    r"presumably|conceivably|probably)\b",
    re.I,
)
STACKED_HEDGE = _rx(
    r"could potentially",
    r"may potentially",
    r"might potentially",
    r"might possibly",
    r"could possibly",
    r"may possibly",
    r"may perhaps",
    r"it could be argued",
    r"to some extent",
)
VAGUE_SUBJECT = re.compile(
    r"\b(?:experts|researchers|scholars|scientists|observers|critics|studies|many|some|others)"
    r" (?:have )?(?:believe|suggest|argue|agree|note|claim|shown|found|say|contend)s?\b|"
    r"\bit is (?:widely|generally|commonly) (?:believed|accepted|known|agreed|thought)\b",
    re.I,
)
SOTA = re.compile(r"\bstate[- ]of[- ]the[- ]art\b|\bSOTA\b", re.I)
KNOWLEDGE = re.compile(r"\bto (?:the best of )?our knowledge\b", re.I)
RECENT = re.compile(
    r"\brecent (?:advances|advancements|progress|developments|breakthroughs|years have seen|work)"
    r"(?: in| of| on)?\b",
    re.I,
)
IN_THIS_PAPER = re.compile(r"\bin this (?:paper|work|study|article|manuscript),? we\b", re.I)
OPENER = re.compile(
    r"^(?:in )?this (?:paper|work|study|article|manuscript),? (?:we )?"
    r"(?:propose|present|introduce|describe|investigate|explore)s?\b",
    re.I,
)
SELF_CITE = re.compile(
    r"\b(?:our|my) (?:prior|previous|earlier|own|seminal|foundational) "
    r"(?:work|study|studies|paper|papers)\b|"
    r"\bas we (?:showed|demonstrated|reported|established) (?:in|previously)\b",
    re.I,
)
TABLE_SHOWS = re.compile(
    r"^(?:Table|Figure|Fig\.|Tab\.)\s*(?:\[REF\]|\S+)\s+"
    r"(?:shows|presents|summari[sz]es|reports|lists|"
    r"illustrates|displays|depicts|contains|gives)\b",
    re.I,
)
FORMULAIC_RW = re.compile(
    r"^[A-Z][A-Za-z\-]+(?: (?:et al\.?|and [A-Z][A-Za-z\-]+))?\s*(?:\(\d{4}\)|\[CITE:[^\]]*\])?\s*"
    r"(?:investigated|explored|studied|proposed|introduced|presented|examined|developed|"
    r"analy[sz]ed|addressed|considered|focused)\b"
)
_ADJ = r"([a-z]+(?:ly|ive|ful|ent|ant|able|ible|ous|ic|al|less))\b"
TRIAD = re.compile(r"\b" + _ADJ + ", " + _ADJ + ",? and " + _ADJ)
METHOD_TERMS = (
    "method",
    "approach",
    "technique",
    "framework",
    "strategy",
    "scheme",
    "procedure",
    "pipeline",
)
OWN_METHOD = re.compile(r"\b(?:our|the proposed|this) (" + "|".join(METHOD_TERMS) + r")s?\b", re.I)
EMOJI = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f000-\U0001f2ff\u2b50\u2b06\u2194-\u21ff]"
)
CURLY = re.compile("[\u2018\u2019\u201c\u201d]")
EM_DASH = re.compile(
    "|".join(
        [
            "\u2014",  # em dash
            r"\\textemdash\b",
            r"\\emdash\b",
            r"(?<!-)---(?!-)",  # LaTeX em dash
            "\\s\u2013\\s",  # spaced en dash used as a dash
            r"(?<=[A-Za-z,)])\s--\s(?=[A-Za-z(])",  # spaced LaTeX en dash used as a dash
        ]
    )
)
MINOR_WORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "for",
    "nor",
    "of",
    "on",
    "in",
    "to",
    "at",
    "by",
    "via",
    "with",
    "from",
    "as",
    "vs",
    "vs.",
    "per",
    "into",
    "over",
    "under",
}


def _finding(pid: int, line: int, text: str) -> Dict:
    return {
        "pattern": pid,
        "name": PATTERN_NAMES[pid],
        "line": line,
        "text": " ".join(text.split())[:160],
        "fix": FIXES[pid],
    }


def _snippet(sentence: str, m: re.Match) -> str:
    start = max(0, m.start() - 40)
    end = m.end() + 40
    return sentence[start:end]


def count_em_dashes(raw: str) -> List[Tuple[int, str]]:
    """Em dashes and dash substitutes in the raw source, as (line, excerpt)."""
    found = []
    latex = textutil.is_latex(raw)
    for i, line in enumerate(raw.split("\n"), 1):
        code = textutil.strip_comment(line) if latex else line
        for m in EM_DASH.finditer(code):
            found.append((i, _snippet(code, m)))
    return found


def _sentence_rules(sents: List[Tuple[int, str]]) -> List[Dict]:
    out: List[Dict] = []
    for line, s in sents:
        for pid, rx in PHRASES.items():
            for m in rx.finditer(s):
                out.append(_finding(pid, line, _snippet(s, m)))
        if TRANSITION.search(s):
            out.append(_finding(7, line, s[:60]))
        has_cite = "[CITE:" in s or re.search(r"\(\D*\d{4}[a-z]?\)|\[\d+(?:[,\-]\s*\d+)*\]", s)
        if not has_cite:
            for m in VAGUE_SUBJECT.finditer(s):
                out.append(_finding(5, line, _snippet(s, m)))
            for m in RECENT.finditer(s):
                out.append(_finding(34, line, _snippet(s, m)))
        if SOTA.search(s) and not re.search(r"\d", s):
            out.append(_finding(31, line, s))
        stacked = list(STACKED_HEDGE.finditer(s))
        for m in stacked:
            out.append(_finding(24, line, _snippet(s, m)))
        if not stacked and len(HEDGES.findall(s)) >= 3:
            out.append(_finding(24, line, s))
        if TABLE_SHOWS.search(s):
            rest = TABLE_SHOWS.sub("", s)
            if not re.search(r"\d", rest) and not re.search(
                r"\b(?:that|how|whether|where|when)\b", rest
            ):
                out.append(_finding(36, line, s))
        for m in TRIAD.finditer(s):
            out.append(_finding(10, line, _snippet(s, m)))
        for tok in re.findall(r"\[CITE:([^\]]*)\]", s):
            if len([k for k in tok.split(",") if k.strip()]) >= 5:
                out.append(_finding(40, line, s))
        for m in re.finditer(r"\[(\d+)\s*[-\u2013]\s*(\d+)\]", s):
            if int(m.group(2)) - int(m.group(1)) >= 4:
                out.append(_finding(40, line, s))
    return out


def _document_rules(text: str, sents: List[Tuple[int, str]]) -> List[Dict]:
    out: List[Dict] = []

    # 32: one novelty hedge is fine; each extra one counts.
    hits = [(ln, s) for ln, s in sents if KNOWLEDGE.search(s)]
    out += [_finding(32, ln, s) for ln, s in hits[1:]]

    # 38: one "In this paper, we" is fine.
    hits = [(ln, s) for ln, s in sents if IN_THIS_PAPER.search(s)]
    out += [_finding(38, ln, s) for ln, s in hits[1:]]

    # 39: more than two self-citation framings.
    hits = [(ln, s) for ln, s in sents if SELF_CITE.search(s)]
    out += [_finding(39, ln, s) for ln, s in hits[2:]]

    # 41: the first sentence of the document or abstract.
    sections = textutil.split_sections(text)
    for name in ("abstract", "preamble"):
        first = textutil.sentences(sections.get(name, ""))
        if first and OPENER.search(first[0][1]):
            line = next((ln for ln, s in sents if s == first[0][1]), 1)
            out.append(_finding(41, line, first[0][1]))
            break

    # 35: three or more consecutive "Author et al. (Year) verb" sentences.
    run: List[Tuple[int, str]] = []
    for ln, s in sents + [(0, "")]:
        if s and FORMULAIC_RW.search(s):
            run.append((ln, s))
            continue
        if len(run) >= 3:
            out += [_finding(35, rl, rs) for rl, rs in run[2:]]
        run = []

    # 11: synonym cycling for the paper's own method.
    terms = Counter(m.group(1).lower() for _, s in sents for m in OWN_METHOD.finditer(s))
    if len(terms) >= 3:
        main = terms.most_common(1)[0][0]
        for ln, s in sents:
            for m in OWN_METHOD.finditer(s):
                if m.group(1).lower() != main:
                    out.append(_finding(11, ln, _snippet(s, m)))

    # 13: subject-less fragments at sentence start are caught per sentence by PHRASES[13].
    # 17 and 29: headings.
    lines = text.split("\n")
    for ln, title in textutil.headings(text):
        tokens = [w for w in re.split(r"\s+", title) if re.search(r"[A-Za-z]", w)]
        content = [w for w in tokens if w.lower().strip(".,:;") not in MINOR_WORDS]
        if (
            len(tokens) >= 4
            and content
            and all(w[0].isupper() for w in content)
            and any(w[0].isupper() for w in tokens[1:] if w.lower() not in MINOR_WORDS)
        ):
            out.append(_finding(17, ln, title))
        body: List[str] = []
        for nxt in lines[ln:]:
            if nxt.startswith("#"):
                break
            if not nxt.strip():
                if body:
                    break
                continue
            body.append(nxt.strip())
        para = " ".join(body)
        if (
            para
            and not para.endswith(":")
            and len(textutil.sentences(para)) == 1
            and textutil.word_count(para) < 15
        ):
            heads = {w.lower() for w in textutil.words(title) if w.lower() not in MINOR_WORDS}
            if heads and len(heads & {w.lower() for w in textutil.words(para)}) / len(heads) >= 0.5:
                out.append(_finding(29, ln + 1, para))
    return out


def _raw_rules(raw: str, n_words: int) -> List[Dict]:
    out: List[Dict] = []
    lines = raw.split("\n")
    in_table = 0
    in_list = False
    latex = textutil.is_latex(raw)
    bold: List[Tuple[int, str]] = []
    for i, line in enumerate(lines, 1):
        code = textutil.strip_comment(line) if latex else line
        in_table += len(re.findall(r"\\begin\{(?:table|tabular|algorithm|algorithmic)\*?\}", code))
        in_table -= len(re.findall(r"\\end\{(?:table|tabular|algorithm|algorithmic)\*?\}", code))
        for m in EMOJI.finditer(code):
            out.append(_finding(18, i, _snippet(code, m)))
        for m in CURLY.finditer(code):
            out.append(_finding(19, i, _snippet(code, m)))
        if re.search(
            r"\\item\s*\\textbf\{[^}]{1,60}[:.]?\s*\}|^\s*[-*]\s+\*\*[^*]{1,60}[:.]\*\*", code
        ):
            if not in_list:
                out.append(_finding(16, i, code))
            in_list = True
            continue
        if code.strip() and not re.match(r"\s*\\item\b", code):
            in_list = False
        if in_table <= 0 and not re.match(r"\s*\\(?:paragraph|section|subsection|caption)", code):
            for m in re.finditer(r"\\textbf\{([^}]*)\}|(?<!\*)\*\*([^*]+)\*\*", code):
                if code[: m.start()].strip() in ("", "\\noindent"):
                    continue  # run-in paragraph heading
                bold.append((i, m.group(0)))
    allowance = max(2, n_words // 500)
    out += [_finding(15, ln, t) for ln, t in bold[allowance:]]
    return out


def scan(raw: str, prose: Optional[str] = None) -> Dict:
    """Scan LaTeX or Markdown source. Returns findings, counts and densities."""
    text = prose if prose is not None else textutil.latex_to_text(raw)
    sents = textutil.sentences(text)
    n_words = textutil.word_count(text)

    findings = _sentence_rules(sents) + _document_rules(text, sents) + _raw_rules(raw, n_words)
    dashes = count_em_dashes(raw)
    findings += [_finding(14, ln, t) for ln, t in dashes]
    findings.sort(key=lambda f: (f["line"], f["pattern"]))

    by_pattern = Counter(f["pattern"] for f in findings)
    total = len(findings)
    return {
        "words": n_words,
        "sentences": len(sents),
        "violations": total,
        "em_dashes": len(dashes),
        "density_per_1000": round(total * 1000 / n_words, 3) if n_words else 0.0,
        "density_per_2000": round(total * 2000 / n_words, 3) if n_words else 0.0,
        "by_pattern": {f"{pid}. {PATTERN_NAMES[pid]}": n for pid, n in sorted(by_pattern.items())},
        "findings": findings,
    }


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Scan a LaTeX or Markdown file for the 41 AI-writing patterns"
    )
    parser.add_argument("file")
    args = parser.parse_args(argv)
    with open(args.file, encoding="utf-8") as f:
        result = scan(f.read())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
