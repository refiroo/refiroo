"""Guards for the structural guarantees introduced by the refactor."""

from harness_identity import TestClient

from app.config import Settings, reload_settings
from app.db import get_engine
from app.engine.model import metadata
from app.engine.model.registry import model_registry
from app.main import app
from app.management.dependencies import get_session


def test_the_database_url_has_no_default():
    """PostgreSQL only (0.9.0-alpha.1): no SQLite file is assumed; startup refuses a missing URL."""
    assert Settings.from_env({}).database_url is None
    assert Settings.from_env({"DATABASE_URL": "  "}).database_url is None


def test_database_engine_tracks_reloaded_settings(monkeypatch):
    reload_settings()
    original_engine = get_engine()
    temporary_engines = []
    try:
        with monkeypatch.context() as patch:
            first_url = "postgresql+psycopg://rdm@localhost:5432/first"
            patch.setenv("DATABASE_URL", first_url)
            reload_settings()
            first_engine = get_engine()
            temporary_engines.append(first_engine)
            assert str(first_engine.url) == first_url

            second_url = "postgresql+psycopg://rdm@localhost:5432/second"
            patch.setenv("DATABASE_URL", second_url)
            reload_settings()
            second_engine = get_engine()
            temporary_engines.append(second_engine)
            assert str(second_engine.url) == second_url
            assert second_engine is not first_engine
    finally:
        reload_settings()
        for engine in temporary_engines:
            engine.dispose()

    assert get_engine() is original_engine


def test_one_session_serves_the_whole_request():
    """The snapshot dependency and the handler must share a session, not open two."""
    opened: list[int] = []
    real_get_session = get_session

    def counting_session():
        yield from _count(real_get_session, opened)

    app.dependency_overrides[get_session] = counting_session
    try:
        with TestClient(app) as client:
            opened.clear()
            response = client.get("/api/v1/object-types", params={"pageSize": 5})
            assert response.status_code == 200
            assert len(opened) == 1
    finally:
        app.dependency_overrides.pop(get_session, None)


def _count(factory, opened: list[int]):
    generator = factory()
    session = next(generator)
    opened.append(id(session))
    try:
        yield session
    finally:
        generator.close()


def test_metadata_identifiers_are_loaded_once_per_release():
    """The second request for the same release must not re-read the metadata tables."""
    with TestClient(app) as client:
        metadata.clear_metadata_cache()
        assert client.get("/api/v1/object-types").status_code == 200
        loaded_release_ids = set(metadata._identifier_cache)
        assert len(loaded_release_ids) == 1

        real_loader = metadata._keyed
        calls: list[str] = []

        def tracking_keyed(session, entity, release_db_id):
            calls.append(entity.__name__)
            return real_loader(session, entity, release_db_id)

        metadata._keyed = tracking_keyed
        try:
            assert client.get("/api/v1/object-types").status_code == 200
            assert client.get("/api/v1/relation-types").status_code == 200
        finally:
            metadata._keyed = real_loader
        assert calls == []


def test_clearing_the_registry_also_clears_metadata_identifiers():
    with TestClient(app) as client:
        assert client.get("/api/v1/object-types").status_code == 200
    assert metadata._identifier_cache  # populated by the request above

    model_registry.clear()
    assert not metadata._identifier_cache

    with TestClient(app) as client:
        assert client.get("/api/v1/object-types").status_code == 200


def test_object_type_public_ids_survive_the_cache():
    """A cached projection must still attach the same public IDs as a cold one."""
    with TestClient(app) as client:
        metadata.clear_metadata_cache()
        cold = client.get("/api/v1/object-types").json()
        warm = client.get("/api/v1/object-types").json()
    assert cold == warm
    assert all(item["id"] for item in cold["items"])
