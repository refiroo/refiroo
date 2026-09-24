import { useEffect, useState } from "react";
import { formatServerTime } from "@/lib/dates";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type {
  ModelRelease,
  ModelReleaseActivation,
  ModelReleaseDiff,
  ModelReleaseSummary,
  ModelRuntimeState,
} from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { ModelDiagnostics } from "@/features/model-admin/ModelDiagnostics";
import { ModelDiff } from "@/features/model-admin/ModelDiff";
import { downloadJson } from "@/lib/download";
import { ModelSummary } from "@/features/model-admin/ModelSummary";
import { Notice } from "@/ui/Notice";

/** Where the Before release of a release-history comparison came from. */
type Baseline = {
  releaseId: string;
  source: "activation" | "installation" | "choice";
  activation?: ModelReleaseActivation;
};

/** The activation check, tagged with the active release it was computed against. */
type ActivationCheck = { activeReleaseId: string } & (
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
  activeReleaseId,
  canManageDrafts,
  canActivate,
  onCreateDraft,
  onActivated,
}: {
  releaseId: string;
  activeReleaseId: string;
  canManageDrafts: boolean;
  canActivate: boolean;
  onCreateDraft: (release: ModelRelease) => void;
  onActivated: (state: ModelRuntimeState) => void;
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
  const [confirm, setConfirm] = useState(false);
  const [pending, setPending] = useState(false);

  // The workbench keys this component by release, so each selection starts from empty state. A change
  // of active release (including activating this one) reloads status, history and the default baseline.
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
  }, [releaseId, activeReleaseId]);

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
        if (!isApiError(cause, "unsupported_schema_version"))
          setComparison({ againstReleaseId, state: "error", message: errorMessage(cause) });
        else if (refusedReleaseId(cause) === release.id) setUnsupportedSchema(true);
        else setComparison({ againstReleaseId, state: "unsupported", schemaVersion: unsupportedSchemaVersion(cause) });
      });
    return () => {
      cancelled = true;
    };
  }, [release, baseline]);

  // Activation readiness is always the current active release against this candidate and live data,
  // whatever baseline the history comparison uses.
  useEffect(() => {
    if (!release || release.id === activeReleaseId) return;
    let cancelled = false;
    api
      .modelReleaseDiff(release.id, activeReleaseId)
      .then((diff) => {
        if (!cancelled) setActivationCheck({ activeReleaseId, state: "ready", diff });
      })
      .catch((cause) => {
        if (cancelled) return;
        // The active release is interpretable by definition, so the refusal concerns this release.
        if (isApiError(cause, "unsupported_schema_version")) setUnsupportedSchema(true);
        else setActivationCheck({ activeReleaseId, state: "error", message: errorMessage(cause) });
      });
    return () => {
      cancelled = true;
    };
  }, [release, activeReleaseId]);

  async function activate() {
    setPending(true);
    setError("");
    try {
      const runtime = await api.modelRuntimeState();
      const activated = await api.activateModelRelease(releaseId, runtime);
      setConfirm(false);
      onActivated(activated);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

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
  // The runtime selection is authoritative; `release.active` is only as fresh as the last load.
  const isActive = release.id === activeReleaseId;
  const check = activationCheck?.activeReleaseId === activeReleaseId ? activationCheck : undefined;
  const readiness = check?.state === "ready" ? check.diff.compatibility : undefined;
  const current = baseline && comparison?.againstReleaseId === baseline.releaseId ? comparison : undefined;
  const baselineRelease = baseline && byId.get(baseline.releaseId);
  const activeRelease = byId.get(activeReleaseId);
  const candidates = [...(releases ?? [])].reverse().filter((item) => item.id !== release.id);
  return (
    <div className="model-editor-stack">
      <header className="model-detail-header">
        <div>
          <p className="eyebrow">Immutable release</p>
          <h2>{release.name}</h2>
          <p>
            {release.key} · version {release.version} · schema {release.schemaVersion}
          </p>
        </div>
        {isActive ? <span className="compatibility compatible">Active</span> : <span className="pill">Inactive</span>}
      </header>
      <dl className="release-metadata">
        <div>
          <dt>Installed</dt>
          <dd>{formatServerTime(release.installedAt)}</dd>
        </div>
      </dl>
      {release.model && <ModelSummary model={release.model} />}
      {error && (
        <div className="notice error-notice" role="alert">
          {error}
        </div>
      )}
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
        {canActivate && !isActive && !unsupportedSchema && (
          <button
            className="primary"
            disabled={readiness?.classification !== "compatible"}
            onClick={() => setConfirm(true)}
          >
            Activate…
          </button>
        )}
      </div>
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
              <div className="notice error-notice" role="alert">
                Release history could not be loaded: {historyError}
              </div>
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
                          {item.active ? " (active)" : ""}
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
            {current?.state === "error" && (
              <div className="notice error-notice" role="alert">
                {current.message}
              </div>
            )}
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
      {!isActive && !unsupportedSchema && (
        <section className="model-result" aria-labelledby="activation-check-heading">
          <div className="model-result-heading">
            <div>
              <p className="eyebrow">Activation check</p>
              <h3 id="activation-check-heading">
                Current active release{activeRelease ? ` ${releaseLabel(activeRelease)}` : ""} → this release
              </h3>
            </div>
            {readiness && (
              <span className={`compatibility ${readiness.classification}`}>
                {readiness.classification.replace("_", " ")}
              </span>
            )}
          </div>
          {check?.state === "error" ? (
            <div className="notice error-notice" role="alert">
              Activation readiness could not be checked: {check.message}
            </div>
          ) : !readiness ? (
            <p className="panel-state">Checking against the active release and stored data…</p>
          ) : (
            <>
              <p className="release-check-note">
                Readiness to activate this release in place of the current active model, including stored live data. It
                does not depend on the release history baseline above.
              </p>
              {readiness.diagnostics.length > 0 && <ModelDiagnostics diagnostics={readiness.diagnostics} />}
              {readiness.classification === "migration_required" && (
                <p className="notice">Activation is blocked because stored runtime data requires migration.</p>
              )}
            </>
          )}
        </section>
      )}
      {confirm && (
        <ConfirmDialog
          title={`Activate ${release.key}@${release.version}?`}
          confirmLabel="Activate release"
          pending={pending}
          error={error}
          onCancel={() => setConfirm(false)}
          onConfirm={activate}
        >
          <p>
            This changes the model used by new requests. The active release remains installed, so rollback is performed
            by activating it again after compatibility checks.
          </p>
        </ConfirmDialog>
      )}
    </div>
  );
}

function baselineExplanation(baseline: Baseline) {
  if (baseline.source === "activation")
    return baseline.activation?.kind === "schemaUpgraded"
      ? "Default: the active release this one replaced in the recorded offline schema upgrade."
      : "Default: the active release this one replaced when it was first activated.";
  if (baseline.source === "installation")
    return "Default: the preceding installed release of the same model. No activation of this release is recorded, so this reflects installation order only.";
  return "Chosen baseline.";
}
