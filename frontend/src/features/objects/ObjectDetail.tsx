import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { fallbackDetail } from "@/model/defaults";
import { fieldValue } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import type { ApplicationDefinition, EngineModel, ObjectItem, PanelDefinition, RetirementImpact } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { RetirementImpactSummary } from "./RetirementImpactSummary";
import { ObjectFormDialog } from "./ObjectFormDialog";
import { HistoryPanel } from "./panels/HistoryPanel";
import { panelComponentRegistry } from "./panels/registry";
import type { PanelProps } from "./panels/types";

export function ObjectDetail({
  model,
  application,
  objectTypeKey,
  objectId,
  workspaceKey,
  onOpen,
  onBack,
  onDeleted,
  onChanged,
  readOnly = false,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  objectTypeKey: string;
  objectId: string;
  workspaceKey: string;
  onOpen: (objectTypeKey: string, objectId: string, applicationKey?: string) => void;
  onBack: () => void;
  onDeleted: () => void;
  onChanged: () => void;
  readOnly?: boolean;
}) {
  const [object, setObject] = useState<ObjectItem>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [retiring, setRetiring] = useState(false);
  const [retirementPending, setRetirementPending] = useState(false);
  const [retirementError, setRetirementError] = useState("");
  const [retirementImpact, setRetirementImpact] = useState<RetirementImpact>();
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const objectType = objectTypeFor(model, objectTypeKey);
  const detail =
    application.details.find((item) => item.objectTypeKey === objectTypeKey) ??
    (objectType ? fallbackDetail(objectType) : undefined);

  /**
   * Loads the object and rejects when it does not belong to the application and workspace the
   * route names. Panels call this through `onReload` and rely on it rejecting, so the rejection is
   * deliberately not converted into component state here.
   */
  async function loadObject() {
    const loaded = await api.object(objectTypeKey, objectId);
    if (loaded.applicationKey !== application.key) throw new Error("This object belongs to another application.");
    if (loaded.workspaceKey !== workspaceKey)
      throw new Error(`This object does not belong to workspace “${workspaceKey}”.`);
    setObject(loaded);
    setError("");
  }

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .object(objectTypeKey, objectId)
      .then((loaded) => {
        if (!active) return;
        if (loaded.applicationKey !== application.key) throw new Error("This object belongs to another application.");
        if (loaded.workspaceKey !== workspaceKey)
          throw new Error(`This object does not belong to workspace “${workspaceKey}”.`);
        setObject(loaded);
        setError("");
      })
      .catch((cause) => active && setError(errorMessage(cause)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
    // The effect repeats loadObject rather than calling it, because it must ignore a response that
    // arrives after the route moved on and loadObject has no cancellation of its own.
  }, [application.key, objectId, objectTypeKey, workspaceKey]);

  if (loading) return <div className="page-loading">Loading object…</div>;
  if (error || !object || !objectType || !detail)
    return (
      <div className="empty-state error-state">
        <h1>Object unavailable</h1>
        <p>{error}</p>
        <div className="empty-actions">
          <button
            className="secondary"
            onClick={() => {
              setLoading(true);
              loadObject()
                .catch((cause) => setError(errorMessage(cause)))
                .finally(() => setLoading(false));
            }}
          >
            Retry
          </button>
          <button className="secondary" onClick={onBack}>
            Back to list
          </button>
        </div>
      </div>
    );
  const currentObject = object;
  const currentObjectType = objectType;

  function handleChanged() {
    setHistoryRefresh((value) => value + 1);
    onChanged();
  }

  const panels = detail.panels.filter((panel) => panel.visible);
  const mainPanels = panels.filter((panel) => panel.region === "main").sort((a, b) => a.order - b.order);
  const sidePanels = panels.filter((panel) => panel.region === "side").sort((a, b) => a.order - b.order);
  const title = fieldValue(object, detail.header.titleField, model);
  const subtitle = detail.header.subtitleField ? fieldValue(object, detail.header.subtitleField, model) : undefined;

  async function retireObject() {
    setRetirementPending(true);
    setRetirementError("");
    try {
      await api.retireObject(
        currentObjectType.key,
        currentObject.id,
        currentObject.activeRevisionId!,
        Boolean(retirementImpact),
      );
      onChanged();
      onDeleted();
    } catch (cause) {
      if (isApiError(cause, "object_has_dependants") && cause.details) {
        setRetirementImpact(cause.details as RetirementImpact);
        setRetirementError("");
      } else {
        setRetirementError(errorMessage(cause));
      }
      if (isApiError(cause, "active_revision_conflict")) {
        try {
          await loadObject();
        } catch (reloadCause) {
          setRetirementError(errorMessage(reloadCause));
        }
        setRetirementImpact(undefined);
      }
      setRetirementPending(false);
    }
  }

  function renderPanel(panel: PanelDefinition) {
    // The registry is keyed by the union discriminant, so each entry is narrower than the union
    // being dispatched. TypeScript cannot correlate the two across an index access, which is why
    // this one widening assertion stands in for the per-entry casts the registry used to carry.
    const Component = panelComponentRegistry[panel.type] as React.ComponentType<PanelProps>;
    return (
      <section className="panel surface" key={panel.key}>
        <h2>{panel.title}</h2>
        <Component
          model={model}
          application={application}
          object={currentObject}
          panel={panel}
          onOpen={onOpen}
          onChanged={handleChanged}
          onObjectChanged={(saved) => {
            setObject(saved);
            handleChanged();
          }}
          onReload={loadObject}
          readOnly={readOnly}
        />
      </section>
    );
  }

  return (
    <>
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        {detail.breadcrumbs.showApplication && <button onClick={onBack}>{application.name}</button>}
        {detail.breadcrumbs.showAncestors &&
          object.path.slice(0, -1).map((part) => (
            <span key={part.id}>
              /<button onClick={() => onOpen(part.objectTypeKey, part.id)}>{part.name}</button>
            </span>
          ))}
        {detail.breadcrumbs.showObjectType && (
          <span>
            /<span>{objectType.name}</span>
          </span>
        )}
      </nav>
      <header className="page-header detail-header">
        <div className="object-icon" style={{ background: application.color }}>
          {iconLetters(objectType.icon ?? objectType.name)}
        </div>
        <div className="detail-title">
          {detail.header.showObjectType && <p className="eyebrow">{objectType.name}</p>}
          <h1>{String(title ?? object.name)}</h1>
          {subtitle !== undefined && subtitle !== null && subtitle !== "" && <p>{String(subtitle)}</p>}
        </div>
        <div className="detail-actions">
          <span className="version">v{object.version}</span>
          {!readOnly && (
            <>
              <button className="primary" onClick={() => setEditing(true)}>
                Edit
              </button>
              <button className="danger-outline" onClick={() => setRetiring(true)}>
                Retire object
              </button>
            </>
          )}
        </div>
      </header>
      <div className={`detail-grid ${sidePanels.length ? "with-side" : ""}`}>
        <div className="panel-column">
          {mainPanels.map(renderPanel)}
          <HistoryPanel objectTypeKey={objectTypeKey} objectId={objectId} refreshToken={historyRefresh} />
        </div>
        {sidePanels.length > 0 && <aside className="panel-column side-panels">{sidePanels.map(renderPanel)}</aside>}
      </div>
      {editing && (
        <ObjectFormDialog
          model={model}
          applicationKey={application.key}
          workspaceKey={workspaceKey}
          objectType={objectType}
          object={object}
          onClose={() => setEditing(false)}
          onSaved={(saved) => {
            setObject(saved);
            setEditing(false);
            handleChanged();
          }}
        />
      )}
      {retiring && (
        <ConfirmDialog
          title={retirementImpact ? `Retire ${retirementImpact.objectCount} objects?` : `Retire “${object.name}”?`}
          confirmLabel={retirementImpact ? "Confirm retirement" : "Retire object"}
          pending={retirementPending}
          error={retirementError}
          onCancel={() => {
            setRetiring(false);
            setRetirementError("");
            setRetirementImpact(undefined);
          }}
          onConfirm={retireObject}
        >
          {retirementImpact ? (
            <RetirementImpactSummary model={model} impact={retirementImpact} />
          ) : (
            <p>
              The engine will first check for dependent objects. If dependencies exist, nothing will be retired until
              you review and confirm the cascade.
            </p>
          )}
        </ConfirmDialog>
      )}
    </>
  );
}

function iconLetters(icon: string) {
  return icon
    .split(/[-\s]/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}
