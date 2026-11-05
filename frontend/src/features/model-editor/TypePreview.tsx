/**
 * The selected type's preview and its layout editor (0.10 A4b; MODEL_AUTHORING "Views and layouts"):
 * the type's record page and table rendered by the record screen's own renderers from the draft,
 * compiled but not installed (D43), over records of the active model read live in a workspace the
 * reader picks (D44). A new type shows an empty record. Nothing the preview shows writes
 * (`api/previewClient`).
 *
 * The preview opens in the editor's centre; the layout editor takes the whole editor (the user,
 * 2026-10-12). A band in the data-context band's way says which one shows. In the layout editor each
 * panel, field and column is a frame with a menu, the keyboard and phone path, and a grip to drag with
 * mouse or pen (D46); each choice is one step of the draft's history.
 */

import { useWorkspaceModel } from "@/model/workspaceModels";
import { useEffect, useMemo, useState, type DragEvent, type ReactNode } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { createPreviewClient, emptyRecord, PREVIEW_EMPTY_ID } from "@/api/previewClient";
import { ObjectDetail } from "@/features/objects/ObjectDetail";
import { ObjectCollectionView } from "@/features/objects/CollectionView";
import { panelComponentRegistry } from "@/features/objects/panels/registry";
import type { PanelProps } from "@/features/objects/panels/types";
import { PreviewDataProvider } from "@/features/workspaces/WorkspaceDataContext";
import { WorkspaceSelector } from "@/features/workspaces/WorkspaceSelector";
import { attributeName, fieldValue } from "@/model/fields";
import type {
  ApplicationDefinition,
  CollectionQueryState,
  DetailViewDefinition,
  DraftOperation,
  EditorMode,
  EngineModel,
  ModelDraftModel,
  ObjectItem,
  PanelDefinition,
  TableViewDefinition,
  Workspace,
} from "@/types";
import { ActionMenu, type ActionMenuItem } from "@/ui/ActionMenu";
import { EmptyState } from "@/ui/EmptyState";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { ControlPopover } from "@/ui/ControlPopover";
import { Notice } from "@/ui/Notice";
import { ObjectLookup } from "@/ui/ObjectLookup";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { Tabs } from "@/ui/Tabs";
import type { OperationSpec } from "@/features/model-editor/operations";
import {
  addFieldSpec,
  fieldToPanel,
  moveColumn,
  moveField,
  movePanel,
  addPanelSpec,
  newFieldGroupSpec,
  panelColumns,
  panelColumnsSpec,
  panelSortSpec,
  panelToRegion,
  regionPanels,
  removeColumn,
  removeField,
  removePanel,
  renamePanelSpec,
  setPanelVisible,
  tableColumnsSpec,
  tableFiltersSpec,
  tableSortSpec,
  type LayoutPlace,
  type Region,
} from "@/features/model-editor/layout";

/** How the preview sends a layout change: one step, as every editor operation (A2). */
export type SendLayout = (operations: DraftOperation[]) => Promise<unknown>;

const REGIONS: readonly Region[] = ["main", "side"];
const noop = () => undefined;
const reload = () => Promise.resolve();

type Dragged =
  { kind: "panel"; key: string } | { kind: "field"; panel: string; field: string } | { kind: "column"; column: string };

export function TypePreview({
  mode,
  draftId,
  version,
  objectTypeKey,
  activeModel,
  workspaceKey: initialWorkspace,
  send,
  onDialog,
  onShowIssues,
  actions,
}: {
  /** The preview, read only, or the layout editor, where the page and table are laid out in place. */
  mode: EditorMode;
  draftId: string;
  /** The draft's version: the preview reads the draft again whenever it changes. */
  version: number;
  objectTypeKey: string;
  activeModel: EngineModel;
  workspaceKey: string;
  send: SendLayout;
  /** Opens a layout dialog in the editor's one operation dialog (D38). */
  onDialog: (operation: OperationSpec, objectTypeKey: string) => void;
  onShowIssues: () => void;
  /** The band's actions: where to go next, and in the layout editor undo and redo. */
  actions: ReactNode;
}) {
  const editing = mode === "layout";
  const [read, setRead] = useState<ModelDraftModel>();
  const [readError, setReadError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceKey, setWorkspaceKey] = useState(initialWorkspace);
  // The records read for one type, workspace and search; others are still loading.
  const [loaded, setLoaded] = useState<{ key: string; items: ObjectItem[] }>();
  const [tab, setTab] = useState("record");

  useEffect(() => {
    let cancelled = false;
    api
      .modelDraftModel(draftId)
      .then((next) => {
        if (cancelled) return;
        setRead(next);
        setReadError("");
      })
      .catch((cause) => !cancelled && setReadError(errorMessage(cause)));
    return () => {
      cancelled = true;
    };
  }, [draftId, version, attempt]);

  useEffect(() => {
    let cancelled = false;
    api
      .workspaces({ pageSize: 100 })
      .then((page) => !cancelled && setWorkspaces(page.items))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  // Records are read under the chosen workspace's own model, and only from a workspace running the
  // draft's model: another model's records say nothing true about this draft (0.11 D55).
  const shownModel = useWorkspaceModel(workspaceKey, activeModel);
  const otherModel = Boolean(read?.model && shownModel.release.key !== read.model.release.key);
  const live = !otherModel && shownModel.objectTypes.some((item) => item.key === objectTypeKey);
  const readKey = `${objectTypeKey}|${workspaceKey}`;
  useEffect(() => {
    if (!live) return;
    let cancelled = false;
    api
      .objects(objectTypeKey, { workspaceKey, pageSize: 1, sort: "name" })
      .then((page) => !cancelled && setLoaded({ key: readKey, items: page.items }))
      .catch(() => !cancelled && setLoaded({ key: readKey, items: [] }));
    return () => {
      cancelled = true;
    };
  }, [objectTypeKey, live, workspaceKey, readKey]);
  const records = !live ? [] : loaded?.key === readKey ? loaded.items : undefined;

  const model = useMemo<EngineModel | undefined>(
    () => (read?.model ? { ...read.model, placements: read.placements } : undefined),
    [read],
  );
  const application = model?.applications.find((item) => item.objectTypeKeys.includes(objectTypeKey));
  const objectType = model?.objectTypes.find((item) => item.key === objectTypeKey);
  // The record the reader chose, else the first by name; a new type, or a type without records, shows
  // the empty record.
  const [chosen, setChosen] = useState<{ key: string; record?: ObjectItem }>();
  const choice = chosen?.key === readKey ? chosen : undefined;
  const shownRecord = choice ? choice.record : records?.[0];
  const objectId = shownRecord?.id ?? PREVIEW_EMPTY_ID;
  const sample = application ? emptyRecord(application.key, objectTypeKey, workspaceKey) : undefined;
  const client = useMemo(
    () => (model ? createPreviewClient(shownModel, model, sample) : undefined),
    // The sample changes only with its place; a new object each render must not make a new client.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [model, shownModel, application?.key, objectTypeKey, workspaceKey],
  );

  const typeName = objectType?.name ?? objectTypeKey;
  const note = editing
    ? "Each change is one step of the draft, undone with Undo."
    : otherModel
      ? "The draft's layout over an empty record: this workspace runs another model, so none of its records is read."
      : "The draft's layout over records read live. Its controls are shown and disabled: the preview writes nothing.";
  const frame = (children: ReactNode, choices?: ReactNode) => (
    <section className={`type-preview type-preview-${mode}`} aria-label={editing ? "Layout editor" : "Preview"}>
      <ModeBand mode={mode} name={typeName} note={note} choices={choices} actions={actions} />
      <div className="type-preview-body">{children}</div>
    </section>
  );

  if (readError) return frame(<InlineError message={readError} onRetry={() => setAttempt((value) => value + 1)} />);
  if (!read) return frame(<Skeleton lines={5} label="Loading the preview" />);
  if (!read.valid || !model || !client)
    return frame(
      <div className="preview-invalid">
        <p className="preview-invalid-title">
          The draft has {read.diagnostics.length} {read.diagnostics.length === 1 ? "issue" : "issues"}, so it cannot be
          previewed
        </p>
        <p className="muted">
          The preview renders the draft as it would run. Fix the issues, or undo the last step, and it comes back.
        </p>
        <button type="button" className="secondary" onClick={onShowIssues}>
          Show issues
        </button>
      </div>,
    );
  if (!application || !objectType)
    return frame(<EmptyState>This type is in no application of the draft, so it has no page to preview.</EmptyState>);

  const place: LayoutPlace = { applicationKey: application.key, objectTypeKey };
  const detail = application.details.find((item) => item.objectTypeKey === objectTypeKey);
  const views = application.views.filter(
    (view): view is TableViewDefinition => view.type === "table" && view.objectTypeKey === objectTypeKey,
  );

  const workspaceLabel = workspaces.find((item) => item.key === workspaceKey)?.label ?? workspaceKey;
  const recordLabel = shownRecord?.name || "Empty record";
  const chevron = <Icon name="chevron-down" size={13} />;
  // What the page shows, as the data-context band's choices are drawn: each a word that opens its list.
  const choices = (
    <div role="group" className="band-context band-compact editor-mode-choices" aria-label="What the page shows">
      <ControlPopover
        label={`Workspace: ${workspaceLabel}`}
        trigger={
          <>
            <span className="band-choice-text">{workspaceLabel}</span>
            {chevron}
          </>
        }
        triggerClassName="band-choice"
        placement="bottom start"
        className="band-popover"
      >
        {(close) => (
          <WorkspaceSelector
            workspaceKey={workspaceKey}
            onChange={(key) => {
              close();
              setWorkspaceKey(key);
            }}
          />
        )}
      </ControlPopover>
      <span aria-hidden="true" className="band-separator">
        /
      </span>
      {live ? (
        <ControlPopover
          label={`Record: ${recordLabel}`}
          trigger={
            <>
              <span className="band-choice-text">{recordLabel}</span>
              {chevron}
            </>
          }
          triggerClassName="band-choice"
          placement="bottom start"
          className="band-popover preview-record-popover"
        >
          {(close) => (
            <div className="preview-record-choice">
              <ObjectLookup
                objectTypeKey={objectTypeKey}
                applicationKey={application.key}
                workspaceKey={workspaceKey}
                label={`${objectType.name} to preview`}
                selectedId={shownRecord?.id ?? null}
                selectedLabel={shownRecord?.name}
                onChange={(item) => {
                  setChosen({ key: readKey, record: item });
                  close();
                }}
              />
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setChosen({ key: readKey });
                  close();
                }}
              >
                Show an empty record
              </button>
            </div>
          )}
        </ControlPopover>
      ) : (
        <span className="band-choice-text muted">Empty record: {objectType.name} is new, no records yet</span>
      )}
    </div>
  );

  const record = !editing ? (
    <PreviewControls>
      <PreviewDataProvider client={client}>
        <ObjectDetail
          key={`${objectId}:${version}`}
          model={model}
          application={application}
          objectTypeKey={objectTypeKey}
          objectId={objectId}
          workspaceKey={workspaceKey}
          onOpen={noop}
          onBack={noop}
          showBackToList={false}
          readOnly={false}
        />
      </PreviewDataProvider>
    </PreviewControls>
  ) : !detail ? (
    <Notice
      actions={
        <button
          type="button"
          className="secondary"
          onClick={() =>
            void send([{ kind: "addDetailPage", applicationKey: application.key, objectType: objectTypeKey }])
          }
        >
          Declare its page
        </button>
      }
    >
      The model declares no detail page for {objectType.name}, so the record screen shows a page of its own. Declare its
      page to lay it out: the server writes the page a new type gets, one step you can undo.
    </Notice>
  ) : (
    <LayoutCanvas
      model={model}
      application={application}
      detail={detail}
      place={place}
      client={client}
      objectId={objectId}
      workspaceKey={workspaceKey}
      send={send}
      onDialog={(operation) => onDialog(operation, objectTypeKey)}
    />
  );

  const table = views.length ? (
    <TablePreview
      key={objectTypeKey}
      model={model}
      application={application}
      views={views}
      place={place}
      client={client}
      live={live}
      workspaceKey={workspaceKey}
      editing={editing}
      version={version}
      send={send}
      onDialog={(operation) => onDialog(operation, objectTypeKey)}
    />
  ) : (
    <EmptyState>The draft declares no table view for {objectType.pluralName}.</EmptyState>
  );

  return frame(
    <>
      <Tabs
        label={editing ? "Layout of" : "Preview of"}
        selected={tab}
        onChange={setTab}
        tabs={[
          { id: "record", label: "Record page", content: <div className="preview-body">{record}</div> },
          { id: "table", label: "Table", content: <div className="preview-body">{table}</div> },
        ]}
      />
    </>,
    choices,
  );
}

/**
 * The page as the record screen draws it, with its editing controls shown and disabled (the user,
 * 2026-10-12): a disabled fieldset disables every button, field and menu inside it, so the preview
 * shows what a reader will be able to do and nothing can be pressed. Links do not follow either.
 */
function PreviewControls({ children, when = true }: { children: ReactNode; when?: boolean }) {
  if (!when) return <>{children}</>;
  return (
    <fieldset className="preview-controls" disabled aria-label="The page's controls, shown and disabled in the preview">
      {children}
    </fieldset>
  );
}

/**
 * The band that says what the centre shows, in the data-context band's way (ADR-039): a preview is
 * marked as a publication is (a read-only view), the layout editor as a change set is (an edit under
 * way), so neither is taken for the live record screen.
 */
function ModeBand({
  mode,
  name,
  note,
  choices,
  actions,
}: {
  mode: EditorMode;
  name: string;
  note: string;
  /** What the page shows (the workspace and the record), once the draft is read. */
  choices?: ReactNode;
  actions: ReactNode;
}) {
  const layout = mode === "layout";
  return (
    <div className={`data-context-band editor-mode-band band-${layout ? "change-set" : "publication"}`}>
      <div className="band-context">
        <div role="group" className="shell-context" aria-label="What this shows">
          {/* The layout editor is the page, so its title is the page's heading; the preview sits under the editor's. */}
          {layout ? <h1 className="editor-mode-title">{name}</h1> : <h2 className="editor-mode-title">{name}</h2>}
          <StatusPill tone={layout ? "changeSet" : "publication"}>{layout ? "Layout editor" : "Preview"}</StatusPill>
        </div>
        {choices}
        <span className="band-note">{note}</span>
      </div>
      <div className="band-actions">{actions}</div>
    </div>
  );
}

/** A frame in Edit layout: a grip to drag with mouse or pen, its title, and its menu. */
function LayoutFrame({
  kind,
  title,
  note,
  hidden,
  menu,
  dragged,
  onDragStart,
  onDrop,
  children,
  className = "",
}: {
  /** What the frame holds, in its name: a panel, a field or a column. */
  kind: "Panel" | "Field" | "Column";
  title: string;
  note?: string;
  hidden?: boolean;
  menu: readonly ActionMenuItem[];
  dragged: Dragged;
  onDragStart: (item: Dragged) => void;
  onDrop: (event: DragEvent) => void;
  children?: ReactNode;
  className?: string;
}) {
  const [over, setOver] = useState(false);
  return (
    <section
      className={`layout-frame ${className}${hidden ? " layout-hidden" : ""}${over ? " drop-target" : ""}`}
      aria-label={`${kind} ${title}`}
      onDragOver={(event) => {
        event.preventDefault();
        event.stopPropagation();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        event.stopPropagation();
        setOver(false);
        onDrop(event);
      }}
    >
      <div className="layout-frame-head">
        <span
          className="layout-grip"
          draggable
          aria-hidden="true"
          title="Drag to move; the menu moves it by keyboard"
          onDragStart={(event) => {
            event.dataTransfer.effectAllowed = "move";
            event.dataTransfer.setData("text/plain", title);
            onDragStart(dragged);
          }}
        >
          <Icon name="grip" />
        </span>
        <span className="layout-frame-title">{title}</span>
        {note && <span className="muted layout-frame-note">{note}</span>}
        <ActionMenu label={`Layout of ${kind.toLowerCase()} ${title}`} tooltip="Layout" items={menu} />
      </div>
      {children}
    </section>
  );
}

/** The record page in Edit layout: its panels by region, each in a frame, fields framed too. */
function LayoutCanvas({
  model,
  application,
  detail,
  place,
  client,
  objectId,
  workspaceKey,
  send,
  onDialog,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  detail: DetailViewDefinition;
  place: LayoutPlace;
  client: typeof api;
  objectId: string;
  workspaceKey: string;
  send: SendLayout;
  onDialog: (operation: OperationSpec) => void;
}) {
  const [object, setObject] = useState<ObjectItem>();
  const [dragged, setDragged] = useState<Dragged>();
  useEffect(() => {
    let cancelled = false;
    client
      .object(place.objectTypeKey, objectId, workspaceKey)
      .then((loaded) => !cancelled && setObject(loaded))
      .catch(() => !cancelled && setObject(undefined));
    return () => {
      cancelled = true;
    };
  }, [client, place.objectTypeKey, objectId, workspaceKey]);

  const step = (operations: DraftOperation[]) => {
    if (operations.length) void send(operations);
  };
  const attributeGroups = detail.panels.filter((panel) => panel.type === "attributes");

  function dropOnPanel(target: PanelDefinition) {
    if (dragged?.kind === "panel" && dragged.key !== target.key)
      step(panelToRegion(place, detail, dragged.key, target.region, target.key));
    if (dragged?.kind === "field" && target.type === "attributes" && dragged.panel !== target.key)
      step(fieldToPanel(place, dragged.panel, target.key, dragged.field));
    setDragged(undefined);
  }
  function dropOnRegion(region: Region) {
    if (dragged?.kind === "panel") step(panelToRegion(place, detail, dragged.key, region));
    setDragged(undefined);
  }
  function dropOnField(panel: PanelDefinition, field: string) {
    if (dragged?.kind !== "field" || panel.type !== "attributes" || dragged.field === field) return;
    if (dragged.panel === panel.key) {
      const without = panel.config.fields.filter((item) => item !== dragged.field);
      step([
        {
          kind: "moveViewItem",
          applicationKey: place.applicationKey,
          detail: place.objectTypeKey,
          panel: panel.key,
          list: "fields",
          item: dragged.field,
          position: without.indexOf(field),
        },
      ]);
    } else step(fieldToPanel(place, dragged.panel, panel.key, dragged.field, panel.config.fields.indexOf(field)));
    setDragged(undefined);
  }

  function panelMenu(panel: PanelDefinition, region: Region, index: number, count: number): ActionMenuItem[] {
    const other: Region = region === "main" ? "side" : "main";
    const columns = panelColumns(panel);
    const sort = panelSortSpec(model, place, panel);
    return [
      {
        id: "up",
        label: "Move up",
        icon: "arrow-left",
        section: "Move",
        disabled: index === 0,
        onAction: () => step(movePanel(place, detail, panel.key, -1)),
      },
      {
        id: "down",
        label: "Move down",
        icon: "arrow-right",
        section: "Move",
        disabled: index === count - 1,
        onAction: () => step(movePanel(place, detail, panel.key, 1)),
      },
      {
        id: "region",
        label: `Move to ${other}`,
        icon: "swap",
        section: "Move",
        onAction: () => step(panelToRegion(place, detail, panel.key, other)),
      },
      {
        id: "visible",
        label: panel.visible ? "Hide" : "Show",
        icon: "toggle",
        section: "Change",
        description: panel.visible ? "It stays on the page, hidden" : undefined,
        onAction: () => step(setPanelVisible(place, panel.key, !panel.visible)),
      },
      {
        id: "rename",
        label: "Rename…",
        icon: "pencil",
        section: "Change",
        onAction: () => onDialog(renamePanelSpec(place, panel)),
      },
      ...(columns
        ? [
            {
              id: "columns",
              label: "Columns…",
              icon: "table" as const,
              section: "Change",
              onAction: () => onDialog(panelColumnsSpec(model, place, panel)),
            },
          ]
        : []),
      ...(sort
        ? [{ id: "sort", label: "Sort…", icon: "sort" as const, section: "Change", onAction: () => onDialog(sort) }]
        : []),
      ...(panel.type === "attributes"
        ? [
            {
              id: "add",
              label: "Add fields…",
              icon: "plus" as const,
              section: "Change",
              onAction: () => onDialog(addFieldSpec(model, place, panel, detail)),
            },
          ]
        : []),
      {
        id: "remove",
        label: "Remove from page",
        icon: "trash",
        section: "Remove",
        tone: "danger",
        description: "Undo puts it back",
        onAction: () => step(removePanel(place, panel.key)),
      },
    ];
  }

  function fieldMenu(panel: PanelDefinition, field: string, index: number, count: number): ActionMenuItem[] {
    return [
      {
        id: "up",
        label: "Move up",
        icon: "arrow-left",
        section: "Move",
        disabled: index === 0,
        onAction: () => step(moveField(place, panel, field, -1)),
      },
      {
        id: "down",
        label: "Move down",
        icon: "arrow-right",
        section: "Move",
        disabled: index === count - 1,
        onAction: () => step(moveField(place, panel, field, 1)),
      },
      ...attributeGroups
        .filter((group) => group.key !== panel.key)
        .map((group) => ({
          id: `to-${group.key}`,
          label: `Move to ${group.title}`,
          icon: "swap" as const,
          section: "Move",
          onAction: () => step(fieldToPanel(place, panel.key, group.key, field)),
        })),
      {
        id: "remove",
        label: "Remove from panel",
        icon: "trash",
        section: "Remove",
        tone: "danger",
        onAction: () => step(removeField(place, panel.key, field)),
      },
    ];
  }

  function content(panel: PanelDefinition) {
    if (panel.type === "attributes")
      return (
        <div className="layout-fields">
          {panel.config.fields.length === 0 && (
            <p className="muted layout-empty">No fields yet. Drag one here or use Add fields….</p>
          )}
          {panel.config.fields.map((field, index) => {
            const value = object ? fieldValue(object, field, model) : undefined;
            const label = attributeName(model, field);
            return (
              <LayoutFrame
                key={field}
                kind="Field"
                className="layout-field"
                title={label}
                menu={fieldMenu(panel, field, index, panel.config.fields.length)}
                dragged={{ kind: "field", panel: panel.key, field }}
                onDragStart={setDragged}
                onDrop={() => dropOnField(panel, field)}
              >
                <span
                  className={
                    value === undefined || value === null || value === "" ? "muted layout-value" : "layout-value"
                  }
                >
                  {value === undefined || value === null || value === "" ? "No value" : String(value)}
                </span>
              </LayoutFrame>
            );
          })}
        </div>
      );
    if (!object) return null;
    const Component = panelComponentRegistry[panel.type] as React.ComponentType<PanelProps>;
    return (
      <PreviewDataProvider client={client}>
        <Component
          model={model}
          application={application}
          object={object}
          panel={panel}
          onOpen={noop}
          onChanged={noop}
          onObjectChanged={noop}
          onReload={reload}
          readOnly
        />
      </PreviewDataProvider>
    );
  }

  return (
    <div className="layout-canvas">
      <header className="layout-record-head">
        <span className="muted">{application.name}</span>
        <strong>
          {object?.name ||
            (objectId === PREVIEW_EMPTY_ID
              ? `New ${model.objectTypes.find((t) => t.key === place.objectTypeKey)?.name ?? ""}`
              : "")}
        </strong>
      </header>
      <div className="layout-regions">
        {REGIONS.map((region) => {
          const panels = regionPanels(detail, region);
          return (
            <div
              key={region}
              className={`layout-region layout-region-${region}`}
              role="group"
              aria-label={region === "main" ? "Main" : "Side"}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                dropOnRegion(region);
              }}
            >
              <span className="layout-region-label">{region === "main" ? "Main" : "Side"}</span>
              {panels.map((panel, index) => (
                <LayoutFrame
                  key={panel.key}
                  kind="Panel"
                  title={panel.title}
                  note={panel.visible ? undefined : "hidden"}
                  hidden={!panel.visible}
                  menu={panelMenu(panel, region, index, panels.length)}
                  dragged={{ kind: "panel", key: panel.key }}
                  onDragStart={setDragged}
                  onDrop={() => dropOnPanel(panel)}
                >
                  <div className="layout-frame-body">{content(panel)}</div>
                </LayoutFrame>
              ))}
              {region === "main" && (
                <div className="layout-add-row">
                  <button
                    type="button"
                    className="secondary layout-add"
                    onClick={() => onDialog(addPanelSpec(model, place, detail))}
                  >
                    <Icon name="plus" /> Add panel…
                  </button>
                  <button
                    type="button"
                    className="secondary layout-add"
                    onClick={() => onDialog(newFieldGroupSpec(model, place, detail))}
                  >
                    <Icon name="plus" /> New field group
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** The type's table views, one at a time, with the first page of real rows; in Edit layout its columns. */
function TablePreview({
  model,
  application,
  views,
  place,
  client,
  live,
  workspaceKey,
  editing,
  version,
  send,
  onDialog,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  views: TableViewDefinition[];
  place: LayoutPlace;
  client: typeof api;
  live: boolean;
  workspaceKey: string;
  editing: boolean;
  version: number;
  send: SendLayout;
  onDialog: (operation: OperationSpec) => void;
}) {
  const [viewKey, setViewKey] = useState(views[0].key);
  const view = views.find((item) => item.key === viewKey) ?? views[0];
  const [chosen, setChosen] = useState<CollectionQueryState>(() => ({
    search: "",
    sort: view.config.defaultSort,
    pageSize: 10,
    filters: [],
  }));
  // The reader's sort holds while the view's default sort is the one it was chosen under; a new
  // default sort, set in the layout editor, is the preview's sort again.
  const [sortUnder, setSortUnder] = useState(view.config.defaultSort);
  const query = sortUnder === view.config.defaultSort ? chosen : { ...chosen, sort: view.config.defaultSort };
  const setQuery = (next: CollectionQueryState) => {
    setChosen(next);
    setSortUnder(view.config.defaultSort);
  };
  const [dragged, setDragged] = useState<string>();
  const step = (operations: DraftOperation[]) => {
    if (operations.length) void send(operations);
  };
  const columns = view.config.columns;

  return (
    <div className="table-preview">
      <div className="table-preview-tools">
        {views.length > 1 && (
          <label className="toolbar-field">
            View
            <select value={view.key} onChange={(event) => setViewKey(event.target.value)}>
              {views.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
        )}
        {editing ? (
          <>
            <button type="button" className="secondary" onClick={() => onDialog(tableColumnsSpec(model, place, view))}>
              Columns…
            </button>
            <button type="button" className="secondary" onClick={() => onDialog(tableFiltersSpec(model, place, view))}>
              Filters…
            </button>
            <button type="button" className="secondary" onClick={() => onDialog(tableSortSpec(model, place, view))}>
              Default sort: {attributeName(model, view.config.defaultSort.replace(/^-/, ""))}
              {view.config.defaultSort.startsWith("-") ? " ↓" : " ↑"}
            </button>
          </>
        ) : (
          <span className="muted">
            {view.name}: sorted by {attributeName(model, view.config.defaultSort.replace(/^-/, ""))}
          </span>
        )}
      </div>
      {editing && (
        <ol className="layout-columns" aria-label={`Columns of ${view.name}`}>
          {columns.map((column, index) => (
            <li key={column}>
              <LayoutFrame
                kind="Column"
                className="layout-column"
                title={attributeName(model, column)}
                menu={[
                  {
                    id: "left",
                    label: "Move left",
                    icon: "arrow-left",
                    disabled: index === 0,
                    onAction: () => step(moveColumn(place, view, column, -1)),
                  },
                  {
                    id: "right",
                    label: "Move right",
                    icon: "arrow-right",
                    disabled: index === columns.length - 1,
                    onAction: () => step(moveColumn(place, view, column, 1)),
                  },
                  {
                    id: "remove",
                    label: "Remove column",
                    icon: "trash",
                    tone: "danger",
                    onAction: () => step(removeColumn(place, view, column)),
                  },
                ]}
                dragged={{ kind: "column", column }}
                onDragStart={() => setDragged(column)}
                // A column dropped on another takes its place: before it from the right, after it from the left.
                onDrop={() => {
                  if (dragged && dragged !== column)
                    step([
                      {
                        kind: "moveViewItem",
                        applicationKey: place.applicationKey,
                        view: view.key,
                        list: "columns",
                        item: dragged,
                        position: columns.indexOf(column),
                      },
                    ]);
                  setDragged(undefined);
                }}
              />
            </li>
          ))}
        </ol>
      )}
      {live ? (
        <PreviewControls when={!editing}>
          <PreviewDataProvider client={client}>
            <ObjectCollectionView
              key={`${view.key}:${version}`}
              model={model}
              application={application}
              view={view}
              workspaceKey={workspaceKey}
              query={query}
              onQueryChange={setQuery}
              onOpen={noop}
              readOnly={editing}
            />
          </PreviewDataProvider>
        </PreviewControls>
      ) : (
        <EmptyState>
          No records yet. The table will show {columns.map((column) => attributeName(model, column)).join(", ")}.
        </EmptyState>
      )}
    </div>
  );
}
