"""The assistant task's folder and files (``engine/tasks/agent/files.py``)."""

import os
import time
from types import SimpleNamespace


def test_a_session_stopped_before_it_wrote_a_transcript_has_nothing_to_resume(
    monkeypatch, tmp_path
):
    """A Stop in the first seconds leaves no conversation: Go on as it was starts the session
    again instead of resuming one that does not exist (0.13 DOC11 13)."""
    from app.engine.tasks.agent import files as agent_files

    files = SimpleNamespace(directory=tmp_path / "files")
    task = SimpleNamespace(public_id="t1", design={"agentSession": "s-1"})
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    assert agent_files.resumable(files, task) is True
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    assert agent_files.resumable(files, task) is False
    folder = agent_files.folder_of(files, task)
    kept = tmp_path / "claude" / "projects" / agent_files._transcript_name(folder)
    kept.mkdir(parents=True)
    (kept / "s-1.jsonl").write_text("{}")
    assert agent_files.resumable(files, task) is True


def _planted(tmp_path):
    """A working folder whose scratch folder, files and Claude Code folder a session has replaced by
    links to a folder of the engine's: ``victim`` stands for ``data/assistant`` itself."""
    victim = tmp_path / "victim"
    victim.mkdir(mode=0o750)
    victim.chmod(0o750)
    secret = victim / "secret.txt"
    secret.write_text("not for the session")
    home = tmp_path / "home"
    (home / "work").mkdir(parents=True)
    (home / "claude").mkdir()
    (home / "work" / "tmp").symlink_to(victim)
    (home / "work" / "proposal.json").symlink_to(secret)
    (home / "work" / "workbook.xlsx").symlink_to(secret)
    (home / "claude" / "sessions").symlink_to(victim)
    return victim, secret, home


def test_a_link_a_session_planted_is_never_followed_by_the_engine(monkeypatch, tmp_path):
    """Review finding: ``mkdir(exist_ok=True)`` and ``chmod`` followed a link in a folder the session
    writes in, so one turn changed the mode of the tasks' root and the next let every session in."""
    from app.engine.tasks.agent import files as agent_files

    victim, secret, home = _planted(tmp_path)
    work = home / "work"
    monkeypatch.setenv("AI_AGENT_SANDBOX", "")
    agent_files.ensure_tmp(work)
    assert (work / "tmp").is_dir() and not (work / "tmp").is_symlink()
    assert oct(victim.stat().st_mode & 0o777) == "0o750" and secret.exists()
    # The engine makes no folder of a task that has them and changes nothing in them.
    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    monkeypatch.setattr(agent_files, "_create_task_folders", lambda *a, **k: 1 / 0)
    agent_files.make_folders(work)
    assert (home / "claude" / "sessions").is_symlink()
    assert oct(victim.stat().st_mode & 0o777) == "0o750"
    # What the session wrote is read through no link, from no other kind of file, and no more than a limit.
    assert agent_files.read_work(work, "proposal.json") is None
    (work / "proposal.json").unlink()
    os.mkfifo(work / "proposal.json")
    assert agent_files.read_work(work, "proposal.json") is None
    (work / "proposal.json").unlink()
    (work / "proposal.json").write_text('{"draftId": 1}')
    assert agent_files.read_work(work, "proposal.json") == '{"draftId": 1}'
    assert agent_files.read_work(work, "proposal.json", limit=3) is None
    # What the engine hands the session replaces a link and writes nothing through it.
    agent_files.put(work, "workbook.xlsx", b"new")
    assert (work / "workbook.xlsx").read_bytes() == b"new" and not (
        work / "workbook.xlsx"
    ).is_symlink()
    assert secret.read_text() == "not for the session"
    (work / "proposal.json").unlink()
    (work / "proposal.json").symlink_to(secret)
    agent_files.drop(work, "proposal.json")
    assert not (work / "proposal.json").exists() and secret.exists()
    # Removing the task's folder removes a link and never what it points to.
    task = SimpleNamespace(public_id="t1", design={})
    monkeypatch.setenv("AI_AGENT_FOLDERS", str(tmp_path))
    monkeypatch.setattr(agent_files, "home_of", lambda files, t: home)
    monkeypatch.setattr(agent_files, "folder_of", lambda files, t: work)
    monkeypatch.setattr(agent_files, "_transcripts", lambda files, t: tmp_path / "none")
    agent_files.remove_folder(None, task)
    assert not home.exists() and secret.read_text() == "not for the session"


def test_in_a_container_a_tasks_folder_has_a_random_name_kept_with_the_task(monkeypatch, tmp_path):
    from app.engine.tasks.agent import files as agent_files

    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    monkeypatch.setenv("AI_AGENT_FOLDERS", str(tmp_path / "assistant"))
    files = SimpleNamespace(directory=tmp_path / "files")
    task = SimpleNamespace(public_id="t1", design={"agentSession": "s-1"})
    session = SimpleNamespace(commit=lambda: None)
    monkeypatch.setattr(agent_files, "load_task", lambda *a, **k: task)
    monkeypatch.setattr(
        agent_files, "_open_root", lambda root: root.mkdir(parents=True, exist_ok=True)
    )
    monkeypatch.setattr(agent_files, "_shared_dir", lambda path: path.mkdir(exist_ok=True))
    agent_files.ensure_folder(session, files, "t1")
    name = task.design[agent_files.FOLDER_KEY]
    assert len(name) >= 32 and "t1" not in name
    assert agent_files.folder_of(files, task) == tmp_path / "assistant" / name / "work"
    assert agent_files.home_of(files, task) == tmp_path / "assistant" / name
    agent_files.ensure_folder(session, files, "t1")
    assert task.design[agent_files.FOLDER_KEY] == name
    other = SimpleNamespace(public_id="t2", design={})
    monkeypatch.setattr(agent_files, "load_task", lambda *a, **k: other)
    agent_files.ensure_folder(session, files, "t2")
    assert other.design[agent_files.FOLDER_KEY] != name
    assert (
        agent_files._transcripts(files, task)
        == tmp_path / "assistant" / name / "claude" / "projects"
    )
    # A new task's folders are made once, the gate around work and claude.
    agent_files.make_folders(agent_files.folder_of(files, task))
    home = agent_files.home_of(files, task)
    assert sorted(p.name for p in home.iterdir()) == ["claude", "work"]
    assert oct(home.stat().st_mode & 0o777) == "0o700" and (home / "work" / "tmp").is_dir()


def test_the_name_is_committed_before_the_folder_moves_and_a_sweep_finishes_a_move_it_finds(
    monkeypatch, tmp_path
):
    """Review finding: the folder was renamed before its name was committed, and a sweep in that
    window removed it as the folder of no task."""
    from app.engine.tasks.agent import files as agent_files

    root = tmp_path / "assistant"
    (root / "t1").mkdir(parents=True)
    (root / "t1" / "workbook.xlsx").write_text("w")
    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    monkeypatch.setenv("AI_AGENT_FOLDERS", str(root))
    files = SimpleNamespace(directory=tmp_path / "files")
    task = SimpleNamespace(public_id="t1", design={"agentSession": "s-1"})
    seen = []
    session = SimpleNamespace(
        commit=lambda: seen.append(
            (task.design.get(agent_files.FOLDER_KEY), (root / "t1").exists())
        )
    )
    monkeypatch.setattr(agent_files, "load_task", lambda *a, **k: task)
    monkeypatch.setattr(agent_files, "_open_root", lambda root: None)
    monkeypatch.setattr(agent_files, "_shared_dir", lambda path: path.mkdir(exist_ok=True))
    assert agent_files.resumable(files, task) is False
    agent_files.ensure_folder(session, files, "t1")
    name = task.design[agent_files.FOLDER_KEY]
    assert seen == [(name, True)]
    assert not (root / "t1").exists()
    assert (agent_files.folder_of(files, task) / "workbook.xlsx").read_text() == "w"
    assert (agent_files.home_of(files, task) / "claude").is_dir() and agent_files.resumable(
        files, task
    ) is False
    # A sweep between the commit and the move finishes the move; it removes the folder of no task only
    # once it has stood for a while; and it keeps what a task names.
    (root / "t2").mkdir()
    (root / "t2" / "workbook.xlsx").write_text("w2")
    (root / "gone").mkdir()
    (root / "young").mkdir()
    old = time.time() - agent_files.FRESH_SECONDS - 10
    os.utime(root / "gone", (old, old))
    rows = [("t1", name), ("t2", "second-name")]
    swept = SimpleNamespace(execute=lambda statement: SimpleNamespace(all=lambda: rows))
    monkeypatch.setattr(agent_files, "close_idle_gates", lambda root, slots: None)
    agent_files.sweep(swept, files)
    assert (root / "second-name" / "work" / "workbook.xlsx").read_text() == "w2"
    assert not (root / "t2").exists() and not (root / "gone").exists()
    assert (root / "young").exists() and agent_files.home_of(files, task).is_dir()
    # Removing the task's folder takes its transcripts with it.
    kept = agent_files.home_of(files, task)
    (kept / "claude" / "projects").mkdir()
    agent_files.remove_folder(files, task)
    assert not kept.exists()
