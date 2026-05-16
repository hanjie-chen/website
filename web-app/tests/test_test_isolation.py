from pathlib import Path
from urllib.parse import urlsplit


def test_app_fixture_uses_temporary_database(app):
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    database_path = Path(urlsplit(database_uri).path)

    assert database_path.name == "site_test.sqlite"
    assert "/tmp/" in str(database_path)
