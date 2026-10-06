/**
 * A record shown inside another record's data, such as its parent in a table column (ADR-040): the
 * record's name on its type's soft fill, in the type's ink, after a small marker. The hue comes from
 * `model/hues`; without one the chip is neutral.
 */

import type { ReactNode } from "react";
import type { Hue } from "@/model/hues";

export function RecordChip({ hue, children }: { hue?: Hue; children: ReactNode }) {
  return (
    <span className="record-chip" data-hue={hue}>
      <span className="record-chip-marker" aria-hidden="true" />
      <span className="record-chip-name">{children}</span>
    </span>
  );
}
