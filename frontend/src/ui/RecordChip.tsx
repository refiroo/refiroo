/**
 * A record shown inside another record's data, such as its parent in a table column, a breadcrumb or
 * a connected record (ADR-040): the record's name on its type's soft fill, in the type's ink, after a
 * small marker. The hue comes from `model/hues`; without one the chip is neutral. With `onOpen` the
 * chip is a button that opens the record.
 */

import type { ReactNode } from "react";
import type { Hue } from "@/model/hues";

export function RecordChip({ hue, children, onOpen }: { hue?: Hue; children: ReactNode; onOpen?: () => void }) {
  const content = (
    <>
      <span className="record-chip-marker" aria-hidden="true" />
      <span className="record-chip-name truncate">{children}</span>
    </>
  );
  if (onOpen)
    return (
      <button type="button" className="record-chip record-chip-link" data-hue={hue} onClick={onOpen}>
        {content}
      </button>
    );
  return (
    <span className="record-chip" data-hue={hue}>
      {content}
    </span>
  );
}
