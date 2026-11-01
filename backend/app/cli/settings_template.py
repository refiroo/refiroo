"""Print every engine setting as a commented template, from the settings catalogue (``config.py``).

The developer instance's ``.dev/settings.env`` (``scripts/dev.sh settings``) and the reference
installation's ``.env.example`` are written from here, so a setting added to the catalogue reaches
both, each with its one-line description and its default; ``tests/unit/cli/test_settings_template.py``
fails while either misses one. Retired settings are never offered.

    python -m app.cli.settings_template --for dev
    python -m app.cli.settings_template --for compose
    python -m app.cli.settings_template --for dev --update .dev/settings.env

``--update`` keeps every line of an existing file, appends the settings it does not name yet, and
comments out a retired setting it still sets, since the engine refuses to start with one.
"""

import argparse
import re
import sys
import textwrap
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import (
    DEFAULT_SOURCE_CODE_URL,
    RETIRED_ASSISTANT_SETTINGS,
    RETIRED_ENCRYPTION_KEY,
    SETTINGS_CATALOGUE,
    CatalogueEntry,
    Settings,
)

# The group headings, in the catalogue's order (OPERATIONS § Settings).
HEADINGS = {
    "runtime": "Runtime",
    "capabilities": "Capability groups: what the engine serves",
    "limits": "Batch and job limits",
    "webhooks": "Webhook subscriptions",
    "ai": "AI: the assistant is off unless AI_AGENT_COMMAND is set, proposals unless AI_PROVIDER is (OPERATIONS § AI proposals)",
}

# Settings a target writes itself, so its template leaves them out. The developer file sets the
# database and the key above the template; compose.yml sets these from the top of .env.example or
# computes them, and the engine image sets the model path and the job file directory.
SET_BY = {
    "dev": ("DATABASE_URL", "SECRETS_ENCRYPTION_KEY"),
    "compose": (
        "DATABASE_URL",
        "SECRETS_ENCRYPTION_KEY",
        "RDM_CURSOR_SIGNING_KEY",
        "PUBLIC_URL",
        "CORS_ORIGINS",
        "RDM_MODEL_PATH",
        "JOB_FILE_DIR",
    ),
}

RETIRED = {
    RETIRED_ENCRYPTION_KEY: "SECRETS_ENCRYPTION_KEY",
    **RETIRED_ASSISTANT_SETTINGS,
}

_NAMED = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*)=")


def _default(entry: CatalogueEntry, defaults: Settings) -> str:
    """The default as the environment writes it; empty for a secret or a value this machine works
    out (a path, a generated key, the running version's source)."""
    if entry.secret:
        return ""
    value: Any = getattr(defaults, entry.field)
    # A path or the version's own source address is worked out where the engine runs.
    if isinstance(value, Path) or value is None or value == DEFAULT_SOURCE_CODE_URL:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, tuple | list):
        return ",".join(str(item) for item in value)
    return str(value)


def entries(target: str) -> list[CatalogueEntry]:
    return [entry for entry in SETTINGS_CATALOGUE if entry.name not in SET_BY[target]]


def render(chosen: list[CatalogueEntry]) -> str:
    """The settings, grouped under their headings, each a comment and a commented default."""
    defaults = Settings.from_env({})
    lines: list[str] = []
    for group, heading in HEADINGS.items():
        members = [entry for entry in chosen if entry.group == group]
        if not members:
            continue
        lines += ["", f"# --- {heading}", ""]
        for entry in members:
            note = " Secret: never shown, keep it out of images and logs." if entry.secret else ""
            lines += textwrap.wrap(
                f"{entry.description}.{note}", 98, initial_indent="# ", subsequent_indent="# "
            )
            lines.append(f"#{entry.name}={_default(entry, defaults)}")
    return "\n".join(lines).lstrip("\n") + "\n"


def template(target: str) -> str:
    return render(entries(target))


def update(target: str, path: Path) -> tuple[list[str], list[str]]:
    """Append the settings ``path`` does not name and comment out the retired ones it sets; the
    names added and the names retired."""
    text = path.read_text()
    named = {match.group(1) for line in text.splitlines() if (match := _NAMED.match(line))}
    retired: list[str] = []
    kept: list[str] = []
    for line in text.splitlines():
        match = _NAMED.match(line)
        name = match.group(1) if match and not line.lstrip().startswith("#") else None
        if name in RETIRED:
            retired.append(name)
            kept.append(f"# Retired: the engine refuses to start with {name}; set {RETIRED[name]}.")
            kept.append(f"#{line}")
        else:
            kept.append(line)
    missing = [entry for entry in entries(target) if entry.name not in named]
    text = "\n".join(kept).rstrip("\n") + "\n"
    if missing:
        text += f"\n# Added by scripts/dev.sh settings on {datetime.now(UTC).date().isoformat()}: settings this file did not list.\n"
        text += "\n" + render(missing)
    if missing or retired:
        path.write_text(text)
    return [entry.name for entry in missing], retired


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--for", dest="target", choices=sorted(SET_BY), required=True)
    parser.add_argument("--update", type=Path, help="Bring an existing settings file up to date")
    arguments = parser.parse_args(argv)
    if arguments.update is None:
        sys.stdout.write(template(arguments.target))
        return 0
    added, retired = update(arguments.target, arguments.update)
    for name in retired:
        print(
            f"Commented out {name}: retired, the engine would refuse to start (set {RETIRED[name]})."
        )
    if added:
        print(f"Added {len(added)} settings, commented out at their defaults: {', '.join(added)}.")
    if not added and not retired:
        print("Every setting is listed; nothing changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
