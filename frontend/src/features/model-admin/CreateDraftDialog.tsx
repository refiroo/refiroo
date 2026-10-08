/**
 * Creates a model draft from an installed release, an empty document, or an imported JSON file.
 *
 * Import and export happen in the browser: the engine reads no server filesystem, so a draft
 * enters the system either by copying a release or by the user handing over a document.
 */

import { useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { FileField } from "@/ui/FileField";
import type { ModelDraft, ModelReleaseSummary } from "@/types";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";

export interface CreateDraftSeed {
  name: string;
  releaseId: string;
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
  const [createError, setCreateError] = useState("");
  const [pending, setPending] = useState(false);

  async function createDraft() {
    setCreateError("");
    setPending(true);
    try {
      let model: Record<string, unknown> = {};
      let baseReleaseId: string | undefined;
      if (createSource === "release") {
        const release = await api.modelRelease(createReleaseId, true);
        model = release.model ?? {};
        baseReleaseId = release.id;
      } else if (createSource === "import") {
        const parsed: unknown = JSON.parse(importText);
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed))
          throw new Error("Imported JSON must be an object.");
        model = parsed as Record<string, unknown>;
      }
      onCreated(
        await api.createModelDraft({
          name: createName.trim(),
          ...(baseReleaseId ? { baseReleaseId } : {}),
          model,
        }),
      );
    } catch (cause) {
      setCreateError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal title="Create draft" eyebrow="Model candidate" size="compact" busy={pending} onClose={onClose}>
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
        <label>
          Starting document
          <select value={createSource} onChange={(event) => setCreateSource(event.target.value as typeof createSource)}>
            <option value="release">Installed release</option>
            <option value="empty">Empty JSON object</option>
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
                  {release.active ? " (active)" : ""}
                </option>
              ))}
            </select>
          </label>
        )}
        {createSource === "import" && (
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
            disabled={pending || !createName.trim() || (createSource === "release" && !createReleaseId)}
          >
            {pending ? "Creating…" : "Create draft"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
