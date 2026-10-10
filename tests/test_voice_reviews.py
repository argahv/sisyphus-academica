"""Tests for voice calibration and the 10-reviewer gate."""

import json

import pytest

from sisyphus.tools import reviews, voice

SAMPLE = (
    "Most replication failures we examined had a mundane cause. Analysts ran the test the software "
    "offered first, and that test assumed something the data did not satisfy. "
    "We do not think this is "
    "carelessness. Default settings carry authority. "
) * 6


class TestVoice:
    def test_profile_has_features_and_guidance(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text(SAMPLE)
        profile = voice.build_profile([f])
        assert profile["sample_words"] > 150
        assert set(voice.TOLERANCES) <= set(profile["features"])
        assert any("Sentences average" in g for g in profile["guidance"])

    def test_short_sample_rejected(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text("Too short.")
        with pytest.raises(ValueError):
            voice.build_profile([f])

    def test_same_style_is_consistent(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text(SAMPLE)
        assert voice.compare(SAMPLE, voice.build_profile([f]))["consistent"]

    def test_different_style_drifts(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text(SAMPLE)
        long_winded = (
            "The comprehensive methodological considerations, which encompass numerous "
            "heterogeneous "
            "computational, statistical, epistemological and organizational dimensions; "
            "furthermore, "
            "notwithstanding considerable interdisciplinary disagreements, were systematically "
            "investigated, documented, reconsidered, and subsequently operationalized. "
        ) * 6
        result = voice.compare(long_winded, voice.build_profile([f]))
        assert not result["consistent"]
        assert any(d["feature"] == "sentence_length_mean" for d in result["deviations"])

    def test_sample_files_from_dir(self, tmp_path):
        (tmp_path / "a.txt").write_text("x")
        (tmp_path / "README.md").write_text("x")
        assert [p.name for p in voice.sample_files(tmp_path)] == ["a.txt"]


def write_reviews(directory, **overrides):
    directory.mkdir(parents=True, exist_ok=True)
    for persona in reviews.PERSONAS:
        review = {
            "reviewer": persona,
            "score": 7,
            "strengths": ["s"],
            "weaknesses": ["w"],
            "must_fix": [],
            "recommendation": "accept",
        }
        review.update(overrides.get(persona, {}))
        (directory / f"{persona}.json").write_text(json.dumps(review))


class TestReviewGate:
    def test_all_ten_accept(self, tmp_path):
        write_reviews(tmp_path)
        result = reviews.evaluate(tmp_path)
        assert result["passed"] and result["accepted"] == "10/10"

    def test_one_missing_fails(self, tmp_path):
        write_reviews(tmp_path)
        (tmp_path / "dreamer.json").unlink()
        result = reviews.evaluate(tmp_path)
        assert not result["passed"] and result["reviewers"]["dreamer"]["status"] == "missing"

    def test_must_fix_blocks_and_builds_revision_plan(self, tmp_path):
        item = {
            "location": "Table 2",
            "issue": "Old baseline",
            "required_change": "Add the 2023 baseline",
        }
        write_reviews(tmp_path, competitor={"recommendation": "minor_revision", "must_fix": [item]})
        result = reviews.evaluate(tmp_path)
        assert not result["passed"]
        assert result["revision_plan"] == [{"reviewer": "competitor", **item}]

    def test_low_score_or_reject_fails(self, tmp_path):
        write_reviews(tmp_path, skeptic={"score": 5}, historian={"recommendation": "Reject"})
        result = reviews.evaluate(tmp_path)
        assert result["reviewers"]["skeptic"]["status"] == "not_accepted"
        assert result["reviewers"]["historian"]["status"] == "not_accepted"

    def test_invalid_schema(self, tmp_path):
        write_reviews(
            tmp_path, theorist={"score": "high", "recommendation": "maybe", "must_fix": "none"}
        )
        problems = reviews.evaluate(tmp_path)["reviewers"]["theorist"]["problems"]
        assert len(problems) == 3

    def test_recommendation_aliases(self):
        assert reviews.normalize_recommendation("Accept with minor revisions") == "minor_revision"
        assert reviews.normalize_recommendation("major revision") == "major_revision"
