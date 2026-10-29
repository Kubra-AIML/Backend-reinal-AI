from ..config import settings
from ..errors import ApiError
from ..schemas.lanes import LanePolicy, RuleWhen
from ..schemas.result import AnalysisResult


def load_policy() -> LanePolicy:
    """Read-only. The backend never invents lane rules: they come from the policy file."""
    path = settings.lane_policy_path
    if not path.is_file():
        raise ApiError(404, "policy_not_ready", "The lane policy file has not been provided yet")
    try:
        return LanePolicy.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ApiError(500, "policy_invalid", "The lane policy file is not valid")


def _matches(when: RuleWhen, result: AnalysisResult) -> bool:
    pred = result.prediction
    if when.quality_verdict is not None and result.quality.verdict != when.quality_verdict:
        return False
    if when.grade is not None and (pred is None or pred.grade != when.grade):
        return False
    if when.referable is not None and (pred is None or pred.referable != when.referable):
        return False
    if when.review_flag is not None and when.review_flag not in result.review_flags:
        return False
    return True


def lane_for(result: AnalysisResult, policy: LanePolicy) -> str:
    """First matching rule wins; otherwise the policy's default lane."""
    for rule in policy.rules:
        if _matches(rule.when, result):
            return rule.lane
    return policy.default_lane