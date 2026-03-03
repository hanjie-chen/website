import os

# get test data dir from env, default is '/articles-data'
Articles_Directory = os.environ.get("SOURCE_ARTICLES_DIRECTORY", "/articles/src")
# Rendered articles html directory, for develop env is /app/rendered-articles, for prod env is /rendered-articles
Rendered_Articles = os.environ.get("RENDERED_ARTICLES_DIRECTORY", "/articles/rendered")

# sqlite database uri (allow override for safe testing)
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SQLALCHEMY_DATABASE_URI", "sqlite:///project.db"
)

# token for internal reimport endpoint
REIMPORT_ARTICLES_TOKEN = os.environ.get("REIMPORT_ARTICLES_TOKEN", "")


# app environment
APP_ENV = os.environ.get("APP_ENV", os.environ.get("FLASK_ENV", "production")).lower()
IS_DEV = APP_ENV in ("development", "dev")
