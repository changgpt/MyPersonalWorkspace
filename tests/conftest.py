import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from daybook import create_app
from daybook import db as db_module
from daybook import seed


@pytest.fixture
def app(tmp_path):
    app = create_app()
    app.config.update(
        TESTING=True,
        DATABASE_PATH=tmp_path / "test.db",
    )
    with app.app_context():
        db_module.init_db()
        seed.seed_note_types(db_module.get_db())
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield db_module.get_db()
