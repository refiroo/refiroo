"""The Prometheus text exposition format, version 0.0.4 (Product 0.11 O1, D193).

Written here rather than taken from ``prometheus_client``: ``/metrics`` exposes figures every
process reported through the database, not one process's registry, so only the format is needed.
"""

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"
MetricKind = Literal["counter", "gauge", "histogram"]
Labels = Mapping[str, str]


@dataclass
class Family:
    """One metric and its samples. A histogram's samples are added with ``histogram``."""

    name: str
    kind: MetricKind
    help: str
    samples: list[tuple[str, Labels, float]] = field(default_factory=list)

    def add(self, labels: Labels, value: float) -> None:
        self.samples.append((self.name, labels, value))

    def histogram(
        self, labels: Labels, bounds: Sequence[float], counts: Sequence[int], total: float
    ) -> None:
        """Add a histogram from its per-bucket counts (not cumulative; the last count is above
        every bound) and the sum of its observations."""
        running = 0
        for bound, count in zip((*bounds, math.inf), counts, strict=True):
            running += count
            self.samples.append((f"{self.name}_bucket", {**labels, "le": _number(bound)}, running))
        self.samples.append((f"{self.name}_sum", labels, total))
        self.samples.append((f"{self.name}_count", labels, running))


def render(families: Iterable[Family]) -> str:
    lines: list[str] = []
    for family in families:
        lines.append(f"# HELP {family.name} {_escape_help(family.help)}")
        lines.append(f"# TYPE {family.name} {family.kind}")
        for name, labels, value in family.samples:
            lines.append(f"{name}{_labels(labels)} {_number(value)}")
    return "\n".join(lines) + "\n"


def _labels(labels: Labels) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{key}="{_escape_label(value)}"' for key, value in labels.items())
    return "{" + inner + "}"


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _escape_help(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n")


def _number(value: float) -> str:
    if math.isinf(value):
        return "+Inf" if value > 0 else "-Inf"
    if math.isnan(value):
        return "NaN"
    if float(value).is_integer():
        return str(int(value))
    return repr(float(value))
