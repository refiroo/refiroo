#!/usr/bin/env python3
"""Generate THIRD_PARTY_NOTICES.md (0.12 L1, D220).

The backend's runtime closure is read from the installed environment (the dependencies of
backend/pyproject.toml, development tools excluded), the frontend's production closure from
`npm ls --omit=dev` (the guide's the same, from guide/), and the file Scalar ships is read from its vendored copy. The four libraries
inside the psycopg binary wheel are listed by hand below, because the wheel does not carry their
licence texts. A licence outside ALLOWED stops the script, so an incompatible addition stops R.

Run from the repository root with the backend virtual environment:

    backend/.venv/bin/python scripts/third_party_notices.py          # write the file
    backend/.venv/bin/python scripts/third_party_notices.py --check  # fail if it is out of date
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from importlib import metadata
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "THIRD_PARTY_NOTICES.md"

# SPDX identifiers compatible with distribution under AGPL-3.0-or-later. LGPL-3.0-only is allowed
# for psycopg alone (dynamic use of an unmodified library).
ALLOWED = {
    "MIT",
    "MIT-0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "Apache-2.0",
    "ISC",
    "0BSD",
    "OFL-1.1",
    "PSF-2.0",
    "Python-2.0",  # the PSF licence as argparse (a guide build dependency) names it
    "BlueOak-1.0.0",  # permissive; guide build dependencies (sax, lru-cache)
    "CC0-1.0",  # public-domain dedication; mdn-data, a guide dependency
    "MPL-2.0",
    "LGPL-3.0-only",
    "Apache-2.0 OR BSD-3-Clause",
    "Apache-2.0 OR MIT",
    "BSD-3-Clause OR Apache-2.0",
}
LGPL_ONLY_FOR = {"psycopg", "psycopg-binary"}

# Python distributions whose metadata names no SPDX identifier; each was set by reading the
# distribution's own licence file (checked 2026-10-27).
PYTHON_LICENSE_OVERRIDES = {
    "pyasn1-modules": "BSD-2-Clause",
    "pyopenssl": "Apache-2.0",
    "segno": "BSD-3-Clause",
    "uvloop": "Apache-2.0 OR MIT",
}

# The libraries the psycopg binary wheel bundles. Their texts are summarised here because the wheel
# carries none; the versions are the ones the wheel for this platform bundles.
PSYCOPG_BUNDLED = [
    ("libpq", "PostgreSQL", "PostgreSQL Licence (BSD-style), (c) PostgreSQL Global Development Group"),
    ("OpenSSL 3", "Apache-2.0", "Apache License 2.0, (c) The OpenSSL Project Authors"),
    ("MIT Kerberos", "BSD-style (MIT Kerberos)", "(c) Massachusetts Institute of Technology and others"),
    ("OpenLDAP", "OpenLDAP Public License 2.8", "(c) The OpenLDAP Foundation"),
]

LICENSE_FILE = re.compile(r"(^|/)(licen[cs]e|copying|notice|authors)[^/]*$", re.IGNORECASE)


def _backend_closure() -> list[dict]:
    pyproject = tomllib.loads((ROOT / "backend" / "pyproject.toml").read_text())
    pending = [Requirement(item) for item in pyproject["project"]["dependencies"]]
    seen: dict[str, metadata.Distribution] = {}
    while pending:
        requirement = pending.pop()
        key = requirement.name.lower().replace("_", "-")
        try:
            dist = metadata.distribution(requirement.name)
        except metadata.PackageNotFoundError:
            if requirement.marker is None:
                raise SystemExit(f"{requirement.name} is required but not installed")
            continue
        extras = requirement.extras
        if key in seen and not extras:
            continue
        seen[key] = dist
        for raw in dist.requires or []:
            child = Requirement(raw)
            wanted = [""] + list(extras)
            if child.marker is None or any(
                child.marker.evaluate({"extra": extra}) for extra in wanted
            ):
                if child.name.lower().replace("_", "-") not in seen:
                    # The marker held for this parent's extras; do not test it again.
                    child.marker = None
                    pending.append(child)
    rows = []
    for key, dist in sorted(seen.items()):
        rows.append(
            {
                "name": dist.metadata["Name"],
                "version": dist.version,
                "license": _python_license(key, dist),
                "texts": _python_texts(dist),
            }
        )
    return rows


def _python_license(key: str, dist: metadata.Distribution) -> str:
    if key in PYTHON_LICENSE_OVERRIDES:
        return PYTHON_LICENSE_OVERRIDES[key]
    for value in (dist.metadata.get("License-Expression"), dist.metadata.get("License")):
        if value and value.strip() in ALLOWED:
            return value.strip()
    raise SystemExit(
        f"{key}: no licence recorded; add it to PYTHON_LICENSE_OVERRIDES after reading its licence"
    )


def _python_texts(dist: metadata.Distribution) -> list[tuple[str, str]]:
    texts = []
    for file in dist.files or []:
        if LICENSE_FILE.search(str(file)):
            try:
                texts.append((file.name, file.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError):
                continue
    return texts


def _frontend_closure() -> list[dict]:
    return _npm_closure(ROOT / "frontend")


def _guide_closure() -> list[dict]:
    """The guide's production closure (0.13 DOC1): Starlight, Astro and what they bundle into the
    built site the engine image carries. The built files do not say which package each piece came
    from, so the whole closure is listed, which includes build-time tools: more than ships, never less.
    The one exception is sharp's platform binaries (``@img/*``, libvips under LGPL-3.0-or-later): they
    resize the logo while the site is built and nothing of them is copied into the built files, so they
    are neither listed nor held to the gate (sharp itself, Apache-2.0, is)."""
    return [row for row in _npm_closure(ROOT / "guide") if not row["name"].startswith("@img/")]


def _npm_closure(frontend: Path) -> list[dict]:
    result = subprocess.run(
        ["npm", "ls", "--omit=dev", "--all", "--json", "--long"],
        cwd=frontend,
        capture_output=True,
        text=True,
        check=False,
    )
    tree = json.loads(result.stdout)
    found: dict[str, dict] = {}

    def walk(node: dict) -> None:
        for name, child in (node.get("dependencies") or {}).items():
            path = child.get("path")
            if path:
                found[path] = {"name": name, "version": child["version"], "path": Path(path)}
            walk(child)

    walk(tree)
    rows = []
    for item in sorted(found.values(), key=lambda row: row["name"]):
        package = json.loads((item["path"] / "package.json").read_text())
        license_value = package.get("license")
        if isinstance(license_value, dict):
            license_value = license_value.get("type")
        if not license_value:
            raise SystemExit(f"{item['name']}: package.json names no licence")
        texts = []
        for file in sorted(item["path"].iterdir()):
            if file.is_file() and LICENSE_FILE.search(file.name):
                texts.append((file.name, file.read_text(encoding="utf-8", errors="replace")))
        rows.append(
            {
                "name": item["name"],
                "version": item["version"],
                "license": license_value,
                "texts": texts,
            }
        )
    return rows


def _check(rows: list[dict], kind: str) -> None:
    for row in rows:
        license_value = row["license"]
        if license_value in ALLOWED:
            if license_value == "LGPL-3.0-only" and row["name"].lower() not in LGPL_ONLY_FOR:
                raise SystemExit(f"{kind} {row['name']}: LGPL-3.0-only is allowed for psycopg only")
            continue
        raise SystemExit(f"{kind} {row['name']} {row['version']}: licence {license_value!r} is not allowed")


def _section(title: str, rows: list[dict]) -> list[str]:
    lines = [f"## {title}", ""]
    for row in rows:
        lines += [f"### {row['name']} {row['version']}", "", f"Licence: {row['license']}", ""]
        for filename, text in row["texts"]:
            lines += [f"`{filename}`", "", "```text", text.strip("\n"), "```", ""]
    return lines


def render() -> str:
    backend = _backend_closure()
    frontend = _frontend_closure()
    _check(backend, "backend")
    _check(frontend, "frontend")
    guide = _guide_closure()
    _check(guide, "guide")
    scalar_dir = ROOT / "backend" / "app" / "management" / "reference" / "scalar"
    scalar = {
        "name": "@scalar/api-reference (standalone.js, vendored)",
        "version": "1.72.2",
        "license": "MIT",
        "texts": [("LICENSE", (scalar_dir / "LICENSE").read_text())],
    }
    lines = [
        "# Third-party notices",
        "",
        "refiroo is licensed under AGPL-3.0-or-later (see `LICENSE`). It ships or depends on the",
        "components below, each under its own licence. This file is generated by",
        "`scripts/third_party_notices.py` from the installed environments and regenerated for every",
        "release; it reflects the platform it was generated on.",
        "",
        "## Contents",
        "",
        f"- Backend (Python) runtime dependencies: {len(backend)}",
        f"- Frontend (browser) production dependencies: {len(frontend)}",
        f"- Guide (built site) dependencies: {len(guide)}",
        "- Vendored: Scalar API Reference",
        "- Libraries bundled inside the psycopg binary wheel: 4",
        "",
    ]
    lines += _section("Backend runtime dependencies", backend)
    lines += _section("Frontend production dependencies", frontend)
    lines += _section("Guide dependencies", guide)
    lines += _section("Vendored in the repository", [scalar])
    lines += [
        "## Libraries bundled inside the psycopg binary wheel",
        "",
        "`psycopg-binary` (LGPL-3.0-only) bundles these libraries. The wheel does not carry their",
        "licence texts; their licences are named here and are available from each project.",
        "",
    ]
    for name, license_name, note in PSYCOPG_BUNDLED:
        lines.append(f"- **{name}**: {license_name}. {note}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    text = render()
    if "--check" in sys.argv:
        if not OUTPUT.exists() or OUTPUT.read_text() != text:
            print("THIRD_PARTY_NOTICES.md is out of date; run scripts/third_party_notices.py")
            return 1
        return 0
    OUTPUT.write_text(text)
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
