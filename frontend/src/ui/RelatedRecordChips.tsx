/**
 * A row's related records in a relation column (0.9 K5, K5b): as many whole chips as the cell's width
 * holds, then "+N more" for the rest; no "+N more" when every record fits (D143 revised).
 *
 * In a table that knows its column's width (`CellRoom`, 0.11 X6) the cell computes how many fit from
 * the chips' texts (`ui/chipFit`) and draws once: nothing is read back from the page and no observer
 * is kept, so rows scroll in cheaply. Elsewhere (the narrow layout sizes columns to their content,
 * and outside a table) the chips are drawn once at their natural width and measured; afterwards only
 * those that fit are drawn, and a resize of the cell recomputes how many from the measured widths
 * (`fittingChips`) without measuring again. Records that change are measured again, and a cell first
 * drawn hidden is measured when it is shown. A cell too narrow for one whole chip shows the first,
 * clipped.
 */

import { useContext, useLayoutEffect, useRef, useState, useSyncExternalStore } from "react";
import type { Hue } from "@/model/hues";
import { RecordChip } from "@/ui/RecordChip";
import { chipMetricsVersion, chipsThatFit, subscribeChipMetrics } from "@/ui/chipFit";
import { fittingChips } from "@/ui/relatedFit";
import { CellRoom } from "@/ui/tableCell";

export interface RelatedChip {
  key: string;
  text: string;
  hue?: Hue;
}

/**
 * The width the chips may take: the table cell's content box. In a table sized to its content (the
 * narrow layout) the chips' own box grows with them while the cell clips it, so the cell decides.
 */
function cellWidth(element: HTMLElement): number {
  const cell = element.closest("td, th") ?? element.parentElement;
  if (!(cell instanceof HTMLElement)) return element.clientWidth;
  const style = getComputedStyle(cell);
  const padding = (Number.parseFloat(style.paddingLeft) || 0) + (Number.parseFloat(style.paddingRight) || 0);
  // In a cell edited in place (0.10 A9) the chips sit beside the edit icons, in a box only as wide as
  // what it shows: they may take the cell less the icons, or they could never grow (0.10 R).
  const editing = element.closest(".cell-edit");
  const actions = editing?.querySelector<HTMLElement>(".cell-edit-actions");
  if (editing instanceof HTMLElement && actions) {
    const gap = Number.parseFloat(getComputedStyle(editing).columnGap) || 0;
    return cell.clientWidth - padding - actions.offsetWidth - gap;
  }
  return Math.min(element.clientWidth || Number.POSITIVE_INFINITY, cell.clientWidth - padding);
}

interface Measured {
  of: string;
  widths: number[];
  gap: number;
  more: number;
}

export function RelatedRecordChips({ chips, total }: { chips: RelatedChip[]; total: number }) {
  const box = useRef<HTMLSpanElement>(null);
  const identity = chips.map((chip) => `${chip.key}:${chip.text}`).join("|") + `#${total}`;
  const [measured, setMeasured] = useState<Measured>();
  const [available, setAvailable] = useState<number>();
  const room = useContext(CellRoom);
  // Read so the cell draws again once the page's fonts have loaded and the widths are recomputed.
  useSyncExternalStore(subscribeChipMetrics, chipMetricsVersion, chipMetricsVersion);
  const computed =
    room !== undefined && chips.length
      ? chipsThatFit(
          chips.map((chip) => chip.text),
          total,
          room,
        )
      : undefined;
  const current = computed !== undefined ? undefined : measured?.of === identity ? measured : undefined;

  useLayoutEffect(() => {
    const element = box.current;
    if (!element || current || computed !== undefined) return;
    const widths = Array.from(element.querySelectorAll<HTMLElement>("[data-related-chip]")).map(
      (chip) => chip.offsetWidth,
    );
    const more = element.querySelector<HTMLElement>("[data-related-measure]")?.offsetWidth ?? 0;
    const gap = Number.parseFloat(getComputedStyle(element).columnGap) || 0;
    // A hidden cell (a column the narrow layout hides) has no widths: measured once it is shown,
    // when the resize observer changes `available`.
    if (!widths.some((width) => width > 0)) return;
    setMeasured({ of: identity, widths, gap, more });
    setAvailable(cellWidth(element));
  }, [identity, current, available, computed]);

  const measuring = computed === undefined;
  useLayoutEffect(() => {
    const element = box.current;
    if (!element || !measuring || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => setAvailable(cellWidth(element)));
    observer.observe(element);
    const cell = element.closest("td, th");
    if (cell) observer.observe(cell);
    return () => observer.disconnect();
  }, [measuring]);

  // Before measuring, and where nothing can be measured (no layout), every chip is drawn.
  const shown =
    computed ??
    (current && available
      ? fittingChips({ widths: current.widths, gap: current.gap, available, total, moreWidth: () => current.more })
      : chips.length);
  const settled = computed !== undefined || current !== undefined;
  // Before measuring, every chip is drawn: the rest of the row's records are counted.
  const hidden = total - (settled ? shown : chips.length);
  const names = chips.map((chip) => chip.text).join(", ");
  return (
    <span
      ref={box}
      className={shown === 1 ? "related-records related-records-one" : "related-records"}
      title={total > chips.length ? `${names} and ${total - chips.length} more` : names}
    >
      {chips.slice(0, settled ? shown : chips.length).map((chip) => (
        <span key={chip.key} className="related-records-chip" data-related-chip="">
          <RecordChip hue={chip.hue}>{chip.text}</RecordChip>
        </span>
      ))}
      {hidden > 0 && <span className="related-records-more">+{hidden} more</span>}
      {!settled && (
        <span className="related-records-measure" data-related-measure="" aria-hidden="true">
          +{total} more
        </span>
      )}
    </span>
  );
}
