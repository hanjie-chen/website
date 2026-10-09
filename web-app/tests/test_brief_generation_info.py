"""Receiving-side contract for public, allowlisted generation diagnostics."""

from copy import deepcopy
from datetime import date

import pytest
from test_daily_briefs import brief_payload, brief_provenance

import app as app_module
import daily_briefs
from daily_briefs import (
    BriefValidationError,
    load_brief,
    load_current_brief,
    store_brief,
    validate_brief_payload,
)


def generation_info():
    return {
        "materials": {
            "webpage": {
                "status": "success",
                "method": "jina",
                "origin": "original",
                "reason": "cloudflare_challenge",
            },
            "hn_post": {"status": "empty", "reason": "none"},
            "hn_comments": {"status": "success", "reason": "none"},
        },
        "summary_sources": ["web_body", "hn_comments"],
        "generation": {
            "status": "success",
            "model": "provider/model-v2",
            "reason": "none",
        },
    }


def payload_with_info(info):
    payload = brief_payload()
    payload["sections"]["ai"]["items"][0]["generation_info"] = info
    return payload


@pytest.fixture(autouse=True)
def fixed_brief_clock(monkeypatch):
    monkeypatch.setattr(daily_briefs, "_brief_today", lambda: date(2026, 7, 27))


@pytest.mark.parametrize(
    "sources", [None, [], ["hn_comments"], sorted(daily_briefs.SUMMARY_SOURCES)]
)
@pytest.mark.parametrize(
    "model", [None, "x", "a" * 128, "provider/model:v2@revision+test"]
)
def test_generation_info_survives_storage_and_public_api(
    client, monkeypatch, sources, model
):
    monkeypatch.setattr(app_module, "DAILY_BRIEF_PUBLISH_TOKEN", "secret-token")
    info = generation_info()
    info["summary_sources"] = sources
    info["generation"]["model"] = model
    payload = payload_with_info(info)
    response = client.post(
        "/internal/briefs",
        json=payload,
        headers={"X-DAILY-BRIEF-TOKEN": "secret-token"},
    )
    assert response.status_code == 201
    assert client.get("/api/briefs/latest").get_json() == payload
    assert client.get(f"/api/briefs/{payload['date']}").get_json() == payload
    assert load_current_brief(app_module.Daily_Briefs_Directory) == payload
    assert load_brief(app_module.Daily_Briefs_Directory, payload["date"]) == payload
    assert store_brief(app_module.Daily_Briefs_Directory, payload)[0] == "unchanged"


@pytest.mark.parametrize("with_provenance", [False, True])
@pytest.mark.parametrize("with_generation_info", [False, True])
def test_legacy_and_additive_item_fields_remain_compatible(
    with_provenance, with_generation_info
):
    payload = brief_payload()
    item = payload["sections"]["ai"]["items"][0]
    if with_provenance:
        item["provenance"] = brief_provenance()
    if with_generation_info:
        item["generation_info"] = generation_info()
    normalized = validate_brief_payload(payload)
    assert normalized == payload
    assert normalized is not payload
    if with_generation_info:
        assert (
            normalized["sections"]["ai"]["items"][0]["generation_info"]
            is not item["generation_info"]
        )


OBJECT_PATHS = [
    (),
    ("materials",),
    ("materials", "webpage"),
    ("materials", "hn_post"),
    ("materials", "hn_comments"),
    ("generation",),
]


def at_path(info, path):
    result = info
    for key in path:
        result = result[key]
    return result


@pytest.mark.parametrize("path", OBJECT_PATHS)
@pytest.mark.parametrize("change", ["extra", "missing", "null", "list"])
def test_rejects_unknown_missing_or_nonobject_nested_fields(path, change):
    info = generation_info()
    value = at_path(info, path)
    if change == "extra":
        value["private_log"] = "must not cross boundary"
    elif change == "missing":
        del value[next(iter(value))]
    else:
        replacement = None if change == "null" else []
        if path:
            at_path(info, path[:-1])[path[-1]] = replacement
        else:
            info = replacement
    with pytest.raises(BriefValidationError):
        validate_brief_payload(payload_with_info(info))


ENUM_PATHS = [
    ("materials", "webpage", "status"),
    ("materials", "webpage", "method"),
    ("materials", "webpage", "origin"),
    ("materials", "webpage", "reason"),
    ("materials", "hn_post", "status"),
    ("materials", "hn_post", "reason"),
    ("materials", "hn_comments", "status"),
    ("materials", "hn_comments", "reason"),
    ("generation", "status"),
    ("generation", "reason"),
]


@pytest.mark.parametrize("path", ENUM_PATHS)
@pytest.mark.parametrize("value", ["invalid", None, True, 1, [], {}])
def test_rejects_unallowlisted_codes_and_wrong_enum_types(path, value):
    info = generation_info()
    at_path(info, path[:-1])[path[-1]] = value
    with pytest.raises(BriefValidationError):
        validate_brief_payload(payload_with_info(info))


@pytest.mark.parametrize(
    "sources",
    [
        "web_body",
        {},
        True,
        ["web_body"] * 2,
        ["web_body"] * 5,
        [None],
        [[]],
        ["article"],
        [1],
    ],
)
def test_rejects_invalid_or_duplicate_summary_sources(sources):
    info = generation_info()
    info["summary_sources"] = sources
    with pytest.raises(BriefValidationError):
        validate_brief_payload(payload_with_info(info))


@pytest.mark.parametrize(
    "model",
    [
        "",
        "a" * 129,
        "-model",
        " model",
        "model ",
        "model\n",
        "模型",
        "model?key=secret",
        "model\\path",
        True,
        3,
        {},
        [],
    ],
)
def test_rejects_unsafe_or_overlong_model_identifier(model):
    info = generation_info()
    info["generation"]["model"] = model
    with pytest.raises(BriefValidationError):
        validate_brief_payload(payload_with_info(info))


def test_compatible_recovery_and_failure_codes_are_preserved():
    info = generation_info()
    info["materials"]["webpage"].update(
        status="success", method="wayback", origin="archived_copy", reason="http_error"
    )
    info["materials"]["hn_post"] = {"status": "not_attempted", "reason": "none"}
    info["materials"]["hn_comments"] = {"status": "failed", "reason": "network_error"}
    info["generation"] = {
        "status": "insufficient",
        "model": None,
        "reason": "no_materials",
    }
    info["summary_sources"] = None
    original = deepcopy(info)
    normalized = validate_brief_payload(payload_with_info(info))
    assert normalized["sections"]["ai"]["items"][0]["generation_info"] == original
    assert info == original


def test_invalid_generation_info_publish_leaves_no_stored_data(client, monkeypatch):
    monkeypatch.setattr(app_module, "DAILY_BRIEF_PUBLISH_TOKEN", "secret-token")
    info = generation_info()
    info["generation"]["reason"] = "private provider exception"
    response = client.post(
        "/internal/briefs",
        json=payload_with_info(info),
        headers={"X-DAILY-BRIEF-TOKEN": "secret-token"},
    )
    assert response.status_code == 400
    assert client.get("/api/briefs").get_json() == {"items": []}
    assert client.get("/api/briefs/latest").status_code == 404
