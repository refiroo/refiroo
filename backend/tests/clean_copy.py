"""Run a package's final checks on a clean copy: the last commit plus the package's own changes (TS2).

Another session's unfinished edits in the shared working tree can fail a package's checks. This
makes a git worktree of ``HEAD`` outside the repository, copies the paths you name from the working
tree into it (an added or edited file arrives, a deleted one is removed there), runs the command in
it and removes the worktree. The paths are arguments because in a shared tree a package's own changes
cannot be guessed from ``git status``.

Run from ``backend/``, the command after ``--`` running in the same folder of the copy::

    .venv/bin/python -m tests.clean_copy backend/app/foo.py backend/tests/test_foo.py -- \\
        .venv/bin/python -m pytest tests/test_foo.py -q

The copy links the repository's ``backend/.venv``, ``frontend/node_modules`` and
``backend/.test-postgres`` (the one test server and its seeds: a seed's fingerprint is made from the
copy's own files, so a changed input rebuilds that seed and an unchanged one is reused).
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LINKS = ("backend/.venv", "backend/.test-postgres", "frontend/node_modules")


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(root), *arguments), capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(arguments)} failed: {result.stderr.strip()}")
    return result.stdout


def repository_root() -> Path:
    here = Path.cwd()
    return Path(_git(here, "rev-parse", "--show-toplevel").strip())


def own_files(root: Path, paths: list[str]) -> list[str]:
    """The files under ``paths`` (relative to ``root``): tracked ones, including those deleted in the
    working tree, and untracked ones that are not ignored."""
    files: list[str] = []
    for path in paths:
        relative = os.path.relpath((root / path).resolve(), root) if os.path.isabs(path) else path
        listed = _git(
            root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", relative
        )
        found = [name for name in listed.split("\0") if name]
        if not found:
            raise SystemExit(
                f"No file of the repository is under '{path}' (paths are relative to {root})."
            )
        files.extend(found)
    return sorted(set(files))


def copy_changes(root: Path, copy: Path, files: list[str]) -> None:
    for name in files:
        source, target = root / name, copy / name
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target, follow_symlinks=False)
        elif target.exists() or target.is_symlink():
            target.unlink()


def link_environment(root: Path, copy: Path) -> None:
    for name in LINKS:
        source = root / name
        if (source.exists() or source.is_symlink()) and not (copy / name).exists():
            (copy / name).symlink_to(source.resolve())


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if "--" not in arguments:
        raise SystemExit("Usage: python -m tests.clean_copy PATH... -- COMMAND...")
    split = arguments.index("--")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "paths", nargs="+", help="the package's own changed paths, relative to the repository root"
    )
    paths = parser.parse_args(arguments[:split]).paths
    command = arguments[split + 1 :]
    if not command:
        raise SystemExit("Name the command to run after '--'.")
    root = repository_root()
    files = own_files(root, paths)
    relative_cwd = Path.cwd().resolve().relative_to(root.resolve())
    parent = Path(tempfile.mkdtemp(prefix="rdm-clean-copy-"))
    copy = parent / "copy"
    _git(root, "worktree", "add", "--detach", "--quiet", str(copy), "HEAD")
    try:
        copy_changes(root, copy, files)
        link_environment(root, copy)
        print(
            f"clean copy of {_git(root, 'rev-parse', '--short', 'HEAD').strip()} plus {len(files)} files: {copy}"
        )
        return subprocess.run(command, cwd=copy / relative_cwd, check=False).returncode
    finally:
        # Links first, so removing the worktree never follows them into the repository.
        for name in LINKS:
            link = copy / name
            if link.is_symlink():
                link.unlink()
        subprocess.run(
            ("git", "-C", str(root), "worktree", "remove", "--force", str(copy)),
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ("git", "-C", str(root), "worktree", "prune"), capture_output=True, check=False
        )
        shutil.rmtree(parent, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
