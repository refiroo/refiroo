import { useEffect, useRef, useState, type CSSProperties } from "react";
import { useLocalNumberPreference } from "@/lib/localPreference";
import { ResizeHandle } from "@/ui/ResizeHandle";
import { RecordActionMenu } from "@/features/objects/RecordActionMenu";
import { EditableField, fieldEditing, type FieldLayout } from "@/features/objects/EditableField";
import { useWorkspaceData, useDataApi, useRecordWrites } from "@/features/workspaces/WorkspaceDataContext";
import { changedObjectType, errorMessage } from "@/api/errors";
import { fallbackDetail } from "@/model/defaults";
import { fieldValue } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import { objectTypeHue } from "@/model/hues";
import type {
  ApplicationDefinition,
  EngineModel,
  ObjectItem,
  PanelDefinition,
  RelationsPanelDefinition,
  RouteState,
} from "@/types";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { ObjectDeleteDialog } from "@/features/objects/ObjectDeleteDialog";
import { ConnectedList } from "./panels/ConnectedList";
import { HistoryPanel } from "./panels/HistoryPanel";
import { CopyValue } from "@/ui/CopyValue";
import { HueTile } from "@/ui/HueTile";
import { Icon } from "@/ui/Icon";
import { RecordChip } from "@/ui/RecordChip";
import { PageHeader } from "@/ui/PageHeader";
import { panelComponentRegistry } from "./panels/registry";
import type { PanelProps } from "./panels/types";
import { Breadcrumbs } from "@/ui/Breadcrumbs";
import { Card } from "@/ui/Card";
import { focusInNavigationRail } from "@/ui/navigationRail";

/**
 * The record a detail followed to its current type (D42). Its next mount is the same record under a
 * new route, not a navigation the user made, so it leaves focus where the user is working.
 */
let followedObjectId: string | undefined;

export function ObjectDetail({
  model,
  application,
  objectTypeKey,
  objectId,
  workspaceKey,
  onOpen,
  onBack,
  showBackToList = true,
  inspector = false,
  onExpand,
  initialAction,
  readOnly = true,
  refreshToken = 0,
  onChanged = () => undefined,
  onTypeChanged,
  onPropose,
  onOpenChanges,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  objectTypeKey: string;
  objectId: string;
  workspaceKey: string;
  onOpen: (objectTypeKey: string, objectId: string, applicationKey?: string, action?: "edit" | "delete") => void;
  /** Opens the changes of a person or client named in the record's history (0.12 Z6, D345). */
  onOpenChanges?: (route: RouteState) => void;
  onBack: () => void;
  showBackToList?: boolean;
  inspector?: boolean;
  onExpand?: () => void;
  initialAction?: "edit" | "delete";
  readOnly?: boolean;
  /** Changes when the collection beside the inspector wrote, so the record is read again. */
  refreshToken?: number;
  onChanged?: () => void;
  /**
   * The record has another type in this context (D42): a restructuring changed it. The route
   * follows it there, replacing the old route so Back does not return to it.
   */
  onTypeChanged?: (objectTypeKey: string) => void;
  /**
   * A record the person cannot change live but can propose a change to, through their own change
   * set (0.12 Z5, D324): the way to do it for a record of this type, if any.
   */
  onPropose?: (applicationKey: string, objectTypeKey: string) => ((objectId?: string) => void) | undefined;
}) {
  const api = useDataApi();
  // The record's own values and its deletion follow its type's writes (Z5, D329); relationships
  // and the records in its panels follow theirs, in their panels.
  const writes = useRecordWrites();
  const recordReadOnly = readOnly || !writes.permits(application.key, objectTypeKey);
  const proposeHere = readOnly ? onPropose?.(application.key, objectTypeKey) : undefined;
  const { changeSet, publication } = useWorkspaceData();
  const [editing, setEditing] = useState(initialAction === "edit");
  const [deleting, setDeleting] = useState(initialAction === "delete");
  const titleRef = useRef<HTMLHeadingElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  // The header field open for editing in place (UA8), and the one whose value takes focus back.
  const [headerField, setHeaderField] = useState<string>();
  const [headerReturn, setHeaderReturn] = useState<string>();
  const [panelRefresh, setPanelRefresh] = useState(0);
  const [object, setObject] = useState<ObjectItem>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const propertiesWidth = useLocalNumberPreference(
    `rdm:layout:properties-width:v1:${application.key}:${objectTypeKey}`,
    300,
    240,
    640,
  );
  const objectType = objectTypeFor(model, objectTypeKey);
  const detail =
    application.details.find((item) => item.objectTypeKey === objectTypeKey) ??
    (objectType ? fallbackDetail(objectType, model) : undefined);

  /**
   * Loads the object and rejects when it does not belong to the application and workspace the
   * route names. Panels call this through `onReload` and rely on it rejecting, so the rejection is
   * deliberately not converted into component state here.
   */
  async function loadObject() {
    const loaded = await api.object(objectTypeKey, objectId, workspaceKey);
    if (loaded.applicationKey !== application.key) throw new Error("This object belongs to another application.");
    if (loaded.workspaceKey !== workspaceKey)
      throw new Error(`This object does not belong to workspace “${workspaceKey}”.`);
    setObject(loaded);
    setError("");
  }

  // Read through a ref, so a new callback from the parent does not read the record again.
  const typeChanged = useRef(onTypeChanged);
  useEffect(() => {
    typeChanged.current = onTypeChanged;
  });

  useEffect(() => {
    let active = true;
    let following = false;
    setLoading(true);
    api
      .object(objectTypeKey, objectId, workspaceKey)
      .then((loaded) => {
        if (!active) return;
        if (loaded.applicationKey !== application.key) throw new Error("This object belongs to another application.");
        if (loaded.workspaceKey !== workspaceKey)
          throw new Error(`This object does not belong to workspace “${workspaceKey}”.`);
        setObject(loaded);
        setError("");
      })
      .catch((cause) => {
        if (!active) return;
        const current = changedObjectType(cause);
        if (current && typeChanged.current) {
          // Still loading: the route opens the record under its current type.
          following = true;
          followedObjectId = objectId;
          typeChanged.current(current);
        } else setError(errorMessage(cause));
      })
      .finally(() => active && !following && setLoading(false));
    return () => {
      active = false;
    };
    // The effect repeats loadObject rather than calling it, because it must ignore a response that
    // arrives after the route moved on and loadObject has no cancellation of its own.
  }, [api, application.key, objectId, objectTypeKey, workspaceKey]);

  // A write beside the record (a tree lens renaming or moving it) re-reads it in place, without the
  // loading state, so focus stays where the user is working.
  const lastRefresh = useRef(refreshToken);
  useEffect(() => {
    if (lastRefresh.current === refreshToken) return;
    lastRefresh.current = refreshToken;
    let active = true;
    api
      .object(objectTypeKey, objectId, workspaceKey)
      .then((loaded) => {
        if (!active) return;
        setObject(loaded);
        setPanelRefresh((value) => value + 1);
        setHistoryRefresh((value) => value + 1);
      })
      .catch((cause) => {
        if (!active) return;
        const current = changedObjectType(cause);
        if (current && typeChanged.current) {
          followedObjectId = objectId;
          typeChanged.current(current);
        } else setError(errorMessage(cause));
      });
    return () => {
      active = false;
    };
  }, [api, objectId, objectTypeKey, workspaceKey, refreshToken]);

  // Read once per mount: whether this mount only followed the record to its current type.
  const [followed] = useState(() => followedObjectId === objectId);
  useEffect(() => {
    if (followed) followedObjectId = undefined;
  }, [followed]);
  useEffect(() => {
    if (loading || initialAction || followed) return;
    // A record chosen in the navigation rail leaves focus there, so the reader goes on browsing.
    if (focusInNavigationRail()) titleRef.current?.scrollIntoView?.({ block: "nearest" });
    else titleRef.current?.focus();
  }, [loading, objectId, inspector, initialAction, followed]);

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
          {showBackToList && (
            <button className="secondary" onClick={onBack}>
              Back to list
            </button>
          )}
        </div>
      </div>
    );
  const currentObject = object;

  const panels = detail.panels.filter((panel) => panel.visible);
  // The inspector lists the relations panels together as Connected (UA4); the full page shows their tables.
  const connected = inspector
    ? panels
        .filter((panel): panel is RelationsPanelDefinition => panel.type === "relations")
        .sort((a, b) => (a.region === b.region ? a.order - b.order : a.region === "side" ? -1 : 1))
    : [];
  const shown = inspector ? panels.filter((panel) => panel.type !== "relations") : panels;
  const mainPanels = shown.filter((panel) => panel.region === "main").sort((a, b) => a.order - b.order);
  const sidePanels = shown.filter((panel) => panel.region === "side").sort((a, b) => a.order - b.order);
  const hue = objectTypeHue(model, objectType.key);
  const title = fieldValue(object, detail.header.titleField, model);
  const subtitle = detail.header.subtitleField ? fieldValue(object, detail.header.subtitleField, model) : undefined;
  const subtitleField = detail.header.subtitleField;
  const subtitleShown =
    subtitleField !== undefined &&
    (fieldEditing(model, object, subtitleField, recordReadOnly) !== undefined ||
      (subtitle !== undefined && subtitle !== null && subtitle !== ""));

  /** The header's title or subtitle, edited in place as a details-panel field is (UA8, U-D16). */
  function headerValue(field: string, layout: FieldLayout) {
    const close = () => {
      setHeaderField(undefined);
      setHeaderReturn(field);
    };
    return (
      <EditableField
        model={model}
        object={currentObject!}
        field={field}
        layout={layout}
        readOnly={recordReadOnly}
        editing={headerField === field}
        disabled={headerField !== undefined && headerField !== field}
        focusOnMount={headerReturn === field}
        onEdit={() => {
          setHeaderReturn(undefined);
          setHeaderField(field);
        }}
        onClose={close}
        onSaved={(saved) => {
          setObject(saved);
          onChanged();
          setHistoryRefresh((value) => value + 1);
          close();
        }}
        onConflict={loadObject}
      />
    );
  }
  const titleField = detail.header.titleField;

  function renderPanel(panel: PanelDefinition) {
    // The registry is keyed by the union discriminant, so each entry is narrower than the union
    // being dispatched. TypeScript cannot correlate the two across an index access, which is why
    // this one widening assertion stands in for the per-entry casts the registry used to carry.
    const Component = panelComponentRegistry[panel.type] as React.ComponentType<PanelProps>;
    return (
      <Card as="section" flush className="panel" key={panel.key}>
        <h2>{panel.title}</h2>
        <Component
          model={model}
          application={application}
          object={currentObject}
          panel={panel}
          onOpen={onOpen}
          onChanged={() => {
            onChanged();
            setHistoryRefresh((value) => value + 1);
          }}
          onObjectChanged={(saved) => {
            setObject(saved);
            onChanged();
            setHistoryRefresh((value) => value + 1);
          }}
          onReload={loadObject}
          readOnly={panel.type === "attributes" ? recordReadOnly : readOnly}
        />
      </Card>
    );
  }

  return (
    <article className={`record-detail${inspector ? " record-inspector" : ""}`} aria-label="Record details">
      {showBackToList && (
        <div className="record-topline">
          <button className="ghost back-link" onClick={onBack}>
            <Icon name="arrow-left" size={15} />
            Back to list
          </button>
        </div>
      )}
      <div className="record-header" data-hue={hue}>
        <Breadcrumbs
          items={[
            detail.breadcrumbs.showApplication && {
              key: "application",
              content: <button onClick={onBack}>{application.name}</button>,
            },
            ...(detail.breadcrumbs.showAncestors
              ? object.path.slice(0, -1).map((part) => ({
                  key: part.id,
                  content: (
                    <RecordChip
                      hue={objectTypeHue(model, part.objectTypeKey)}
                      onOpen={() => onOpen(part.objectTypeKey, part.id)}
                    >
                      {part.name}
                    </RecordChip>
                  ),
                }))
              : []),
            detail.breadcrumbs.showObjectType && { key: "type", content: objectType.name, current: true },
          ]}
        />
        <PageHeader
          variant="detail"
          onContextMenu={(event) => {
            event.preventDefault();
            setMenuOpen(true);
          }}
          icon={<HueTile hue={hue} icon={objectType.icon} size={40} />}
          eyebrow={detail.header.showObjectType ? objectType.name : undefined}
          title={headerField === titleField ? undefined : headerValue(titleField, "title")}
          titleLabel={String(title ?? object.name)}
          titleEditor={headerField === titleField ? headerValue(titleField, "title") : undefined}
          titleRef={titleRef}
          description={subtitleShown ? headerValue(subtitleField!, "subtitle") : undefined}
          actions={
            <>
              <span className="version" title="Record version, used to detect concurrent changes">
                v{object.version}
              </span>
              {onExpand && (
                <button className="secondary expand-record" onClick={onExpand}>
                  Expand to full page
                </button>
              )}
              {proposeHere && (
                <button className="primary" onClick={() => proposeHere(object.id)}>
                  Propose a change
                </button>
              )}
              <RecordActionMenu
                object={object}
                readOnly={recordReadOnly}
                label="Record actions"
                isOpen={menuOpen}
                onOpenChange={setMenuOpen}
                onEdit={() => setEditing(true)}
                onDelete={() => setDeleting(true)}
              />
            </>
          }
        />
        {/* The record's own ID, as the API returns it (`id`), to copy into another system. */}
        <p className="record-meta">
          <CopyValue label="ID" value={object.id} />
        </p>
      </div>
      <div
        key={panelRefresh}
        className={`detail-grid ${sidePanels.length ? "with-side" : ""}`}
        style={{ "--properties-width": `${propertiesWidth.value}px` } as CSSProperties}
      >
        {sidePanels.length > 0 && <aside className="panel-column side-panels">{sidePanels.map(renderPanel)}</aside>}
        {sidePanels.length > 0 && !inspector && (
          <ResizeHandle
            className="properties-resizer"
            label="Resize record properties"
            value={propertiesWidth.value}
            min={240}
            max={640}
            direction={-1}
            onChange={propertiesWidth.change}
            onReset={propertiesWidth.reset}
          />
        )}
        <div className="panel-column main-panels">
          {connected.length > 0 && (
            <ConnectedList model={model} object={object} panels={connected} onOpen={onOpen} onManage={onExpand} />
          )}
          {mainPanels.map(renderPanel)}
          {!changeSet && !publication && (
            <HistoryPanel
              model={model}
              objectTypeKey={objectTypeKey}
              objectId={objectId}
              hue={hue}
              refreshToken={historyRefresh}
              onOpenChanges={onOpenChanges}
            />
          )}
        </div>
      </div>
      {editing && !recordReadOnly && (
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
            setHistoryRefresh((value) => value + 1);
            setPanelRefresh((value) => value + 1);
            onChanged();
          }}
        />
      )}
      {deleting && !recordReadOnly && (
        <ObjectDeleteDialog
          model={model}
          object={object}
          onClose={() => setDeleting(false)}
          onDeleted={() => {
            onChanged();
            onBack();
          }}
        />
      )}
    </article>
  );
}
