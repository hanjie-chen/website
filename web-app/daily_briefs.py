from __future__ import annotations

import fcntl
import json
import logging
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

LOGGER = logging.getLogger(__name__)
SCHEMA_VERSION = 2
CURRENT_POINTER_NAME = "current.json"
ARCHIVE_INDEX_NAME = "archive-index.json"
ARCHIVE_INDEX_VERSION = 1
RETENTION_DAYS = 14
BRIEF_TIMEZONE = ZoneInfo("Asia/Singapore")
SECTION_LIMITS = {"ai": 5, "non_ai_hot": 2}
ROOT_KEYS = {"schema_version", "date", "generated_at", "timezone", "sections"}
SECTION_KEYS = {"note", "items"}
ITEM_KEYS = {
    "hn_item_id",
    "title",
    "summary",
    "content_status",
    "why",
    "source_url",
    "discussion_url",
    "points",
    "comments",
}
OPTIONAL_ITEM_KEYS = {"provenance", "generation_info"}
PROVENANCE_KEYS = {
    "summary_basis",
    "retrieval_method",
    "retrieval_status",
    "material_origin",
    "fallback_reason",
}
SUMMARY_BASES = {
    "article",
    "source_and_comments",
    "hn_comments",
    "hn_post",
    "video_captions",
    "none",
    "unknown",
}
RETRIEVAL_METHODS = {
    "direct",
    "jina",
    "wayback",
    "github_readme",
    "github_raw",
    "youtube_caption",
    "story_text",
    "none",
    "unknown",
}
RETRIEVAL_STATUSES = {
    "success",
    "failed",
    "not_attempted",
    "not_needed",
    "unknown",
}
MATERIAL_ORIGINS = {
    "original",
    "archived_copy",
    "same_article",
    "syndicated_copy",
    "alternate_reporting",
    "unknown",
}
FALLBACK_REASONS = {
    "none",
    "challenge_page",
    "cloudflare_challenge",
    "datadome_challenge",
    "vercel_challenge",
    "empty_content",
    "network_timeout",
    "tls_issuer_unavailable",
    "source_material_insufficient",
    "unknown",
}
CONTENT_STATUSES = {"ok", "fetch_failed", "summary_failed", "title_only"}
MATERIAL_STATUSES = RETRIEVAL_STATUSES | {"empty"}
GENERATION_STATUSES = {"success", "insufficient", "failed", "not_attempted", "unknown"}
SUMMARY_SOURCES = {"web_metadata", "web_body", "hn_post", "hn_comments"}
GENERATION_REASONS = FALLBACK_REASONS | {
    "network_error",
    "http_error",
    "extraction_failed",
    "rate_limited",
    "authentication_failed",
    "provider_unavailable",
    "invalid_response",
    "no_materials",
}
MODEL_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,127}")
ARCHIVE_INDEX_KEYS = {"index_version", "briefs"}
ARCHIVE_ENTRY_KEYS = {
    "date",
    "generated_at",
    "ai_items",
    "non_ai_hot_items",
}


class BriefValidationError(ValueError):
    pass


def validate_brief_payload(payload) -> dict:
    if not isinstance(payload, dict) or set(payload) != ROOT_KEYS:
        raise BriefValidationError("payload must contain the exact schema v2 fields")
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
    content = (
        json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    with _store_lock(target_directory):
        today = _brief_today()
        if not _within_retention(normalized["date"], today):
            raise BriefValidationError(
                "date must be within the latest 14 calendar days (Asia/Singapore)"
            )
        archive_entries = _load_archive_entries(target_directory)
        target = target_directory / f"{normalized['date']}.json"
        try:
            existing = target.read_bytes()
        except FileNotFoundError:
            status = "created"
        else:
            status = "unchanged" if existing == content else "updated"

        if status != "unchanged":
            _atomic_write(target, content)

        archive_entries = _update_archive_entries(archive_entries, normalized)
        _prune_locked(target_directory, archive_entries, today)
    return status, normalized


def load_current_brief(directory) -> dict | None:
    root = Path(directory)
    current_date = _load_current_date(root)
    if current_date is None or not _within_retention(current_date, _brief_today()):
        return None
    return _load_valid_file(root / f"{current_date}.json")


def load_brief(directory, date_label: str) -> dict | None:
    try:
        canonical_date = _validate_date(date_label)
    except BriefValidationError:
        return None
    if not _within_retention(canonical_date, _brief_today()):
        return None
    return _load_valid_file(Path(directory) / f"{canonical_date}.json")


def load_brief_archive(directory) -> list[dict]:
    root = Path(directory)
    try:
        today = _brief_today()
        return [
            entry
            for entry in _load_archive_entries(root)
            if _within_retention(entry["date"], today)
        ]
    except BriefValidationError as exc:
        LOGGER.error(
            "component=daily_brief_store status=invalid_archive_index file=%s error=%s",
            root / ARCHIVE_INDEX_NAME,
            exc,
        )
        return []


def _brief_today() -> date:
    return datetime.now(BRIEF_TIMEZONE).date()


def _within_retention(date_label: str, today: date) -> bool:
    return (
        today - timedelta(days=RETENTION_DAYS - 1)
        <= date.fromisoformat(date_label)
        <= today
    )


def prune_briefs(directory) -> int:
    """Remove expired dated files and refresh metadata under the publishing lock."""
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    with _store_lock(root):
        return _prune_locked(root, _load_archive_entries(root), _brief_today())


def _prune_locked(directory: Path, entries: list[dict], today: date) -> int:
    retained = [entry for entry in entries if _within_retention(entry["date"], today)]
    # Publish metadata before deleting payloads. Readers also enforce retention,
    # so a delayed or interrupted cleanup cannot expose expired briefs.
    _write_archive_index(directory, retained)
    pointer_path = directory / CURRENT_POINTER_NAME
    if retained:
        pointer = (
            json.dumps({"date": retained[0]["date"]}, sort_keys=True) + "\n"
        ).encode("utf-8")
        if _load_current_date(directory) != retained[0]["date"]:
            _atomic_write(pointer_path, pointer)
    else:
        pointer_path.unlink(missing_ok=True)

    removed = 0
    # Scan dated filenames here to remove out-of-window orphan files as well.
    # Legacy future-dated payloads also fall outside the retention window. Public
    # reads continue to use the index/pointer without a directory scan.
    for path in directory.glob("*.json"):
        try:
            date_label = _validate_date(path.stem)
        except BriefValidationError:
            continue
        if not _within_retention(date_label, today) and path.is_file():
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def _load_current_date(directory: Path) -> str | None:
    pointer_path = directory / CURRENT_POINTER_NAME
    try:
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        if not isinstance(pointer, dict) or set(pointer) != {"date"}:
            raise BriefValidationError("current pointer must contain only date")
        return _validate_date(pointer["date"])
    except (OSError, json.JSONDecodeError, BriefValidationError) as exc:
        if not isinstance(exc, FileNotFoundError):
            LOGGER.error(
                "component=daily_brief_store status=invalid_current file=%s error=%s",
                pointer_path,
                exc,
            )
        return None


def _load_archive_entries(directory: Path) -> list[dict]:
    index_path = directory / ARCHIVE_INDEX_NAME
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as exc:
        raise BriefValidationError("archive index must contain valid JSON") from exc

    if not isinstance(payload, dict) or set(payload) != ARCHIVE_INDEX_KEYS:
        raise BriefValidationError("archive index must contain the exact fields")
    if payload["index_version"] != ARCHIVE_INDEX_VERSION:
        raise BriefValidationError("unsupported archive index version")
    raw_entries = payload["briefs"]
    if not isinstance(raw_entries, list):
        raise BriefValidationError("archive index briefs must be a list")

    entries = [_validate_archive_entry(entry) for entry in raw_entries]
    dates = [entry["date"] for entry in entries]
    if len(dates) != len(set(dates)):
        raise BriefValidationError("archive index dates must be unique")
    if dates != sorted(dates, reverse=True):
        raise BriefValidationError("archive index must be sorted newest first")
    return entries


def _validate_archive_entry(entry) -> dict:
    if not isinstance(entry, dict) or set(entry) != ARCHIVE_ENTRY_KEYS:
        raise BriefValidationError("archive entry must contain the exact fields")

    ai_items = _validate_count(entry["ai_items"], "archive ai_items")
    non_ai_hot_items = _validate_count(
        entry["non_ai_hot_items"], "archive non_ai_hot_items"
    )
    if ai_items > SECTION_LIMITS["ai"]:
        raise BriefValidationError("archive ai_items exceeds the section limit")
    if non_ai_hot_items > SECTION_LIMITS["non_ai_hot"]:
        raise BriefValidationError("archive non_ai_hot_items exceeds the section limit")

    return {
        "date": _validate_date(entry["date"]),
        "generated_at": _validate_generated_at(entry["generated_at"]),
        "ai_items": ai_items,
        "non_ai_hot_items": non_ai_hot_items,
    }


def _update_archive_entries(entries: list[dict], brief: dict) -> list[dict]:
    entry = {
        "date": brief["date"],
        "generated_at": brief["generated_at"],
        "ai_items": len(brief["sections"]["ai"]["items"]),
        "non_ai_hot_items": len(brief["sections"]["non_ai_hot"]["items"]),
    }
    by_date = {existing["date"]: existing for existing in entries}
    by_date[entry["date"]] = entry
    return [by_date[date_label] for date_label in sorted(by_date, reverse=True)]


def _write_archive_index(directory: Path, entries: list[dict]) -> None:
    content = (
        json.dumps(
            {"index_version": ARCHIVE_INDEX_VERSION, "briefs": entries},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    target = directory / ARCHIVE_INDEX_NAME
    try:
        if target.read_bytes() == content:
            return
    except FileNotFoundError:
        pass
    _atomic_write(target, content)


@contextmanager
def _store_lock(directory: Path):
    lock_path = directory / ".store.lock"
    with lock_path.open("a", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _atomic_write(target: Path, content: bytes) -> None:
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
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
    if not isinstance(item, dict) or not ITEM_KEYS <= set(item) <= (
        ITEM_KEYS | OPTIONAL_ITEM_KEYS
    ):
        raise BriefValidationError("item must contain the exact schema v2 fields")

    content_status = item["content_status"]
    if not isinstance(content_status, str) or content_status not in CONTENT_STATUSES:
        raise BriefValidationError("unsupported content_status")

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

    normalized = {
        "hn_item_id": hn_item_id,
        "title": _validate_text(item["title"], "title", 300),
        "summary": _validate_text(item["summary"], "summary", 4000),
        "content_status": content_status,
        "why": _validate_text(item["why"], "why", 1000),
        "source_url": source_url,
        "discussion_url": discussion_url,
        "points": _validate_count(item["points"], "points"),
        "comments": _validate_count(item["comments"], "comments"),
    }
    if "provenance" in item:
        normalized["provenance"] = _validate_provenance(item["provenance"])
    if "generation_info" in item:
        normalized["generation_info"] = _validate_generation_info(
            item["generation_info"]
        )
    return normalized


def _validate_provenance(provenance) -> dict:
    if not isinstance(provenance, dict) or set(provenance) != PROVENANCE_KEYS:
        raise BriefValidationError("provenance must contain the exact fields")

    fields = {
        "summary_basis": SUMMARY_BASES,
        "retrieval_method": RETRIEVAL_METHODS,
        "retrieval_status": RETRIEVAL_STATUSES,
        "material_origin": MATERIAL_ORIGINS,
        "fallback_reason": FALLBACK_REASONS,
    }
    normalized = {}
    for field, allowed_values in fields.items():
        value = provenance[field]
        if not isinstance(value, str) or value not in allowed_values:
            raise BriefValidationError(f"unsupported provenance {field}")
        normalized[field] = value
    return normalized


def _validate_generation_info(info) -> dict:
    info = _validate_exact_object(
        info, "generation_info", {"materials", "summary_sources", "generation"}
    )
    materials = _validate_exact_object(
        info["materials"],
        "generation_info.materials",
        {"webpage", "hn_post", "hn_comments"},
    )
    normalized_materials = {}
    for source in ("webpage", "hn_post", "hn_comments"):
        field = f"generation_info.materials.{source}"
        enums = {"status": MATERIAL_STATUSES, "reason": GENERATION_REASONS}
        if source == "webpage":
            enums.update(method=RETRIEVAL_METHODS, origin=MATERIAL_ORIGINS)
        material = _validate_exact_object(materials[source], field, set(enums))
        normalized_materials[source] = {
            key: _validate_enum(material[key], f"{field}.{key}", values)
            for key, values in enums.items()
        }

    sources = info["summary_sources"]
    if sources is not None:
        if not isinstance(sources, list) or len(sources) > len(SUMMARY_SOURCES):
            raise BriefValidationError(
                "generation_info.summary_sources must be null or a list of up to four sources"
            )
        sources = [
            _validate_enum(source, "generation_info.summary_sources", SUMMARY_SOURCES)
            for source in sources
        ]
        if len(sources) != len(set(sources)):
            raise BriefValidationError("generation_info.summary_sources must be unique")

    generation = _validate_exact_object(
        info["generation"], "generation_info.generation", {"status", "model", "reason"}
    )
    model = generation["model"]
    if model is not None and (
        not isinstance(model, str) or MODEL_IDENTIFIER.fullmatch(model) is None
    ):
        raise BriefValidationError(
            "generation_info.generation.model must be null or an ASCII model identifier of up to 128 characters"
        )
    return {
        "materials": normalized_materials,
        "summary_sources": sources,
        "generation": {
            "status": _validate_enum(
                generation["status"],
                "generation_info.generation.status",
                GENERATION_STATUSES,
            ),
            "model": model,
            "reason": _validate_enum(
                generation["reason"],
                "generation_info.generation.reason",
                GENERATION_REASONS,
            ),
        },
    }


def _validate_exact_object(value, field, keys) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise BriefValidationError(f"{field} must contain the exact fields")
    return value


def _validate_enum(value, field, allowed) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise BriefValidationError(f"unsupported {field}")
    return value


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
