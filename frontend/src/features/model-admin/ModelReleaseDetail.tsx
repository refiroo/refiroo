import { useEffect, useState } from "react";
import { formatServerTime } from "@/lib/dates";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type { ModelRelease, ModelReleaseDiff, ModelRuntimeState } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { ModelDiff } from "@/features/model-admin/ModelDiff";
import { downloadJson } from "@/lib/download";
import { ModelSummary } from "@/features/model-admin/ModelSummary";
import { Notice } from "@/ui/Notice";

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
  const [diff, setDiff] = useState<ModelReleaseDiff>();
  const [error, setError] = useState("");
  const [unsupportedSchema, setUnsupportedSchema] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setRelease(undefined);
    setDiff(undefined);
    setError("");
    setUnsupportedSchema(false);
    api
      .modelRelease(releaseId, true)
      .then((loaded) => {
        if (cancelled) return;
        setRelease(loaded);
        if (!loaded.active)
          api
            .modelReleaseDiff(loaded.id, activeReleaseId)
            .then((result) => {
              if (!cancelled) setDiff(result);
            })
            .catch((cause) => {
              if (cancelled) return;
              if (isApiError(cause, "unsupported_schema_version")) {
                setUnsupportedSchema(true);
              } else {
                setError(errorMessage(cause));
              }
            });
      })
      .catch((cause) => {
        if (!cancelled) setError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [releaseId, activeReleaseId]);

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

  if (error && !release)
    return (
      <div className="inline-state error-notice" role="alert">
        {error}
      </div>
    );
  if (!release) return <div className="panel-state">Loading release…</div>;
  return (
    <div className="model-editor-stack">
      <header className="model-detail-header">
        <div>
          <p className="eyebrow">Immutable release</p>
          <h2>{release.name}</h2>
          <p>
            {release.key} · {release.version} · schema {release.schemaVersion}
          </p>
        </div>
        {release.active && <span className="compatibility compatible">Active</span>}
      </header>
      <dl className="release-metadata">
        <div>
          <dt>Installed</dt>
          <dd>{formatServerTime(release.installedAt)}</dd>
        </div>
        <div>
          <dt>Canonical hash</dt>
          <dd>
            <code>{release.modelHash}</code>
          </dd>
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
        {canActivate && !release.active && !unsupportedSchema && (
          <button
            className="primary"
            disabled={!diff || diff.compatibility.classification !== "compatible"}
            onClick={() => setConfirm(true)}
          >
            Activate…
          </button>
        )}
      </div>
      {unsupportedSchema && (
        <Notice tone="info" title="Historical release">
          This release uses schema {release.schemaVersion}, which this deployment cannot interpret for semantic
          comparison or activation. The release metadata and raw JSON remain available for inspection and export.
        </Notice>
      )}
      {!release.active && !diff && !error && !unsupportedSchema && (
        <div className="panel-state">Comparing with the active release…</div>
      )}
      {diff && <ModelDiff changes={diff.changes} compatibility={diff.compatibility} />}
      {diff?.compatibility.classification === "migration_required" && (
        <p className="notice">Activation is blocked because stored runtime data requires migration.</p>
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
