"""CI only: run one share of the backend tests, so the suite spreads over several runners.

GitHub's runner (2 cores, 8 GB) ran out of memory three quarters into the whole suite (2026-11-08).
Loaded with ``-p ci_shard`` and ``CI_SHARD=<index>/<total>`` (index from 1); a test module goes to the
share chosen by balancing the collected tests' weight, so a module stays together as
``--dist loadfile`` expects. Without
``CI_SHARD`` it selects everything.
"""

import os

import pytest


def _weight(module: str, tests: int) -> float:
    # Unit tests take milliseconds; the others clone databases and drive the application.
    return tests / 20 if module.startswith("tests/unit/") else tests


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    spec = os.environ.get("CI_SHARD")
    if not spec:
        return
    index, total = (int(part) for part in spec.split("/"))
    counts: dict[str, int] = {}
    for item in items:
        module = item.nodeid.split("::", 1)[0]
        counts[module] = counts.get(module, 0) + 1
    # Heaviest module first onto the lightest share: the same collection gives the same split.
    load = [0.0] * total
    share: dict[str, int] = {}
    for module in sorted(counts, key=lambda name: (-_weight(name, counts[name]), name)):
        lightest = min(range(total), key=lambda i: (load[i], i))
        share[module] = lightest
        load[lightest] += _weight(module, counts[module])
    keep = [item for item in items if share[item.nodeid.split("::", 1)[0]] == index - 1]
    drop = [item for item in items if share[item.nodeid.split("::", 1)[0]] != index - 1]
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep
