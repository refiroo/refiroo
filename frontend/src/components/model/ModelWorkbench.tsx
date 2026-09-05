import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client";
import type { CapabilitiesResponse, ModelDraft, ModelRelease, ModelReleaseSummary, ModelRuntimeState, RouteState } from "../../types";
import { ModelDraftEditor } from "./ModelDraftEditor";
import { ModelReleaseDetail } from "./ModelReleaseDetail";

type ModelsRoute = Extract<RouteState, { kind: "models" }>;

function appendUnique<T extends { id: string }>(current: T[], incoming: T[]) {
  const ids = new Set(current.map((item) => item.id));
  return [...current, ...incoming.filter((item) => !ids.has(item.id))];
}

export function ModelWorkbench({ route, onRouteChange, onActiveModelChange }: { route: ModelsRoute; onRouteChange: (route: ModelsRoute) => void; onActiveModelChange?: () => Promise<unknown> }) {
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse>();
  const [releases, setReleases] = useState<ModelReleaseSummary[]>([]);
  const [releaseCursor, setReleaseCursor] = useState<string | null>();
  const [drafts, setDrafts] = useState<ModelDraft[]>([]);
  const [draftCursor, setDraftCursor] = useState<string | null>();
  const [runtime, setRuntime] = useState<ModelRuntimeState>();
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [createSource, setCreateSource] = useState<"empty" | "release" | "import">("release");
  const [createName, setCreateName] = useState("");
  const [createReleaseId, setCreateReleaseId] = useState("");
  const [importText, setImportText] = useState("{}");
  const [createError, setCreateError] = useState("");
  const [pending, setPending] = useState(false);
  const newDraftButtonRef = useRef<HTMLButtonElement>(null);
  const pendingRef = useRef(false);

  useEffect(() => { pendingRef.current = pending; }, [pending]);

  useEffect(() => {
    if (!creating) return;
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !pendingRef.current) setCreating(false);
    };
    window.addEventListener("keydown", escape);
    return () => { window.removeEventListener("keydown", escape); newDraftButtonRef.current?.focus(); };
  }, [creating]);

  useEffect(() => {
    if (!capabilities?.modelAdmin.manageDrafts || !route.draftId || drafts.some((item) => item.id === route.draftId)) return;
    let cancelled = false;
    api.modelDraft(route.draftId).then((draft) => {
      if (!cancelled) setDrafts((items) => appendUnique(items, [draft]));
    }).catch((cause) => {
      if (!cancelled) setError(cause instanceof Error ? cause.message : String(cause));
    });
    return () => { cancelled = true; };
  }, [capabilities?.modelAdmin.manageDrafts, route.draftId]);

  async function load() {
    setError("");
    try {
      const [caps, releasePage, state] = await Promise.all([api.capabilities(), api.modelReleases(), api.modelRuntimeState()]);
      setCapabilities(caps); setReleases(releasePage.items); setReleaseCursor(releasePage.nextCursor); setRuntime(state);
      setCreateReleaseId((current) => current || state.activeReleaseId);
      if (caps.modelAdmin.manageDrafts) {
        const draftPage = await api.modelDrafts();
        setDrafts(draftPage.items); setDraftCursor(draftPage.nextCursor);
      } else { setDrafts([]); setDraftCursor(null); }
      if (!route.releaseId && !route.draftId && releasePage.items.length) onRouteChange({ kind: "models", releaseId: state.activeReleaseId });
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  }

  useEffect(() => { void load(); }, []);

  async function moreReleases() {
    if (!releaseCursor) return;
    try {
      const page = await api.modelReleases({ cursor: releaseCursor });
      setReleases((items) => appendUnique(items, page.items)); setReleaseCursor(page.nextCursor);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  }

  async function moreDrafts() {
    if (!draftCursor) return;
    try {
      const page = await api.modelDrafts({ cursor: draftCursor });
      setDrafts((items) => appendUnique(items, page.items)); setDraftCursor(page.nextCursor);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  }

  function startFromRelease(release: ModelRelease) {
    setCreateSource("release"); setCreateReleaseId(release.id); setCreateName(`${release.name} draft`); setCreating(true);
  }

  async function createDraft() {
    setCreateError(""); setPending(true);
    try {
      let model: Record<string, unknown> = {};
      let baseReleaseId: string | undefined;
      if (createSource === "release") {
        const release = await api.modelRelease(createReleaseId, true);
        model = release.model ?? {};
        baseReleaseId = release.id;
      } else if (createSource === "import") {
        const parsed: unknown = JSON.parse(importText);
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("Imported JSON must be an object.");
        model = parsed as Record<string, unknown>;
      }
      const draft = await api.createModelDraft({ name: createName.trim(), ...(baseReleaseId ? { baseReleaseId } : {}), model });
      setDrafts((items) => [draft, ...items]); setCreating(false); onRouteChange({ kind: "models", draftId: draft.id });
    } catch (cause) { setCreateError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setPending(false); }
  }

  async function reloadDraft(id: string) {
    const loaded = await api.modelDraft(id);
    setDrafts((items) => items.map((item) => item.id === id ? loaded : item));
  }

  function updateDraft(updated: ModelDraft) {
    setDrafts((items) => items.map((item) => item.id === updated.id ? updated : item));
  }

  function installed(releaseId: string) {
    void load().then(() => onRouteChange({ kind: "models", releaseId }));
  }

  function activated(state: ModelRuntimeState) {
    setRuntime(state);
    void Promise.all([load(), onActiveModelChange?.()]).then(() => onRouteChange({ kind: "models", releaseId: state.activeReleaseId }));
  }

  const selectedDraft = route.draftId ? drafts.find((item) => item.id === route.draftId) : undefined;
  const activeReleaseId = runtime?.activeReleaseId ?? releases.find((item) => item.active)?.id ?? "";
  return <div className="model-workbench">
    <header className="page-header model-page-header"><div><p className="eyebrow">Model administration</p><h1>Models</h1><p>Review immutable releases and safely move JSON candidates through draft, validation, installation and activation.</p></div>{capabilities?.modelAdmin.manageDrafts && <button ref={newDraftButtonRef} className="primary" onClick={() => setCreating(true)}>New draft</button>}</header>
    {error && <div className="inline-state error-notice" role="alert"><span>{error}</span><button className="secondary" onClick={load}>Retry</button></div>}
    {!capabilities && !error && <div className="panel-state">Loading model catalogue…</div>}
    {capabilities && !capabilities.modelAdmin.manageDrafts && <p className="notice">Model mutations are disabled. Installed releases remain available for read-only inspection and export.</p>}
    <div className="model-workbench-grid">
      <aside className="surface model-catalogue">
        <section><div className="model-list-heading"><h2>Releases</h2><span>{releases.length}</span></div>{releases.map((release) => <button key={release.id} className={route.releaseId === release.id ? "active" : ""} onClick={() => onRouteChange({ kind: "models", releaseId: release.id })}><strong>{release.name}</strong><small>{release.key} · {release.version}</small>{release.active && <span className="pill active-pill">Active</span>}</button>)}{releaseCursor && <button className="load-more" onClick={moreReleases}>Load more releases</button>}</section>
        {capabilities?.modelAdmin.manageDrafts && <section><div className="model-list-heading"><h2>Drafts</h2><span>{drafts.length}</span></div>{drafts.length ? drafts.map((draft) => <button key={draft.id} className={route.draftId === draft.id ? "active" : ""} onClick={() => onRouteChange({ kind: "models", draftId: draft.id })}><strong>{draft.name}</strong><small>Version {draft.version} · {new Date(draft.updatedAt).toLocaleString()}</small></button>) : <p className="panel-state">No drafts yet.</p>}{draftCursor && <button className="load-more" onClick={moreDrafts}>Load more drafts</button>}</section>}
      </aside>
      <section className="surface model-detail">
        {selectedDraft ? <ModelDraftEditor draft={selectedDraft} canInstall={!!capabilities?.modelAdmin.install} onSaved={updateDraft} onReload={() => reloadDraft(selectedDraft.id)} onInstalled={installed} onDeleted={() => { setDrafts((items) => items.filter((item) => item.id !== selectedDraft.id)); onRouteChange({ kind: "models", releaseId: activeReleaseId }); }} /> : route.releaseId && activeReleaseId ? <ModelReleaseDetail releaseId={route.releaseId} activeReleaseId={activeReleaseId} canManageDrafts={!!capabilities?.modelAdmin.manageDrafts} canActivate={!!capabilities?.modelAdmin.activate} onCreateDraft={startFromRelease} onActivated={activated} /> : <div className="empty-state">Choose an installed release or draft.</div>}
      </section>
    </div>
    {creating && <div className="dialog-backdrop" onMouseDown={() => !pending && setCreating(false)}><div className="dialog compact-dialog" role="dialog" aria-modal="true" aria-labelledby="create-draft-title" onMouseDown={(event) => event.stopPropagation()}><div className="dialog-header"><div><p className="eyebrow">Model candidate</p><h2 id="create-draft-title">Create draft</h2></div><button className="close" aria-label="Close" disabled={pending} onClick={() => setCreating(false)}>×</button></div><form onSubmit={(event) => { event.preventDefault(); void createDraft(); }}><label>Draft name<input autoFocus required maxLength={300} value={createName} onChange={(event) => setCreateName(event.target.value)} /></label><label>Starting document<select value={createSource} onChange={(event) => setCreateSource(event.target.value as typeof createSource)}><option value="release">Installed release</option><option value="empty">Empty JSON object</option><option value="import">Import JSON</option></select></label>{createSource === "release" && <label>Base release<select value={createReleaseId} onChange={(event) => setCreateReleaseId(event.target.value)}>{releases.map((release) => <option key={release.id} value={release.id}>{release.key}@{release.version}{release.active ? " (active)" : ""}</option>)}</select></label>}{createSource === "import" && <><label>JSON document<textarea rows={12} value={importText} onChange={(event) => setImportText(event.target.value)} /></label><label>Or choose a JSON file<input type="file" accept="application/json,.json" onChange={(event) => { const file = event.target.files?.[0]; if (file) file.text().then(setImportText).catch((cause) => setCreateError(String(cause))); }} /></label></>}{createError && <div className="notice error-notice" role="alert">{createError}</div>}<div className="dialog-actions"><button type="button" className="secondary" disabled={pending} onClick={() => setCreating(false)}>Cancel</button><button className="primary" disabled={pending || !createName.trim() || (createSource === "release" && !createReleaseId)}>{pending ? "Creating…" : "Create draft"}</button></div></form></div></div>}
  </div>;
}
