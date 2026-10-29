import json

import pytest
from jsonschema import Draft202012Validator

from app.config import BASE_DIR
from app.main import app
from app.schemas.errors import ErrorResponse
from app.services.fixtures import FIXTURE_DIR, FIXTURE_NAMES

CONTRACT_DIR = BASE_DIR / "contracts"

REQUIRED_PATHS = [
    "/api/health",
    "/api/meta",
    "/api/cases",
    "/api/cases/{case_ref}",
    "/api/cases/{case_ref}/reviews",
    "/api/reason-codes",
    "/api/evidence",
    "/api/evidence/{name}",
]


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_openapi_json_is_up_to_date():
    on_disk = _load(CONTRACT_DIR / "openapi.json")
    current = json.loads(json.dumps(app.openapi()))
    assert on_disk == current, "contracts/openapi.json is stale. Run: python scripts/export_openapi.py"


def test_openapi_contains_required_endpoints():
    paths = _load(CONTRACT_DIR / "openapi.json")["paths"]
    missing = [p for p in REQUIRED_PATHS if p not in paths]
    assert not missing, f"missing from OpenAPI: {missing}"


def test_openapi_has_request_examples():
    schemas = _load(CONTRACT_DIR / "openapi.json")["components"]["schemas"]
    review_schemas = [v for k, v in schemas.items() if k.startswith("ReviewCreate")]
    assert review_schemas and review_schemas[0].get("examples")


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_fixture_validates_against_exported_json_schema(name):
    schema = _load(CONTRACT_DIR / "analysis_result.schema.json")
    instance = _load(FIXTURE_DIR / f"{name}.json")
    Draft202012Validator(schema).validate(instance)


def test_error_json_schema_is_up_to_date():
    on_disk = _load(CONTRACT_DIR / "error_response.schema.json")
    assert on_disk == ErrorResponse.model_json_schema(), (
        "error_response.schema.json is stale. Run: python scripts/generate_contract_files.py"
    )


def test_health_reports_database_ok_after_migration(client):
    body = client.get("/api/health").json()
    assert body["api"] == "ok"
    assert body["database"] == "ok"
    assert body["engine"]["mode"] == "stub"