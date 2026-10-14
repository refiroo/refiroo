/**
 * Add a workbook to an open draft (0.10 A5b), or the next version of a stored import profile's
 * (A5c, D85): an XLSX or CSV file uploaded to its owner (A3, D5), which supersedes the owner's
 * earlier file; its profiling is queued and the caller follows it. The workspace is the one whose
 * records the profile compares the columns with (D69), and the draft's dry run or the profile's
 * check runs against.
 */

import { useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { SourceFile, SourceFileUpload } from "@/types";
import { WorkspaceField } from "@/features/model-editor/WorkspaceField";
import { FileField } from "@/ui/FileField";
import { FormField } from "@/ui/FormField";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";

/** The files a workbook is uploaded from. */
export const WORKBOOK_ACCEPT = ".xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv";

export function AddWorkbookDialog({
  owner,
  replaces,
  defaultWorkspace,
  title,
  description,
  onUploaded,
  onClose,
}: {
  owner: SourceFileUpload["owner"];
  /** The owner's current file, which the upload supersedes. */
  replaces?: string;
  defaultWorkspace: string;
  /** In place of the draft's wording. */
  title?: string;
  description?: string;
  onUploaded: (file: SourceFile) => void;
  onClose: () => void;
}) {
  const [file, setFile] = useState<File>();
  const [workspace, setWorkspace] = useState(defaultWorkspace);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function upload() {
    if (!file) return;
    setPending(true);
    setError("");
    try {
      onUploaded(await api.uploadSourceFile(file, { owner, ...(workspace ? { workspaceKey: workspace } : {}) }));
      onClose();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal
      title={title ?? (replaces ? "Upload a newer workbook" : "Add a workbook")}
      eyebrow="Source file"
      description={
        description ??
        (replaces
          ? `Replaces ${replaces}: the profile keeps its mapping, and the columns are read again.`
          : "Its sheets and columns are profiled; then map them onto the model.")
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
        <WorkspaceField value={workspace} onChange={setWorkspace} onError={setError} />
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
