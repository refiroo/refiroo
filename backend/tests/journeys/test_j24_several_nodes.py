"""J24.2, J24.8, J34 and J38 on several nodes — the job worker run by more than one process on one
database (USER_JOURNEYS.md, Base 0.11 N2).

Two job workers in this process stand for two nodes, as J24.3's do: each claims, runs and commits
through the database alone. A worker keeps its job's lease with a heartbeat while it runs (D170);
submissions of one subject are decided one after another (D171); a profile checks only its current
file (D172); a long step does its work before it takes the job's row, so a cancel answers at once
(D175). A lock held from the test's own connection is a timing device only: it holds a step at a
point a client cannot choose. The cases on real processes are in ``test_j24_several_processes.py``.
"""

import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace

import pytest
import test_j27_export as j27_export
import test_j34_onboard as j34
import test_j35_next_version as j35
import test_j37_workspace_migration as j37
import test_j38_3_move as j38
import workbooks
from scenario import W1, Held, ok, refused
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.pool import NullPool
from test_j24_background_job import _items, _named, _submit
from test_j36_workspace_models import BOTH
from test_j38_1_model_mapping import _beside, _create, _infer

from app.db import SessionLocal
from app.engine.jobs.worker import JobWorker
from app.models.database import Job

# A lease shorter than most steps of every kind (seconds).
LEASE = 0.3
# How long a walk's jobs may take before the test calls them stuck.
STEP_SECONDS = 90


class _Nodes:
    """Two workers on threads of their own, standing for two nodes, in place of the application's
    worker: ``run_until_idle`` waits until no job of their kinds is queued or running."""

    def __init__(self, original: JobWorker, lease: float) -> None:
        self.original = original
        settings = replace(original.settings, lease_seconds=lease)
        self.workers = [
            JobWorker(
                SessionLocal,
                settings,
                owner=f"node-{name}-{original.thread_name}",
                kinds=original.kinds,
                files=original.files,
                sweeps=False,
                thread_name=f"{original.thread_name}-{name}",
            )
            for name in ("a", "b")
        ]
        for worker in self.workers:
            worker.start()

    def wake(self) -> None:
        for worker in self.workers:
            worker.wake()

    def sweep(self, *args, **kwargs):
        return self.original.sweep(*args, **kwargs)

    def run_until_idle(self) -> int:
        self.wake()
        deadline = time.monotonic() + STEP_SECONDS
        while time.monotonic() < deadline:
            with SessionLocal() as session:
                busy = session.scalar(
                    select(func.count()).where(
                        Job.kind.in_(self.original.kinds), Job.state.in_(("queued", "running"))
                    )
                )
            if not busy:
                return 0
            time.sleep(0.05)
        raise AssertionError(
            f"a job stayed queued or running for {STEP_SECONDS} s: the two nodes kept taking it "
            "from each other"
        )

    def stop(self) -> None:
        for worker in self.workers:
            worker.stop(timeout=STEP_SECONDS)


@contextmanager
def _two_nodes(world, lease: float = LEASE) -> Iterator[None]:
    """The application's job and export workers replaced by two nodes each, with ``lease``."""
    state = world.api.client.app.state
    saved = state.job_worker, state.export_worker
    nodes = [_Nodes(saved[0], lease), _Nodes(saved[1], lease)]
    state.job_worker, state.export_worker = nodes
    try:
        yield
    finally:
        state.job_worker, state.export_worker = saved
        for each in nodes:
            each.stop()


@contextmanager
def _holding(world, statement: str, **params) -> Iterator[Held]:
    """``statement`` (a lock) held from the test's own connection while the block runs; requests
    and workers started with ``Held.start`` meanwhile wait for it where they need it."""
    engine = create_engine(world.database, poolclass=NullPool)
    holder = engine.connect()
    held = Held(ThreadPoolExecutor(4), engine)
    try:
        holder.execute(text(statement), params)
        yield held
    finally:
        holder.rollback()
        holder.close()
        held.close()


def _worker(world, owner: str) -> JobWorker:
    """A worker with the application's settings and files, standing for one node."""
    original = world.api.client.app.state.job_worker
    return JobWorker(SessionLocal, original.settings, owner=owner, files=original.files)


# --- J24.8: a long step keeps its job (case 2) -----------------------------------------------------


@pytest.mark.journey("J24.8")
@pytest.mark.structures("R", "R.u")
def test_a_long_step_keeps_its_job_batch(world):
    """Given two nodes with a lease shorter than a chunk. When a background batch runs. Then it
    completes in the worker that claimed each chunk and every item is applied once."""
    with _two_nodes(world):
        job = _submit(world, _items(world, 40, "N"))
        world.api.client.app.state.job_worker.run_until_idle()
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    assert (done["state"], done["counts"]["applied"]) == ("completed", 40)
    assert _named(world, "N") == [f"N {n:03d}" for n in range(40)]


@pytest.mark.journey("J24.8", "J34.3", "J34.4")
@pytest.mark.structures("K")
def test_a_long_step_keeps_its_job_profile_dry_run_and_inference(world):
    """Given two nodes with a short lease. When W1 above 1,000 rows is profiled on a draft, dry
    run and inferred. Then each job completes once, the dry run reporting every row."""
    with _two_nodes(world):
        workspace = j34._workspace(world)
        book = workbooks.w1(rows=1200)
        j34._materials(world, book, workspace)
        draft = j34._draft(world)
        keys = j34._item_type(world, draft)
        source = j34._profiled(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content)
        done = j34._dry_run(world, draft, source, workspace, j34._profile(world, book, keys))
        assert done["summary"]["rows"] == {"total": 1200, "run": 1200}
        j34._infer(world, draft)


@pytest.mark.journey("J24.8", "J35.1")
@pytest.mark.structures("K")
def test_a_long_step_keeps_its_job_import_and_check(world):
    """Given two nodes with a short lease. When W1 is installed with its profile and imported, and
    its next version uploaded to the profile. Then the import, the profile and the check complete."""
    with _two_nodes(world):
        workspace, profile_key, _book = j35._loaded(world)
        j35._next_version(world, workspace, profile_key)


@pytest.mark.journey("J24.8", "J37.2")
@pytest.mark.structures(*BOTH)
def test_a_long_step_keeps_its_job_migration(world):
    """J37.2's walk (a preview, then the confirmed migration) on two nodes with a short lease."""
    with _two_nodes(world):
        j37.test_confirm_accepting_the_loss(world)


@pytest.mark.journey("J24.8", "J38.8")
@pytest.mark.structures(*BOTH)
def test_a_long_step_keeps_its_job_mapping_inference_and_move(world):
    """Given two nodes with a short lease. When a mapping is inferred and the whole workspace's
    move previewed and confirmed. Then each job completes once and the move loads the ledger."""
    with _two_nodes(world):
        _other, target, key = j38._mapped(world)
        ledger = j38._ledger(world, "Nodes")
        job, _rows = j38._preview(world, key, target)
        job, rows = j38._confirm(world, job)
    assert j38._records(rows)[ledger["id"]]["outcome"] == "create"


@pytest.mark.journey("J24.8", "J27.1")
@pytest.mark.structures("R", "R.n", "H", "H.code", "K", "K.code", "Bnn", "Bnn.weight", "Hparent")
def test_a_long_step_keeps_its_job_export(world):
    """J27.1's walk (a live export and its manifest) on two nodes with a short lease."""
    with _two_nodes(world):
        j27_export.test_a_live_export_holds_the_stated_scope_parents_first_with_its_manifest(world)


# --- J24.2: a cancel during a long step (case 3) ---------------------------------------------------


@pytest.mark.journey("J24.2", "J38.3")
@pytest.mark.structures(*BOTH)
def test_a_cancel_while_a_move_deletes_in_the_source_answers_at_once(world):
    """Given a move (``mode: move``) confirmed, its load at its last step deleting in the source.
    When it is cancelled. Then the cancel answers 202 at once, and the job ends cancelled with no
    change set of the source."""
    _other, target, key = j38._mapped(world)
    ledger = j38._ledger(world, "Cancelled")
    job, _rows = j38._preview(world, key, target, {"parentObjectId": ledger["id"]}, mode="move")
    before = j38._change_sets(world, W1)
    ok(world.api.post(f"/jobs/{job['id']}/confirm"), 202)
    worker = _worker(world, "mover")
    with world.holding(W1) as held:
        running = held.start(worker.run_until_idle)
        held.waiting(1)
        answer = held.start(lambda: world.api.post(f"/jobs/{job['id']}/cancel"))
        ok(answer.result(timeout=5), 202)
    running.result(timeout=30)
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    assert done["state"] == "cancelled", done
    assert j38._change_sets(world, W1) == before


@pytest.mark.journey("J24.2", "J34.4")
@pytest.mark.structures("K")
def test_an_inference_cancelled_before_it_commits_writes_nothing(world):
    """Given a draft's inference completed, and a second one at its last step. When the second is
    cancelled. Then it ends cancelled, completing nothing: its proposals are not served
    (``409 INFERENCE_NOT_READY``, as for any cancelled inference)."""
    draft, _book, _source, _workspace = j34._inferred(world)
    started = ok(
        world.api.post(f"/model-drafts/{draft['id']}/inference", {"mode": "newApplication"}), 202
    )
    worker = _worker(world, "inferrer")
    statement = (
        "SELECT 1 FROM model_draft_proposals WHERE draft_id = "
        "(SELECT id FROM model_drafts WHERE public_id = :draft) FOR UPDATE"
    )
    with _holding(world, statement, draft=draft["id"]) as held:
        running = held.start(worker.run_until_idle)
        held.waiting(1)
        ok(world.api.post(f"/jobs/{started['jobId']}/cancel"), 202)
    running.result(timeout=30)
    read = ok(world.api.get(f"/model-drafts/{draft['id']}/inference"))
    assert (read["jobId"], read["state"]) == (started["jobId"], "cancelled"), read
    proposals = world.api.get(f"/model-drafts/{draft['id']}/inference/proposals")
    refused(proposals, 409, "INFERENCE_NOT_READY")


# --- J34 and J38: two submissions at once (case 4) -------------------------------------------------


def _sent_together(world, *calls):
    """``calls`` in flight together, none committed before all reached the job table."""
    with _holding(world, "LOCK TABLE jobs IN SHARE MODE") as held:
        futures = [held.start(call) for call in calls]
        held.waiting(len(calls))
    return [ok(future.result(timeout=30), 202) for future in futures]


def _one_stands(world, kind, read_path):
    """Of the kind's two latest jobs, one ends cancelled and the other completed; the read names
    the completed one."""
    world.api.client.app.state.job_worker.run_until_idle()
    jobs = ok(world.api.get("/jobs", kind=kind, pageSize=2))["items"]
    states = {job["id"]: job["state"] for job in jobs}
    assert sorted(states.values()) == ["cancelled", "completed"], states
    (kept,) = [job_id for job_id, state in states.items() if state == "completed"]
    read = ok(world.api.get(read_path))
    assert (read["jobId"], read["state"]) == (kept, "completed"), read


@pytest.mark.journey("J34.3", "J34.4")
@pytest.mark.structures("K")
def test_two_dry_runs_or_inferences_sent_at_once(world):
    """Given W1 profiled on a draft. When two dry runs are sent at once, and then two inferences.
    Then of each pair one ends cancelled and the other completed, and the draft's dry run and
    inference read the completed one."""
    workspace = j34._workspace(world)
    book = workbooks.w1(rows=200)
    j34._materials(world, book, workspace)
    draft = j34._draft(world)
    keys = j34._item_type(world, draft)
    source = j34._profiled(
        world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content, workspaceKey=workspace
    )
    body = {
        "sourceFileId": source["id"],
        "workspaceKey": workspace,
        "profile": j34._profile(world, book, keys),
    }

    def dry_run():
        return world.api.post(f"/model-drafts/{draft['id']}/dry-run", body)

    _sent_together(world, dry_run, dry_run)
    _one_stands(world, "dryRun", f"/model-drafts/{draft['id']}/dry-run")

    def inference():
        return world.api.post(f"/model-drafts/{draft['id']}/inference", {"mode": "newApplication"})

    _sent_together(world, inference, inference)
    _one_stands(world, "inference", f"/model-drafts/{draft['id']}/inference")


@pytest.mark.journey("J38.1")
@pytest.mark.structures(*BOTH)
def test_two_mapping_inferences_sent_at_once(world):
    """Given a mapping between two workspaces. When its inference is sent twice at once. Then one
    ends cancelled and the other completed, and the mapping's inference reads the completed one."""
    _other, _release, target = _beside(world)
    key = _create(world, W1, target)["key"]
    _infer(world, key, W1, target)
    body = {"sourceWorkspaceKey": W1, "targetWorkspaceKey": target}

    def inference():
        return world.api.post(f"/model-mappings/{key}/inference", body)

    _sent_together(world, inference, inference)
    _one_stands(world, "mappingInference", f"/model-mappings/{key}/inference")


@pytest.mark.journey("J35.1")
@pytest.mark.structures("K")
def test_a_profile_checks_its_newest_file_when_the_older_is_profiled_last(world):
    """Given a stored profile. When two files are uploaded to it and the older is profiled last, on
    another node. Then the profile's check is of the newer file."""
    workspace, profile_key, _book = j35._loaded(world)
    owner = {"profileKey": profile_key}
    content = workbooks.w1_next(rows=200).content
    older = ok(j34._upload(world, owner, "older.xlsx", content, workspaceKey=workspace), 201)
    newer = ok(j34._upload(world, owner, "newer.xlsx", content, workspaceKey=workspace), 201)
    a, b = _worker(world, "node-a"), _worker(world, "node-b")
    statement = "SELECT 1 FROM source_files WHERE public_id = :id FOR UPDATE"
    with _holding(world, statement, id=older["id"]) as held:
        slow = held.start(a.run_once)
        held.waiting(1)
        b.run_until_idle()
    slow.result(timeout=30)
    a.run_until_idle()
    check = ok(world.api.get(f"/import-profiles/{profile_key}/check", workspaceKey=workspace))
    assert (check["state"], check["sourceFileId"]) == ("completed", newer["id"]), check
