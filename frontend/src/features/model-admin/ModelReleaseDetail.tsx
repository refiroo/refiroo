import { useEffect, useState } from "react";
import { formatServerTime } from "@/lib/dates";
import { actorText } from "@/ui/ActorName";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type { ModelRelease, ModelReleaseActivation, ModelReleaseDiff, ModelReleaseSummary, Workspace } from "@/types";
import { ModelDiagnostics } from "@/features/model-admin/ModelDiagnostics";
import { CompatibilityPill, ModelDiff } from "@/features/model-admin/ModelDiff";
import { downloadJson } from "@/lib/download";
import { ModelSummary } from "@/features/model-admin/ModelSummary";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { Notice } from "@/ui/Notice";
import { StatusPill } from "@/ui/StatusPill";

/** Where the Before release of a release-history comparison came from. */
type Baseline = {
  releaseId: string;
  source: "activation" | "installation" | "choice";
  activation?: ModelReleaseActivation;
};

/** The release checked against each workspace of its model, tagged with the assignments it read. */
type ActivationCheck = { assignments: string } & (
  { state: "ready"; diff: ModelReleaseDiff } | { state: "error"; message: string }
);

/** A history comparison result, tagged with the baseline it was computed against. */
type Comparison = { againstReleaseId: string } & (
  | { state: "ready"; diff: ModelReleaseDiff }
  | { state: "unsupported"; schemaVersion?: string }
  | { state: "error"; message: string }
);

function releaseLabel(release: Pick<ModelReleaseSummary, "key" | "version">) {
  return `${release.key} ${release.version}`;
}

async function allReleases() {
  const items: ModelReleaseSummary[] = [];
  let cursor: string | undefined;
  do {
    const page = await api.modelReleases({ cursor, pageSize: 500 });
    items.push(...page.items);
    cursor = page.nextCursor ?? undefined;
  } while (cursor);
  return items;
}

/**
 * The default Before release: the release that was active when this one was first activated, when
 * that is recorded; otherwise the preceding installed release of the same model key.
 */
function defaultBaseline(
  release: ModelRelease,
  releases: ModelReleaseSummary[],
  introduction: ModelReleaseActivation | undefined,
): Baseline | undefined {
  if (introduction && releases.some((item) => item.id === introduction.previousReleaseId))
    return { releaseId: introduction.previousReleaseId, source: "activation", activation: introduction };
  const sameKey = releases.filter((item) => item.key === release.key);
  const index = sameKey.findIndex((item) => item.id === release.id);
  const preceding = index > 0 ? sameKey[index - 1] : undefined;
  return preceding && { releaseId: preceding.id, source: "installation" };
}

function refusalDetail(cause: unknown, key: "releaseId" | "schemaVersion") {
  const details = isApiError(cause) ? (cause.details as Record<string, unknown> | undefined) : undefined;
  const value = details?.[key];
  return typeof value === "string" ? value : undefined;
}

const refusedReleaseId = (cause: unknown) => refusalDetail(cause, "releaseId");
const unsupportedSchemaVersion = (cause: unknown) => refusalDetail(cause, "schemaVersion");

export function ModelReleaseDetail({
  releaseId,
  workspaces,
  canManageDrafts,
  canActivate,
  canInstall = false,
  isDefault = false,
  onCreateDraft,
  onActivate,
  onStatusChanged,
  onDeleted,
  pageTitle,
}: {
  releaseId: string;
  /** The page's own title; the release's name is not repeated under it. */
  pageTitle?: string;
  /** The active workspaces with the release each runs (0.11 M5). */
  workspaces: Workspace[];
  canManageDrafts: boolean;
  canActivate: boolean;
  onCreateDraft: (release: ModelRelease) => void;
  /** Opens the activation dialog with this release (D51). */
  onActivate: (releaseId: string) => void;
  /** May retire, restore and delete releases: the right to install models (0.12 MR1). */
  canInstall?: boolean;
  /** The default workspace runs it, so it is not retired (MR1). */
  isDefault?: boolean;
  /** The release was retired or brought back. */
  onStatusChanged?: (release: ModelRelease) => void;
  /** The release was deleted. */
  onDeleted?: (release: ModelRelease) => void;
}) {
  const [release, setRelease] = useState<ModelRelease>();
  const [releases, setReleases] = useState<ModelReleaseSummary[]>();
  const [defaultBase, setDefaultBase] = useState<Baseline>();
  const [baseline, setBaseline] = useState<Baseline>();
  const [comparison, setComparison] = useState<Comparison>();
  const [activationCheck, setActivationCheck] = useState<ActivationCheck>();
  const [historyError, setHistoryError] = useState("");
  const [error, setError] = useState("");
  const [unsupportedSchema, setUnsupportedSchema] = useState(false);
  const [copyMessage, setCopyMessage] = useState("");
  const [confirming, setConfirming] = useState<"retire" | "delete">();
  const [lifecyclePending, setLifecyclePending] = useState(false);
  const [lifecycleError, setLifecycleError] = useState("");
  // Which workspace runs which release; an activation anywhere changes it and reloads what depends on it.
  const assignments = workspaces.map((item) => `${item.key}=${item.model.releaseId}`).join(",");

  // The workbench keys this component by release, so each selection starts from empty state. An
  // activation (of this release or another) reloads status, history and the default baseline.
  useEffect(() => {
    let cancelled = false;
    api
      .modelRelease(releaseId, true)
      .then(async (loaded) => {
        if (cancelled) return;
        setRelease(loaded);
        try {
          const [installed, history] = await Promise.all([
            allReleases(),
            api.modelReleaseActivations(loaded.id, { pageSize: 1 }),
          ]);
          if (cancelled) return;
          const initial = defaultBaseline(loaded, installed, history.items[0]);
          setHistoryError("");
          setReleases(installed);
          setDefaultBase(initial);
          setBaseline(initial);
        } catch (cause) {
          if (!cancelled) setHistoryError(errorMessage(cause));
        }
      })
      .catch((cause) => {
        if (!cancelled) setError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [releaseId, assignments]);

  // Release history: an earlier baseline (Before) against the selected release (After).
  useEffect(() => {
    if (!release || !baseline) return;
    const againstReleaseId = baseline.releaseId;
    let cancelled = false;
    api
      .modelReleaseDiff(release.id, againstReleaseId)
      .then((diff) => {
        if (!cancelled) setComparison({ againstReleaseId, state: "ready", diff });
      })
      .catch((cause) => {
        if (cancelled) return;
        if (!isApiError(cause, "UNSUPPORTED_SCHEMA_VERSION"))
          setComparison({ againstReleaseId, state: "error", message: errorMessage(cause) });
        else if (refusedReleaseId(cause) === release.id) setUnsupportedSchema(true);
        else setComparison({ againstReleaseId, state: "unsupported", schemaVersion: unsupportedSchemaVersion(cause) });
      });
    return () => {
      cancelled = true;
    };
  }, [release, baseline]);

  // This release against each workspace running a release of its model, their own data each
  // (D25), whatever baseline the history comparison uses. The list does not depend on the release
  // compared with, so the release is compared with itself.
  useEffect(() => {
    if (!release) return;
    let cancelled = false;
    api
      .modelReleaseDiff(release.id, release.id)
      .then((diff) => {
        if (!cancelled) setActivationCheck({ assignments, state: "ready", diff });
      })
      .catch((cause) => {
        if (cancelled) return;
        if (isApiError(cause, "UNSUPPORTED_SCHEMA_VERSION")) setUnsupportedSchema(true);
        else setActivationCheck({ assignments, state: "error", message: errorMessage(cause) });
      });
    return () => {
      cancelled = true;
    };
  }, [release, assignments]);

  async function copy(label: string, value: string) {
    try {
      if (!navigator.clipboard) throw new Error("Clipboard access is unavailable");
      await navigator.clipboard.writeText(value);
      setCopyMessage(`${label} copied.`);
    } catch {
      setCopyMessage(
        `Could not copy the ${label.replace(/^\w/, (first) => first.toLowerCase())}. Select the value and copy it manually.`,
      );
    }
  }

  async function changeLifecycle(action: "retire" | "restore" | "delete") {
    if (!release) return;
    setLifecyclePending(true);
    setLifecycleError("");
    try {
      if (action === "delete") {
        await api.deleteModelRelease(release);
        onDeleted?.(release);
      } else {
        const changed = await api.setModelReleaseStatus(release, action === "retire" ? "retired" : "active");
        setRelease({ ...changed, model: release.model });
        setConfirming(undefined);
        onStatusChanged?.(changed);
      }
    } catch (cause) {
      setLifecycleError(errorMessage(cause));
    } finally {
      setLifecyclePending(false);
    }
  }

  function chooseBaseline(id: string) {
    setBaseline(id === defaultBase?.releaseId ? defaultBase : { releaseId: id, source: "choice" });
  }

  if (error && !release)
    return (
      <div className="inline-state error-notice" role="alert">
        {error}
      </div>
    );
  if (!release) return <div className="panel-state">Loading release…</div>;
  const byId = new Map(releases?.map((item) => [item.id, item]));
  // The workspaces' assignments are authoritative; a release's `workspaces` is only as fresh as its load.
  const runBy = workspaces.filter((item) => item.model.releaseId === release.id);
  const label = (key: string) => workspaces.find((item) => item.key === key)?.label ?? key;
  const check = activationCheck?.assignments === assignments ? activationCheck : undefined;
  const readiness = check?.state === "ready" ? check.diff.compatibility.workspaces : undefined;
  const current = baseline && comparison?.againstReleaseId === baseline.releaseId ? comparison : undefined;
  const baselineRelease = baseline && byId.get(baseline.releaseId);
  const candidates = [...(releases ?? [])].reverse().filter((item) => item.id !== release.id);
  return (
    <div className="model-editor-stack">
      <header className="model-detail-header">
        <div>
          {release.name === pageTitle ? (
            <p className="muted">Immutable release</p>
          ) : (
            <>
              <p className="eyebrow">Immutable release</p>
              <h2>{release.name}</h2>
            </>
          )}
          <p>
            {release.key} · version {release.version} · schema {release.schemaVersion}
          </p>
        </div>
        <span className="model-row-marks">
          {release.status === "retired" && <StatusPill tone="warning">Retired</StatusPill>}
          {runBy.length ? (
            <StatusPill tone="success">Run by {runBy.map((item) => item.label).join(", ")}</StatusPill>
          ) : (
            <StatusPill tone="neutral">Run by no workspace</StatusPill>
          )}
        </span>
      </header>
      {release.status === "retired" && (
        <Notice tone="info" title="Retired">
          This release is no longer offered for new workspaces, change sets or activations
          {runBy.length ? "; the workspaces that run it keep working" : ""}.
        </Notice>
      )}
      <dl className="release-metadata">
        <div>
          <dt>Installed</dt>
          <dd>{formatServerTime(release.installedAt)}</dd>
        </div>
      </dl>
      {release.model && <ModelSummary model={release.model} />}
      {error && <Notice tone="error">{error}</Notice>}
      {lifecycleError && !confirming && <Notice tone="error">{lifecycleError}</Notice>}
      <div className="model-actions">
        {release.model && (
          <button
            className="secondary"
            onClick={() =>
              downloadJson(`${release.key}-${release.version}.json`, JSON.stringify(release.model, null, 2))
            }
          >
            Export JSON
          </button>
        )}
        {canManageDrafts && (
          <button className="secondary" onClick={() => onCreateDraft(release)}>
            Create draft from release
          </button>
        )}
        {canActivate && !unsupportedSchema && release.status === "active" && runBy.length < workspaces.length && (
          <button className="primary" onClick={() => onActivate(release.id)}>
            Activate in a workspace…
          </button>
        )}
        {canInstall && release.status === "active" && !isDefault && (
          <button className="secondary" disabled={lifecyclePending} onClick={() => setConfirming("retire")}>
            Retire…
          </button>
        )}
        {canInstall && release.status === "retired" && (
          <button className="secondary" disabled={lifecyclePending} onClick={() => void changeLifecycle("restore")}>
            Bring back
          </button>
        )}
        {canInstall && release.deletable && (
          <button className="danger" disabled={lifecyclePending} onClick={() => setConfirming("delete")}>
            Delete…
          </button>
        )}
      </div>
      {confirming === "retire" && (
        <ConfirmDialog
          title={`Retire ${release.name} ${release.version}?`}
          confirmLabel="Retire"
          pending={lifecyclePending}
          error={lifecycleError}
          onCancel={() => {
            setConfirming(undefined);
            setLifecycleError("");
          }}
          onConfirm={() => void changeLifecycle("retire")}
        >
          <p>
            It will no longer be offered for new workspaces, change sets or activations.
            {runBy.length
              ? ` ${runBy.map((item) => item.label).join(", ")} keep${runBy.length === 1 ? "s" : ""} running it.`
              : ""}{" "}
            You can bring it back at any time.
          </p>
        </ConfirmDialog>
      )}
      {confirming === "delete" && (
        <ConfirmDialog
          title={`Delete ${release.name} ${release.version}?`}
          confirmLabel="Delete release"
          pending={lifecyclePending}
          error={lifecycleError}
          onCancel={() => {
            setConfirming(undefined);
            setLifecycleError("");
          }}
          onConfirm={() => void changeLifecycle("delete")}
        >
          <p>
            Nothing was made under this release, so it can be removed for good. Drafts started from it stay. This cannot
            be undone; export the JSON first if you may need it again.
          </p>
        </ConfirmDialog>
      )}
      <details className="release-technical">
        <summary>Technical details</summary>
        <div className="release-technical-body">
          <p>Inspection aids for API and support use. They are assigned by the engine and cannot be edited.</p>
          <dl>
            <div>
              <dt>Release ID</dt>
              <dd>
                <code>{release.id}</code>
                <button
                  className="secondary"
                  aria-label="Copy release ID"
                  onClick={() => copy("Release ID", release.id)}
                >
                  Copy
                </button>
              </dd>
              <dd className="release-technical-hint">Identifies this installed release in API requests and support.</dd>
            </div>
            <div>
              <dt>Content hash</dt>
              <dd>
                <code>{release.modelHash}</code>
                <button
                  className="secondary"
                  aria-label="Copy content hash"
                  onClick={() => copy("Content hash", release.modelHash)}
                >
                  Copy
                </button>
              </dd>
              <dd className="release-technical-hint">
                Verifies identical normalized model content across installations.
              </dd>
            </div>
          </dl>
          <span className="release-technical-feedback" role="status">
            {copyMessage}
          </span>
        </div>
      </details>
      {unsupportedSchema ? (
        <Notice tone="info" title="Historical release">
          This release uses schema {release.schemaVersion}, which this deployment cannot interpret for semantic
          comparison or activation. The release metadata and raw JSON remain available for inspection and export.
        </Notice>
      ) : (
        <section className="model-result" aria-labelledby="release-history-heading">
          <div className="model-result-heading">
            <div>
              <p className="eyebrow">Release history</p>
              <h3 id="release-history-heading">Changes in this release</h3>
            </div>
          </div>
          <div className="release-comparison-body">
            {historyError ? (
              <Notice tone="error">Release history could not be loaded: {historyError}</Notice>
            ) : !releases ? (
              <p className="panel-state">Loading release history…</p>
            ) : (
              <>
                {candidates.length > 0 && (
                  <label className="release-baseline-field">
                    Compare with
                    <select
                      className="field-input"
                      value={baseline?.releaseId ?? ""}
                      onChange={(event) => chooseBaseline(event.target.value)}
                    >
                      {!baseline && (
                        <option value="" disabled>
                          No earlier release
                        </option>
                      )}
                      {candidates.map((item) => (
                        <option key={item.id} value={item.id}>
                          {releaseLabel(item)}
                          {workspaces.some((workspace) => workspace.model.releaseId === item.id) ? " (run)" : ""}
                          {item.id === defaultBase?.releaseId ? " (default)" : ""}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                {baseline && baselineRelease ? (
                  <p className="release-comparison-direction">
                    <span>
                      Before: <strong>{releaseLabel(baselineRelease)}</strong>
                    </span>
                    <span aria-hidden="true">→</span>
                    <span>
                      After: <strong>{releaseLabel(release)}</strong> (this release)
                    </span>
                    <small>{baselineExplanation(baseline)}</small>
                  </p>
                ) : (
                  <p className="panel-state">
                    No earlier release to compare with: no activation of this release records a predecessor and it is
                    the first installed release of {release.key}.
                    {candidates.length > 0 && " Choose a release in Compare with to compare anyway."}
                  </p>
                )}
              </>
            )}
            {baseline && !current && <p className="panel-state">Comparing releases…</p>}
            {current?.state === "error" && <Notice tone="error">{current.message}</Notice>}
            {current?.state === "unsupported" && baselineRelease && (
              <Notice tone="info" title="Comparison unavailable">
                {releaseLabel(baselineRelease)} uses schema {current.schemaVersion ?? baselineRelease.schemaVersion},
                which this deployment cannot interpret for semantic comparison. Choose another release in Compare with.
                Its metadata and raw JSON remain available from the release list.
              </Notice>
            )}
          </div>
          {current?.state === "ready" && baselineRelease && (
            <ModelDiff
              changes={current.diff.changes}
              emptyMessage={`No semantic changes: ${releaseLabel(baselineRelease)} and this release define the same model.`}
            />
          )}
        </section>
      )}
      {!unsupportedSchema && (
        <section className="model-result" aria-labelledby="activation-check-heading">
          <div className="model-result-heading">
            <div>
              <p className="eyebrow">Activation check</p>
              <h3 id="activation-check-heading">Workspaces running {release.key}</h3>
            </div>
          </div>
          {check?.state === "error" ? (
            <Notice tone="error">Activation readiness could not be checked: {check.message}</Notice>
          ) : !readiness ? (
            <p className="panel-state">Checking each workspace's stored data…</p>
          ) : readiness.length ? (
            <>
              <p className="release-check-note">
                Each workspace running a release of {release.key}, its own data against this release. Activating changes
                one workspace; a workspace on another model is checked when you choose it to activate into.
              </p>
              <ul className="release-workspace-checks">
                {readiness.map((item) => (
                  <li key={item.workspaceKey}>
                    <strong>{label(item.workspaceKey)}</strong>{" "}
                    {item.releaseId === release.id ? (
                      <StatusPill tone="success">Runs this release</StatusPill>
                    ) : (
                      <CompatibilityPill classification={item.classification} />
                    )}
                    {item.releaseId !== release.id && item.diagnostics.length > 0 && (
                      <ModelDiagnostics diagnostics={item.diagnostics} />
                    )}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="release-check-note">
              No workspace runs {release.key}. Activating this release into a workspace checks that workspace's data
              first.
            </p>
          )}
        </section>
      )}
    </div>
  );
}

function baselineExplanation(baseline: Baseline) {
  if (baseline.source === "activation") {
    // Who made it, when recorded (0.12 Z4); a selection from before sign-in names nobody.
    const actor = baseline.activation?.actor;
    const by = actor ? ` ${actorText(actor)}` : "";
    return baseline.activation?.kind === "schemaUpgraded"
      ? `Default: the active release this one replaced in the recorded offline schema upgrade${by}.`
      : `Default: the active release this one replaced when it was first activated${by}.`;
  }
  if (baseline.source === "installation")
    return "Default: the preceding installed release of the same model. No activation of this release is recorded, so this reflects installation order only.";
  return "Chosen baseline.";
}
