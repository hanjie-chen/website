import os
import sys

# ensure /app is on sys.path when running as a script
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from config import Articles_Directory
from import_articles_scripts import import_articles
from models import db


def main():
    with app.app_context():
        db.drop_all()
        db.create_all()
        import_articles(Articles_Directory, db)
    print("Database initialized and articles imported.")


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    main()
