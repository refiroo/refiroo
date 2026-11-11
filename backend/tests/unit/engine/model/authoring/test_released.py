"""``engine/model/authoring/released.py``: the release a draft is compared with (0.11 D37)."""

import copy
from uuid import uuid4

from app.db import SessionLocal
from app.engine.model.authoring.released import base_release
from app.engine.model.compiler import parse_model
from app.engine.model.drafts import create_draft
from app.engine.model.releases import install_model_release


def _install(session, model):
    release, _created = install_model_release(session, parse_model(model))
    return release


def test_a_draft_is_compared_with_its_base_else_the_newest_release_of_its_model_else_nothing(
    seeded,
):
    model = copy.deepcopy(seeded.configuration.model)
    model["release"]["key"] = f"unit-{uuid4().hex[:8]}"
    with SessionLocal() as session:
        older = _install(session, model)
        newer_model = copy.deepcopy(model)
        newer_model["release"]["version"] += "-newer"
        newer = _install(session, newer_model)
        session.flush()

        based = create_draft(session, name="Based", model=model, base_release_id=older.public_id)
        assert base_release(session, based).id == older.id

        unbased = create_draft(session, name="Unbased", model=model, base_release_id=None)
        assert base_release(session, unbased).id == newer.id

        new_model = copy.deepcopy(model)
        new_model["release"]["key"] = f"new-{uuid4().hex[:8]}"
        fresh = create_draft(session, name="New model", model=new_model, base_release_id=None)
        assert base_release(session, fresh) is None
        session.rollback()
