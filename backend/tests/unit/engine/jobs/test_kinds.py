"""``engine/jobs/kinds.py``: the one registry of job kinds agrees with the database's check, the
workers' lists, the groups and actions of a refusal, and each kind's step."""

from app.engine.authorization.catalogue import GROUPS, JOB_GROUPS
from app.engine.authorization.writes import JOB_ACTIONS
from app.engine.jobs import kinds
from app.engine.jobs.worker import JobWorker
from app.models.database import Job


def test_the_registry_names_the_kinds_the_database_allows():
    check = next(c for c in Job.__table_args__ if getattr(c, "name", None) == "ck_job_kind")
    allowed = {part.strip(" '") for part in str(check.sqltext).split("(")[1].rstrip(")").split(",")}
    assert set(kinds.KIND_NAMES) == allowed


def test_every_kind_has_a_group_an_action_and_a_step_the_worker_has():
    assert set(JOB_GROUPS) == set(JOB_ACTIONS) == set(kinds.KIND_NAMES)
    assert set(JOB_GROUPS.values()) <= set(GROUPS)
    for kind in kinds.JOB_KINDS:
        assert kind.step is None or hasattr(JobWorker, kind.step)


def test_each_kind_belongs_to_one_worker():
    together = kinds.BATCH_KINDS + kinds.EXPORT_KINDS + kinds.ASSISTANT_KINDS
    assert sorted(together) == sorted(kinds.KIND_NAMES)
    assert kinds.EXPORT_KINDS == ("export",) and kinds.ASSISTANT_KINDS == ("aiTask",)
