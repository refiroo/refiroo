/**
 * Creates a model draft from an installed release, an empty model, or an imported JSON file. An empty
 * model is a document of the newest schema language with a release identity and no elements, so the
 * editor's first operation has something to build on (0.10 A4a).
 *
 * Import and export happen in the browser: the engine reads no server filesystem, so a draft
 * enters the system either by copying a release or by the user handing over a document.
 *
 * "New from a workbook" (0.10 A5b) is the same dialog with a workbook to upload: the draft is
 * created, the workbook uploaded to it and profiled, and the editor opens on it. It starts from the
 * active release, so the applications already there stay; an empty model is a choice. What to
 * propose (0.10 A6b) is asked here and handed to the editor, which proposes and applies it once the
 * workbook is profiled; mapping by hand stays a choice.
 */

import { useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { FileField } from "@/ui/FileField";
import { FormField } from "@/ui/FormField";
import { WORKBOOK_ACCEPT } from "@/ui/AddWorkbookDialog";
import { proposeWhenProfiled } from "@/model/proposing";
import { nameOfFile, proposeRequest, ProposeFields, type ProposeChoice } from "@/ui/ProposeFields";
import { WorkspaceField } from "@/ui/WorkspaceField";
import { emptyDraftModel } from "@/model/emptyDraftModel";
import { schemaLanguages } from "@/state/useSystem";
import type { ModelDraft, ModelReleaseSummary } from "@/types";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";

export interface CreateDraftSeed {
  name: string;
  releaseId: string;
  /** Ask for a workbook to upload to the new draft (0.10 A5b). */
  workbook?: boolean;
}

export function CreateDraftDialog({
  releases,
  seed,
  onClose,
  onCreated,
}: {
  releases: ModelReleaseSummary[];
  seed: CreateDraftSeed;
  onClose: () => void;
  onCreated: (draft: ModelDraft) => void;
}) {
  const [createSource, setCreateSource] = useState<"empty" | "release" | "import">("release");
  const [createName, setCreateName] = useState(seed.name);
  const [createReleaseId, setCreateReleaseId] = useState(seed.releaseId);
  const [importText, setImportText] = useState("{}");
  const [workbook, setWorkbook] = useState<File>();
  const [propose, setPropose] = useState<ProposeChoice>({ mode: "newApplication", applicationName: "" });
  const [workspace, setWorkspace] = useState("");
  // A draft created whose workbook did not upload: trying again uploads to it, creating no second one.
  const [created, setCreated] = useState<ModelDraft>();
  const [createError, setCreateError] = useState("");
  const [pending, setPending] = useState(false);

  // A new model starts the draft empty, whatever the starting document says (it is not shown then).
  const newModel = Boolean(seed.workbook) && propose.mode === "newModel";
  const source = newModel ? "empty" : createSource;

  async function createDraft() {
    setCreateError("");
    setPending(true);
    try {
      let model: Record<string, unknown> = {};
      let baseReleaseId: string | undefined;
      if (source === "empty") model = emptyDraftModel(createName.trim(), await schemaLanguages());
      if (source === "release") {
        const release = await api.modelRelease(createReleaseId, true);
        model = release.model ?? {};
        baseReleaseId = release.id;
      } else if (source === "import") {
        const parsed: unknown = JSON.parse(importText);
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed))
          throw new Error("Imported JSON must be an object.");
        model = parsed as Record<string, unknown>;
      }
      const draft =
        created ??
        (await api.createModelDraft({
          name: createName.trim(),
          ...(baseReleaseId ? { baseReleaseId } : {}),
          model,
        }));
      setCreated(draft);
      if (workbook) {
        try {
          await api.uploadSourceFile(workbook, {
            owner: { draftId: draft.id },
            ...(workspace ? { workspaceKey: workspace } : {}),
          });
        } catch (cause) {
          throw new Error(
            `Draft ${draft.name} was created, but the workbook was not uploaded: ${errorMessage(cause)}`,
            {
              cause,
            },
          );
        }
      }
      const request = workbook ? proposeRequest(propose) : undefined;
      if (request) proposeWhenProfiled(draft.id, request);
      onCreated(draft);
    } catch (cause) {
      setCreateError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal
      title={seed.workbook ? "New from a workbook" : "Create draft"}
      eyebrow="Model candidate"
      description={
        seed.workbook
          ? "A draft with the workbook: its sheets and columns are profiled, and the engine writes a first draft of the model and its mapping into the editor. Each proposal is a step you can change or undo."
          : undefined
      }
      size={seed.workbook ? "wide" : "compact"}
      busy={pending}
      onClose={onClose}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void createDraft();
        }}
      >
        <label>
          Draft name
          <input
            autoFocus
            required
            maxLength={300}
            value={createName}
            onChange={(event) => setCreateName(event.target.value)}
          />
        </label>
        {seed.workbook && (
          <FormField label="Workbook" help="An XLSX workbook or a CSV file">
            {(control) => (
              <FileField
                control={control}
                accept={WORKBOOK_ACCEPT}
                onFile={(file) => {
                  setWorkbook(file);
                  if (file && !propose.applicationName)
                    setPropose((current) => ({ ...current, applicationName: nameOfFile(file.name) }));
                }}
              />
            )}
          </FormField>
        )}
        {seed.workbook && <ProposeFields value={propose} onChange={setPropose} start />}
        {seed.workbook && (
          <WorkspaceField
            label="Compare with the records of"
            value={workspace}
            onChange={setWorkspace}
            onError={setCreateError}
            withDefault
            help={
              propose.mode === "extend"
                ? "Columns whose values are this workspace's records are matched to their types"
                : "The dry run checks the workbook against this workspace"
            }
          />
        )}
        {!newModel && (
          <div className="dialog-pair">
            <label>
              Starting document
              <select
                value={createSource}
                onChange={(event) => setCreateSource(event.target.value as typeof createSource)}
              >
                <option value="release">Installed release</option>
                <option value="empty">Empty model</option>
                <option value="import">Import JSON</option>
              </select>
            </label>
            {createSource === "release" && (
              <label>
                Base release
                <select value={createReleaseId} onChange={(event) => setCreateReleaseId(event.target.value)}>
                  {releases.map((release) => (
                    <option key={release.id} value={release.id}>
                      {release.key}@{release.version}
                      {release.assigned ? " (active)" : ""}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
        )}
        {source === "import" && (
          <>
            <label>
              JSON document
              <textarea rows={12} value={importText} onChange={(event) => setImportText(event.target.value)} />
            </label>
            <label>
              Or choose a JSON file
              <FileField
                accept="application/json,.json"
                onFile={(file) => {
                  if (file)
                    file
                      .text()
                      .then(setImportText)
                      .catch((cause) => setCreateError(errorMessage(cause)));
                }}
              />
            </label>
          </>
        )}
        {createError && <Notice tone="error">{createError}</Notice>}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={() => onClose()}>
            Cancel
          </button>
          <button
            className="primary"
            disabled={
              pending ||
              !createName.trim() ||
              (source === "release" && !createReleaseId) ||
              (seed.workbook && !workbook)
            }
          >
            {pending ? "Creating…" : seed.workbook && propose.mode !== "none" ? "Create and propose" : "Create draft"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
