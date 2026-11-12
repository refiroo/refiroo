/**
 * New workspace from a workbook (0.17 PL4, PP-D1): a side sheet in two steps. First the file and a name
 * (prefilled from the file's name); refiroo then reads the workbook, proposes its lists and checks every
 * row, and "What refiroo found" says what loads and what does not and why. Create workspace installs the
 * model, creates the workspace and loads the workbook into its live data in one step; Adjust opens the
 * draft on the workbook canvas (PL3b), whose toolbar finishes with the same step;
 * Cancel removes the draft the look made. Under More ways to start sits today's way of making a
 * workspace on an installed model.
 */

import { useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { WORKBOOK_ACCEPT } from "@/features/model-editor/AddWorkbookDialog";
import {
  findings,
  lookAtWorkbook,
  rememberWorkspaceLoad,
  workspaceNameOfFile,
  type LookedAt,
} from "@/features/workspaces/fromWorkbook";
import type { RouteState } from "@/types";
import { Disclosure } from "@/ui/Disclosure";
import { FileField } from "@/ui/FileField";
import { FormField } from "@/ui/FormField";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";

/** The problems an install refusal lists: a model's diagnostics, or a profile's problems. */
export function problemsOf(cause: unknown): string[] {
  if (!isApiError(cause)) return [];
  const details = cause.details;
  const list = Array.isArray(details) ? details : (details as { problems?: unknown } | undefined)?.problems;
  if (!Array.isArray(list)) return [];
  return list.flatMap((item: { message?: unknown; path?: unknown }) =>
    typeof item.message === "string"
      ? [typeof item.path === "string" ? `${item.message} (${item.path})` : item.message]
      : [],
  );
}

/**
 * The one route that installs a draft, creates a workspace and loads the draft's workbook into it
 * (PL4): the sheet's Create workspace and the canvas's Create workspace… both end here. The load's
 * job is remembered for the new workspace's page; the new workspace's key comes back.
 */
export async function createWorkspaceFromDraft(
  draft: { id: string; version: number },
  name: string,
  fileName: string,
): Promise<string> {
  const created = await api.createWorkspaceFromWorkbook({
    draftId: draft.id,
    expectedVersion: draft.version,
    name,
  });
  rememberWorkspaceLoad(created.workspace.key, created.job.id, fileName);
  return created.workspace.key;
}

export function NewFromWorkbook({
  onClose,
  onCreated,
  onNavigate,
  onOtherWays,
}: {
  onClose: () => void;
  /** The workspace exists and its workbook is loading: land on its page. */
  onCreated: (workspaceKey: string) => void;
  /** Adjust: opens the draft on the workbook canvas. */
  onNavigate: (route: RouteState) => void;
  /** More ways to start: today's dialog for a workspace on an installed model. */
  onOtherWays: () => void;
}) {
  const [file, setFile] = useState<File>();
  const [name, setName] = useState("");
  const [stage, setStage] = useState("");
  const [looked, setLooked] = useState<LookedAt>();
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [problems, setProblems] = useState<string[]>([]);

  const found = looked?.dryRun ? findings(looked.dryRun, looked.typeNames, looked.reasons) : undefined;

  function fail(cause: unknown) {
    setError(errorMessage(cause));
    setProblems(problemsOf(cause));
  }

  async function look() {
    if (!file || !name.trim()) return;
    setError("");
    setProblems([]);
    setWorking(true);
    try {
      const result = await lookAtWorkbook(file, name.trim(), setStage);
      setLooked(result);
      if (result.dryRun && result.dryRun.state !== "completed")
        setError(result.dryRun.error?.message ?? "refiroo could not check the rows of this workbook.");
    } catch (cause) {
      fail(cause);
    } finally {
      setWorking(false);
      setStage("");
    }
  }

  async function create() {
    if (!looked || !file) return;
    setError("");
    setProblems([]);
    setWorking(true);
    try {
      onCreated(await createWorkspaceFromDraft(looked.draft, name.trim(), file.name));
    } catch (cause) {
      fail(cause);
      setWorking(false);
    }
  }

  async function discard() {
    // The draft the look made goes with a Cancel; one that cannot be removed is left to Settings › Model.
    if (looked) await api.deleteModelDraft(looked.draft.id, looked.draft.version).catch(() => undefined);
    onClose();
  }

  const heading = "New workspace from a workbook";
  if (!looked)
    return (
      <Modal
        title={heading}
        eyebrow="New workspace"
        description="Drop a workbook and name the workspace. refiroo reads it and shows what it found before anything is created."
        busy={working}
        onClose={onClose}
      >
        <form
          className="dialog-body fw-body"
          onSubmit={(event) => {
            event.preventDefault();
            if (!working) void look();
          }}
        >
          <FormField label="Workbook" help="An XLSX workbook or a CSV file">
            {(control) => (
              <FileField
                control={control}
                accept={WORKBOOK_ACCEPT}
                disabled={working}
                onFile={(chosen) => {
                  setFile(chosen);
                  if (chosen && !name.trim()) setName(workspaceNameOfFile(chosen.name));
                }}
              />
            )}
          </FormField>
          <label>
            Name
            <input
              required
              maxLength={300}
              value={name}
              disabled={working}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          {working && <p role="status">{stage || "Working"}…</p>}
          {error && (
            <Notice tone="error" title="Not read">
              {error}
              <ProblemList problems={problems} />
            </Notice>
          )}
          <div className="fw-more">
            <Disclosure label="More ways to start" variant="link">
              <p className="muted-text">
                A workspace on a model that is installed already, or one without data, is made in Settings.
              </p>
              <button type="button" className="secondary" disabled={working} onClick={onOtherWays}>
                New workspace on an installed model
              </button>
            </Disclosure>
          </div>
          <div className="dialog-actions">
            <button type="button" className="secondary" disabled={working} onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="primary" disabled={working || !file || !name.trim()}>
              {working ? "Reading…" : "Read the workbook"}
            </button>
          </div>
        </form>
      </Modal>
    );

  const ready = looked.dryRun?.state === "completed" && found !== undefined && found.lists.length > 0;
  return (
    <Modal
      title={heading}
      eyebrow="New workspace"
      description={`${name.trim()} · ${file?.name ?? "the workbook"}`}
      busy={working}
      onClose={() => void discard()}
    >
      <div className="dialog-body fw-body">
        <section className="fw-found" aria-labelledby="fw-found-title">
          <h3 id="fw-found-title">What refiroo found</h3>
          {found && found.lists.length > 0 ? (
            <>
              <p className="fw-total">
                {found.rows.toLocaleString("en")} {found.rows === 1 ? "row" : "rows"} checked, every one:{" "}
                {found.refused === 0
                  ? "all of them load."
                  : `${found.refused.toLocaleString("en")} ${found.refused === 1 ? "does" : "do"} not load.`}
              </p>
              <ul className="fw-lists">
                {found.lists.map((list) => (
                  <li key={list.key} className="fw-list">
                    <div className="fw-list-head">
                      <strong>{list.list}</strong>
                      <small>
                        {list.sheet ? `from ${list.sheet} · ` : ""}
                        {list.rows.toLocaleString("en")} {list.rows === 1 ? "row" : "rows"}
                      </small>
                    </div>
                    <small>
                      {list.loads.toLocaleString("en")} {list.loads === 1 ? "row loads" : "rows load"}
                      {list.skipped > 0 ? `, ${list.skipped.toLocaleString("en")} skipped for want of a key` : ""}
                    </small>
                    {list.refused.length > 0 && (
                      <ul className="fw-refused" aria-label={`Rows of ${list.list} that do not load`}>
                        {list.refused.map((item) => (
                          <li key={item.code}>
                            {item.rows.toLocaleString("en")} {item.rows === 1 ? "row does" : "rows do"} not load:{" "}
                            {item.reason ?? item.code}
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="fw-total">
              refiroo found no list in this workbook by itself. Choose Adjust: on the canvas, drag a sheet onto the
              board to make a list of its rows, then shape it.
            </p>
          )}
        </section>
        {error && (
          <Notice tone="error" title="The workspace was not created">
            {error}
            <ProblemList problems={problems} />
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={working} onClick={() => void discard()}>
            Cancel
          </button>
          <button
            type="button"
            className={ready ? "secondary" : "primary"}
            disabled={working}
            onClick={() =>
              onNavigate({ kind: "settings", page: "model", draftId: looked.draft.id, editor: { show: "canvas" } })
            }
          >
            Adjust
          </button>
          {/* With nothing to create from, Adjust is the one way on: the button that could not finish is not shown. */}
          {ready && (
            <button type="button" className="primary" disabled={working} onClick={() => void create()}>
              {working ? "Creating…" : "Create workspace"}
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}

export function ProblemList({ problems }: { problems: string[] }) {
  if (problems.length === 0) return null;
  return (
    <ul className="fw-problems">
      {problems.slice(0, 8).map((problem) => (
        <li key={problem}>{problem}</li>
      ))}
    </ul>
  );
}
