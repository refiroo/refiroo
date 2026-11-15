/**
 * Proposing a change (0.12 Z5, D324, D325): a person who changes records only in change sets (a
 * Contributor, D231) edits from live data through their own change set. "Propose a change"
 * continues their newest open one, found by `createdBy`; with none, a small dialog names a new one.
 * Change sets stay shared (D255); "their own" only finds one.
 */

import { useEffect, useState, type FormEvent } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { counted } from "@/lib/count";
import { newestFirst } from "@/model/newestFirst";
import type { ChangeSet } from "@/types";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";

export interface OwnChangeSet {
  changeSet?: ChangeSet;
  /** The records and relationships it changes, once counted. */
  changes?: number;
}

/** The person's newest open change set in `workspaceKey`, while `enabled`; read again on `refreshToken`. */
export function useOwnChangeSet(
  workspaceKey: string,
  personId: string | undefined,
  enabled: boolean,
  refreshToken = 0,
): OwnChangeSet {
  const [own, setOwn] = useState<OwnChangeSet & { for?: string }>({});
  const target = enabled && personId ? `${workspaceKey}:${personId}:${refreshToken}` : undefined;
  useEffect(() => {
    if (!target) return;
    let active = true;
    Promise.resolve()
      .then(() => api.changeSets(workspaceKey, undefined, personId))
      .then(async (page) => {
        const newest = newestFirst(page.items, "updatedAt")[0];
        const changes = newest
          ? await Promise.all([
              api.objectChanges(newest.id, { pageSize: 1, includeTotal: true }),
              api.relationChanges(newest.id, { pageSize: 1, includeTotal: true }),
            ]).then(
              ([records, relations]) => (records.totalCount ?? 0) + (relations.totalCount ?? 0),
              () => undefined,
            )
          : undefined;
        if (active) setOwn({ for: target, changeSet: newest, changes });
      })
      .catch(() => active && setOwn({ for: target }));
    return () => {
      active = false;
    };
  }, [target, workspaceKey, personId]);
  return own.for === target ? own : {};
}

/** How the band and the button name a change set and its count: "Spring determinations · 3 changes". */
export function ownChangeSetText(own: OwnChangeSet): string | undefined {
  if (!own.changeSet) return undefined;
  const name = own.changeSet.name || "Untitled change set";
  if (own.changes === undefined) return `Your change set: ${name}`;
  return `Your change set: ${name} · ${counted(own.changes, "change")}`;
}

/** The first proposal: name the person's change set, create it, then go on editing in it. */
export function ProposeDialog({
  workspaceKey,
  workspaceLabel,
  personName,
  onClose,
  onStarted,
}: {
  workspaceKey: string;
  workspaceLabel: string;
  personName?: string;
  onClose: () => void;
  onStarted: (changeSet: ChangeSet) => void;
}) {
  const suggested = personName ? `Changes by ${personName}` : "My changes";
  const [name, setName] = useState(suggested);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  async function start(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      onStarted(await api.createChangeSet(workspaceKey, name.trim() || suggested));
    } catch (cause) {
      setError(errorMessage(cause));
      setPending(false);
    }
  }
  return (
    <Modal title="Propose a change" busy={pending} dirty={name !== suggested} onClose={onClose} size="compact">
      <form onSubmit={start}>
        <p>
          Your changes go into a change set of your own, not live. Someone who holds Publish in {workspaceLabel}{" "}
          publishes it.
        </p>
        <label>
          Change set name
          <input autoFocus value={name} maxLength={300} onChange={(event) => setName(event.target.value)} />
        </label>
        {error && <Notice tone="error">{error}</Notice>}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending}>
            Start and edit
          </button>
        </div>
      </form>
    </Modal>
  );
}
