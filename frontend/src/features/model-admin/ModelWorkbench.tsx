/**
 * Settings › Model (Track U U3, U-D10 as revised 2026-10-06): the model workbench as before, its
 * catalogue of releases and drafts beside the selected release or draft. Each has its own address;
 * without one the active release is shown. Below 760px the catalogue and the selection take turns.
 */

import { useEffect, useRef, useState } from "react";
import { formatServerTime } from "@/lib/dates";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type {
  CapabilitiesResponse,
  ModelDraft,
  ModelRelease,
  ModelReleaseSummary,
  WorkspaceModel,
  SettingsRoute,
} from "@/types";
import { CapabilityStatus } from "@/features/administration/CapabilityStatus";
import { CreateDraftDialog, type CreateDraftSeed } from "@/features/model-admin/CreateDraftDialog";
import { ModelDraftEditor } from "@/features/model-admin/ModelDraftEditor";
import { ModelReleaseDetail } from "@/features/model-admin/ModelReleaseDetail";
import { CatalogueEntry, CatalogueLayout } from "@/ui/CatalogueLayout";
import { Icon } from "@/ui/Icon";
import { EmptyState } from "@/ui/EmptyState";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { StatusPill } from "@/ui/StatusPill";
import { useToast } from "@/ui/Toast";
import { Notice } from "@/ui/Notice";

type ModelsRoute = Extract<SettingsRoute, { page: "model" }>;

const MODEL: ModelsRoute = { kind: "settings", page: "model" };

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
  const toast = useToast();
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse>();
  const [releases, setReleases] = useState<ModelReleaseSummary[]>([]);
  const [releaseCursor, setReleaseCursor] = useState<string | null>();
  const [drafts, setDrafts] = useState<ModelDraft[]>([]);
  const [draftCursor, setDraftCursor] = useState<string | null>();
  const [runtime, setRuntime] = useState<WorkspaceModel>();
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
        api.defaultWorkspaceModel(),
      ]);
      setCapabilities(caps);
      setReleases(releasePage.items);
      setReleaseCursor(releasePage.nextCursor);
      setRuntime(state);
      setCreateReleaseId((current) => current || state.releaseId);
      if (caps.modelAdmin.manageDrafts) {
        const draftPage = await api.modelDrafts();
        setDrafts(draftPage.items);
        setDraftCursor(draftPage.nextCursor);
      } else {
        setDrafts([]);
        setDraftCursor(null);
      }
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
    void load().then(() => {
      toast("The draft was installed as a release. It is not active until you activate it.");
      onRouteChange({ ...MODEL, releaseId });
    });
  }

  function activated(state: WorkspaceModel) {
    setRuntime(state);
    void Promise.all([load(), onActiveModelChange?.()]).then(() => {
      toast("The release is now the active model.");
      onRouteChange({ ...MODEL, releaseId: state.releaseId });
    });
  }

  const selectedDraft = route.draftId ? drafts.find((item) => item.id === route.draftId) : undefined;
  const activeReleaseId = runtime?.releaseId ?? releases.find((item) => item.assigned)?.id ?? "";
  const activeRelease = releases.find((item) => item.id === activeReleaseId);
  // Without a selection in the address the active release is shown, as the workbench always did.
  const shownReleaseId = route.draftId ? undefined : (route.releaseId ?? (activeReleaseId || undefined));
  const selected = Boolean(route.releaseId || route.draftId);
  const catalogue = (
    <nav className="model-catalogue" aria-label="Model catalogue">
      <section>
        <h2 className="nav-label">
          Releases <span>{releases.length}</span>
        </h2>
        {releases.map((release) => (
          <CatalogueEntry
            key={release.id}
            icon="model"
            title={release.name}
            subtitle={`${release.key} · ${release.version}`}
            current={shownReleaseId === release.id}
            onSelect={() => onRouteChange({ ...MODEL, releaseId: release.id })}
            pill={release.id === activeReleaseId && <StatusPill tone="success">Active</StatusPill>}
          />
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
              <CatalogueEntry
                key={draft.id}
                icon="list"
                title={draft.name}
                subtitle={`Version ${draft.version} · ${formatServerTime(draft.updatedAt)}`}
                current={route.draftId === draft.id}
                onSelect={() => onRouteChange({ ...MODEL, draftId: draft.id })}
              />
            ))
          ) : (
            <EmptyState>No drafts yet.</EmptyState>
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
    <SettingsLayout
      eyebrow="Administration"
      title="Model"
      description={
        <>
          Review immutable releases and safely move JSON candidates through draft, validation, installation and
          activation.
          {activeRelease && (
            <>
              {" "}
              <StatusPill tone="success">
                Active · {activeRelease.name} {activeRelease.version}
              </StatusPill>
            </>
          )}
        </>
      }
      actions={
        capabilities?.modelAdmin.manageDrafts && (
          <>
            <button
              className="secondary"
              onClick={() => setCreating({ name: "", releaseId: createReleaseId, workbook: true })}
            >
              <Icon name="table" /> New from a workbook
            </button>
            <button
              ref={newDraftButtonRef}
              className="primary"
              onClick={() => setCreating({ name: "", releaseId: createReleaseId })}
            >
              <Icon name="plus" /> New draft
            </button>
          </>
        )
      }
    >
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
        <Notice>
          Model mutations are disabled. Installed releases remain available for read-only inspection and export.
        </Notice>
      )}
      <CatalogueLayout
        catalogue={catalogue}
        hasSelection={!!selected}
        backLabel="All releases and drafts"
        onBack={() => onRouteChange(MODEL)}
      >
        {selectedDraft ? (
          <ModelDraftEditor
            draft={selectedDraft}
            canInstall={!!capabilities?.modelAdmin.install}
            onSaved={updateDraft}
            onReload={() => reloadDraft(selectedDraft.id)}
            onInstalled={installed}
            onOpenEditor={() => onRouteChange({ ...MODEL, draftId: selectedDraft.id, editor: {} })}
            onDeleted={() => {
              setDrafts((items) => items.filter((item) => item.id !== selectedDraft.id));
              toast(`Draft ${selectedDraft.name} was deleted.`);
              onRouteChange(MODEL);
            }}
          />
        ) : shownReleaseId && activeReleaseId ? (
          <ModelReleaseDetail
            key={shownReleaseId}
            releaseId={shownReleaseId}
            activeReleaseId={activeReleaseId}
            canManageDrafts={!!capabilities?.modelAdmin.manageDrafts}
            canActivate={!!capabilities?.modelAdmin.activate}
            onCreateDraft={startFromRelease}
            onActivated={activated}
          />
        ) : (
          <div className="panel-state">Choose an installed release or draft.</div>
        )}
      </CatalogueLayout>
      {creating && (
        <CreateDraftDialog
          releases={releases}
          seed={creating}
          onClose={() => setCreating(undefined)}
          onCreated={(draft) => {
            setDrafts((items) => [draft, ...items]);
            setCreating(undefined);
            onRouteChange({ ...MODEL, draftId: draft.id, editor: {} });
          }}
        />
      )}
    </SettingsLayout>
  );
}
