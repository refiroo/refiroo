"""J12.16–J12.17 — Rehearse a restore: a backup restored into a separate database, checked there by
the engine and recorded in the instance (USER_JOURNEYS.md, Base 0.11 O2, D198–D203).

The backup and the restore are real ``pg_dump`` and ``pg_restore`` runs on the harness's server, as
an operator runs them; the check is ``python -m app.cli.restore_check`` with the instance's
``DATABASE_URL``; the restored copy is then served by a real engine process.
"""

import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import postgres_server
import pytest
import seeds
from processes import run
from scenario import W1, application, ok, scenario_seed
from service import command, execute, render, scalar
from sqlalchemy import URL
from test_j36_workspace_models import BOTH, _model, _on, _other

# The harness's server is created with the ICU root collation, so a new database has it.
LIBC = "LOCALE_PROVIDER libc LOCALE 'C'"
# A process row as a running instance leaves it in a backup (D203).
_PROCESS_ROW = (
    "INSERT INTO engine_processes (process_id, host, pid, engine_version, started_at, "
    "heartbeat_at, report) VALUES ('dumped-host:4242:abcd1234', 'dumped-host', 4242, '0.11.0', "
    "now(), now(), '{}')"
)


def _libpq(url: URL) -> list[str]:
    """``url``'s connection as client program arguments."""
    host = url.query.get("host") or url.host
    port = url.query.get("port") or (str(url.port) if url.port else "5432")
    return ["-h", str(host), "-p", str(port), "-U", url.username or "postgres", "-d", url.database]


def _dump(url: URL, target: Path) -> None:
    done = subprocess.run(
        [postgres_server._binary("pg_dump"), "-Fc", "-f", str(target), *_libpq(url)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr


def _restore(dump: Path, options: str = "") -> URL:
    """A new database with ``options`` holding ``dump``, as an operator restores it."""
    copy = seeds.create_empty(options)
    done = subprocess.run(
        [postgres_server._binary("pg_restore"), "--no-owner", *_libpq(copy), str(dump)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return copy


@contextmanager
def _backed_up(configuration) -> Iterator[tuple[URL, dict, Path]]:
    """An instance with W1 on X (an open change set in it) and a workspace on Y's model holding a
    record, and a process row; its backup. Yields the instance, what was made and the dump."""
    name = scenario_seed(configuration)
    ids = seeds.ensure(name)["ids"]
    url = seeds.clone(name)
    folder = Path(tempfile.mkdtemp(prefix="rdm-o2-"))
    try:
        with application(configuration, url) as world:
            other = _other(world)
            y = world.install(other.configuration.model, name="Y")["id"]
            on_y = _on(world, y)
            made = other.made("R", "Kept on Y", workspace=on_y)
            change_set = world.change_set(name="Open at backup")
            made = {
                "ids": ids,
                "x": _model(world)["releaseId"],
                "y": y,
                "y_key": other.configuration.model["release"]["key"],
                "on_y": on_y,
                "record": made["id"],
                "change_set": change_set["id"],
            }
        execute(url, _PROCESS_ROW)
        dump = folder / "instance.dump"
        _dump(url, dump)
        yield url, made, dump
    finally:
        seeds.drop(url.database)
        for item in folder.iterdir():
            item.unlink()
        folder.rmdir()


def _check(url: URL, copy: URL, *args: str) -> subprocess.CompletedProcess[str]:
    return command("app.cli.restore_check", url, "--restored", render(copy), *args)


def _rehearsals(configuration, url: URL) -> list[dict]:
    with application(configuration, url) as world:
        return ok(world.api.get("/system/backup-rehearsals"))["items"]


def _count(url: URL, statement: str, workspace: str) -> int:
    return int(scalar(url, statement, workspace=workspace))


RECORDS = "SELECT count(*) FROM objects WHERE workspace_key = :workspace"
RELATIONS = (
    "SELECT count(*) FROM object_relations r JOIN objects o ON o.id = r.from_object_id "
    "WHERE o.workspace_key = :workspace"
)


@pytest.mark.journey("J12.16", "J36")
@pytest.mark.structures(*BOTH)
def test_rehearse_a_restore(configuration):
    """Given an instance whose workspaces run two models, one with an open change set. When it is
    backed up with pg_dump, restored with pg_restore into a new database and the check runs
    against the copy. Then the check passes and says so, naming each workspace served with its
    release; the instance lists the rehearsal first with each workspace's counts, equal to the
    instance's; an engine process started on the copy serves each workspace under its own model,
    reads its records, keeps the change set open on its release and lists no process from the
    dump."""
    with _backed_up(configuration) as (url, made, dump):
        copy = _restore(dump)
        try:
            checked = _check(url, copy, "--backup", "instance.dump")
            assert checked.returncode == 0, checked.stdout + checked.stderr
            assert "Traceback" not in checked.stdout + checked.stderr
            assert "passed" in checked.stdout
            for workspace in (W1, made["on_y"]):
                assert workspace in checked.stdout

            rehearsals = _rehearsals(configuration, url)
            latest = rehearsals[0]
            assert latest["result"] == "passed" and latest["backup"] == "instance.dump"
            assert latest["failure"] is None and latest["dataAsOf"] is not None
            assert latest["revisionAfter"] == latest["revisionBefore"]
            workspaces = {item["workspaceKey"]: item for item in latest["workspaces"]}
            assert workspaces[W1]["release"]["id"] == made["x"]
            assert workspaces[made["on_y"]]["release"]["id"] == made["y"]
            for key, item in workspaces.items():
                assert item["state"] == "served" and item["reason"] is None
                assert item["records"] == _count(url, RECORDS, key) == item["liveRecords"]
                assert item["relations"] == _count(url, RELATIONS, key)
            assert workspaces[W1]["openChangeSets"] == 1
            assert workspaces[made["on_y"]]["records"] == 1

            with run(configuration, copy, made["ids"]) as process:
                api = process.world.api
                assert ok(api.get(f"/workspaces/{W1}/model"))["releaseId"] == made["x"]
                on_y = ok(api.get(f"/workspaces/{made['on_y']}/model"))
                assert on_y["releaseId"] == made["y"]
                other = _other(process.world)
                record = ok(other.read("R", made["record"], workspaceKey=made["on_y"]))
                assert record["name"] == "Kept on Y"
                assert ok(api.get(f"/change-sets/{made['change_set']}"))["name"] == "Open at backup"
                processes = ok(api.get("/system/processes"))["items"]
                assert [item["pid"] for item in processes] == [process.pid]
        finally:
            seeds.drop(copy.database)


@pytest.mark.journey("J12.17", "J36")
@pytest.mark.structures(*BOTH)
def test_a_rehearsal_that_fails_is_recorded(configuration):
    """Given the instance's backup. When it is restored into a database with the default
    collation and checked; restored properly, with the release of the workspace on Y's model
    written outside the schema window, and checked; and checked naming the instance's own
    database. Then the first fails naming the collation and what to do, recorded failed with its
    code; the second fails with that workspace not served (unsupportedSchema) and W1 served,
    recorded; the third is refused before anything is changed or recorded."""
    with _backed_up(configuration) as (url, made, dump):
        copy = _restore(dump, options=LIBC)
        try:
            checked = _check(url, copy, "--backup", "wrong-collation.dump")
            assert checked.returncode == 1
            assert "ICU root collation 'und'" in checked.stderr, checked.stderr
            assert "CREATE DATABASE" in checked.stderr and "Traceback" not in checked.stderr
        finally:
            seeds.drop(copy.database)
        first = _rehearsals(configuration, url)[0]
        assert first["result"] == "failed" and first["backup"] == "wrong-collation.dump"
        assert first["failure"]["code"] == "DATABASE_COLLATION"
        assert "ICU root collation" in first["failure"]["message"]

        copy = _restore(dump)
        try:
            execute(
                copy,
                "UPDATE model_releases SET schema_version = '0.4' WHERE public_id = :id",
                id=made["y"],
            )
            checked = _check(url, copy)
            assert checked.returncode == 1
            assert made["on_y"] in checked.stderr and "0.4" in checked.stderr
        finally:
            seeds.drop(copy.database)
        rehearsals = _rehearsals(configuration, url)
        second = rehearsals[0]
        assert second["result"] == "failed" and second["backup"] is None
        assert second["failure"]["code"] == "WORKSPACES_NOT_SERVED"
        workspaces = {item["workspaceKey"]: item for item in second["workspaces"]}
        assert workspaces[made["on_y"]]["state"] == "unavailable"
        assert workspaces[made["on_y"]]["reason"] == "unsupportedSchema"
        assert workspaces[W1]["state"] == "served"

        refused = _check(url, url)
        assert refused.returncode == 2
        assert "the instance's own database" in refused.stderr
        assert len(_rehearsals(configuration, url)) == len(rehearsals) == 2


@pytest.mark.journey("J12.16")
@pytest.mark.parametrize(
    "restored",
    ["mysql://operator:s3cret-pass@db.example/copy", "not a url s3cret-pass"],
)
def test_a_refused_restored_url_hides_its_password(restored, capsys):
    """An operator who mistypes ``--restored`` sees why it was refused, never the password."""
    from app.cli.restore_check import main

    with pytest.raises(SystemExit) as refused:
        main(["--restored", restored])
    assert refused.value.code == 2
    message = capsys.readouterr().err
    assert "Nothing was checked or recorded." in message
    assert "s3cret-pass" not in message
