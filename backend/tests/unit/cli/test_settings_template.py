"""The settings templates (``app/cli/settings_template.py``): the developer file and
``.env.example`` name every engine setting the catalogue holds, each at a default the engine reads,
never a retired one; ``compose.yml`` passes ``.env`` to the engine; an existing file is brought up to
date without losing a line."""

import re
from pathlib import Path

from app.cli import settings_template as templates
from app.config import SETTINGS_CATALOGUE, Settings

ROOT = Path(__file__).resolve().parents[4]
ENV_EXAMPLE = ROOT / ".env.example"
GENERATED = "# ===== Every other engine setting =====\n"
NAMED = re.compile(r"^#?([A-Z][A-Z0-9_]*)=(.*)$", re.MULTILINE)


def _named(text: str) -> dict[str, str]:
    return dict(NAMED.findall(text))


def test_each_template_names_every_setting_but_the_ones_its_target_sets():
    catalogue = {entry.name for entry in SETTINGS_CATALOGUE}
    for target, set_by in templates.SET_BY.items():
        named = _named(templates.template(target))
        assert set(named) == catalogue - set(set_by), target
        assert not set(named) & set(templates.RETIRED), target


def test_every_default_written_is_one_the_engine_reads():
    """Every line uncommented as it stands starts the engine with its defaults."""
    for target in templates.SET_BY:
        written = {
            name: value for name, value in _named(templates.template(target)).items() if value
        }
        assert Settings.from_env(written) == Settings.from_env({}).model_copy(
            update={"cursor_signing_key": Settings.from_env(written).cursor_signing_key}
        ), target


def test_env_example_holds_the_generated_template_and_names_every_setting():
    text = ENV_EXAMPLE.read_text()
    assert text.count(GENERATED) == 1, "the generated part's heading"
    assert text.split(GENERATED)[1].split("\n\n", 1)[1] == templates.template("compose"), (
        "regenerate: cd backend && .venv/bin/python -m app.cli.settings_template --for compose"
    )
    head = text.split(GENERATED)[0]
    named = _named(text) | {name: "" for name in templates.SET_BY["compose"] if name in text}
    assert {entry.name for entry in SETTINGS_CATALOGUE} <= set(named)
    for name in ("PUBLIC_URL", "SECRETS_ENCRYPTION_KEY", "RDM_CURSOR_SIGNING_KEY"):
        assert f"\n{name}=" in head, name


def test_compose_passes_env_to_the_engine():
    compose = (ROOT / "compose.yml").read_text()
    engine = compose.split("\n  engine:\n")[1].split("\n  web:\n")[0]
    # RDM_ENV_FILE names another file (the one given to `docker compose --env-file`).
    assert "\n    env_file: ${RDM_ENV_FILE:-.env}\n" in engine


def test_an_existing_file_gains_what_it_misses_and_loses_no_line(tmp_path):
    path = tmp_path / "settings.env"
    original = "DATABASE_URL=postgresql+psycopg://x\n#LOG_LEVEL=DEBUG\nINFERENCE_ASSISTANT=a:b\n"
    path.write_text(original)
    added, retired = templates.update("dev", path)
    text = path.read_text()
    assert retired == ["INFERENCE_ASSISTANT"] and "\n#INFERENCE_ASSISTANT=a:b\n" in text
    assert "LOG_LEVEL" not in added and "DATABASE_URL=postgresql+psycopg://x\n" in text
    assert set(added) == {e.name for e in SETTINGS_CATALOGUE} - {
        "LOG_LEVEL",
        *templates.SET_BY["dev"],
    }
    assert templates.update("dev", path) == ([], []) and path.read_text() == text
