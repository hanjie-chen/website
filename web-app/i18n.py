from __future__ import annotations

from typing import Optional

SUPPORTED_LANGUAGES = ("zh", "en")
DEFAULT_LANGUAGE = "zh"
LANG_COOKIE_NAME = "preferred_language"
HTML_LANG = {
    "zh": "zh-CN",
    "en": "en",
}
TRANSLATIONS = {
    "zh": {
        "language.zh": "中文",
        "language.en": "English",
        "nav.home": "首页",
        "nav.articles": "文章",
        "nav.about": "关于我",
        "footer.copy": "翰杰个人站",
    },
    "en": {
        "language.zh": "中文",
        "language.en": "English",
        "nav.home": "Home",
        "nav.articles": "Articles",
        "nav.about": "About Me",
        "footer.copy": "for hanjie site",
    },
}


def normalize_language(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    normalized = value.strip().lower().replace("_", "-")
    if normalized.startswith("zh"):
        return "zh"
    if normalized.startswith("en"):
        return "en"
    return None


def get_language_from_cookie(raw_cookie: Optional[str]) -> Optional[str]:
    return normalize_language(raw_cookie)


def get_language_from_header(raw_header: Optional[str]) -> Optional[str]:
    if not raw_header:
        return None

    candidates = []
    for position, item in enumerate(raw_header.split(",")):
        token = item.strip()
        if not token:
            continue

        parts = [part.strip() for part in token.split(";") if part.strip()]
        language_tag = parts[0]
        quality = 1.0

        for part in parts[1:]:
            if part.startswith("q="):
                try:
                    quality = float(part[2:])
                except ValueError:
                    quality = 0.0
                break

        normalized = normalize_language(language_tag)
        if normalized:
            candidates.append((quality, position, normalized))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (-item[0], item[1]))
    return candidates[0][2]


def resolve_preferred_language(
    cookie_value: Optional[str], accept_language_header: Optional[str]
) -> str:
    cookie_language = get_language_from_cookie(cookie_value)
    if cookie_language:
        return cookie_language

    header_language = get_language_from_header(accept_language_header)
    if header_language:
        return header_language

    return DEFAULT_LANGUAGE


def html_lang_code(lang: Optional[str]) -> str:
    normalized = normalize_language(lang) or DEFAULT_LANGUAGE
    return HTML_LANG.get(normalized, HTML_LANG[DEFAULT_LANGUAGE])


def get_language_from_path(path: Optional[str]) -> Optional[str]:
    if not path:
        return None

    first_segment = path.lstrip("/").split("/", 1)[0]
    if first_segment in SUPPORTED_LANGUAGES:
        return first_segment

    return None


def public_path(lang: str, suffix: str = "") -> str:
    normalized = normalize_language(lang) or DEFAULT_LANGUAGE
    suffix = suffix or ""
    if suffix and not suffix.startswith("/"):
        suffix = f"/{suffix}"
    if not suffix:
        return f"/{normalized}/"
    return f"/{normalized}{suffix}"


def alternate_language(lang: str) -> str:
    normalized = normalize_language(lang) or DEFAULT_LANGUAGE
    return "en" if normalized == "zh" else "zh"


def switch_language_path(path: str, target_lang: str) -> str:
    parts = [segment for segment in path.split("/") if segment]
    if parts and parts[0] in SUPPORTED_LANGUAGES:
        suffix = "/".join(parts[1:])
        return public_path(target_lang, suffix)
    return public_path(target_lang)


def translate(lang: Optional[str], key: str, fallback: Optional[str] = None) -> str:
    normalized = normalize_language(lang) or DEFAULT_LANGUAGE
    return TRANSLATIONS.get(normalized, {}).get(
        key, fallback if fallback is not None else key
    )
