/**
 * What Install, Activate and Apply say alike about a workspace's release change (0.11 M5, D26; 0.16 WM1): its open change
 * sets that stay on the release it runs now, and the first reasons the data does not fit.
 */

import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { plural } from "@/lib/count";
import { attributeTypeName, relationTypeName, suggestedVersion, typeName } from "@/model/outline";
import type { ChangeSet, DraftOperation, ModelChange, ModelDiagnostic, ModelDraftOutline, Subscription } from "@/types";
import { FormField } from "@/ui/FormField";
import { everyPage } from "@/lib/everyPage";
import { Notice } from "@/ui/Notice";
import { holdsAnywhere, useHeldAnywhere } from "@/state/permissions";
import { useCapabilities } from "@/state/useSystem";
import { useRef, useState, type ReactNode } from "react";

/** Every open change set of the workspace, page by page (a workspace holds few). */
export function openChangeSets(workspaceKey: string): Promise<ChangeSet[]> {
  return everyPage((cursor) => api.changeSets(workspaceKey, cursor));
}

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

/** The diagnostic of a change that alters what a current contract version's readers get (C-D2). */
const CONTRACT_VERSION_REQUIRED = "CONSUMER_CONTRACT_VERSION_REQUIRED";

/**
 * Which consumer APIs the person keeps at their current version through a breaking change (KV1).
 * Keeping is a choice of the dialog, not a draft step: the draft keeps its version and the main action
 * sends `keepContractVersions`. `blocked` is true while a break is neither raised nor kept, and for
 * what a flag never covers (a lowered version, a changed earlier version).
 */
export function useKeptContracts(diagnostics: ModelDiagnostic[] | undefined, workspaceKey?: string) {
  // Offered only to people who may install a release, as the main action is (hidden, never disabled).
  const held = useHeldAnywhere();
  const mayKeep = holdsAnywhere(held, "model-release");
  // The names of the bound webhooks come from the subscriptions list: asked only where it can be read.
  const { capabilities } = useCapabilities();
  const readsWebhooks = Boolean(
    capabilities?.consumerSubscriptions?.manageSubscriptions && holdsAnywhere(held, "integration-admin"),
  );
  const [chosen, setChosen] = useState<ReadonlySet<string>>(new Set());
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const asked = useRef<string>(undefined);
  const byApi = contractsByApi(diagnostics ?? []);
  const errorsOf = (key: string) => (byApi.get(key) ?? []).filter((d) => d.severity === "error");
  // What can be kept: every error of the API is a break of its current version.
  const keepable = (key: string) => {
    const errors = errorsOf(key);
    return mayKeep && errors.length > 0 && errors.every((d) => d.code === CONTRACT_VERSION_REQUIRED);
  };
  // A choice outlives its row only while the row still breaks (a raised version breaks nothing).
  const kept = new Set([...chosen].filter(keepable));
  const blocked = [...byApi].some(([key]) => errorsOf(key).length > 0 && !kept.has(key));
  return {
    mayKeep,
    keepable,
    isKept: (key: string) => kept.has(key),
    /** True when any API is kept: what `keepContractVersions` is sent as. */
    keeping: kept.size > 0,
    blocked,
    /** The workspace's webhooks bound to this version of the API (KV-D7). */
    webhooksOf: (key: string, version: number) =>
      subscriptions.filter((item) => item.consumerApi === key && item.contractVersion === version),
    keep: (key: string) => {
      setChosen((before) => new Set(before).add(key));
      if (!workspaceKey || !readsWebhooks || asked.current === workspaceKey) return;
      asked.current = workspaceKey;
      setSubscriptions([]);
      // The names are a help: a list that cannot be read leaves the line out.
      everyPage((cursor) => api.subscriptions({ cursor, workspaceKey }))
        .then(setSubscriptions)
        .catch(() => undefined);
    },
    unkeep: (key: string) =>
      setChosen((before) => {
        const next = new Set(before);
        next.delete(key);
        return next;
      }),
  };
}

export type KeptContracts = ReturnType<typeof useKeptContracts>;

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
  contracts,
}: {
  outline: ModelDraftOutline;
  diagnostics: ModelDiagnostic[];
  run: (operations: DraftOperation[]) => Promise<unknown>;
  pending: boolean;
  contracts: KeptContracts;
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
          const earlier = errors.filter((d) => d.code === KEPT_VERSION_CHANGED);
          const breaking = errors.filter((d) => d.code !== KEPT_VERSION_CHANGED);
          // A version the release stops serving, on purpose: a warning, but never "Compatible".
          const stopped = (byApi.get(item.key) ?? []).filter((d) => d.code === KEPT_VERSION_STOPPED);
          const version = item.contractVersion ?? 1;
          const next = version + 1;
          const changes = breaking.map((d) => d.message.replace(/; raise contractVersion.*$/, ""));
          const raise = (label: string) => (
            <button
              type="button"
              className="primary"
              disabled={pending}
              onClick={() => {
                contracts.unkeep(item.key);
                void run([{ kind: "raiseConsumerApiVersion", consumerApi: item.key }]);
              }}
            >
              {label}
            </button>
          );
          const webhooks = contracts.webhooksOf(item.key, version);
          return (
            <li key={item.key}>
              <span>
                <strong>{item.name}</strong> <span className="muted">{`${item.key} v${version}`}</span>
              </span>
              {breaking.length && contracts.isKept(item.key) ? (
                <>
                  <div className="install-contract-kept" role="status">
                    <strong>Stays v{version}, changed in place</strong>
                    Once applied, every reader of{" "}
                    <span className="mono">{`/api/consumer/${item.key}/v${version}`}</span> gets the new shape:
                    <ul>
                      {changes.map((change) => (
                        <li key={change}>{change}</li>
                      ))}
                      {webhooks.length > 0 && (
                        <li>
                          Webhooks bound to v{version}: {webhooks.map((hook) => hook.name).join(", ")}
                        </li>
                      )}
                    </ul>
                  </div>
                  {raise(`Raise to v${next} instead`)}
                </>
              ) : breaking.length ? (
                <>
                  <span className="install-contract-break">
                    Needs version {next}: {changes.join("; ")}
                  </span>
                  <span className="install-contract-actions">
                    {raise(`Raise to v${next}`)}
                    {contracts.keepable(item.key) && (
                      <button
                        type="button"
                        className="danger"
                        disabled={pending}
                        onClick={() => contracts.keep(item.key)}
                      >
                        Keep v{version}, break its readers
                      </button>
                    )}
                  </span>
                </>
              ) : earlier.length ? (
                <span className="install-contract-break">{earlier.map((d) => d.message).join("; ")}</span>
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
      {contracts.blocked && (
        <p className="muted">
          Activation is refused while a consumer API needs a higher contract version
          {contracts.mayKeep ? ", unless you keep its version." : "."}
        </p>
      )}
    </section>
  );
}
