import { useEffect, useRef, useState } from "react";
import { formatServerTime } from "@/lib/dates";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type {
  CapabilitiesResponse,
  ModelDraft,
  ModelRelease,
  ModelReleaseSummary,
  ModelRuntimeState,
  RouteState,
} from "@/types";
import { CapabilityStatus } from "@/features/administration/CapabilityStatus";
import { CreateDraftDialog, type CreateDraftSeed } from "@/features/model-admin/CreateDraftDialog";
import { ModelDraftEditor } from "@/features/model-admin/ModelDraftEditor";
import { ModelReleaseDetail } from "@/features/model-admin/ModelReleaseDetail";
import { Icon } from "@/ui/Icon";
import { SidebarPortal } from "@/ui/SidebarSlot";

type ModelsRoute = Extract<RouteState, { kind: "models" }>;

function appendUnique<T extends { id: string }>(current: T[], incoming: T[]) {
  const ids = new Set(current.map((item) => item.id));
  return [...current, ...incoming.filter((item) => !ids.has(item.id))];
}

export function ModelWorkbench({
  route,
  onRouteChange,
  onActiveModelChange,
}: {
  route: ModelsRoute;
  onRouteChange: (route: ModelsRoute) => void;
  onActiveModelChange?: () => Promise<unknown>;
}) {
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse>();
  const [releases, setReleases] = useState<ModelReleaseSummary[]>([]);
  const [releaseCursor, setReleaseCursor] = useState<string | null>();
  const [drafts, setDrafts] = useState<ModelDraft[]>([]);
  const [draftCursor, setDraftCursor] = useState<string | null>();
  const [runtime, setRuntime] = useState<ModelRuntimeState>();
  const [error, setError] = useState("");
  const [creating, setCreating] = useState<CreateDraftSeed>();
  const [createReleaseId, setCreateReleaseId] = useState("");
  const newDraftButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!capabilities?.modelAdmin.manageDrafts || !route.draftId || drafts.some((item) => item.id === route.draftId))
      return;
    let cancelled = false;
    api
      .modelDraft(route.draftId)
      .then((draft) => {
        if (!cancelled) setDrafts((items) => appendUnique(items, [draft]));
      })
      .catch((cause) => {
        if (!cancelled) setError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [capabilities?.modelAdmin.manageDrafts, route.draftId]);

  async function load() {
    setError("");
    try {
      const [caps, releasePage, state] = await Promise.all([
        api.capabilities(),
        api.modelReleases(),
        api.modelRuntimeState(),
      ]);
      setCapabilities(caps);
      setReleases(releasePage.items);
      setReleaseCursor(releasePage.nextCursor);
      setRuntime(state);
      setCreateReleaseId((current) => current || state.activeReleaseId);
      if (caps.modelAdmin.manageDrafts) {
        const draftPage = await api.modelDrafts();
        setDrafts(draftPage.items);
        setDraftCursor(draftPage.nextCursor);
      } else {
        setDrafts([]);
        setDraftCursor(null);
      }
      if (!route.releaseId && !route.draftId && releasePage.items.length)
        onRouteChange({ kind: "models", releaseId: state.activeReleaseId });
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function moreReleases() {
    if (!releaseCursor) return;
    try {
      const page = await api.modelReleases({ cursor: releaseCursor });
      setReleases((items) => appendUnique(items, page.items));
      setReleaseCursor(page.nextCursor);
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  async function moreDrafts() {
    if (!draftCursor) return;
    try {
      const page = await api.modelDrafts({ cursor: draftCursor });
      setDrafts((items) => appendUnique(items, page.items));
      setDraftCursor(page.nextCursor);
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  function startFromRelease(release: ModelRelease) {
    setCreating({ name: `${release.name} draft`, releaseId: release.id });
  }

  async function reloadDraft(id: string) {
    const loaded = await api.modelDraft(id);
    setDrafts((items) => items.map((item) => (item.id === id ? loaded : item)));
  }

  function updateDraft(updated: ModelDraft) {
    setDrafts((items) => items.map((item) => (item.id === updated.id ? updated : item)));
  }

  function installed(releaseId: string) {
    void load().then(() => onRouteChange({ kind: "models", releaseId }));
  }

  function activated(state: ModelRuntimeState) {
    setRuntime(state);
    void Promise.all([load(), onActiveModelChange?.()]).then(() =>
      onRouteChange({ kind: "models", releaseId: state.activeReleaseId }),
    );
  }

  const selectedDraft = route.draftId ? drafts.find((item) => item.id === route.draftId) : undefined;
  const activeReleaseId = runtime?.activeReleaseId ?? releases.find((item) => item.active)?.id ?? "";
  const activeRelease = releases.find((item) => item.id === activeReleaseId);
  const catalogue = (
    <nav className="model-catalogue" aria-label="Model catalogue">
      <section>
        <h2 className="nav-label">
          Releases <span>{releases.length}</span>
        </h2>
        {releases.map((release) => (
          <button
            key={release.id}
            className={route.releaseId === release.id ? "active" : ""}
            aria-current={route.releaseId === release.id ? "page" : undefined}
            onClick={() => onRouteChange({ kind: "models", releaseId: release.id })}
          >
            <Icon name="model" />
            <span className="catalogue-text">
              <strong>{release.name}</strong>
              <small>
                {release.key} · {release.version}
              </small>
            </span>
            {release.active && <span className="pill active-pill">Active</span>}
          </button>
        ))}
        {releaseCursor && (
          <button className="load-more" onClick={moreReleases}>
            Load more releases
          </button>
        )}
      </section>
      {capabilities?.modelAdmin.manageDrafts && (
        <section>
          <h2 className="nav-label">
            Drafts <span>{drafts.length}</span>
          </h2>
          {drafts.length ? (
            drafts.map((draft) => (
              <button
                key={draft.id}
                className={route.draftId === draft.id ? "active" : ""}
                aria-current={route.draftId === draft.id ? "page" : undefined}
                onClick={() => onRouteChange({ kind: "models", draftId: draft.id })}
              >
                <Icon name="list" />
                <span className="catalogue-text">
                  <strong>{draft.name}</strong>
                  <small>
                    Version {draft.version} · {formatServerTime(draft.updatedAt)}
                  </small>
                </span>
              </button>
            ))
          ) : (
            <p className="explorer-empty">No drafts yet.</p>
          )}
          {draftCursor && (
            <button className="load-more" onClick={moreDrafts}>
              Load more drafts
            </button>
          )}
        </section>
      )}
    </nav>
  );
  return (
    <div className="model-workbench">
      <div className="context-bar">
        <div role="group" className="shell-context" aria-label="Current context">
          <span>Model administration</span>
          {activeRelease && (
            <span className="context-status">
              Active · {activeRelease.name} {activeRelease.version}
            </span>
          )}
        </div>
      </div>
      <header className="page-header collection-header">
        <div className="page-title">
          <span className="page-icon" aria-hidden="true">
            <Icon name="model" size={20} />
          </span>
          <div>
            <h1>Models</h1>
            <p>
              Review immutable releases and safely move JSON candidates through draft, validation, installation and
              activation.
            </p>
          </div>
        </div>
        {capabilities?.modelAdmin.manageDrafts && (
          <div className="collection-header-actions">
            <button
              ref={newDraftButtonRef}
              className="primary"
              onClick={() => setCreating({ name: "", releaseId: createReleaseId })}
            >
              <Icon name="plus" /> New draft
            </button>
          </div>
        )}
      </header>
      {error && (
        <div className="inline-state error-notice" role="alert">
          <span>{error}</span>
          <button className="secondary" onClick={load}>
            Retry
          </button>
        </div>
      )}
      {!capabilities && !error && <div className="panel-state">Loading model catalogue…</div>}
      {capabilities && <CapabilityStatus capabilities={capabilities} />}
      {capabilities && !capabilities.modelAdmin.manageDrafts && (
        <p className="notice info-notice">
          Model mutations are disabled. Installed releases remain available for read-only inspection and export.
        </p>
      )}
      <SidebarPortal>{catalogue}</SidebarPortal>
      <section className="surface model-detail">
        {selectedDraft ? (
          <ModelDraftEditor
            draft={selectedDraft}
            canInstall={!!capabilities?.modelAdmin.install}
            onSaved={updateDraft}
            onReload={() => reloadDraft(selectedDraft.id)}
            onInstalled={installed}
            onDeleted={() => {
              setDrafts((items) => items.filter((item) => item.id !== selectedDraft.id));
              onRouteChange({ kind: "models", releaseId: activeReleaseId });
            }}
          />
        ) : route.releaseId && activeReleaseId ? (
          <ModelReleaseDetail
            key={route.releaseId}
            releaseId={route.releaseId}
            activeReleaseId={activeReleaseId}
            canManageDrafts={!!capabilities?.modelAdmin.manageDrafts}
            canActivate={!!capabilities?.modelAdmin.activate}
            onCreateDraft={startFromRelease}
            onActivated={activated}
          />
        ) : (
          <div className="panel-state">Choose an installed release or draft.</div>
        )}
      </section>
      {creating && (
        <CreateDraftDialog
          releases={releases}
          seed={creating}
          onClose={() => setCreating(undefined)}
          onCreated={(draft) => {
            setDrafts((items) => [draft, ...items]);
            setCreating(undefined);
            onRouteChange({ kind: "models", draftId: draft.id });
          }}
        />
      )}
    </div>
  );
}
