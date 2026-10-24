/**
 * New move… (0.11 X4, D139): the source workspace, the target workspace and the mapping, one saved
 * between their two models or a new one. A new mapping is created from the two workspaces, the
 * engine proposes it (the inference runs as a job, followed over its stream) and its open
 * proposals are applied as steps marked Proposed before the editor opens. Opened from Moves, or
 * from a workspace's page in Settings › Workspaces with that workspace as the source.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { isFinal, useJobStream } from "@/features/jobs/useJobStream";
import { everyPage } from "@/lib/everyPage";
import { WorkspaceField } from "@/features/workspaces/WorkspaceField";
import type { ModelMappingSummary, Workspace } from "@/types";
import { FormField } from "@/ui/FormField";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";

const NEW = "";

/** A mapping key from its name: lower case words joined by hyphens. */
export function mappingKeyOf(name: string): string {
  const key = name
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return key || "mapping";
}

const modelOf = (workspace: Workspace) => `${workspace.model.releaseName} ${workspace.model.releaseVersion}`;

export function NewMoveDialog({
  source: initialSource = "",
  onClose,
  onOpened,
}: {
  /** The workspace whose data moves, when the dialog is opened from it. */
  source?: string;
  onClose: () => void;
  onOpened: (mappingKey: string, from: string, to: string) => void;
}) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [mappings, setMappings] = useState<ModelMappingSummary[]>([]);
  const [from, setFrom] = useState(initialSource);
  const [to, setTo] = useState("");
  const [chosen, setChosen] = useState<string>();
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string>();
  const [inference, setInference] = useState<{ key: string; jobId: string }>();

  useEffect(() => {
    let active = true;
    Promise.all([
      everyPage((cursor) => api.workspaces({ cursor })),
      everyPage((cursor) => api.modelMappings({ cursor })),
    ])
      .then(([items, saved]) => {
        if (!active) return;
        setWorkspaces(items);
        setMappings(saved);
      })
      .catch((cause) => active && setError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, []);

  const source = workspaces.find((item) => item.key === from);
  const target = workspaces.find((item) => item.key === to);
  const between = mappings.filter(
    (item) => item.sourceModelKey === source?.model.releaseKey && item.targetModelKey === target?.model.releaseKey,
  );
  const mappingKey = chosen ?? between[0]?.key ?? NEW;
  const suggested = source && target ? `${source.label} to ${target.label}` : "";
  const newName = name || suggested;

  async function applied(key: string) {
    try {
      const mapping = await api.modelMapping(key);
      await api.applyMappingProposals(key, mapping.version).catch((cause) => {
        if (!isApiError(cause, "NOTHING_TO_APPLY")) throw cause;
      });
      onOpened(key, from, to);
    } catch (cause) {
      setError(errorMessage(cause));
      setBusy(undefined);
    }
  }

  useJobStream(inference?.jobId, (job) => {
    if (!inference || !isFinal(job)) return;
    const key = inference.key;
    setInference(undefined);
    if (job.state === "completed") void applied(key);
    else {
      // The mapping is saved; it opens unproposed, to be completed by hand.
      setError(job.error?.message ?? "The engine could not propose the mapping.");
      setBusy(undefined);
    }
  });

  async function open() {
    if (!from || !to) return;
    setError("");
    if (mappingKey !== NEW) {
      onOpened(mappingKey, from, to);
      return;
    }
    setBusy("Saving the mapping…");
    try {
      const created = await api.createModelMapping({
        key: mappingKeyOf(newName),
        name: newName,
        sourceWorkspaceKey: from,
        targetWorkspaceKey: to,
      });
      setBusy("Proposing the mapping from the two models and their records…");
      const started = await api.proposeMapping(created.key, from, to);
      setInference({ key: created.key, jobId: started.jobId });
    } catch (cause) {
      setError(
        isApiError(cause, "MODEL_MAPPING_EXISTS")
          ? `A mapping named “${newName}” exists already; choose it above or give the new one another name.`
          : errorMessage(cause),
      );
      setBusy(undefined);
    }
  }

  return (
    <Modal title="New copy or move" onClose={onClose} busy={Boolean(busy)} size="wide">
      <form
        className="dialog-body"
        onSubmit={(event) => {
          event.preventDefault();
          void open();
        }}
      >
        <p className="muted">
          Nothing changes yet: the editor opens with a dry run of every item, and there you choose to copy or to move;
          either loads into a change set of the target for review.
        </p>
        <WorkspaceField
          label="From workspace"
          value={from}
          onChange={setFrom}
          onError={setError}
          describe={modelOf}
          holding="browse"
        />
        <WorkspaceField
          label="To workspace"
          holding="copy-move"
          value={to}
          onChange={setTo}
          onError={setError}
          describe={modelOf}
          exclude={from}
        />
        <fieldset className="migration-choice">
          <legend>Mapping</legend>
          {between.map((item) => (
            <label key={item.key} className={mappingKey === item.key ? "selected" : undefined}>
              <input
                type="radio"
                name="mapping"
                checked={mappingKey === item.key}
                onChange={() => setChosen(item.key)}
              />
              <span>
                <span>{item.name}</span>
                <small>Version {item.version}</small>
              </span>
            </label>
          ))}
          <label className={mappingKey === NEW ? "selected" : undefined}>
            <input type="radio" name="mapping" checked={mappingKey === NEW} onChange={() => setChosen(NEW)} />
            <span>
              <span>A new mapping, proposed</span>
              <small>
                The engine proposes it from the two models and the records the workspaces share; you complete it.
              </small>
            </span>
          </label>
        </fieldset>
        {mappingKey === NEW && (
          <FormField label="Name of the new mapping">
            {(control) => (
              <input {...control} value={newName} onChange={(event) => setName(event.target.value)} required />
            )}
          </FormField>
        )}
        {busy && (
          <p role="status" className="muted">
            {busy}
          </p>
        )}
        {error && (
          <Notice tone="error" focusOnMount>
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={Boolean(busy)}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={Boolean(busy) || !from || !to || !newName}>
            Open the editor
          </button>
        </div>
      </form>
    </Modal>
  );
}
