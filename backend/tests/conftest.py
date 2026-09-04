import os
from pathlib import Path

TEST_DB_PATH = Path(__file__).resolve().parent / "test-rdm-engine.db"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

import pytest

from app.db import engine
from app.models.database import Base


@pytest.fixture(autouse=True, scope="session")
def _test_database():
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    TEST_DB_PATH.unlink(missing_ok=True)
