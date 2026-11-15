/**
 * Why the rows of one list were refused (0.17 PL3b): each reason with the rows it refused and the
 * engine's own words from the first of them. "See the rows" opens the dry run's rows behind it; a
 * reason that is a value no record matches also names the wrong values, and the column they stand in
 * can be corrected with the editor's value map. Nothing here changes the draft: the page does.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { count, plural } from "@/lib/count";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";
import { reasonOf, wrongValuesOf, type WrongValues } from "./canvasModel";

export interface Reason {
  code: string;
  rows: number;
  /** The dry run's number for the source whose rows were refused. */
  source: number;
}

interface Read extends Reason {
  message?: string;
  wrong: WrongValues[];
}

export function RefusedDialog({
  draftId,
  list,
  reasons,
  onSeeRows,
  onCorrect,
  onClose,
}: {
  draftId: string;
  list: string;
  reasons: readonly Reason[];
  onSeeRows: (reason: Reason) => void;
  /** Open the value map of a column with the wrong values the refusal named. */
  onCorrect: (reason: Reason, found: WrongValues) => void;
  onClose: () => void;
}) {
  const [read, setRead] = useState<Read[]>();
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const answered: Read[] = [];
        for (const reason of reasons) {
          // The first refused rows are the evidence: the reason in the engine's words and the values named.
          const page = await api.modelDraftDryRunRows(draftId, {
            source: reason.source,
            status: "rejected",
            code: reason.code,
            pageSize: 100,
          });
          answered.push({ ...reason, message: reasonOf(page.items), wrong: wrongValuesOf(page.items) });
        }
        if (!cancelled) setRead(answered);
      } catch (cause) {
        if (!cancelled) setError(errorMessage(cause));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [draftId, reasons]);
  return (
    <Modal
      title={`${list}: rows refused`}
      eyebrow="Dry run"
      description="Every row was checked. These are the reasons, with the rows each one refused."
      size="wide"
      onClose={onClose}
    >
      <div className="dialog-body canvas-refused">
        {error && <Notice tone="error">{error}</Notice>}
        {!read && !error && <Skeleton lines={3} label="Reading the refused rows" />}
        <ul className="canvas-refused-list">
          {(read ?? []).map((item) => (
            <li key={`${item.source}:${item.code}`} className="canvas-refused-reason">
              <p>
                <strong>{count(item.rows)}</strong> {plural(item.rows, "row")} · {item.message ?? item.code}
              </p>
              {item.wrong.map((found) => (
                <p key={found.column} className="canvas-refused-wrong">
                  Not found in <strong>{found.column}</strong>:{" "}
                  {found.values
                    .slice(0, 6)
                    .map((value) => `“${value.text}” (${value.rows})`)
                    .join(", ")}
                  {found.values.length > 6 ? ` and ${found.values.length - 6} more` : ""}
                </p>
              ))}
              <div className="canvas-refused-actions wrap-row">
                <button type="button" className="secondary" onClick={() => onSeeRows(item)}>
                  See the rows
                </button>
                {item.wrong.map((found) => (
                  <button key={found.column} type="button" className="secondary" onClick={() => onCorrect(item, found)}>
                    Correct the values of {found.column}…
                  </button>
                ))}
              </div>
            </li>
          ))}
        </ul>
        <div className="dialog-actions">
          <button type="button" className="primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </Modal>
  );
}
