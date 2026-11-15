/**
 * What Install, Activate and Apply say alike about a workspace's release change (0.11 M5, D26; 0.16 WM1): its open change
 * sets that stay on the release it runs now, and the first reasons the data does not fit.
 */

import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { plural } from "@/lib/count";
import { attributeTypeName, relationTypeName, suggestedVersion, typeName } from "@/model/outline";
import type { ChangeSet, DraftOperation, ModelChange, ModelDiagnostic, ModelDraftOutline } from "@/types";
import { FormField } from "@/ui/FormField";
import { everyPage } from "@/lib/everyPage";
import { Notice } from "@/ui/Notice";
import { useState, type ReactNode } from "react";

/** Every open change set of the workspace, page by page (a workspace holds few). */
export function openChangeSets(workspaceKey: string): Promise<ChangeSet[]> {
  return everyPage((cursor) => api.changeSets(workspaceKey, cursor));
}

/** The candidate releases by model, the workspace's own model first, each newest first (M6). */

/** The workspace's open change sets that stay on the release it runs now (D26). */
export function LeftBehindChangeSets({
  workspaceLabel,
  version,
  changeSets,
}: {
  workspaceLabel: string;
  version: string;
  changeSets: ChangeSet[];
}) {
  return (
    <section aria-labelledby="activate-left-behind" className="activate-left-behind">
      <h3 id="activate-left-behind" className="install-heading">
        Change sets left on {version}
      </h3>
      {changeSets.length ? (
        <>
          <p className="muted">
            These open change sets of {workspaceLabel} stay pinned to the release it runs now. They cannot be published
            until each is moved to the new release or discarded.
          </p>
          <ul>
            {changeSets.map((item) => (
              <li key={item.id}>
                {item.name ?? "Unnamed change set"} · version {item.version}
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="muted">None: {workspaceLabel} has no open change set.</p>
      )}
    </section>
  );
}

/** The first reasons the data does not fit, in plain words; the release's page lists every one. */
const REASONS_SHOWN = 5;

export function MigrationReasons({ diagnostics }: { diagnostics: ModelDiagnostic[] }) {
  if (!diagnostics.length) return null;
  const more = diagnostics.length - REASONS_SHOWN;
  return (
    <ul className="migration-reasons">
      {diagnostics.slice(0, REASONS_SHOWN).map((item, index) => (
        <li key={`${item.path}:${index}`}>{item.message}</li>
      ))}
      {more > 0 && (
        <li>
          And {more} more {plural(more, "reason")}, listed on the release's page.
        </li>
      )}
    </ul>
  );
}

export const MIGRATION_NEEDED = "Activation needs a migration";

/**
 * The verdict "the data does not fit": a warning titled "Activation needs a migration" (SR-D2); each dialog writes
 * its own sentences inside. A release of another model passes its own title.
 */
export function ActivationVerdict({ title = MIGRATION_NEEDED, children }: { title?: string; children: ReactNode }) {
  return (
    <Notice tone="warning" title={title}>
      {children}
    </Notice>
  );
}

const COLLECTIONS: Record<string, string> = {
  objectTypes: "Object types",
  attributeTypes: "Attribute types",
  relationTypes: "Relation types",
  objectTypeRelations: "Allowed relations",
  applications: "Applications",
  consumerApis: "Consumer APIs",
};

/** The differences in a line per collection and kind: "Object types added: Unit, Pack". */
export function summarizeChanges(
  changes: ModelChange[],
  outline: ModelDraftOutline,
): { label: string; names: string[] }[] {
  const lines = new Map<string, Set<string>>();
  for (const change of changes) {
    const parts = change.path
      .split("/")
      .slice(1)
      .map((part) => part.replaceAll("~1", "/").replaceAll("~0", "~"));
    const collection = parts[0];
    if (!collection || !(collection in COLLECTIONS)) continue;
    const width = collection === "objectTypeRelations" ? 4 : 2;
    if (parts.length < width) continue;
    const whole = parts.length === width;
    const kind = whole ? change.kind : "changed";
    const name =
      collection === "objectTypes"
        ? typeName(outline, parts[1])
        : collection === "objectTypeRelations"
          ? `${typeName(outline, parts[2])} → ${typeName(outline, parts[3])}`
          : collection === "applications"
            ? (outline.applications.find((a) => a.key === parts[1])?.name ?? parts[1])
            : collection === "consumerApis"
              ? (outline.consumerApis.find((a) => a.key === parts[1])?.name ?? parts[1])
              : collection === "attributeTypes"
                ? attributeTypeName(outline, parts[1])
                : relationTypeName(outline, parts[1]);
    const label = `${COLLECTIONS[collection]} ${kind}`;
    lines.set(label, (lines.get(label) ?? new Set()).add(name));
  }
  return [...lines].map(([label, names]) => ({ label, names: [...names] }));
}

/** The diagnostic of a kept earlier version that would read differently (0.13 DF3). */
const KEPT_VERSION_CHANGED = "CONSUMER_KEPT_VERSION_CHANGED";
/** The warning for an earlier version the release stops serving (0.13 DF3). */
export const KEPT_VERSION_STOPPED = "CONSUMER_VERSION_STOPPED";

/** The consumer contract diagnostics by the consumer API their pointer names. */
export function contractsByApi(diagnostics: ModelDiagnostic[]): Map<string, ModelDiagnostic[]> {
  const found = new Map<string, ModelDiagnostic[]>();
  for (const item of diagnostics) {
    const key = item.path.split("/")[2]?.replaceAll("~1", "/").replaceAll("~0", "~");
    if (key) found.set(key, [...(found.get(key) ?? []), item]);
  }
  return found;
}

/** The release identity the draft installs as (D18): its key, name and version, editable. */
export function useReleaseIdentity(outline: ModelDraftOutline) {
  const [key, setKey] = useState(outline.release.key ?? "");
  const [name, setName] = useState(outline.release.name ?? "");
  const [version, setVersion] = useState(() => suggestedVersion(outline));
  const changed =
    key.trim() !== (outline.release.key ?? "") ||
    name.trim() !== (outline.release.name ?? "") ||
    version.trim() !== (outline.release.version ?? "");
  return {
    key,
    setKey,
    name,
    setName,
    version,
    setVersion,
    changed,
    complete: Boolean(key.trim() && version.trim() && name.trim()),
    /** The `setRelease` step a changed identity needs first. */
    operation: { kind: "setRelease", key: key.trim(), name: name.trim(), version: version.trim() },
  };
}

export type ReleaseIdentity = ReturnType<typeof useReleaseIdentity>;

export function ReleaseIdentityFields({
  identity,
  outline,
}: {
  identity: ReleaseIdentity;
  outline: ModelDraftOutline;
}) {
  return (
    <div className="install-identity">
      <FormField label="Release key">
        {(control) => (
          <input
            {...control}
            className="mono"
            value={identity.key}
            onChange={(event) => identity.setKey(event.target.value)}
          />
        )}
      </FormField>
      <FormField
        label="Version"
        help={outline.baseRelease?.version ? `Base release ${outline.baseRelease.version}` : undefined}
      >
        {(control) => (
          <input
            {...control}
            className="mono"
            value={identity.version}
            onChange={(event) => identity.setVersion(event.target.value)}
          />
        )}
      </FormField>
      <FormField label="Name">
        {(control) => (
          <input {...control} value={identity.name} onChange={(event) => identity.setName(event.target.value)} />
        )}
      </FormField>
    </div>
  );
}

export function activationRefusal(cause: unknown): string {
  if (isApiError(cause)) {
    const diagnostics = ((cause.details ?? {}) as { diagnostics?: { message: string }[] }).diagnostics ?? [];
    return [cause.message, ...diagnostics.map((item) => item.message)].join(" ");
  }
  return errorMessage(cause);
}

/** Each consumer API of the draft against what its consumers read now, with the step a break needs (D58). */
export function ConsumerContracts({
  outline,
  diagnostics,
  run,
  pending,
}: {
  outline: ModelDraftOutline;
  diagnostics: ModelDiagnostic[];
  run: (operations: DraftOperation[]) => Promise<unknown>;
  pending: boolean;
}) {
  const byApi = contractsByApi(diagnostics);
  const removed = [...byApi].filter(([key]) => !outline.consumerApis.some((item) => item.key === key));
  if (!outline.consumerApis.length && !removed.length) return null;
  return (
    <section aria-labelledby="install-consumer-apis">
      <h3 id="install-consumer-apis" className="install-heading">
        Consumer APIs
      </h3>
      <ul className="install-contracts">
        {outline.consumerApis.map((item) => {
          const errors = (byApi.get(item.key) ?? []).filter((d) => d.severity === "error");
          // A kept earlier version that would read differently is not cured by a higher version.
          const kept = errors.filter((d) => d.code === KEPT_VERSION_CHANGED);
          const breaking = errors.filter((d) => d.code !== KEPT_VERSION_CHANGED);
          // A version the release stops serving, on purpose: a warning, but never "Compatible".
          const stopped = (byApi.get(item.key) ?? []).filter((d) => d.code === KEPT_VERSION_STOPPED);
          const next = (item.contractVersion ?? 1) + 1;
          return (
            <li key={item.key}>
              <span>
                <strong>{item.name}</strong>{" "}
                <span className="muted">{`${item.key} v${item.contractVersion ?? 1}`}</span>
              </span>
              {breaking.length ? (
                <>
                  <span className="install-contract-break">
                    Needs version {next}:{" "}
                    {breaking.map((d) => d.message.replace(/; raise contractVersion.*$/, "")).join("; ")}
                  </span>
                  <button
                    type="button"
                    className="primary"
                    disabled={pending}
                    onClick={() => void run([{ kind: "raiseConsumerApiVersion", consumerApi: item.key }])}
                  >
                    Raise to v{next}
                  </button>
                </>
              ) : kept.length ? (
                <span className="install-contract-break">{kept.map((d) => d.message).join("; ")}</span>
              ) : stopped.length ? (
                <span className="install-contract-warn">{stopped.map((d) => d.message).join(" ")}</span>
              ) : (
                <span className="install-contract-ok">Compatible</span>
              )}
            </li>
          );
        })}
        {removed.map(([key, items]) => (
          <li key={key}>
            <span>
              <strong>{key}</strong> <span className="muted">removed</span>
            </span>
            <span className="install-contract-warn">{items.map((d) => d.message).join(" ")}</span>
          </li>
        ))}
      </ul>
      {byApi.size > 0 && [...byApi.values()].flat().some((d) => d.severity === "error") && (
        <p className="muted">Activation is refused while a consumer API needs a higher contract version.</p>
      )}
    </section>
  );
}
