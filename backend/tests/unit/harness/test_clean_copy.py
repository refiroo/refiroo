"""The clean copy holds the last commit plus the named paths, and is removed after (TS2)."""

import ast
import subprocess
import sys
from pathlib import Path

import clean_copy


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(("git", "-C", str(root), *arguments), check=True, capture_output=True)


def test_the_copy_has_the_commit_and_only_the_named_changes(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "backend").mkdir(parents=True)
    _git(root, "init", "--quiet")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    for name in ("mine.txt", "theirs.txt", "removed.txt"):
        (root / "backend" / name).write_text("committed")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "base")
    (root / "backend/mine.txt").write_text("package change")
    (root / "backend/theirs.txt").write_text("another session's unfinished edit")
    (root / "backend/removed.txt").unlink()
    (root / "backend/new.txt").write_text("added")
    monkeypatch.chdir(root / "backend")
    probe = (
        "from pathlib import Path;"
        "print({n: (Path(n).read_text() if Path(n).exists() else None)"
        " for n in ('mine.txt', 'theirs.txt', 'removed.txt', 'new.txt')})"
    )
    printed = tmp_path / "out.txt"
    code = clean_copy.main(
        [
            "backend/mine.txt",
            "backend/removed.txt",
            "backend/new.txt",
            "--",
            "sh",
            "-c",
            f'{sys.executable} -c "{probe}" > {printed}',
        ]
    )
    assert code == 0
    assert ast.literal_eval(printed.read_text()) == {
        "mine.txt": "package change",
        "theirs.txt": "committed",
        "removed.txt": None,
        "new.txt": "added",
    }
    worktrees = subprocess.run(
        ("git", "-C", str(root), "worktree", "list"), capture_output=True, text=True, check=True
    ).stdout
    assert len(worktrees.strip().splitlines()) == 1  # the copy is removed
