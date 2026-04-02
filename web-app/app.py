from flask import Flask, render_template, request, send_from_directory, abort, url_for
from models import db, Article_Meta_Data
from import_articles_scripts import import_articles
import os
import re
from bs4 import BeautifulSoup
from navigation import build_docs_context, build_article_shell_context

from config import (
    Articles_Directory,
    Rendered_Articles,
    IS_DEV,
    SQLALCHEMY_DATABASE_URI,
    REIMPORT_ARTICLES_TOKEN,
)


app = Flask(__name__)
app.json.ensure_ascii = False

# configure the database uri
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
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


def _slugify_heading(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    slug = re.sub(r"[-\s]+", "-", slug, flags=re.UNICODE)
    return slug or "section"


def _build_article_toc(article_content: str):
    soup = BeautifulSoup(article_content, "html.parser")
    toc_items = []
    slug_counts = {}
    current_h1 = None
    current_h2 = None

    for heading in soup.find_all(["h1", "h2", "h3"]):
        heading_text = heading.get_text(" ", strip=True)
        if not heading_text:
            continue

        base_slug = _slugify_heading(heading_text)
        slug_counts[base_slug] = slug_counts.get(base_slug, 0) + 1
        heading_id = (
            base_slug
            if slug_counts[base_slug] == 1
            else f"{base_slug}-{slug_counts[base_slug]}"
        )

        heading["id"] = heading_id
        toc_item = {
            "id": heading_id,
            "text": heading_text,
            "level": int(heading.name[1]),
            "children": [],
        }

        # Build a shallow page outline: h1 owns following h2 items, and h2 owns h3.
        if toc_item["level"] == 1:
            toc_items.append(toc_item)
            current_h1 = toc_item
            current_h2 = None
        elif toc_item["level"] == 2:
            if current_h1 is not None:
                current_h1["children"].append(toc_item)
            else:
                toc_items.append(toc_item)
            current_h2 = toc_item
        else:
            if current_h2 is not None:
                current_h2["children"].append(toc_item)
            elif current_h1 is not None:
                current_h1["children"].append(toc_item)
            else:
                toc_items.append(toc_item)

    return str(soup), toc_items


def _fetch_all_articles():
    return db.session.execute(db.select(Article_Meta_Data)).scalars().all()


def _fetch_api_articles():
    return (
        db.session.execute(db.select(Article_Meta_Data).order_by(Article_Meta_Data.id))
        .scalars()
        .all()
    )


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
        version = int(os.path.getmtime(asset_path))
    except OSError:
        return url_for("static", filename=filename)

    return url_for("static", filename=filename, v=version)


@app.context_processor
def inject_asset_url():
    return {"asset_url": _asset_url}


@app.route("/")
def index():
    # use the file in the templates
    return render_template("index.html")


@app.route("/articles")
def article_index():
    articles = _fetch_all_articles()
    docs_context = build_docs_context(articles, current_category="")
    return render_template("article_index.html", **docs_context)


@app.route("/articles/category/<path:category_path>")
def article_category(category_path):
    articles = _fetch_all_articles()
    docs_context = build_docs_context(articles, current_category=category_path)

    if category_path and docs_context["current_node"].path != category_path:
        abort(404)

    return render_template("article_index.html", **docs_context)


@app.route("/about")
def about_me():
    return render_template("about_me.html")


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


@app.route("/articles/<int:article_id>")
def view_article(article_id):
    article = db.session.execute(
        db.select(Article_Meta_Data).where(Article_Meta_Data.id == article_id)
    ).scalar()

    if not article:
        abort(404)

    # 转换category中的/为-以匹配文件系统路径
    category_path = article.category.replace(os.sep, "-")

    # 真正的 html_path
    html_path = f"{Rendered_Articles}{os.sep}{category_path}{os.sep}{article_id}.html"

    try:
        with open(html_path, "r", encoding="utf-8") as f:
            article_content = f.read()
    except FileNotFoundError:
        abort(404)

    article_content, toc_items = _build_article_toc(article_content)
    shell_context = build_article_shell_context(_fetch_all_articles(), article)

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
    if not REIMPORT_ARTICLES_TOKEN:
        abort(404)

    request_token = request.headers.get("X-REIMPORT-ARTICLES-TOKEN", "")
    if request_token != REIMPORT_ARTICLES_TOKEN:
        abort(403)

    with app.app_context():
        import_articles(Articles_Directory, db)
    return {"status": "ok"}
