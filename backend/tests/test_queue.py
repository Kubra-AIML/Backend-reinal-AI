import hashlib
import json

from app.config import settings
from app.services.engine_stub import pick_fixture_name

JPEG_HEAD = b"\xff\xd8\xff\xe0"

# TEST-ONLY policy with neutral lane names. It carries no clinical meaning.
POLICY = {
    "policy_version": "test-1",
    "lanes": [
        {"id": "lane_a", "label": "Lane A", "priority": 1},
        {"id": "lane_b", "priority": 2},
        {"id": "lane_c", "priority": 3},
    ],
    "rules": [
        {"lane": "lane_a", "when": {"referable": True}},
        {"lane": "lane_b", "when": {"quality_verdict": "unusable"}},
    ],
    "default_lane": "lane_c",
}


def payload_for(fixture_name):
    for i in range(2000):
        data = JPEG_HEAD + f"probe-{i}".encode()
        if pick_fixture_name(hashlib.sha256(data).hexdigest()) == fixture_name:
            return data
    raise AssertionError("no payload found")


def upload(client, data):
    return client.post("/api/cases", files={"file": ("eye.jpg", data, "image/jpeg")}).json()


def use_policy(monkeypatch, tmp_path, policy=POLICY):
    path = tmp_path / "lane_policy.json"
    path.write_text(json.dumps(policy), encoding="utf-8")
    monkeypatch.setattr(settings, "lane_policy_path", path)
    return path


def seed(client):
    for name in ("grade0", "grade3", "unusable_blurry", "non_fundus"):
        upload(client, payload_for(name))


def test_queue_without_policy_is_clear_404(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "lane_policy_path", tmp_path / "missing.json")
    for path in ("/api/queue", "/api/lanes"):
        r = client.get(path)
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "policy_not_ready"


def test_no_policy_file_is_shipped_with_the_backend():
    from app.config import BASE_DIR

    assert not (BASE_DIR / "policy" / "lane_policy.json").exists()


def test_lanes_are_served(client, monkeypatch, tmp_path):
    use_policy(monkeypatch, tmp_path)
    body = client.get("/api/lanes").json()
    assert body["policy_version"] == "test-1"
    assert [d["id"] for d in body["lanes"]] == ["lane_a", "lane_b", "lane_c"]


def test_sort_by_lane_priority(client, monkeypatch, tmp_path):
    seed(client)
    use_policy(monkeypatch, tmp_path)
    body = client.get("/api/queue").json()
    assert body["total"] == 4
    assert body["policy_version"] == "test-1"
    assert [i["lane"] for i in body["items"]] == ["lane_a", "lane_b", "lane_c", "lane_c"]
    assert body["items"][0]["lane_label"] == "Lane A"
    assert body["items"][0]["lane_priority"] == 1


def test_filter_by_lane(client, monkeypatch, tmp_path):
    seed(client)
    use_policy(monkeypatch, tmp_path)
    body = client.get("/api/queue?lane=lane_a").json()
    assert body["total"] == 1
    assert body["items"][0]["grade"] == 3
    assert client.get("/api/queue?lane=lane_c").json()["total"] == 2


def test_unknown_lane_is_422(client, monkeypatch, tmp_path):
    use_policy(monkeypatch, tmp_path)
    r = client.get("/api/queue?lane=made_up")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "unknown_lane"


def test_first_matching_rule_wins(client, monkeypatch, tmp_path):
    seed(client)
    reordered = {**POLICY, "rules": [POLICY["rules"][1], POLICY["rules"][0]]}
    use_policy(monkeypatch, tmp_path, reordered)
    # grade3 is referable and not unusable, so it still lands in lane_a
    assert client.get("/api/queue?lane=lane_a").json()["total"] == 1


def test_sort_newest_and_oldest(client, monkeypatch, tmp_path):
    refs = [upload(client, payload_for(n))["case_ref"] for n in ("grade0", "grade3", "unusable_blurry")]
    use_policy(monkeypatch, tmp_path)
    newest = [i["case_ref"] for i in client.get("/api/queue?sort=newest").json()["items"]]
    oldest = [i["case_ref"] for i in client.get("/api/queue?sort=oldest").json()["items"]]
    assert newest == list(reversed(refs))
    assert oldest == refs


def test_queue_paging(client, monkeypatch, tmp_path):
    seed(client)
    use_policy(monkeypatch, tmp_path)
    page = client.get("/api/queue?limit=2&offset=1").json()
    assert page["total"] == 4
    assert len(page["items"]) == 2


def test_queue_rejects_bad_sort(client, monkeypatch, tmp_path):
    use_policy(monkeypatch, tmp_path)
    assert client.get("/api/queue?sort=urgency").status_code == 422


def test_invalid_policy_gives_clear_error(client, monkeypatch, tmp_path):
    bad = {**POLICY, "rules": [{"lane": "ghost_lane", "when": {"referable": True}}]}
    use_policy(monkeypatch, tmp_path, bad)
    r = client.get("/api/queue")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "policy_invalid"


def test_rule_without_conditions_is_invalid(client, monkeypatch, tmp_path):
    bad = {**POLICY, "rules": [{"lane": "lane_a", "when": {}}]}
    use_policy(monkeypatch, tmp_path, bad)
    assert client.get("/api/queue").status_code == 500


def test_queue_never_changes_stored_results(client, monkeypatch, tmp_path):
    case = upload(client, payload_for("grade3"))
    use_policy(monkeypatch, tmp_path)
    client.get("/api/queue")
    assert client.get(f"/api/cases/{case['id']}").json()["result"] == case["result"]