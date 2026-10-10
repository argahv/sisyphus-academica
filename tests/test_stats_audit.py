"""Tests for the statistical audit: p-value recomputation and consistency checks."""

import pytest

from sisyphus.tools import stats_audit as sa


class TestDistributions:
    @pytest.mark.parametrize(
        "test,stat,df1,df2,expected",
        [
            ("t", 2.228, 10, None, 0.05),
            ("t", 1.96, 1e6, None, 0.05),
            ("z", 1.96, None, None, 0.05),
            ("F", 3.204, 2, 45, 0.05),
            ("chi2", 3.841, 1, None, 0.05),
            ("chi2", 18.307, 10, None, 0.05),
            ("r", 0.2732, 50, None, 0.05),
        ],
    )
    def test_known_critical_values(self, test, stat, df1, df2, expected):
        assert sa.p_value(test, stat, df1, df2) == pytest.approx(expected, abs=0.0015)


def _checks(text, analysis=None):
    return [i["check"] for i in sa.audit_text(text, analysis)["issues"] if i["level"] == "error"]


class TestAudit:
    def test_consistent_t_test_passes(self):
        assert sa.audit_text("The groups differed, t(28) = 2.20, p = .036.")["passed"]

    def test_inconsistent_t_test_flagged(self):
        assert "p_mismatch" in _checks("The groups differed, t(28) = 1.20, p = .036.")

    def test_p_less_than_bound(self):
        assert sa.audit_text("Large effect, t(98) = 5.10, p < .001.")["passed"]
        assert "p_mismatch" in _checks("Small effect, t(98) = 1.10, p < .001.")

    def test_f_and_chi2_from_latex(self):
        ok = r"A main effect, $F(2, 45) = 5.10$, $p = 0.010$, and $\chi^2(1) = 9.87$, $p < 0.01$."
        assert sa.audit_text(ok)["passed"]

    def test_mcnemar_without_df_assumes_one(self):
        assert sa.audit_text(r"McNemar's test gave $\chi^2 = 9.87$, $p < 0.01$.")["passed"]

    def test_one_tailed_halves_p(self):
        assert sa.audit_text("One-tailed test, t(28) = 1.80, p = .041.")["passed"]

    def test_significant_with_large_p_flagged(self):
        assert "significance_claim" in _checks("The difference was significant (p = .08).")

    def test_not_significant_is_fine(self):
        assert "significance_claim" not in _checks("The difference was not significant (p = .08).")

    def test_impossible_values(self):
        assert "impossible_value" in _checks("We found p = 1.30 for the test.")
        assert "impossible_value" in _checks("The correlation r(40) = 1.20, p < .001 was strong.")
        assert "impossible_value" in _checks("The test gave p = 0 exactly.")

    def test_estimate_outside_ci(self):
        assert "estimate_outside_ci" in _checks("Accuracy was 94.3% (95% CI [95.0%, 96.0%]).")
        assert sa.audit_text("Accuracy was 94.3% (95% CI [92.6%, 96.0%]).")["passed"]

    def test_bonferroni_arithmetic(self):
        bad = "We used a Bonferroni correction for 12 comparisons, adjusted alpha = 0.01."
        assert "bonferroni_arithmetic" in _checks(bad)
        good = "We used a Bonferroni correction for 12 comparisons, adjusted alpha = 0.0042."
        assert "bonferroni_arithmetic" not in _checks(good)

    def test_multiple_comparisons_without_correction(self):
        text = " ".join(f"Test {i} gave t(20) = 2.90, p = .009." for i in range(5))
        assert "multiple_comparisons" in _checks(text)
        assert "multiple_comparisons" not in _checks(text + " We applied the Holm correction.")

    def test_p_hacking_signal_is_a_warning(self):
        result = sa.audit_text("The effect held, t(12) = 2.20, p = .048.")
        assert result["passed"]
        assert any(i["check"] == "p_hacking_signal" for i in result["issues"])

    def test_abstract_numbers_must_appear_in_body(self):
        src = (
            "\\begin{abstract}Accuracy rose by 12.5 points.\\end{abstract}\n"
            "\\section{Results}\nAccuracy rose by 15.3 points.\n"
        )
        assert "summary_number_not_in_body" in _checks(src)
        fixed = src.replace("12.5", "15.3")
        assert "summary_number_not_in_body" not in _checks(fixed)

    def test_rounded_summary_numbers_match(self):
        src = (
            "\\begin{abstract}Error fell by 73%.\\end{abstract}\n"
            "\\section{Results}\nError fell by 72.6%.\n"
        )
        assert "summary_number_not_in_body" not in _checks(src)

    def test_statistics_must_trace_to_analysis(self):
        text = "The groups differed, t(28) = 2.20, p = .036."
        assert "untraceable" in _checks(text, {"tests": [{"statistic": 3.1, "p_value": 0.004}]})
        assert "untraceable" not in _checks(
            text, {"tests": [{"statistic": 2.2031, "p_value": 0.036}]}
        )


def test_demo_paper_passes(demo_run):
    from sisyphus.tools import workspace

    analysis = workspace.load_json(demo_run / "analysis" / "statistics.json")
    result = sa.audit_text(workspace.paper_source(demo_run), analysis)
    assert result["passed"], result["issues"]
    assert result["tests_found"] == 2
