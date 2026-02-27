import os
import sys

import pytest

# Ensure tests can import modules from web-app/ (e.g. app.py, models.py).
TESTS_DIR = os.path.dirname(__file__)
APP_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import app as app_module
from models import Article_Meta_Data, db


@pytest.fixture()
def app(tmp_path):
    # Use a per-test temporary rendered folder to avoid polluting real data.
    test_rendered_path = tmp_path / "rendered"
    test_rendered_path.mkdir(parents=True, exist_ok=True)

    # Save original runtime settings and restore them after each test.
    original_rendered = app_module.Rendered_Articles
    original_rendered_folder = app_module.app.config.get("RENDERED_ARTICLES_FOLDER")

    app_module.app.config.update(
        TESTING=True,
        RENDERED_ARTICLES_FOLDER=str(test_rendered_path),
    )
    app_module.Rendered_Articles = str(test_rendered_path)

    with app_module.app.app_context():
        # Ensure table metadata exists for tests.
        db.create_all()

    yield app_module.app

    with app_module.app.app_context():
        # Remove only test rows (file_path starts with tests/) to stay safe.
        db.session.execute(
            db.delete(Article_Meta_Data).where(Article_Meta_Data.file_path.like("tests/%"))
        )
        db.session.commit()
        db.session.remove()

    app_module.Rendered_Articles = original_rendered
    app_module.app.config["RENDERED_ARTICLES_FOLDER"] = original_rendered_folder


@pytest.fixture()
def client(app):
    # Flask test client sends HTTP requests without starting a real server.
    return app.test_client()
