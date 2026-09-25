"""Seed the Track S volume fixture into a database for a browser runner (Base 0.8 S5).

Migrates ``--database`` with the volume model as its active release, bulk-writes the fixture at
``--scale`` and prints the dataset's public identifiers as JSON, so a browser runner can start the
real server over the same database and address known records::

    cd backend && .venv/bin/python tests/volume_seed.py --scale 0.1 --database /tmp/v.db --model /tmp/m.json
"""

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from volume_fixture import scaled_shape, seed_volume, volume_model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--scale", type=float, default=0.1, help="1 is the plan's full volume")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True, help="where to write the volume model")
    arguments = parser.parse_args()

    arguments.database.unlink(missing_ok=True)
    arguments.model.write_text(json.dumps(volume_model()))
    os.environ["DATABASE_URL"] = f"sqlite:///{arguments.database}"
    os.environ["RDM_MODEL_PATH"] = str(arguments.model)

    from fastapi.testclient import TestClient

    from app.db import get_engine
    from app.main import create_app

    with TestClient(create_app()):
        dataset = seed_volume(get_engine(), scaled_shape(arguments.scale))
    get_engine().dispose()
    print(json.dumps(asdict(dataset)))


if __name__ == "__main__":
    main()
