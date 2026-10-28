import json

import pytest
from pydantic import ValidationError

from app.config import BASE_DIR, settings
from app.schemas.result import AnalysisResult
from app.services.fixtures import FIXTURE_NAMES, load_fixture


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_fixture_is_valid_and_labelled_stub(name):
    r = load_fixture(name)
    assert r.engine == "stub"
    assert r.notice and "STUB" in r.notice
    assert r.schema_version == settings.schema_version


@pytest.mark.parametrize("name", ["unusable_blurry", "non_fundus"])
def test_unusable_fixtures_have_no_prediction(name):
    r = load_fixture(name)
    assert r.quality.verdict != "usable"
    assert r.prediction is None
    assert r.quality.reason_codes
    assert r.review_flags


def test_one_fixture_per_grade():
    grades = [load_fixture(f"grade{i}").prediction.grade for i in range(5)]
    assert grades == [0, 1, 2, 3, 4]


def test_uncalibrated_scores_are_labelled():
    for i in range(5):
        assert load_fixture(f"grade{i}").prediction.calibration_status == "uncalibrated"


def _valid_data():
    return load_fixture("grade2").model_dump(mode="json")


def test_rejects_prediction_on_unusable():
    data = _valid_data()
    data["quality"]["verdict"] = "unusable"
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(data)


def test_rejects_usable_without_prediction():
    data = _valid_data()
    data["prediction"] = None
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(data)


def test_rejects_bad_grade():
    data = _valid_data()
    data["prediction"]["grade"] = 5
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(data)


def test_rejects_scores_not_summing_to_one():
    data = _valid_data()
    data["prediction"]["class_scores"] = [0.5, 0.5, 0.5, 0.5, 0.5]
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(data)


def test_rejects_stub_without_notice():
    data = _valid_data()
    data["notice"] = None
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(data)


def test_unknown_fixture_raises():
    with pytest.raises(KeyError):
        load_fixture("does_not_exist")


def test_exported_json_schema_is_up_to_date():
    path = BASE_DIR / "contracts" / "analysis_result.schema.json"
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == AnalysisResult.model_json_schema()