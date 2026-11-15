"""The test server's guards and its owner rule (TS2): no synced data folder, enough free space, no
run stops a server another still uses."""

import shutil
import tempfile
from collections import namedtuple
from pathlib import Path

import postgres_server
import pytest
from sqlalchemy import text

Usage = namedtuple("Usage", "total used free")


@pytest.fixture(autouse=True)
def _own_server(monkeypatch):
    monkeypatch.delenv(postgres_server.EXTERNAL_SERVER, raising=False)


def test_a_data_folder_in_a_synced_place_is_refused(tmp_path):
    home = tmp_path / "home"
    for synced in (
        home / "Library/Mobile Documents/com~apple~CloudDocs/test-postgres",
        home / "Dropbox/test-postgres",
        home / "OneDrive - Company/test-postgres",
        home / "Library/CloudStorage/OneDrive-Personal/test-postgres",
    ):
        synced.mkdir(parents=True)
        with pytest.raises(postgres_server.ServerUnavailable, match="syncs"):
            postgres_server.guard(synced, home)


def test_desktop_and_documents_are_synced_only_when_icloud_syncs_them(tmp_path):
    home = tmp_path / "home"
    documents = home / "Documents/test-postgres"
    documents.mkdir(parents=True)
    postgres_server.guard(documents, home)
    (home / "Library/Mobile Documents/com~apple~CloudDocs/Documents").mkdir(parents=True)
    with pytest.raises(postgres_server.ServerUnavailable, match="iCloud Drive"):
        postgres_server.guard(documents, home)


def test_the_resolved_path_is_checked_not_the_link(tmp_path):
    home = tmp_path / "home"
    synced = home / "Dropbox/data"
    synced.mkdir(parents=True)
    link = tmp_path / "repo/.test-postgres"
    link.parent.mkdir()
    link.symlink_to(synced)
    with pytest.raises(postgres_server.ServerUnavailable, match="Dropbox"):
        postgres_server.guard(link, home)
    plain = tmp_path / "volume/test-postgres"
    plain.mkdir(parents=True)
    other = tmp_path / "repo/other"
    other.symlink_to(plain)
    postgres_server.guard(other, home)


def test_a_link_to_a_missing_volume_says_to_mount_it(tmp_path):
    link = tmp_path / ".test-postgres"
    link.symlink_to(tmp_path / "missing-volume")
    with pytest.raises(postgres_server.ServerUnavailable, match="Connect or mount"):
        postgres_server.guard(link, tmp_path)


def test_below_ten_gb_free_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(
        postgres_server.shutil, "disk_usage", lambda _path: Usage(100 * 1024**3, 0, 9 * 1024**3)
    )
    with pytest.raises(postgres_server.ServerUnavailable, match="Only 9.0 GB are free"):
        postgres_server.guard(tmp_path / "data", tmp_path)
    monkeypatch.setattr(
        postgres_server.shutil, "disk_usage", lambda _path: Usage(100 * 1024**3, 0, 11 * 1024**3)
    )
    postgres_server.guard(tmp_path / "data", tmp_path)


def test_an_external_server_skips_the_guards(tmp_path, monkeypatch):
    monkeypatch.setenv(postgres_server.EXTERNAL_SERVER, "postgresql://postgres@localhost/postgres")
    monkeypatch.setattr(postgres_server.shutil, "disk_usage", lambda _path: Usage(1, 1, 0))
    postgres_server.guard(Path(tmp_path / "Dropbox/data"), tmp_path)


def test_the_server_never_turns_fsync_on():
    assert postgres_server.SETTINGS["fsync"] == "off"


def test_no_run_stops_a_server_another_run_still_uses(tmp_path, monkeypatch):
    try:
        postgres_server._binary("pg_ctl")
    except postgres_server.ServerUnavailable:
        pytest.skip("needs the PostgreSQL binaries; CI uses an external server")
    # A server of its own (a short path: a socket's is limited), so the shared one is never touched.
    root = Path(tempfile.mkdtemp(prefix="pgt", dir="/tmp"))
    monkeypatch.setattr(postgres_server, "ROOT", root)
    monkeypatch.setattr(postgres_server, "DATA", root / "data")
    monkeypatch.setattr(postgres_server, "LOG", root / "server.log")
    monkeypatch.setattr(postgres_server, "STARTED_MARK", root / "started-by-harness")
    monkeypatch.setattr(postgres_server, "SOCKET_DIRECTORY", root)
    monkeypatch.setattr(postgres_server, "PORT", 55499)
    # This run's own registration is not the one released (R172-F7).
    monkeypatch.setattr(postgres_server, "_USE", {"connection": None})
    monkeypatch.setitem(postgres_server.SETTINGS, "unix_socket_directories", f"'{root}'")
    monkeypatch.setitem(postgres_server.SETTINGS, "port", "55499")
    monkeypatch.setattr(postgres_server, "guard", lambda *_: None)
    try:
        assert postgres_server.start() is True  # this run started it
        other = postgres_server._lock_connection()  # another run, using it too
        other.execute(
            text("SELECT pg_advisory_lock_shared(hashtext(:n))"), {"n": postgres_server.USERS_LOCK}
        )
        postgres_server.stop()  # the first run ends: the other still uses the server
        assert postgres_server.is_running()
        other.close()  # the other run ends too
        postgres_server.stop()
        assert not postgres_server.is_running()
    finally:
        postgres_server.release_use()
        if postgres_server.is_running():
            postgres_server._run(
                postgres_server._binary("pg_ctl"),
                "stop",
                "--pgdata",
                str(root / "data"),
                "--mode",
                "immediate",
            )
        shutil.rmtree(root, ignore_errors=True)


def test_start_and_stop_wait_for_each_other(tmp_path, monkeypatch):
    import threading

    # Nothing of the shared server is touched: stop() reads these (R172-F6).
    monkeypatch.setattr(postgres_server, "SOCKET_DIRECTORY", tmp_path)
    monkeypatch.setattr(postgres_server, "DATA", tmp_path / "data")
    monkeypatch.setattr(postgres_server, "STARTED_MARK", tmp_path / "started-by-harness")
    monkeypatch.setattr(postgres_server, "PORT", 55498)
    monkeypatch.setattr(postgres_server, "_USE", {"connection": None})
    finished = threading.Event()

    def stopping():
        postgres_server.stop()
        finished.set()

    with postgres_server._exclusive():  # a start (or stop) in progress
        thread = threading.Thread(target=stopping)
        thread.start()
        assert not finished.wait(0.5)
    assert finished.wait(5)
    thread.join()
