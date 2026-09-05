import os
from pathlib import Path

import pytest

TEST_DB_PATH = Path(__file__).resolve().parent / "test-rdm-engine.db"

os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")

from app.db import get_engine
from app.models.database import Base


@pytest.fixture(autouse=True, scope="session")
def _test_database():
    yield
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    TEST_DB_PATH.unlink(missing_ok=True)
