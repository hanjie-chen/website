from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

LOGGER = logging.getLogger(__name__)
SCHEMA_VERSION = 1
SECTION_LIMITS = {"ai": 5, "non_ai_hot": 2}
ROOT_KEYS = {"schema_version", "date", "generated_at", "timezone", "sections"}
SECTION_KEYS = {"note", "items"}
ITEM_KEYS = {
    "hn_item_id",
    "title",
    "summary",
    "why",
    "source_url",
    "discussion_url",
    "points",
    "comments",
}


class BriefValidationError(ValueError):
    pass


def validate_brief_payload(payload) -> dict:
    if not isinstance(payload, dict) or set(payload) != ROOT_KEYS:
        raise BriefValidationError("payload must contain the exact schema v1 fields")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise BriefValidationError("unsupported schema_version")

    date_label = _validate_date(payload["date"])
    generated_at = _validate_generated_at(payload["generated_at"])
    if payload["timezone"] != "Asia/Singapore":
        raise BriefValidationError("timezone must be Asia/Singapore")

    raw_sections = payload["sections"]
    if not isinstance(raw_sections, dict) or set(raw_sections) != set(SECTION_LIMITS):
        raise BriefValidationError("sections must contain ai and non_ai_hot")

    sections = {}
    total_items = 0
    for section_name, item_limit in SECTION_LIMITS.items():
        section = raw_sections[section_name]
        if not isinstance(section, dict) or set(section) != SECTION_KEYS:
            raise BriefValidationError(f"invalid {section_name} section")
        note = _validate_text(
            section["note"], f"{section_name}.note", 500, allow_empty=True
        )
        items = section["items"]
        if not isinstance(items, list) or len(items) > item_limit:
            raise BriefValidationError(f"{section_name} contains too many items")
        normalized_items = [_validate_item(item) for item in items]
        total_items += len(normalized_items)
        sections[section_name] = {"note": note, "items": normalized_items}

    if total_items == 0:
        raise BriefValidationError("brief must contain at least one item")

    return {
        "schema_version": SCHEMA_VERSION,
        "date": date_label,
        "generated_at": generated_at,
        "timezone": "Asia/Singapore",
        "sections": sections,
    }


def store_brief(directory, payload) -> tuple[str, dict]:
    normalized = validate_brief_payload(payload)
    target_directory = Path(directory)
    target_directory.mkdir(parents=True, exist_ok=True)
    target = target_directory / f"{normalized['date']}.json"
    content = (
        json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    try:
        existing = target.read_bytes()
    except FileNotFoundError:
        status = "created"
    else:
        if existing == content:
            return "unchanged", normalized
        status = "updated"

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target_directory,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, target)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return status, normalized


def load_brief(directory, date_label: str) -> dict | None:
    try:
        canonical_date = _validate_date(date_label)
    except BriefValidationError:
        return None
    path = Path(directory) / f"{canonical_date}.json"
    return _load_valid_file(path)


def list_briefs(directory) -> list[dict]:
    root = Path(directory)
    if not root.is_dir():
        return []

    briefs = []
    for path in sorted(root.glob("*.json"), reverse=True):
        try:
            date.fromisoformat(path.stem)
        except ValueError:
            continue
        payload = _load_valid_file(path)
        if payload is not None:
            briefs.append(payload)
    return briefs


def _load_valid_file(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        normalized = validate_brief_payload(payload)
    except (OSError, json.JSONDecodeError, BriefValidationError) as exc:
        LOGGER.error(
            "component=daily_brief_store status=invalid file=%s error=%s", path, exc
        )
        return None
    if normalized["date"] != path.stem:
        LOGGER.error(
            "component=daily_brief_store status=date_mismatch file=%s payload_date=%s",
            path,
            normalized["date"],
        )
        return None
    return normalized


def _validate_item(item) -> dict:
    if not isinstance(item, dict) or set(item) != ITEM_KEYS:
        raise BriefValidationError("item must contain the exact schema v1 fields")

    hn_item_id = _validate_text(item["hn_item_id"], "hn_item_id", 32)
    if not hn_item_id.isdigit():
        raise BriefValidationError("hn_item_id must contain only digits")
    source_url = _validate_http_url(item["source_url"], "source_url")
    discussion_url = _validate_http_url(item["discussion_url"], "discussion_url")
    discussion = urlsplit(discussion_url)
    discussion_ids = parse_qs(discussion.query).get("id", [])
    if (
        discussion.hostname != "news.ycombinator.com"
        or discussion.path != "/item"
        or discussion_ids != [hn_item_id]
    ):
        raise BriefValidationError("discussion_url must match hn_item_id")

    return {
        "hn_item_id": hn_item_id,
        "title": _validate_text(item["title"], "title", 300),
        "summary": _validate_text(item["summary"], "summary", 4000),
        "why": _validate_text(item["why"], "why", 1000),
        "source_url": source_url,
        "discussion_url": discussion_url,
        "points": _validate_count(item["points"], "points"),
        "comments": _validate_count(item["comments"], "comments"),
    }


def _validate_date(value) -> str:
    if not isinstance(value, str):
        raise BriefValidationError("date must be a string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise BriefValidationError("date must use YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise BriefValidationError("date must use canonical YYYY-MM-DD")
    return value


def _validate_generated_at(value) -> str:
    if not isinstance(value, str) or len(value) > 64:
        raise BriefValidationError("generated_at must be an RFC3339 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise BriefValidationError("generated_at must be an RFC3339 string") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise BriefValidationError("generated_at must include a timezone offset")
    return value


def _validate_text(value, field, max_length, allow_empty=False) -> str:
    if not isinstance(value, str):
        raise BriefValidationError(f"{field} must be a string")
    cleaned = value.strip()
    if not allow_empty and not cleaned:
        raise BriefValidationError(f"{field} must not be empty")
    if len(cleaned) > max_length:
        raise BriefValidationError(f"{field} is too long")
    return cleaned


def _validate_http_url(value, field) -> str:
    url = _validate_text(value, field, 2048)
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise BriefValidationError(f"{field} must be an HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise BriefValidationError(f"{field} must not contain credentials")
    return url


def _validate_count(value, field) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BriefValidationError(f"{field} must be an integer")
    if value < 0 or value > 10_000_000:
        raise BriefValidationError(f"{field} is out of range")
    return value
