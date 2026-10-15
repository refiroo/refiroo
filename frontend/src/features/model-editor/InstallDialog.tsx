/**
 * Install and activate from the editor (0.10 A4a, A-D8, D18, D42): one confirmed step running the
 * existing installation and activation. It shows the release identity, its version proposed from
 * the base release and editable, the differences from the base release, validity and the
 * compatibility with stored data. A changed identity is a `setRelease` step first. A refused
 * activation leaves the installed release, and the dialog says so.
 *
 * Each consumer API is shown checked against what the active release's consumers read (0.10 A4c,
 * D58): one that needs a higher contract version offers the step that raises it, and activation
 * waits until none does, as the server would refuse it.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type { ModelChange, ModelCompilation, ModelDiagnostic, ModelDraftOutline, ModelRelease } from "@/types";
import { FormField } from "@/ui/FormField";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";
import type { RunStep } from "@/features/model-editor/OperationDialog";
import { suggestedVersion, typeName } from "@/features/model-editor/outline";

const COLLECTIONS: Record<string, string> = {
  objectTypes: "Object types",
  attributeTypes: "Attribute types",
  relationTypes: "Relation types",
  objectTypeRelations: "Allowed relations",
  applications: "Applications",
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
            : collection === "attributeTypes"
              ? (outline.attributeTypes.find((a) => a.key === parts[1])?.name ?? parts[1])
              : (outline.relationTypes.find((r) => r.key === parts[1])?.name ?? parts[1]);
    const label = `${COLLECTIONS[collection]} ${kind}`;
    lines.set(label, (lines.get(label) ?? new Set()).add(name));
  }
  return [...lines].map(([label, names]) => ({ label, names: [...names] }));
}

/** The consumer contract diagnostics by the consumer API their pointer names. */
export function contractsByApi(diagnostics: ModelDiagnostic[]): Map<string, ModelDiagnostic[]> {
  const found = new Map<string, ModelDiagnostic[]>();
  for (const item of diagnostics) {
    const key = item.path.split("/")[2]?.replaceAll("~1", "/").replaceAll("~0", "~");
    if (key) found.set(key, [...(found.get(key) ?? []), item]);
  }
  return found;
}

type Outcome = { kind: "installed"; release: ModelRelease; reason: string } | { kind: "active"; release: ModelRelease };

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

export function InstallDialog({
  draftId,
  outline,
  run,
  latestVersion,
  onActivated,
  onInstalledOnly,
  onClose,
}: {
  draftId: string;
  outline: ModelDraftOutline;
  run: RunStep;
  /** The draft's version now, after any step this dialog ran. */
  latestVersion: () => number;
  onActivated: (release: ModelRelease) => Promise<void>;
  onInstalledOnly: () => void;
  onClose: () => void;
}) {
  const [compilation, setCompilation] = useState<ModelCompilation>();
  const [loadError, setLoadError] = useState("");
  const identity = useReleaseIdentity(outline);
  const version = identity.version;
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [outcome, setOutcome] = useState<Outcome>();

  useEffect(() => {
    let cancelled = false;
    api
      .compileModelDraft(draftId, outline.version)
      .then((result) => {
        if (!cancelled) setCompilation(result);
      })
      .catch((cause) => {
        if (!cancelled) setLoadError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [draftId, outline.version]);

  const contractsBreak = compilation?.consumerContracts?.classification === "version_required";
  const blocked = !compilation?.valid || contractsBreak || !identity.complete;

  async function confirm() {
    setPending(true);
    setError("");
    try {
      if (identity.changed) {
        const outcome = await run([identity.operation]);
        if (outcome === "stale") {
          onClose();
          return;
        }
      }
      const release = await api.installModelDraft(draftId, latestVersion());
      try {
        const state = await api.defaultWorkspaceModel();
        await api.activateWorkspaceModel(release.id, state);
      } catch (cause) {
        setOutcome({ kind: "installed", release, reason: activationRefusal(cause) });
        onInstalledOnly();
        return;
      }
      setOutcome({ kind: "active", release });
      await onActivated(release);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  if (outcome?.kind === "installed")
    return (
      <Modal title="Installed, not active" eyebrow="Install and activate" size="compact" onClose={onClose}>
        <div className="dialog-body">
          <Notice
            tone="warning"
            title={`${outcome.release.name} ${outcome.release.version} is installed but not active`}
          >
            {outcome.reason} The active model is unchanged. Activate the release later from Settings › Model.
          </Notice>
          <div className="dialog-actions">
            <button type="button" className="primary" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </Modal>
    );

  const lines = compilation ? summarizeChanges(compilation.changes, outline) : [];
  const errors = compilation?.diagnostics.filter((item) => item.severity === "error") ?? [];
  const compatible = compilation?.compatibility.classification === "compatible";
  return (
    <Modal
      title="Install and activate"
      eyebrow="Release the draft"
      description="Creates an immutable release from this draft, then makes it the active model. This draft continues as the next version."
      busy={pending}
      onClose={onClose}
    >
      <form
        className="dialog-body install-dialog"
        onSubmit={(event) => {
          event.preventDefault();
          if (!pending && !blocked) void confirm();
        }}
      >
        <ReleaseIdentityFields identity={identity} outline={outline} />
        {loadError && <Notice tone="error">{loadError}</Notice>}
        {!compilation && !loadError && <Skeleton lines={3} label="Comparing with the base release" />}
        {compilation && (
          <>
            <section aria-labelledby="install-changes">
              <h3 id="install-changes" className="install-heading">
                {outline.baseRelease?.version
                  ? `What changes against ${outline.baseRelease.version}`
                  : "What the release holds"}
              </h3>
              {compilation.valid ? (
                lines.length ? (
                  <dl className="install-changes">
                    {lines.map((line) => (
                      <div key={line.label}>
                        <dt>{line.label}</dt>
                        <dd>{line.names.join(", ")}</dd>
                      </div>
                    ))}
                  </dl>
                ) : (
                  <p className="muted">No model element changes.</p>
                )
              ) : null}
            </section>
            <div className="install-verdicts">
              {compilation.valid ? (
                <Notice tone="success" title="Valid">
                  No issues.
                </Notice>
              ) : (
                <Notice tone="error" title="Not valid">
                  {errors.length} {errors.length === 1 ? "issue stops" : "issues stop"} this step. Each is in the Issues
                  list.
                </Notice>
              )}
              {compilation.valid &&
                (compatible ? (
                  <Notice tone="success" title="Compatible with stored data">
                    No record, value or relationship needs a migration.
                  </Notice>
                ) : (
                  <Notice tone="warning" title="Activation needs a migration">
                    {compilation.compatibility.diagnostics.map((item) => item.message).join(" ")} The release would be
                    installed but not activated.
                  </Notice>
                ))}
            </div>
            {compilation.valid && compilation.consumerContracts && (
              <ConsumerContracts
                outline={outline}
                diagnostics={compilation.consumerContracts.diagnostics}
                run={run}
                pending={pending}
              />
            )}
          </>
        )}
        {error && (
          <Notice tone="error" title="Not installed">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={pending}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={pending || blocked}>
            {pending ? "Installing…" : `Install ${version.trim()} and activate`}
          </button>
        </div>
      </form>
    </Modal>
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
function ConsumerContracts({
  outline,
  diagnostics,
  run,
  pending,
}: {
  outline: ModelDraftOutline;
  diagnostics: ModelDiagnostic[];
  run: RunStep;
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
          const breaking = (byApi.get(item.key) ?? []).filter((d) => d.severity === "error");
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
                    onClick={() =>
                      void run([
                        { kind: "setConsumerApiPart", consumerApi: item.key, pointer: "/contractVersion", value: next },
                      ])
                    }
                  >
                    Raise to v{next}
                  </button>
                </>
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
