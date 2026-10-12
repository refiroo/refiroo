/**
 * Add a workbook to an open draft (0.10 A5b): an XLSX or CSV file uploaded to the draft (A3, D5),
 * which supersedes the draft's earlier file; its profiling is queued and the source pane follows it.
 * The workspace is the one whose records the profile compares the columns with (D69) and the dry
 * run checks against.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { SourceFile, Workspace } from "@/types";
import { FileField } from "@/ui/FileField";
import { FormField } from "@/ui/FormField";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";

/** The files a workbook is uploaded from. */
export const WORKBOOK_ACCEPT = ".xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv";

export function AddWorkbookDialog({
  draftId,
  replaces,
  defaultWorkspace,
  onUploaded,
  onClose,
}: {
  draftId: string;
  /** The draft's current file, which the upload supersedes. */
  replaces?: string;
  defaultWorkspace: string;
  onUploaded: (file: SourceFile) => void;
  onClose: () => void;
}) {
  const [file, setFile] = useState<File>();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspace, setWorkspace] = useState(defaultWorkspace);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .workspaces()
      .then((page) => {
        if (!cancelled) setWorkspaces(page.items);
      })
      .catch((cause) => {
        if (!cancelled) setError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function upload() {
    if (!file) return;
    setPending(true);
    setError("");
    try {
      onUploaded(await api.uploadSourceFile(file, { owner: { draftId }, workspaceKey: workspace }));
      onClose();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal
      title={replaces ? "Upload a newer workbook" : "Add a workbook"}
      eyebrow="Source file"
      description={
        replaces
          ? `Replaces ${replaces}: the profile keeps its mapping, and the columns are read again.`
          : "Its sheets and columns are profiled; then map them onto the model."
      }
      size="compact"
      busy={pending}
      onClose={onClose}
    >
      <form
        className="dialog-body"
        onSubmit={(event) => {
          event.preventDefault();
          if (!pending) void upload();
        }}
      >
        <FormField label="Workbook" help="An XLSX workbook or a CSV file">
          {(control) => <FileField control={control} accept={WORKBOOK_ACCEPT} onFile={setFile} />}
        </FormField>
        <FormField label="Compare with the records of">
          {(control) => (
            <select {...control} value={workspace} onChange={(event) => setWorkspace(event.target.value)}>
              {workspaces.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label}
                </option>
              ))}
            </select>
          )}
        </FormField>
        {error && (
          <Notice tone="error" title="Not uploaded">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={pending}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={pending || !file}>
            {pending ? "Uploading…" : "Upload"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
