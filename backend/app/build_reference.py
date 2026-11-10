"""Which commit, and which tag, the running code was built from (0.13 BR).

An image carries them as ``REFIROO_BUILD_COMMIT`` and ``REFIROO_BUILD_TAG``, set when it is built
(the image has no ``.git``); a checkout asks ``git`` once. Either may be unknown, and then it is
``None``: the reference is only shown where it is known.
"""

import os
import re
import subprocess
from dataclasses import dataclass
from functools import lru_cache

from .config import PROJECT_ROOT

COMMIT_VARIABLE = "REFIROO_BUILD_COMMIT"
TAG_VARIABLE = "REFIROO_BUILD_TAG"
SHORT_COMMIT_LENGTH = 8
_COMMIT = re.compile(r"[0-9a-f]{7,40}")
_TAG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,99}")


@dataclass(frozen=True)
class BuildReference:
    commit: str | None
    tag: str | None


def _git(*arguments: str) -> str | None:
    try:
        done = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), *arguments],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        )
    except OSError, subprocess.SubprocessError:
        return None
    return done.stdout.strip() or None


def _clean(value: str | None, pattern: re.Pattern[str]) -> str | None:
    value = (value or "").strip()
    return value if pattern.fullmatch(value) else None


@lru_cache(maxsize=1)
def build_reference() -> BuildReference:
    commit = _clean(os.environ.get(COMMIT_VARIABLE), _COMMIT)
    tag = _clean(os.environ.get(TAG_VARIABLE), _TAG)
    if commit is None and tag is None and (PROJECT_ROOT / ".git").exists():
        commit = _clean(_git("rev-parse", "HEAD"), _COMMIT)
        tag = _clean(_git("describe", "--tags", "--exact-match", "HEAD"), _TAG)
    return BuildReference(commit[:SHORT_COMMIT_LENGTH] if commit else None, tag)
