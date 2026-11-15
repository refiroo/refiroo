/**
 * The canvas's right pane (0.17 CE1): Inspector, Navigation, Views and Consumer APIs. Every panel in it is the
 * model editor's own, mounted over the same draft: the element panel for a list, a relationship or its type, an
 * application or a navigation group; the column panel for a workbook column; the list panel, with what a load does
 * with the records no row names, for a sheet's list; the consumer API pane and panel. A field gets a short panel of
 * rows, each sending the editor's operation for it, above the panel of its attribute type. Nothing here builds a
 * model operation: it asks the operation table (`operationsFor`, `operationById`) and sends through the editing hook.
 */

import { useState } from "react";
import { ColumnPanel } from "@/features/model-editor/ColumnPanel";
import { ConsumerApiPane, ConsumerApiPanel } from "@/features/model-editor/ConsumerApis";
import { ElementPanel } from "@/features/model-editor/ElementPanel";
import { ListPanel } from "@/features/model-editor/ListPanel";
import { dropOperations, listHeader, listStatus, sourceOfList } from "@/features/model-editor/lists";
import { OperationsMenu } from "@/features/model-editor/OperationsMenu";
import { operationById, operationsFor, valueTypeLabel, type OperationTarget } from "@/features/model-editor/operations";
import { applicationsOf, objectTypeOf, typeName } from "@/model/outline";
import type { DraftEditing } from "@/features/model-editor/useDraftEditing";
import type { DraftSource } from "@/features/model-editor/useDraftSource";
import type { SourceDialogs } from "@/features/model-editor/useSourceDialogs";
import type { CanvasSelection, ConsumerApiTab, EditorSelection, ModelDraftOutline } from "@/types";
import { EditInPlaceValue } from "@/ui/EditInPlace";
import { Switch } from "@/ui/Switch";
import { Tabs } from "@/ui/Tabs";
import { TextInPlace } from "@/ui/TextInPlace";
import type { CanvasCard, CanvasField, CanvasLine } from "./canvasModel";
import { editorSelectionOf, renameFieldOperations, targetOfSelection, type CanvasPick } from "./canvasView";

export type InspectorTab = "inspector" | "navigation" | "views" | "consumer";

/** What a field is, as rows: each one the editor's operation for the field, started where it stands. */
function FieldPanel({
  card,
  field,
  target,
  editing,
  outline,
}: {
  card: CanvasCard;
  field: CanvasField;
  target: OperationTarget;
  editing: DraftEditing;
  outline: ModelDraftOutline;
}) {
  const offered = new Set(operationsFor(target, outline).map((item) => item.id));
  const attribute =
    target.on === "attribute"
      ? outline.objectTypes
          .find((item) => item.key === target.objectType)
          ?.attributes.find((item) => item.attributeType === target.attributeType)
      : undefined;
  const operate = (id: string) => {
    const operation = operationById(id);
    if (operation) editing.operate(operation, target);
  };
  const renamable = renameFieldOperations(card, field, field.label, outline).length > 0;
  const flips: [string, string, boolean][] = attribute
    ? [
        ["attribute-required", "Required", attribute.required],
        ["attribute-unique", "Unique", attribute.unique],
        ["attribute-read-only", "Read-only", attribute.readOnly],
      ]
    : [];
  const moves = ["attribute-list", "attribute-move", "attribute-detach"].filter((id) => offered.has(id));
  return (
    <section className="canvas-inspect" aria-label={`Attribute ${field.label}`}>
      <h2>{field.label}</h2>
      <p className="canvas-inspect-sub">{`Attribute of ${card.name}${field.typeLabel ? ` · ${field.typeLabel}` : ""}`}</p>
      {renamable && (
        <div className="canvas-inspect-row">
          <span>Name</span>
          <TextInPlace
            value={field.label}
            label="Name"
            savedText="Renamed."
            onSave={async (name) => {
              const { outcome, step } = await editing.runAnswered(renameFieldOperations(card, field, name, outline));
              // Held back because the draft moved on: the editing hook says so, and nothing was renamed.
              if (outcome === "stale") return false as const;
              return () => editing.undo(step === undefined ? undefined : [step]);
            }}
          />
        </div>
      )}
      {attribute && (
        <div className="canvas-inspect-row">
          <span>Value type</span>
          {offered.has("attribute-value-type") ? (
            <EditInPlaceValue layout="row" name="Value type" onEdit={() => operate("attribute-value-type")}>
              <span className="attribute-value">{valueTypeLabel(attribute.valueType)}</span>
            </EditInPlaceValue>
          ) : (
            <span>{valueTypeLabel(attribute.valueType)}</span>
          )}
        </div>
      )}
      {flips
        .filter(([id]) => offered.has(id))
        .map(([id, label, on]) => (
          <div key={id} className="canvas-inspect-row">
            <span>{label}</span>
            <Switch variant="canvas" label={label} checked={on} onChange={() => operate(id)} />
          </div>
        ))}
      <div className="canvas-inspect-row">
        <span>Filled by</span>
        <span className="canvas-inspect-mono">
          {field.columns.length
            ? [...new Set(field.columns.map((column) => `${column.sheet} · ${column.header}`))].join(", ")
            : "No column yet"}
        </span>
      </div>
      {moves.length > 0 && (
        <div className="canvas-inspect-actions">
          {moves.map((id) => (
            <button key={id} type="button" className="secondary" onClick={() => operate(id)}>
              {operationById(id)?.label(target as never, outline)}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

export interface InspectorProps {
  editing: DraftEditing;
  outline: ModelDraftOutline;
  selection: CanvasSelection;
  cards: readonly CanvasCard[];
  lines: readonly CanvasLine[];
  source: DraftSource;
  sourceDialogs: SourceDialogs;
  busy: boolean;
  proposedElements: ReadonlySet<string>;
  phone: boolean;
  tab: InspectorTab;
  onTab: (tab: InspectorTab) => void;
  onPick: (pick: CanvasPick | undefined) => void;
  /** Opens the list's tables and record page in the main area, as a preview or as the layout editor; absent without a running model to read records through. */
  onPreview?: (typeKey: string, mode: "preview" | "layout") => void;
  /** The consumer API open in the Consumer APIs tab. */
  consumer: EditorSelection;
  onConsumer: (selection: EditorSelection) => void;
  /** A panel the board has no card for, shown instead of the selection's own (the page clears it on a pick). */
  panel?: EditorSelection;
  onPanel: (panel: EditorSelection | undefined) => void;
}

/** What the Inspector tab shows for the selection. */
function InspectorBody({
  editing,
  outline,
  selection,
  cards,
  lines,
  source,
  sourceDialogs,
  busy,
  proposedElements,
  phone,
  onPick,
  onPreview,
  onViews,
  panel: shown,
  onPanel: setShown,
}: InspectorProps & { onViews: () => void }) {
  const [elementTab, setElementTab] = useState("attributes");
  const profile = source.profile?.profile;
  const own = editorSelectionOf(selection, cards, lines, outline);
  const active = shown ?? own;
  const select = (next: EditorSelection) => {
    if (next.show === "type") onPick({ element: "type", key: next.key });
    else if (next.show === "application") onPick({ element: "application", key: next.key });
    else if (next.show === "group") onPick({ element: "group", application: next.application, key: next.key });
    else setShown(next);
  };
  const panelProps = {
    outline,
    tab: elementTab,
    onTab: setElementTab,
    menuOpen: editing.menuOpen,
    onMenuOpenChange: editing.setMenuOpen,
    canDrag: !phone,
    onOperation: editing.operate,
    onSelect: select,
    run: editing.run,
  } as const;

  if (selection.element === "column" && selection.sheet && selection.key)
    return (
      <ColumnPanel
        key={`${selection.sheet}:${selection.key}`}
        sheet={selection.sheet}
        header={selection.key}
        source={source}
        outline={outline}
        busy={busy}
        run={(operations) => void editing.runGuarded(operations)}
        onMap={() => sourceDialogs.openMap(selection.sheet!, selection.key!)}
        onValueMap={(use) => sourceDialogs.openValueMap(use, selection.key!)}
        onRows={sourceDialogs.openRows}
      />
    );
  if (selection.element === "list" && selection.sheet !== undefined && selection.block !== undefined) {
    const sheet = source.sheets.find((item) => item.name === selection.sheet);
    const block = sheet?.blocks.find((item) => item.index === selection.block);
    if (!sheet || !block) return <p className="canvas-hint">Reading the list…</p>;
    const loads = sourceOfList(profile, sheet.name, block);
    return (
      <ListPanel
        key={`${sheet.name}:${block.index}`}
        sheet={sheet.name}
        block={block}
        header={listHeader(block, source.columns(sheet.name))}
        fileId={source.profile?.sourceFile?.id}
        listSource={loads}
        status={listStatus(loads, proposedElements)}
        outline={outline}
        busy={busy}
        onAdjust={() => sourceDialogs.openList("adjust", sheet.name, block.index)}
        onLoad={() => sourceDialogs.openList("load", sheet.name, block.index)}
        onSetMissing={(operations) => void editing.runGuarded(operations)}
        readings={{
          profile,
          columns: source.columns(sheet.name),
          run: (operations) => void editing.runGuarded(operations),
        }}
        onDrop={() => {
          if (loads) void editing.runGuarded(dropOperations(outline, profile, loads));
        }}
        onShowType={(key) => onPick({ element: "type", key })}
      />
    );
  }
  if (selection.element === "field" && !shown) {
    const card = cards.find((item) => item.typeKey === selection.key);
    const field = card?.fields.find((item) => item.id === selection.field);
    const target = targetOfSelection(selection, cards, lines, outline);
    if (card && field && target && field.kind !== "name")
      return (
        <>
          <FieldPanel card={card} field={field} target={target} editing={editing} outline={outline} />
          <ElementPanel {...panelProps} selection={own} onPreview={onViews} />
        </>
      );
  }
  if (active.show === undefined)
    return (
      <p className="canvas-hint">
        Select an object type, an attribute, a line or an application to see it here. Everything the model editor can do
        to it is in its ⋯ menu and in this panel.
      </p>
    );
  return (
    <ElementPanel
      key={JSON.stringify(active)}
      {...panelProps}
      selection={active}
      onPreview={() => (active.show === "type" && onPreview ? onPreview(active.key, "preview") : onViews())}
    />
  );
}

/** Navigation: the groups of every application, each with its entries, with the editor's group operations. */
function NavigationTab({
  outline,
  editing,
  onPick,
  selection,
}: {
  outline: ModelDraftOutline;
  editing: DraftEditing;
  onPick: (pick: CanvasPick | undefined) => void;
  selection: CanvasSelection;
}) {
  return (
    <div className="canvas-navigation-tab">
      <p className="canvas-hint">Drag an object type's Connect onto a group to place it there, or use its ⋯ menu.</p>
      {outline.applications.map((application) => (
        <section key={application.key} className="canvas-application" aria-label={`Navigation of ${application.name}`}>
          <h3>
            <span>{application.name}</span>
            <OperationsMenu
              tooltip=""
              label={`Navigation operations for ${application.name}`}
              target={{ on: "application", applicationKey: application.key }}
              outline={outline}
              onOperation={editing.operate}
            />
          </h3>
          {application.navigation.groups.map((group) => (
            <div
              key={group.key}
              className={`canvas-group${selection.element === "group" && selection.key === group.key && selection.application === application.key ? " selected" : ""}`}
              data-canvas-group={group.key}
              data-application={application.key}
            >
              <span className="canvas-group-head">
                <button
                  type="button"
                  className="canvas-group-label"
                  onClick={() => onPick({ element: "group", application: application.key, key: group.key })}
                >
                  {group.label}
                </button>
                <OperationsMenu
                  tooltip=""
                  label={`Operations for the group ${group.label}`}
                  target={{ on: "group", applicationKey: application.key, group: group.key }}
                  outline={outline}
                  onOperation={editing.operate}
                />
              </span>
              <ul>
                {group.entries.map((entry) => {
                  const key = entry.collection ?? entry.view ?? "";
                  const name = entry.collection
                    ? (objectTypeOf(outline, entry.collection)?.pluralName ?? key)
                    : (application.views.find((view) => view.key === entry.view)?.name ?? key);
                  return (
                    <li key={`${entry.collection ? "c" : "v"}:${key}`}>
                      <span>{name}</span>
                      <OperationsMenu
                        tooltip=""
                        label={`Operations for the entry ${name}`}
                        target={{
                          on: "groupEntry",
                          applicationKey: application.key,
                          group: group.key,
                          ...(entry.collection ? { collection: entry.collection } : { view: entry.view }),
                        }}
                        outline={outline}
                        onOperation={editing.operate}
                      />
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
          <div className="canvas-group canvas-group-loose" data-canvas-group="" data-application={application.key}>
            <span className="canvas-group-label">Not in a group</span>
            <ul>
              {application.navigation.ungrouped.map((key) => (
                <li key={key}>
                  <span>{objectTypeOf(outline, key)?.pluralName ?? key}</span>
                </li>
              ))}
            </ul>
          </div>
          <div
            className="canvas-group canvas-group-new"
            data-canvas-group=""
            data-fresh="true"
            data-application={application.key}
          >
            New group
          </div>
        </section>
      ))}
    </div>
  );
}

/** Views: the selected list's views and its record page, opened in the editor's own preview and layout editing. */
function ViewsTab({
  outline,
  editing,
  selection,
  cards,
  onPreview,
}: {
  outline: ModelDraftOutline;
  editing: DraftEditing;
  selection: CanvasSelection;
  cards: readonly CanvasCard[];
  onPreview?: (typeKey: string, mode: "preview" | "layout") => void;
}) {
  const typeKey = selection.element === "type" || selection.element === "field" ? selection.key : undefined;
  const card = cards.find((item) => item.typeKey === typeKey);
  if (!typeKey || !card)
    return <p className="canvas-hint">Select an object type to see its views and its record page.</p>;
  const applications = applicationsOf(outline, typeKey);
  return (
    <section className="canvas-views" aria-label={`Views of ${card.name}`}>
      <h2>{card.name}</h2>
      {onPreview && (
        <div className="canvas-inspect-actions">
          <button type="button" className="primary" onClick={() => onPreview(typeKey, "preview")}>
            Preview tables and record page
          </button>
          <button type="button" className="secondary" onClick={() => onPreview(typeKey, "layout")}>
            Edit layout
          </button>
        </div>
      )}
      {applications.map((application) => {
        const views = application.views.filter((view) => view.collection === typeKey || view.shows.includes(typeKey));
        return (
          <div key={application.key} className="canvas-views-application">
            <h3>
              <span>{application.name}</span>
              <OperationsMenu
                tooltip=""
                label={`View operations for ${application.name}`}
                target={{ on: "application", applicationKey: application.key }}
                outline={outline}
                onOperation={editing.operate}
              />
            </h3>
            <ul>
              {views.length === 0 && <li className="canvas-hint">No view of {card.name} here yet.</li>}
              {views.map((view) => (
                <li key={view.key}>
                  <span>
                    {view.name} <small>{view.type ?? "view"}</small>
                  </span>
                  <OperationsMenu
                    tooltip=""
                    label={`Operations for the view ${view.name}`}
                    target={{ on: "view", applicationKey: application.key, view: view.key }}
                    outline={outline}
                    onOperation={editing.operate}
                  />
                </li>
              ))}
            </ul>
          </div>
        );
      })}
      <p className="canvas-hint">
        Tables and the record page of {typeName(outline, typeKey)} open in the main area, laid out as in the model
        editor.
      </p>
    </section>
  );
}

/** Consumer APIs: the editor's own pane and panel, with its ＋. */
function ConsumerTab({
  outline,
  editing,
  consumer,
  onConsumer,
}: {
  outline: ModelDraftOutline;
  editing: DraftEditing;
  consumer: EditorSelection;
  onConsumer: (selection: EditorSelection) => void;
}) {
  const open = (next: EditorSelection) => onConsumer(next);
  const onMenu = (next: EditorSelection) => {
    open(next);
    editing.setMenuOpen(true);
  };
  const selected =
    consumer.show === "consumerApi"
      ? (consumer as { show: "consumerApi"; key: string; tab?: ConsumerApiTab })
      : undefined;
  return (
    <div className="canvas-consumer-tab">
      <div className="canvas-consumer-add">
        <OperationsMenu
          label="Add a consumer API"
          icon="plus"
          tooltip="Add"
          target={{ on: "consumerApis" }}
          outline={outline}
          onOperation={editing.operate}
        />
      </div>
      <ConsumerApiPane outline={outline} selection={consumer} onSelect={open} onMenu={onMenu} />
      {selected && (
        <ConsumerApiPanel
          key={selected.key}
          draftId={editing.draftId}
          outline={outline}
          selection={selected}
          onSelect={open}
          menuOpen={editing.menuOpen}
          onMenuOpenChange={editing.setMenuOpen}
          onOperation={editing.operate}
          run={editing.run}
        />
      )}
    </div>
  );
}

export function CanvasInspector(props: InspectorProps) {
  const { tab, onTab, outline, editing, selection, cards, onPreview, consumer, onConsumer } = props;
  return (
    <aside className="canvas-pane canvas-inspector" aria-label="Inspector">
      <Tabs
        label="Inspector"
        selected={tab}
        onChange={(id) => onTab(id as InspectorTab)}
        tabs={[
          {
            id: "inspector",
            label: "Inspector",
            content: <InspectorBody {...props} onViews={() => onTab("views")} />,
          },
          {
            id: "navigation",
            label: "Navigation",
            content: <NavigationTab outline={outline} editing={editing} onPick={props.onPick} selection={selection} />,
          },
          {
            id: "views",
            label: "Views",
            content: (
              <ViewsTab outline={outline} editing={editing} selection={selection} cards={cards} onPreview={onPreview} />
            ),
          },
          {
            id: "consumer",
            label: "Consumer APIs",
            content: <ConsumerTab outline={outline} editing={editing} consumer={consumer} onConsumer={onConsumer} />,
          },
        ]}
      />
    </aside>
  );
}
