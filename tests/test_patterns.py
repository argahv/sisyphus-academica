"""Tests for the 41-pattern AI-writing detector and the em dash counter."""

import pytest

from sisyphus.tools import patterns, workspace

EXAMPLES = {
    1: "This is a pivotal result for the field.",
    2: "The renowned lab built the first version.",
    3: "The model improves accuracy, highlighting the importance of clean data.",
    4: "The results on the benchmark are remarkable.",
    5: "Researchers suggest that this method works well.",
    6: "Despite these challenges, the field continues to thrive.",
    7: "We delve into the data to find the cause.",
    8: "The cache serves as a bridge between the two layers.",
    9: "It is not just fast but also accurate on long inputs.",
    10: "The design is efficient, scalable, and practical for teams.",
    11: "Our method is fast. Our approach scales well. Our framework generalizes to new data.",
    12: "We cover everything from tokenizers to deployment.",
    13: "It was shown that the bound is tight.",
    14: "The model \u2014 trained on two datasets \u2014 converges quickly.",
    15: r"We use \textbf{one} input, \textbf{two} outputs and \textbf{three} layers in total.",
    16: "\\begin{itemize}\n\\item \\textbf{Speed:} the model is fast.\n\\end{itemize}",
    17: "\\section{Results On Large Scale Benchmarks}\nThe model wins six of eight tasks.",
    18: "The model works well \U0001f680 on all tasks.",
    19: "The authors call it \u201cattention\u201d in the paper.",
    20: "I hope this helps with the analysis of the model.",
    21: "As of my last update, the benchmark had ten tasks.",
    22: "Great question about the training setup of the model.",
    23: "We normalize the inputs in order to stabilize training.",
    24: "This change could potentially reduce the error.",
    25: "This result paves the way for larger systems.",
    26: "We propose a data-driven estimate of the noise.",
    27: "At its core, the model is a lookup table.",
    28: "Let's dive into the details of the training loop.",
    29: "\\section{Training details}\nTraining details are given here.\n\nWe train for ten epochs.",
    30: "In response to the reviewers, we added an ablation table.",
    31: "Our method is state-of-the-art on these tasks.",
    32: "To our knowledge, this is new. To the best of our knowledge, the bound is also new.",
    33: "Further research is needed on this question.",
    34: "Recent advances in deep learning changed translation.",
    35: (
        "Smith et al. (2020) proposed sparse attention. "
        "Jones et al. (2021) studied linear attention. "
        "Lee (2022) introduced kernel attention. Kim (2023) examined memory."
    ),
    36: "Table 1 shows the results.",
    37: "Despite these limitations, the work matters for practitioners.",
    38: "In this paper, we study sparsity. In this paper, we also study speed.",
    39: (
        "Our prior work set the stage. Our previous work added data. "
        "Our earlier work added a model. Our own work then did more."
    ),
    40: r"Attention has been studied widely \citep{a2017,b2018,c2019,d2020,e2021}.",
    41: "This paper proposes a new tokenizer for code.",
}


@pytest.mark.parametrize("pid", sorted(EXAMPLES))
def test_each_pattern_is_detected(pid):
    found = {f["pattern"] for f in patterns.scan(EXAMPLES[pid])["findings"]}
    assert (
        pid in found
    ), f"pattern {pid} ({patterns.PATTERN_NAMES[pid]}) not detected; got {sorted(found)}"


def test_all_41_patterns_have_names_and_fixes():
    assert sorted(patterns.PATTERN_NAMES) == list(range(1, 42))
    assert sorted(patterns.FIXES) == list(range(1, 42))
    assert sorted(EXAMPLES) == list(range(1, 42))


def test_clean_academic_text_has_no_findings():
    text = (
        "We trained the model for ten epochs on 4000 examples. Accuracy rose from 61.2% to 74.8% "
        "on the held-out set, and the gain held across five seeds. The largest errors came from "
        "inputs longer than 512 tokens, which the model truncates. Table 2 shows that truncation "
        "explains 40% of the remaining errors."
    )
    assert patterns.scan(text)["violations"] == 0


def test_demo_paper_is_clean(demo_run):
    result = patterns.scan(workspace.paper_source(demo_run))
    assert result["violations"] == 0, result["findings"]
    assert result["words"] > 500


def test_single_knowledge_hedge_and_in_this_paper_are_allowed():
    text = "To our knowledge, this is new. In this paper, we study X. The results follow."
    found = {f["pattern"] for f in patterns.scan(text)["findings"]}
    assert 32 not in found and 38 not in found


def test_sota_with_numbers_is_allowed():
    text = "The previous state-of-the-art accuracy on ImageNet was 88.5%, and we reach 89.1%."
    assert 31 not in {f["pattern"] for f in patterns.scan(text)["findings"]}


def test_cited_attribution_is_allowed():
    text = r"Researchers suggest that pooling fails here \citep{ruxton2006}."
    assert 5 not in {f["pattern"] for f in patterns.scan(text)["findings"]}


class TestEmDashes:
    @pytest.mark.parametrize(
        "text",
        [
            "a \u2014 b",
            "a\u2014b",
            "word --- word",
            "word -- word",
            r"a \textemdash{} b",
            "a \u2013 b",
        ],
    )
    def test_counted(self, text):
        assert patterns.scan(text)["em_dashes"] == 1

    @pytest.mark.parametrize(
        "text",
        [
            "pages 10--20",
            "0.6--1.2 s",
            "a well-known x-ray",
            "\\emph{x} % a comment \u2014 here",
            "range 2010\u20132020",
        ],
    )
    def test_not_counted(self, text):
        assert patterns.scan(text)["em_dashes"] == 0


def test_density_and_line_numbers():
    text = "Clean first line here.\n\nWe delve into it.\n"
    result = patterns.scan(text)
    assert result["violations"] == 1
    assert result["findings"][0]["line"] == 3
    assert result["density_per_1000"] == pytest.approx(1000 / result["words"], rel=1e-3)
