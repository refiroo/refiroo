/**
 * The workbook's three readings in the editor's column and list panels (0.17 CE1, PP-D77, the CE1
 * parity rule): fill blanks from the cell above, rows holding only one column are headings, and
 * columns read as rows, each with its Stop entry where it is on. The wording, the questions
 * (`ReadingAsks`) and the operations (`readings.ts`) are the canvas's own; every entry is one request
 * through the page's step, and a refusal is said where the page says one. A sheet no source reads has
 * nothing to set a reading on, so the entries are not shown.
 */

import { useState, type ReactNode } from "react";
import { objectTypeOf } from "@/model/outline";
import type { DraftOperation, ModelDraftOutline, ProfileSource, SourceColumn } from "@/types";
import type { DraftProfileDocument } from "@/types/sources";
import { StatusPill } from "@/ui/StatusPill";
import { HeadingPopover, UnpivotPopover } from "@/features/model-editor/ReadingAsks";
import {
  addedColumns,
  fillDownOperations,
  freeColumnName,
  headingOperations,
  readingsOf,
  unpivotDefaults,
  unpivotOperations,
} from "@/features/model-editor/readings";

/** The marks of the readings a column is on, as the column's row and panel show them. */
export function ReadingMarks({
  profile,
  sheet,
  header,
}: {
  profile: DraftProfileDocument | null | undefined;
  sheet: string;
  header: string;
}) {
  const readings = readingsOf(profile, sheet, header);
  if (!readings.length) return null;
  return (
    <>
      {readings.map((reading) => (
        <StatusPill key={reading.kind} tone="neutral" className="reading-mark">
          {reading.label}
        </StatusPill>
      ))}
    </>
  );
}

interface Common {
  profile: DraftProfileDocument | null | undefined;
  outline: ModelDraftOutline;
  /** Every column of the sheet, read from the file's profile. */
  columns: SourceColumn[] | undefined;
  sheet: string;
  busy: boolean;
  run: (operations: DraftOperation[]) => void;
}

function useAsk() {
  const [ask, setAsk] = useState<ReactNode>(null);
  return { ask, close: () => setAsk(null), open: setAsk };
}

/** The names no column of the sheet has yet, and the question's start for the two new columns. */
function takenOf({ columns, profile, sheet }: Pick<Common, "columns" | "profile" | "sheet">) {
  return new Set([
    ...(columns ?? []).flatMap((item) => (item.header ? [item.header] : [])),
    ...addedColumns(profile, sheet).map((item) => item.header),
  ]);
}

/** Read columns as rows: the question names the columns, then the two new columns. */
function unpivotAsk(
  common: Common,
  owner: ProfileSource,
  headers: string[],
  ticked: string[],
  anchor: HTMLElement,
  ui: ReturnType<typeof useAsk>,
) {
  const { profile, outline, sheet, run, columns } = common;
  ui.open(
    <UnpivotPopover
      anchor={anchor}
      choose={{ headers, ticked }}
      initial={unpivotDefaults(ticked, takenOf(common))}
      onClose={ui.close}
      targets={{
        types: outline.objectTypes.map((item) => ({ key: item.key, name: item.name })),
        initial: owner.objectTypeKey,
      }}
      onSubmit={(names, chosen, typeKey) => {
        ui.close();
        run(
          unpivotOperations(
            { sheet, columns: chosen, ...names, drop: { on: "card", typeKey: typeKey ?? owner.objectTypeKey } },
            profile,
            outline,
            (header) => columns?.find((item) => item.header === header),
          ),
        );
      }}
    />,
  );
}

/** A list's entry: its columns read as rows. */
export function ListReadings({ owner, headers, ...common }: Common & { owner: ProfileSource; headers: string[] }) {
  const ui = useAsk();
  const on = Boolean(owner.unpivot);
  return (
    <>
      {on ? (
        <button
          type="button"
          className="secondary"
          disabled={common.busy}
          onClick={() => common.run([{ kind: "clearUnpivot", source: owner.id }])}
        >
          Stop reading these columns as rows
        </button>
      ) : (
        <button
          type="button"
          className="secondary"
          disabled={common.busy || headers.length < 2}
          onClick={(event) => unpivotAsk(common, owner, headers, [], event.currentTarget, ui)}
        >
          Read these columns as rows…
        </button>
      )}
      {ui.ask}
    </>
  );
}

/** A column's entries: blanks filled, headings, and the column read as one of several that are rows. */
export function ColumnReadings({
  owner,
  header,
  headers,
  ...common
}: Common & { owner: ProfileSource; header: string; headers: string[] }) {
  const ui = useAsk();
  const { profile, outline, sheet, run, busy } = common;
  const fill = owner.fillDown?.includes(header) ?? false;
  const headings = owner.headings?.column === header;
  const wide = owner.unpivot?.columns.includes(header) ?? false;

  function headingAsk(anchor: HTMLElement) {
    const type = objectTypeOf(outline, owner.objectTypeKey);
    const parents = outline.objectTypes
      .filter((item) => item.key !== owner.objectTypeKey)
      .map((item) => ({ key: item.key, name: item.name }));
    const taken = takenOf(common);
    const initialInto = freeColumnName(`${header} heading`, taken);
    ui.open(
      <HeadingPopover
        anchor={anchor}
        column={header}
        initialInto={initialInto}
        parents={parents}
        initialParent={type?.parents.find((key) => parents.some((item) => item.key === key))}
        onClose={ui.close}
        onSubmit={(answer) => {
          ui.close();
          run(headingOperations({ sheet, column: header, rowType: owner.objectTypeKey, ...answer }, profile, outline));
        }}
      />,
    );
  }

  return (
    <>
      <button
        type="button"
        className="secondary"
        disabled={busy}
        onClick={() => run(fillDownOperations(owner, header, !fill))}
      >
        {fill ? "Stop filling blanks from the cell above" : "Fill blanks from the cell above"}
      </button>
      {headings ? (
        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={() => run([{ kind: "clearHeadingRows", source: owner.id }])}
        >
          Stop reading rows holding only this column as headings
        </button>
      ) : (
        <button type="button" className="secondary" disabled={busy} onClick={(e) => headingAsk(e.currentTarget)}>
          Rows holding only this column are headings…
        </button>
      )}
      {wide ? (
        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={() => run([{ kind: "clearUnpivot", source: owner.id }])}
        >
          Stop reading these columns as rows
        </button>
      ) : (
        <button
          type="button"
          className="secondary"
          disabled={busy || headers.length < 2}
          onClick={(event) => unpivotAsk(common, owner, headers, [header], event.currentTarget, ui)}
        >
          Read these columns as rows…
        </button>
      )}
      {ui.ask}
    </>
  );
}
