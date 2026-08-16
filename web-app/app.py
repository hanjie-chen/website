import hmac
import os
from urllib.parse import quote, urlsplit, urlunsplit

from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from article_views import (
    article_html_path,
    article_view_model,
    build_article_toc,
    localized_articles,
)
from config import (
    DAILY_BRIEF_PUBLISH_TOKEN,
    IS_DEV,
    REIMPORT_ARTICLES_TOKEN,
    SQLALCHEMY_DATABASE_URI,
    Articles_Directory,
    Daily_Briefs_Directory,
    Rendered_Articles,
)
from daily_briefs import (
    BriefValidationError,
    load_brief,
    load_brief_archive,
    load_current_brief,
    store_brief,
)
from i18n import (
    DEFAULT_LANGUAGE,
    LANG_COOKIE_NAME,
    alternate_language,
    get_language_from_path,
    html_lang_code,
    resolve_preferred_language,
    switch_language_path,
    translate,
)
from import_articles_scripts import import_articles
from models import Article_Meta_Data, db
from navigation import build_article_shell_context, build_docs_context

# Flask route layer for the public site and the internal reindex endpoint.
app = Flask(__name__)
app.json.ensure_ascii = False

# configure the database uri
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["MAX_CONTENT_LENGTH"] = 128 * 1024
# Register rendered_articles as additional static folder
app.config["RENDERED_ARTICLES_FOLDER"] = Rendered_Articles

# 注册rendered-articles为静态文件夹
app.add_url_rule(
    "/rendered-articles/<path:filename>",
    endpoint="rendered-articles",
    view_func=lambda filename: send_from_directory(
        app.config["RENDERED_ARTICLES_FOLDER"], filename
    ),
)

# 初始化应用
db.init_app(app)


def _fetch_all_articles():
    return db.session.execute(db.select(Article_Meta_Data)).scalars().all()


def _fetch_api_articles():
    return (
        db.session.execute(db.select(Article_Meta_Data).order_by(Article_Meta_Data.id))
        .scalars()
        .all()
    )


def _localized_all_articles(lang: str):
    return localized_articles(Rendered_Articles, _fetch_all_articles(), lang)


def _serialize_article_summary(article: Article_Meta_Data):
    return {
        "id": article.id,
        "title": article.title,
        "category": article.category,
        "brief": article.brief_introduction,
    }


def _serialize_article_detail(article: Article_Meta_Data):
    return {
        "id": article.id,
        "title": article.title,
        "author": article.author,
        "instructor": article.instructor,
        "category": article.category,
        "brief": article.brief_introduction,
        "rollout_date": article.rollout_date.isoformat(),
        "ultimate_modified_date": article.ultimate_modified_date.isoformat(),
    }


def _asset_url(filename: str) -> str:
    static_folder = app.static_folder or ""
    asset_path = os.path.join(static_folder, filename)

    try:
        # Use the file mtime as a stable asset version.
        # The value only changes when the file on disk changes, so templates keep
        # emitting the same URL until a CSS/JS/image update actually happens.
        version = int(os.path.getmtime(asset_path))
    except OSError:
        return url_for("static", filename=filename)

    return url_for("static", filename=filename, v=version)


def _safe_redirect_target(next_path: str | None, fallback_path: str) -> str:
    if not next_path:
        return fallback_path

    candidate = next_path.strip()
    if not candidate:
        return fallback_path

    parsed = urlsplit(candidate)
    if parsed.scheme or parsed.netloc:
        return fallback_path

    if not parsed.path.startswith("/") or parsed.path.startswith("//"):
        return fallback_path

    return urlunsplit(("", "", parsed.path, parsed.query, parsed.fragment))


def _source_hostname(source_url: str) -> str:
    """Return a compact display hostname for an already validated source URL."""
    try:
        hostname = urlsplit(source_url).hostname or ""
    except ValueError:
        return ""
    return hostname.lower().removeprefix("www.")


OFFICIAL_SOURCE_LABELS = {
    "claude.com": "Claude 官方",
}


def _source_display_name(source_url: str) -> str:
    """Return an allowlisted official label or the compact source hostname."""
    hostname = _source_hostname(source_url)
    return OFFICIAL_SOURCE_LABELS.get(hostname, hostname)


@app.context_processor
def inject_template_helpers():
    # Keep template logic shallow: routes decide the language namespace, and
    # templates consume shared helpers for translated UI copy and asset URLs.
    current_lang = None
    if request.view_args:
        current_lang = request.view_args.get("lang")

    current_lang = current_lang or get_language_from_path(request.path)
    if current_lang is None:
        current_lang = DEFAULT_LANGUAGE
    target_lang = alternate_language(current_lang)
    switch_path = switch_language_path(request.path, target_lang)

    return {
        "asset_url": _asset_url,
        "current_lang": current_lang,
        "alternate_lang": target_lang,
        "html_lang": html_lang_code(current_lang),
        "switch_lang_url": f"/set-language/{target_lang}?next={quote(switch_path, safe='/')}",
        "source_display_name": _source_display_name,
        "t": lambda key, fallback=None: translate(current_lang, key, fallback=fallback),
    }


def _require_supported_language(lang: str) -> str:
    canonical_language = get_language_from_path(lang)
    if canonical_language is None:
        abort(404)
    return canonical_language


@app.route("/")
def root_index():
    preferred_language = resolve_preferred_language(
        request.cookies.get(LANG_COOKIE_NAME),
        request.headers.get("Accept-Language"),
    )
    return redirect(url_for("index", lang=preferred_language), code=302)


@app.route("/<lang>")
def index_without_trailing_slash(lang):
    canonical_language = _require_supported_language(lang)
    return redirect(url_for("index", lang=canonical_language), code=302)


@app.route("/<lang>/")
def index(lang):
    current_lang = _require_supported_language(lang)
    return render_template(
        "index.html",
        current_lang=current_lang,
        current_brief=load_current_brief(Daily_Briefs_Directory),
    )


@app.route("/set-language/<lang>")
def set_language(lang):
    current_lang = _require_supported_language(lang)
    fallback_path = url_for("index", lang=current_lang)
    next_path = _safe_redirect_target(request.args.get("next"), fallback_path)
    response = redirect(next_path, code=302)
    response.set_cookie(
        LANG_COOKIE_NAME,
        current_lang,
        max_age=60 * 60 * 24 * 365,
        samesite="Lax",
    )
    return response


@app.route("/<lang>/articles")
def article_index(lang):
    current_lang = _require_supported_language(lang)
    articles = _localized_all_articles(current_lang)
    docs_context = build_docs_context(articles, current_category="", lang=current_lang)
    return render_template("article_index.html", **docs_context)


@app.route("/<lang>/articles/category/<path:category_path>")
def article_category(lang, category_path):
    current_lang = _require_supported_language(lang)
    articles = _localized_all_articles(current_lang)
    docs_context = build_docs_context(
        articles, current_category=category_path, lang=current_lang
    )

    if category_path and docs_context["current_node"].path != category_path:
        abort(404)

    return render_template("article_index.html", **docs_context)


@app.route("/<lang>/about")
def about_me(lang):
    current_lang = _require_supported_language(lang)
    return render_template("about_me.html", current_lang=current_lang)


@app.route("/<lang>/briefs")
def brief_index(lang):
    current_lang = _require_supported_language(lang)
    return render_template(
        "brief_index.html",
        current_lang=current_lang,
        briefs=load_brief_archive(Daily_Briefs_Directory),
    )


@app.route("/<lang>/briefs/<brief_date>")
def brief_detail(lang, brief_date):
    current_lang = _require_supported_language(lang)
    brief = load_brief(Daily_Briefs_Directory, brief_date)
    if brief is None:
        abort(404)
    return render_template(
        "brief_detail.html",
        current_lang=current_lang,
        brief=brief,
    )


@app.route("/api/articles")
def api_articles():
    return {
        "items": [
            _serialize_article_summary(article) for article in _fetch_api_articles()
        ]
    }


@app.route("/api/articles/<int:article_id>")
def api_article_detail(article_id):
    article = db.session.execute(
        db.select(Article_Meta_Data).where(Article_Meta_Data.id == article_id)
    ).scalar()

    if not article:
        abort(404)

    return _serialize_article_detail(article)


# deal with 404 error
@app.errorhandler(404)
def page_not_found(error_info):  # 接受异常对象作为参数
    # print(f"Error: {error_info}, Description: {error_info.description}, URL: {request.url}") # 打印错误信息到控制台
    return render_template(
        "404.html", error=error_info, url=request.url
    ), 404  # 将错误信息传递给模板


@app.route("/<lang>/articles/<int:article_id>")
def view_article(lang, article_id):
    current_lang = _require_supported_language(lang)
    canonical_article = db.session.execute(
        db.select(Article_Meta_Data).where(Article_Meta_Data.id == article_id)
    ).scalar()

    if not canonical_article:
        abort(404)

    article = article_view_model(Rendered_Articles, canonical_article, current_lang)
    html_path = article_html_path(Rendered_Articles, canonical_article, current_lang)

    try:
        with open(html_path, "r", encoding="utf-8") as f:
            article_content = f.read()
    except FileNotFoundError:
        abort(404)

    article_content, toc_items = build_article_toc(article_content)
    shell_context = build_article_shell_context(
        _localized_all_articles(current_lang),
        article,
        lang=current_lang,
    )

    # 返回模板，使用相对路径
    return render_template(
        "article_details.html",
        article=article,
        article_content=article_content,
        toc_items=toc_items,
        current_article_id=article.id,
        **shell_context,
    )


if IS_DEV:
    # 在路由函数之前添加这些调试代码
    @app.route("/debug")
    def debug_info():
        # 1. 检查数据库中的文章
        articles = db.session.execute(db.select(Article_Meta_Data)).scalars().all()
        db_info = "Database Articles:\n"
        for article in articles:
            db_info += f"ID: {article.id}, Title: {article.title}, Category: {article.category}, Cover_image_url: {article.cover_image_url}\n"

        # 2. 检查rendered_articles目录
        rendered_path = app.config["RENDERED_ARTICLES_FOLDER"]
        dir_info = f"\nRendered Articles Directory ({rendered_path}):\n"
        if os.path.exists(rendered_path):
            for root, dirs, files in os.walk(rendered_path):
                dir_info += f"Directory: {root}\n"
                for file in files:
                    dir_info += f"  File: {file}\n"
        else:
            dir_info += "Directory does not exist!\n"

        # 3. 显示应用
        config_info = "\nApp Configuration:\n"
        config_info += (
            f"RENDERED_ARTICLES_FOLDER: {app.config['RENDERED_ARTICLES_FOLDER']}\n"
        )

        return f"<pre>{db_info}\n{dir_info}\n{config_info}</pre>"


@app.route("/internal/reindex", methods=["POST"])
def reindex_articles():
    # Only the sync pipeline should hit this endpoint; public callers should
    # not be able to force a re-import of the article source tree.
    if not REIMPORT_ARTICLES_TOKEN:
        abort(404)

    request_token = request.headers.get("X-REIMPORT-ARTICLES-TOKEN", "")
    if request_token != REIMPORT_ARTICLES_TOKEN:
        abort(403)

    with app.app_context():
        import_articles(Articles_Directory, db)
    return {"status": "ok"}


@app.route("/internal/briefs", methods=["POST"])
def publish_brief():
    if not DAILY_BRIEF_PUBLISH_TOKEN:
        abort(404)

    request_token = request.headers.get("X-DAILY-BRIEF-TOKEN", "")
    if not hmac.compare_digest(request_token, DAILY_BRIEF_PUBLISH_TOKEN):
        abort(403)
    if not request.is_json:
        return {"error": "Content-Type must be application/json"}, 415

    payload = request.get_json(silent=True)
    if payload is None:
        return {"error": "request body must contain valid JSON"}, 400
    try:
        status, normalized = store_brief(Daily_Briefs_Directory, payload)
    except BriefValidationError as exc:
        return {"error": str(exc)}, 400

    response_code = 201 if status == "created" else 200
    return {"status": status, "date": normalized["date"]}, response_code
