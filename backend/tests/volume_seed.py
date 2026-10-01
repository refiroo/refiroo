"""A database holding the Track S volume fixture for a browser runner (Base 0.8 S5; PG2).

Clones the volume seed at ``--scale`` from the seed store on the development server (built once,
``browser_seeds.py``), writes the volume model to ``--model`` and prints the dataset's public
identifiers as JSON with ``database_url``, so a browser runner can start the real server over that
database and address known records; the runner drops it when it ends::

    cd backend && .venv/bin/python tests/volume_seed.py --scale 0.1 --model /tmp/m.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from browser_seeds import clone


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--scale", type=float, default=0.1, help="1 is the plan's full volume")
    parser.add_argument("--model", type=Path, required=True, help="where to write the volume model")
    arguments = parser.parse_args()
    print(json.dumps(clone("volume", model=arguments.model, scale=arguments.scale)))


if __name__ == "__main__":
    main()
