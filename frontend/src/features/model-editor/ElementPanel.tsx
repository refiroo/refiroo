/**
 * The editor's centre (0.10 A4a): the selected element with its operations. A type shows its key,
 * where it stands, its attributes and its relations; an application its types and navigation
 * groups; a relation type or an attribute type where it is used. Every operation is the descriptor
 * table's (D38), offered by the element's menu and by the menus of its rows.
 */

import type { ReactNode } from "react";
import type {
  EditorSelection,
  ModelDraftOutline,
  OutlineApplication,
  OutlineMark,
  OutlineNavigationGroup,
  OutlineRelation,
} from "@/types";
import { HueTile } from "@/ui/HueTile";
import { Icon } from "@/ui/Icon";
import { Tabs } from "@/ui/Tabs";
import { MarkPill } from "@/features/model-editor/MarkPill";
import { ProposedPill } from "@/features/model-editor/ProposedBecause";
import { GroupFoldCell } from "@/features/model-editor/GroupFoldCell";
import { TypePlacement } from "@/features/model-editor/TypePlacement";
import { EditorTable, type EditorColumn } from "@/features/model-editor/EditorTable";
import { YES_NO } from "@/features/model-editor/EditableCell";
import { describeCandidates } from "@/features/model-editor/candidates";
import { EditInPlaceValue } from "@/ui/EditInPlace";
import { EditableText } from "@/features/model-editor/EditableText";
import type { RunStep, StepOutcome } from "@/features/model-editor/OperationDialog";
import { Facts, type Fact } from "@/features/model-editor/Facts";
import { EmptyState } from "@/ui/EmptyState";
import { OperationsMenu, type OnOperation } from "@/features/model-editor/OperationsMenu";
import { SettingsTable } from "@/features/model-editor/SettingsTable";
import {
  applicationSettings,
  attributeTypeSettings,
  relationTypeSettings,
  typeSettings,
} from "@/features/model-editor/elementSettings";
export type { OnOperation };
import { DRAG_ATTRIBUTE } from "@/features/model-editor/ModelPane";
import {
  CARDINALITIES,
  cardinalityLabel,
  operationById,
  operationsFor,
  VALUE_TYPES,
  valueTypeLabel,
  type FieldValues,
  type OperationTarget,
} from "@/features/model-editor/operations";
import {
  applicationOf,
  attributeTypeOf,
  collectionViews,
  draftTypeHue,
  entryName,
  entryRefId,
  groupEntries,
  isReleased,
  kindChip,
  linkWords,
  objectTypeOf,
  openingView,
  placeOf,
  relationTypeOf,
  relationsOf,
  typeName,
  VIEW_KINDS,
  type NavigationEntryRef,
} from "@/features/model-editor/outline";

export function Header({
  tile,
  title,
  mark,
  proposed,
  facts,
  rename,
  outline,
  children,
}: {
  tile?: ReactNode;
  title: string;
  mark?: OutlineMark;
  /** Still as the inference proposed it (0.10 A6b): marked Proposed in place of its mark. */
  proposed?: boolean;
  facts: ReactNode;
  /** The name is edited in place as a record's title is; saving is one `setLabel` step. */
  rename: (name: string) => Promise<StepOutcome>;
  outline: ModelDraftOutline;
  children?: ReactNode;
}) {
  return (
    <header className="element-header">
      {tile}
      <div className="element-title">
        <EditableText
          heading
          value={title}
          outline={outline}
          onSave={rename}
          after={proposed ? <ProposedPill /> : mark && <MarkPill mark={mark} />}
        />
        {facts}
      </div>
      <div className="element-actions">{children}</div>
    </header>
  );
}

export function OperationButton({
  id,
  target,
  outline,
  onOperation,
  preset,
  primary = false,
  children,
}: {
  id: string;
  target: OperationTarget;
  outline: ModelDraftOutline;
  onOperation: OnOperation;
  /** Values the dialog opens with. */
  preset?: FieldValues;
  primary?: boolean;
  children: ReactNode;
}) {
  const item = operationById(id);
  if (!item || !operationsFor(target, outline).includes(item)) return null;
  return (
    <button
      type="button"
      className={primary ? "primary" : "secondary"}
      onClick={() => onOperation(item, target, preset)}
    >
      {children}
    </button>
  );
}

/** An element's key, and whether it can still change (A-D6): a released key changes with a migration, labels always free. */
const keyFacts = (key: string, mark: OutlineMark | undefined, extra: Fact[] = []) => (
  <Facts
    label="About this element"
    facts={[
      { icon: "type", label: <code>{key}</code>, title: "Key" },
      isReleased(mark)
        ? {
            icon: "lock",
            label: "Released: a key change needs a migration",
            title:
              "Released, so changing the key needs a migration and integrations naming it must change; labels change freely",
          }
        : { icon: "pencil", label: "Key editable until released" },
      ...extra,
    ]}
  />
);

export function ElementPanel({
  outline,
  selection,
  tab,
  onTab,
  menuOpen,
  onMenuOpenChange,
  canDrag,
  onOperation,
  onSelect,
  run,
  onPreview,
  proposed,
}: {
  outline: ModelDraftOutline;
  selection: EditorSelection;
  /** Why the selected element is as it is, while it is still as proposed (0.10 A6b, D94). */
  proposed?: ReactNode;
  tab: string;
  onTab: (tab: string) => void;
  /** The element's operations menu, opened from the model pane by Shift+F10. */
  menuOpen: boolean;
  onMenuOpenChange: (open: boolean) => void;
  canDrag: boolean;
  onOperation: OnOperation;
  onSelect: (selection: EditorSelection) => void;
  /** Applies a step at the draft's version (the editor's). */
  run: RunStep;
  /** Opens the selected type's preview in the centre (0.10 A4b). */
  onPreview: () => void;
}) {
  const editing = { outline, run };
  /** A relation's editable rules, the same in a type's Relations and a relation type's pairs. */
  const relationColumns: EditorColumn<OutlineRelation>[] = [
    {
      key: "cardinality",
      label: "Cardinality",
      cell: (relation) => cardinalityLabel(relation.cardinality),
      edit: (relation) => ({
        label: "Cardinality",
        value: relation.cardinality ?? "many-to-many",
        options: CARDINALITIES,
        operations: (cardinality) => [
          {
            kind: "setRelationRule",
            relationType: relation.relationType,
            from: relation.from,
            to: relation.to,
            cardinality,
          },
        ],
      }),
    },
    {
      key: "required",
      label: "Required",
      cell: (relation) => (relation.containment ? "Containment" : relation.required ? "Yes" : "No"),
      edit: (relation) =>
        relation.containment
          ? undefined
          : {
              label: "Required",
              value: String(relation.required),
              options: YES_NO,
              operations: (value) => [
                {
                  kind: "setRelationRule",
                  relationType: relation.relationType,
                  from: relation.from,
                  to: relation.to,
                  required: value === "true",
                },
              ],
            },
    },
    {
      key: "carries",
      label: "Carries",
      cell: (relation) => {
        const target: OperationTarget = {
          on: "relation",
          relationType: relation.relationType,
          from: relation.from,
          to: relation.to,
        };
        const choose = operationById("relation-attributes");
        const summary = relation.attributeTypeKeys?.length
          ? relation.attributeTypeKeys.map((key) => attributeTypeOf(outline, key)?.name ?? key).join(", ")
          : "Nothing";
        return choose && operationsFor(target, outline).includes(choose) ? (
          <EditInPlaceValue
            layout="row"
            name="Attributes of the relationship"
            onEdit={() => onOperation(choose, target)}
          >
            <span className="attribute-value">{summary}</span>
          </EditInPlaceValue>
        ) : (
          summary
        );
      },
    },
    {
      key: "candidates",
      label: "Which records",
      cell: (relation) => {
        const target: OperationTarget = {
          on: "relation",
          relationType: relation.relationType,
          from: relation.from,
          to: relation.to,
        };
        const choose = operationById("relation-candidates");
        const summary =
          describeCandidates(outline, relation.candidates ?? undefined, { from: relation.from, to: relation.to }) ||
          "Any";
        return choose ? (
          <EditInPlaceValue layout="row" name="Which records" onEdit={() => onOperation(choose, target)}>
            <span className="attribute-value">{summary}</span>
          </EditInPlaceValue>
        ) : (
          summary
        );
      },
    },
  ];
  const menu = (label: string, target: OperationTarget) => (
    <OperationsMenu
      label={label}
      target={target}
      outline={outline}
      onOperation={onOperation}
      isOpen={menuOpen}
      onOpenChange={onMenuOpenChange}
    />
  );

  if (selection.show === "type") {
    const type = objectTypeOf(outline, selection.key);
    if (!type) return <Missing what="type" />;
    const target: OperationTarget = { on: "objectType", objectType: type.key };
    const relations = relationsOf(outline, type.key);
    return (
      <section className="element-panel" aria-labelledby="element-title">
        <Header
          tile={<HueTile hue={draftTypeHue(outline, type.key)} icon={type.icon ?? undefined} size={40} />}
          title={type.name}
          outline={outline}
          rename={(name) => run([{ kind: "setLabel", element: { objectType: type.key }, name }])}
          mark={type.mark}
          proposed={Boolean(proposed)}
          facts={keyFacts(type.key, type.mark)}
        >
          <button type="button" className="secondary" onClick={onPreview}>
            <Icon name="monitor" /> Preview
          </button>
          {menu(`Operations for ${type.name}`, target)}
        </Header>
        {proposed}
        <TypePlacement outline={outline} type={type} onSelect={onSelect} />
        <Tabs
          label={`${type.name} structure`}
          selected={tab}
          onChange={onTab}
          tabs={[
            {
              id: "attributes",
              label: `Attributes (${type.attributes.length})`,
              content: (
                <div className="element-tab">
                  <EditorTable
                    editing={editing}
                    scope="attributes"
                    label={`Attributes of ${type.name}`}
                    noun={["attribute", "attributes"]}
                    rows={type.attributes}
                    rowKey={(attribute) => attribute.attributeType}
                    rowAttributes={(attribute) =>
                      canDrag
                        ? {
                            draggable: true,
                            className: "draggable-row",
                            onDragStart: (event) => {
                              event.dataTransfer.setData(DRAG_ATTRIBUTE, `${type.key}\u0000${attribute.attributeType}`);
                              event.dataTransfer.effectAllowed = "move";
                            },
                          }
                        : {}
                    }
                    menu={(attribute) => (
                      <OperationsMenu
                        label={`Operations for ${attribute.name}`}
                        target={{ on: "attribute", objectType: type.key, attributeType: attribute.attributeType }}
                        outline={outline}
                        onOperation={onOperation}
                      />
                    )}
                    emptyMessage={`${type.name} has no attributes yet.`}
                    columns={[
                      {
                        key: "attribute",
                        label: "Attribute",
                        cell: (attribute) => (
                          <>
                            {canDrag && (
                              <span
                                className="drag-grip"
                                title="Drag onto a type in the model pane to move it"
                                aria-hidden="true"
                              >
                                <Icon name="grip" size={14} />
                              </span>
                            )}
                            {attribute.name} <code className="element-key">{attribute.attributeType}</code>
                          </>
                        ),
                      },
                      {
                        key: "valueType",
                        label: "Value type",
                        cell: (attribute) => valueTypeLabel(attribute.valueType),
                        edit: (attribute) => ({
                          label: "Value type",
                          value: attribute.valueType ?? "text",
                          options: VALUE_TYPES,
                          operations: (valueType) => [
                            { kind: "setValueType", attributeType: attribute.attributeType, valueType },
                          ],
                        }),
                      },
                      {
                        key: "required",
                        label: "Required",
                        cell: (attribute) => (attribute.required ? "Yes" : "No"),
                        edit: (attribute) => ({
                          label: "Required",
                          value: String(attribute.required),
                          options: YES_NO,
                          operations: (value) => [
                            {
                              kind: "setAttributeBinding",
                              objectType: type.key,
                              attributeType: attribute.attributeType,
                              required: value === "true",
                            },
                          ],
                        }),
                      },
                      {
                        key: "unique",
                        label: "Unique",
                        cell: (attribute) => (attribute.unique ? "Yes" : "No"),
                        edit: (attribute) => ({
                          label: "Unique",
                          value: String(attribute.unique),
                          options: YES_NO,
                          operations: (value) => [
                            {
                              kind: "setAttributeTypeFeatures",
                              attributeType: attribute.attributeType,
                              features: { unique: value === "true" },
                            },
                          ],
                        }),
                      },
                      {
                        key: "readOnly",
                        label: "Read-only",
                        cell: (attribute) => (attribute.readOnly ? "Yes" : "No"),
                        edit: (attribute) => ({
                          label: "Read-only",
                          value: String(attribute.readOnly),
                          options: YES_NO,
                          operations: (value) => [
                            {
                              kind: "setAttributeBinding",
                              objectType: type.key,
                              attributeType: attribute.attributeType,
                              readOnly: value === "true",
                            },
                          ],
                        }),
                      },
                      {
                        key: "hidden",
                        label: "Hidden",
                        cell: (attribute) => (attribute.hidden ? "Yes" : "No"),
                        edit: (attribute) => ({
                          label: "Hidden on this type",
                          value: String(Boolean(attribute.hidden)),
                          options: YES_NO,
                          operations: (value) => [
                            {
                              kind: "setAttributeBinding",
                              objectType: type.key,
                              attributeType: attribute.attributeType,
                              ui: { hidden: value === "true" ? true : null },
                            },
                          ],
                        }),
                      },
                      {
                        key: "helpText",
                        label: "Help text",
                        cell: (attribute) => attribute.helpText || "None",
                        edit: (attribute) => ({
                          label: "Help text on this type",
                          value: attribute.helpText ?? "",
                          optional: true,
                          operations: (value) => [
                            {
                              kind: "setAttributeBinding",
                              objectType: type.key,
                              attributeType: attribute.attributeType,
                              ui: { helpText: value || null },
                            },
                          ],
                        }),
                      },
                      {
                        key: "sharedWith",
                        label: "Shared with",
                        cell: (attribute) =>
                          attribute.sharedWith.length
                            ? attribute.sharedWith.map((key) => typeName(outline, key)).join(", ")
                            : "—",
                      },
                      { key: "state", label: "State", cell: (attribute) => <MarkPill mark={attribute.mark} /> },
                    ]}
                  />
                  <div className="element-tab-actions">
                    <OperationButton
                      id="type-new-attribute"
                      target={target}
                      outline={outline}
                      onOperation={onOperation}
                    >
                      <Icon name="plus" /> New attribute
                    </OperationButton>
                    <OperationButton id="type-attach" target={target} outline={outline} onOperation={onOperation}>
                      Attach an existing one…
                    </OperationButton>
                  </div>
                </div>
              ),
            },
            {
              id: "relations",
              label: `Relations (${relations.length})`,
              content: (
                <div className="element-tab">
                  <EditorTable
                    editing={editing}
                    scope="relations"
                    label={`Relations of ${type.name}`}
                    noun={["relation", "relations"]}
                    rows={relations}
                    rowKey={(relation) => `${relation.relationType}:${relation.from}:${relation.to}`}
                    menu={(relation) => (
                      <OperationsMenu
                        label={`Operations for ${relationTypeOf(outline, relation.relationType)?.name ?? relation.relationType} from ${typeName(outline, relation.from)}`}
                        target={{
                          on: "relation",
                          relationType: relation.relationType,
                          from: relation.from,
                          to: relation.to,
                        }}
                        outline={outline}
                        onOperation={onOperation}
                      />
                    )}
                    emptyMessage={`${type.name} takes part in no relation yet.`}
                    columns={[
                      {
                        key: "relation",
                        label: "Relation",
                        cell: (relation) => {
                          const relationType = relationTypeOf(outline, relation.relationType);
                          return (
                            <>
                              {relation.from === type.key
                                ? relationType?.name
                                : (relationType?.reverseName ?? relationType?.name)}
                              {relation.containment && <span className="muted"> · containment</span>}
                            </>
                          );
                        },
                      },
                      {
                        key: "fromTo",
                        label: "From → to",
                        cell: (relation) => `${typeName(outline, relation.from)} → ${typeName(outline, relation.to)}`,
                      },
                      ...relationColumns,
                      { key: "state", label: "State", cell: (relation) => <MarkPill mark={relation.mark} /> },
                    ]}
                  />
                  <div className="element-tab-actions">
                    <OperationButton id="type-allow" target={target} outline={outline} onOperation={onOperation}>
                      Allow a relation…
                    </OperationButton>
                    <button type="button" className="secondary" onClick={() => onSelect({ show: "matrix" })}>
                      Open the relationship matrix
                    </button>
                  </div>
                </div>
              ),
            },
            {
              id: "settings",
              label: "Settings",
              content: (
                <div className="element-tab">
                  <SettingsTable
                    scope="type-settings"
                    label={`Settings of ${type.name}`}
                    settings={typeSettings(outline, type)}
                    outline={outline}
                    run={run}
                    onOperation={onOperation}
                  />
                </div>
              ),
            },
          ]}
        />
      </section>
    );
  }

  if (selection.show === "application") {
    const application = applicationOf(outline, selection.key);
    if (!application) return <Missing what="application" />;
    const target: OperationTarget = { on: "application", applicationKey: application.key };
    return (
      <section className="element-panel" aria-labelledby="element-title">
        <Header
          title={application.name}
          outline={outline}
          rename={(name) => run([{ kind: "setLabel", element: { applicationKey: application.key }, name }])}
          mark={application.mark}
          facts={keyFacts(application.key, application.mark, [
            { icon: "type", label: `${application.objectTypeKeys.length} object types` },
            { icon: "list", label: `${application.navigation.groups.length} navigation groups` },
          ])}
        >
          {menu(`Operations for ${application.name}`, target)}
        </Header>
        <h3 className="element-subheading">Settings</h3>
        <SettingsTable
          scope="application-settings"
          label={`Settings of ${application.name}`}
          settings={applicationSettings(application)}
          outline={outline}
          run={run}
          onOperation={onOperation}
        />
        <h3 className="element-subheading">Object types</h3>
        <EditorTable
          editing={editing}
          scope="application-types"
          label={`Object types of ${application.name}`}
          noun={["object type", "object types"]}
          rows={application.ownTypes}
          rowKey={(key) => key}
          menu={(key) => (
            <OperationsMenu
              label={`Operations for ${typeName(outline, key)}`}
              target={{ on: "objectType", objectType: key, applicationKey: application.key }}
              outline={outline}
              onOperation={onOperation}
            />
          )}
          emptyMessage="No object types yet."
          columns={[
            {
              key: "type",
              label: "Type",
              cell: (key) => <TypeLink outline={outline} typeKey={key} onSelect={onSelect} />,
            },
            {
              key: "stands",
              label: "Stands",
              cell: (key) => {
                const type = objectTypeOf(outline, key);
                return type ? placeOf(outline, type) : "—";
              },
            },
            {
              key: "attributes",
              label: "Attributes",
              cell: (key) => objectTypeOf(outline, key)?.attributes.length ?? 0,
            },
            { key: "relations", label: "Relations", cell: (key) => relationsOf(outline, key).length },
            {
              key: "state",
              label: "State",
              cell: (key) => {
                const type = objectTypeOf(outline, key);
                return type && <MarkPill mark={type.mark} />;
              },
            },
          ]}
        />
        {application.borrowed.length > 0 && (
          <>
            <h3 className="element-subheading">
              From other applications <span className="muted">{application.borrowed.length}</span>
            </h3>
            <EditorTable
              editing={editing}
              scope="application-borrowed"
              label={`Types of ${application.name} from other applications`}
              noun={["borrowed type", "borrowed types"]}
              rows={application.borrowed}
              rowKey={(item) => item.objectType}
              menu={(item) => (
                <OperationsMenu
                  label={`Operations for ${typeName(outline, item.objectType)}`}
                  target={{ on: "objectType", objectType: item.objectType, applicationKey: application.key }}
                  outline={outline}
                  onOperation={onOperation}
                />
              )}
              emptyMessage="No types from other applications."
              columns={[
                {
                  key: "type",
                  label: "Type",
                  cell: (item) => (
                    <TypeLink
                      outline={outline}
                      typeKey={item.objectType}
                      application={item.home ?? application.key}
                      dashed
                      onSelect={onSelect}
                    />
                  ),
                },
                {
                  key: "from",
                  label: "From",
                  cell: (item) => (item.home ? (applicationOf(outline, item.home)?.name ?? item.home) : "—"),
                },
                {
                  key: "usedBy",
                  label: "Used by",
                  cell: (item) => (
                    <>
                      {item.uses.map((use) => (
                        <div key={`${use.view}:${use.role}`}>
                          <span className="model-pane-chip">{kindChip(use.viewType)}</span> {use.viewName} · {use.role}
                        </div>
                      ))}
                    </>
                  ),
                },
                {
                  key: "relation",
                  label: "Relation",
                  cell: (item) => (
                    <>
                      {item.uses.map((use) => (
                        <div key={`${use.view}:${use.role}`}>
                          {use.role === "link" ? linkWords(outline, application, use) : (use.relationName ?? "—")}
                        </div>
                      ))}
                    </>
                  ),
                },
                {
                  key: "group",
                  label: "Group",
                  cell: (item) =>
                    application.navigation.groups.find((group) =>
                      group.entries.some((entry) => entry.collection === item.objectType),
                    )?.label ?? "—",
                },
                {
                  key: "state",
                  label: "State",
                  cell: (item) => {
                    const type = objectTypeOf(outline, item.objectType);
                    return type && <MarkPill mark={type.mark} />;
                  },
                },
              ]}
            />
          </>
        )}
        {application.unused.length > 0 && (
          <>
            <h3 className="element-subheading">
              Listed, used by no view here <span className="muted">{application.unused.length}</span>
            </h3>
            <EditorTable
              editing={editing}
              scope="application-unused"
              label={`Types of ${application.name} used by no view`}
              noun={["type", "types"]}
              rows={application.unused}
              rowKey={(key) => key}
              menu={(key) => (
                <OperationsMenu
                  label={`Operations for ${typeName(outline, key)}`}
                  target={{ on: "objectType", objectType: key, applicationKey: application.key }}
                  outline={outline}
                  onOperation={onOperation}
                />
              )}
              emptyMessage="No unused types."
              columns={[
                {
                  key: "type",
                  label: "Type",
                  cell: (key) => <TypeLink outline={outline} typeKey={key} onSelect={onSelect} />,
                },
                {
                  key: "stands",
                  label: "Stands",
                  cell: (key) => {
                    const type = objectTypeOf(outline, key);
                    return type ? placeOf(outline, type) : "—";
                  },
                },
                {
                  key: "state",
                  label: "State",
                  cell: (key) => {
                    const type = objectTypeOf(outline, key);
                    return type && <MarkPill mark={type.mark} />;
                  },
                },
                {
                  key: "unlist",
                  label: "Unlisting",
                  cell: (key) => (application.unlistable.includes(key) ? "Can be unlisted" : ""),
                },
              ]}
            />
          </>
        )}
        <div className="element-tab-actions">
          <OperationButton id="application-add-type" target={target} outline={outline} onOperation={onOperation}>
            <Icon name="plus" /> Object type
          </OperationButton>
          <OperationButton id="application-list-type" target={target} outline={outline} onOperation={onOperation}>
            List an existing type…
          </OperationButton>
        </div>
        <h3 className="element-subheading">Views</h3>
        <EditorTable
          editing={editing}
          scope="application-views"
          label={`Views of ${application.name}`}
          noun={["view", "views"]}
          rows={application.views}
          rowKey={(view) => view.key}
          menu={(view) => (
            <OperationsMenu
              label={`Operations for the view ${view.name}`}
              target={{ on: "view", applicationKey: application.key, view: view.key }}
              outline={outline}
              onOperation={onOperation}
            />
          )}
          emptyMessage="No views yet."
          columns={[
            { key: "view", label: "View", cell: (view) => view.name },
            { key: "kind", label: "Kind", cell: (view) => VIEW_KINDS[view.type ?? ""] ?? view.type },
            {
              key: "shows",
              label: "Shows",
              cell: (view) => (
                <span className="type-links">
                  {view.shows.map((key) => (
                    <TypeLink key={key} outline={outline} typeKey={key} onSelect={onSelect} />
                  ))}
                </span>
              ),
            },
            { key: "state", label: "State", cell: (view) => <MarkPill mark={view.mark} /> },
          ]}
        />
        <div className="element-tab-actions">
          <OperationButton id="application-add-view" target={target} outline={outline} onOperation={onOperation}>
            <Icon name="plus" /> View
          </OperationButton>
        </div>
        <h3 className="element-subheading">Navigation groups</h3>
        <EditorTable
          editing={editing}
          scope="navigation-groups"
          label={`Navigation groups of ${application.name}`}
          noun={["navigation group", "navigation groups"]}
          rows={application.navigation.groups}
          rowKey={(group) => group.key}
          reorder={{
            onMove: (group, position) =>
              run([{ kind: "setNavigationGroup", applicationKey: application.key, group, position }]),
          }}
          menu={(group) => (
            <OperationsMenu
              label={`Operations for the group ${group.label}`}
              target={{ on: "group", applicationKey: application.key, group: group.key }}
              outline={outline}
              onOperation={onOperation}
            />
          )}
          emptyMessage="No navigation groups: every collection stands at the top of the sidebar."
          columns={[
            {
              key: "group",
              label: "Group",
              cell: (group) => (
                <button
                  type="button"
                  className="link-button"
                  onClick={() => onSelect({ show: "group", application: application.key, key: group.key })}
                >
                  {group.label}
                </button>
              ),
              edit: (group) => ({
                label: "Label",
                value: group.label,
                operations: (label) => [
                  { kind: "setNavigationGroup", applicationKey: application.key, group: group.key, label },
                ],
              }),
            },
            {
              key: "entries",
              label: "Entries",
              cell: (group) =>
                group.entries.length ? (
                  <EntryChips outline={outline} application={application} group={group} onSelect={onSelect} />
                ) : (
                  "None yet"
                ),
            },
            {
              key: "starts",
              label: "Starts folded",
              cell: (group) => (
                <GroupFoldCell
                  applicationKey={application.key}
                  group={group.key}
                  label={group.label}
                  folded={group.collapsed}
                  outline={outline}
                  run={run}
                />
              ),
            },
            { key: "state", label: "State", cell: (group) => <MarkPill mark={group.mark} /> },
          ]}
        />
        {application.navigation.ungrouped.length > 0 && application.navigation.groups.length > 0 && (
          <p className="muted">
            In no group: {application.navigation.ungrouped.map((key) => typeName(outline, key)).join(", ")}.{" "}
            <button
              type="button"
              className="link-button"
              onClick={() => {
                const item = operationById("application-group-add");
                if (item)
                  onOperation(item, target, {
                    entries: application.navigation.ungrouped.map((key) => `collection:${key}`),
                  });
              }}
            >
              Add to a group…
            </button>
          </p>
        )}
        <div className="element-tab-actions">
          <OperationButton id="application-add-group" target={target} outline={outline} onOperation={onOperation}>
            <Icon name="plus" /> Navigation group
          </OperationButton>
        </div>
      </section>
    );
  }

  if (selection.show === "group") {
    const application = applicationOf(outline, selection.application);
    const group = application?.navigation.groups.find((item) => item.key === selection.key);
    if (!application || !group) return <Missing what="navigation group" />;
    const target: OperationTarget = { on: "group", applicationKey: application.key, group: group.key };
    const entries = groupEntries(application, group.key);
    return (
      <section className="element-panel" aria-labelledby="element-title">
        <Header
          title={group.label}
          outline={outline}
          rename={(label) =>
            run([{ kind: "setNavigationGroup", applicationKey: application.key, group: group.key, label }])
          }
          mark={group.mark}
          proposed={Boolean(proposed)}
          facts={
            <Facts
              label="About this group"
              facts={[
                {
                  icon: "list",
                  label: (
                    <>
                      Navigation group of{" "}
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => onSelect({ show: "application", key: application.key })}
                      >
                        {application.name}
                      </button>
                    </>
                  ),
                },
                { icon: "type", label: <code>{group.key}</code>, title: "Key" },
                { icon: "toggle", label: group.collapsed ? "Starts folded" : "Starts open" },
                { icon: "list", label: `${entries.length} ${entries.length === 1 ? "entry" : "entries"}` },
              ]}
            />
          }
        >
          {menu(`Operations for the group ${group.label}`, target)}
        </Header>
        {proposed}
        <h3 className="element-subheading">Entries</h3>
        <EditorTable
          editing={editing}
          scope="group-entries"
          label={`Entries of ${group.label}`}
          noun={["entry", "entries"]}
          rows={entries}
          rowKey={entryRefId}
          reorder={{
            onMove: (id, position) => {
              const entry = entries.find((item) => entryRefId(item) === id);
              if (!entry) return;
              return run([
                {
                  kind: "placeCollection",
                  applicationKey: application.key,
                  ...(entry.kind === "matrix" ? { view: entry.key } : { collection: entry.key }),
                  group: group.key,
                  position,
                },
              ]);
            },
          }}
          menu={(entry) => (
            <OperationsMenu
              label={`Operations for ${entryName(outline, application, entry)}`}
              target={{
                on: "groupEntry",
                applicationKey: application.key,
                group: group.key,
                ...(entry.kind === "matrix" ? { view: entry.key } : { collection: entry.key }),
              }}
              outline={outline}
              onOperation={onOperation}
            />
          )}
          emptyMessage="This group has no entries yet. Add collections and relation matrices to it."
          columns={[
            {
              key: "entry",
              label: "Entry",
              cell: (entry) => (
                <EntryTag outline={outline} application={application} entry={entry} onSelect={onSelect} />
              ),
            },
            {
              key: "kind",
              label: "Kind",
              cell: (entry) =>
                entry.kind === "matrix"
                  ? "Relation matrix"
                  : application.borrowed.some((item) => item.objectType === entry.key)
                    ? "Borrowed list"
                    : "List",
            },
            {
              key: "opens",
              label: "Opens on",
              cell: (entry) =>
                entry.kind === "matrix"
                  ? openingLabel(application.views.find((view) => view.key === entry.key))
                  : openingLabel(openingView(application, entry.key)),
              edit: (entry) => {
                if (entry.kind === "matrix") return undefined;
                const views = collectionViews(application, entry.key);
                if (views.length < 2) return undefined;
                const natural = openingView(
                  { ...application, navigation: { ...application.navigation, opens: {} } },
                  entry.key,
                );
                return {
                  label: "Opens on",
                  value: openingView(application, entry.key)?.key ?? "",
                  options: views.map((view) => ({ value: view.key, label: viewLabel(view) })),
                  operations: (view) => [
                    {
                      kind: "setCollectionOpening",
                      applicationKey: application.key,
                      collection: entry.key,
                      view: view === natural?.key ? null : view,
                    },
                  ],
                };
              },
            },
            { key: "state", label: "State", cell: () => <MarkPill mark={group.mark} /> },
          ]}
        />
        <div className="element-tab-actions">
          <OperationButton id="group-add" target={target} outline={outline} onOperation={onOperation} primary>
            <Icon name="plus" /> Add to group…
          </OperationButton>
          <OperationButton id="group-rename" target={target} outline={outline} onOperation={onOperation}>
            Rename…
          </OperationButton>
          <OperationButton id="group-fold" target={target} outline={outline} onOperation={onOperation}>
            {group.collapsed ? "Start unfolded" : "Start folded"}
          </OperationButton>
        </div>
      </section>
    );
  }

  if (selection.show === "relationType") {
    const relationType = relationTypeOf(outline, selection.key);
    if (!relationType) return <Missing what="relation type" />;
    const target: OperationTarget = { on: "relationType", relationType: relationType.key };
    const pairs = outline.relations.filter((item) => item.relationType === relationType.key);
    return (
      <section className="element-panel" aria-labelledby="element-title">
        <Header
          title={relationType.name}
          outline={outline}
          rename={(name) => run([{ kind: "setLabel", element: { relationType: relationType.key }, name }])}
          mark={relationType.mark}
          proposed={Boolean(proposed)}
          facts={keyFacts(relationType.key, relationType.mark, [
            ...(relationType.reverseKey
              ? [{ icon: "arrow-left" as const, label: <code>{relationType.reverseKey}</code>, title: "Reverse key" }]
              : []),
            ...(relationType.containment
              ? [{ icon: "tree" as const, label: "Containment: places a record under its parent" }]
              : []),
          ])}
        >
          {menu(`Operations for ${relationType.name}`, target)}
        </Header>
        {proposed}
        <h3 className="element-subheading">Settings</h3>
        <SettingsTable
          scope="relation-type-settings"
          label={`Settings of ${relationType.name}`}
          settings={relationTypeSettings(relationType)}
          outline={outline}
          run={run}
          onOperation={onOperation}
        />
        <h3 className="element-subheading">Names</h3>
        <dl className="element-names">
          <div>
            <dt>
              <Icon name="arrow-right" size={14} /> From the “from” type
            </dt>
            <dd>
              <EditableText
                value={relationType.name}
                outline={outline}
                onSave={(name) => run([{ kind: "setLabel", element: { relationType: relationType.key }, name }])}
              />
            </dd>
          </div>
          <div>
            <dt>
              <Icon name="arrow-left" size={14} /> From the “to” type
            </dt>
            <dd>
              <EditableText
                label="Reverse name"
                value={relationType.reverseName ?? ""}
                outline={outline}
                onSave={(reverseName) =>
                  run([{ kind: "setLabel", element: { relationType: relationType.key }, reverseName }])
                }
              />
            </dd>
          </div>
        </dl>
        <h3 className="element-subheading">Allowed between</h3>
        <EditorTable
          editing={editing}
          scope="relation-pairs"
          label={`Types ${relationType.name} is allowed between`}
          noun={["pair", "pairs"]}
          rows={pairs}
          rowKey={(pair) => `${pair.from}:${pair.to}`}
          menu={(pair) => (
            <OperationsMenu
              label={`Operations for ${relationType.name} from ${typeName(outline, pair.from)} to ${typeName(outline, pair.to)}`}
              target={{ on: "relation", relationType: relationType.key, from: pair.from, to: pair.to }}
              outline={outline}
              onOperation={onOperation}
            />
          )}
          emptyMessage="No pair of types allows it yet."
          columns={[
            {
              key: "from",
              label: "From",
              cell: (pair) => <TypeLink outline={outline} typeKey={pair.from} onSelect={onSelect} />,
            },
            {
              key: "to",
              label: "To",
              cell: (pair) => <TypeLink outline={outline} typeKey={pair.to} onSelect={onSelect} />,
            },
            ...relationColumns,
            { key: "state", label: "State", cell: (pair) => <MarkPill mark={pair.mark} /> },
          ]}
        />
        <div className="element-tab-actions">
          <OperationButton id="relation-type-allow" target={target} outline={outline} onOperation={onOperation}>
            <Icon name="plus" /> Allow between two types…
          </OperationButton>
          <button type="button" className="secondary" onClick={() => onSelect({ show: "matrix" })}>
            <Icon name="matrix" /> Relationship matrix
          </button>
        </div>
      </section>
    );
  }

  if (selection.show === "attributeType") {
    const attributeType = attributeTypeOf(outline, selection.key);
    if (!attributeType) return <Missing what="attribute type" />;
    const target: OperationTarget = { on: "attributeType", attributeType: attributeType.key };
    const features = ["searchable", "filterable", "sortable", "unique"].filter(
      (name) => attributeType.features[name] === true,
    );
    return (
      <section className="element-panel" aria-labelledby="element-title">
        <Header
          title={attributeType.name}
          outline={outline}
          rename={(name) => run([{ kind: "setLabel", element: { attributeType: attributeType.key }, name }])}
          mark={attributeType.mark}
          proposed={Boolean(proposed)}
          facts={keyFacts(attributeType.key, attributeType.mark, [
            { icon: "type", label: valueTypeLabel(attributeType.valueType), title: "Value type" },
            ...features.map((name) => ({ icon: "check" as const, label: name[0].toUpperCase() + name.slice(1) })),
          ])}
        >
          {menu(`Operations for ${attributeType.name}`, target)}
        </Header>
        {proposed}
        <h3 className="element-subheading">Settings</h3>
        <SettingsTable
          scope="attribute-type-settings"
          label={`Settings of ${attributeType.name}`}
          settings={attributeTypeSettings(attributeType)}
          outline={outline}
          run={run}
          onOperation={onOperation}
        />
        <h3 className="element-subheading">Attached to</h3>
        <EditorTable
          editing={editing}
          scope="attribute-type-bindings"
          label={`Types ${attributeType.name} is attached to`}
          noun={["type", "types"]}
          rows={attributeType.boundBy}
          rowKey={(key) => key}
          menu={(key) => (
            <OperationsMenu
              label={`Operations for ${attributeType.name} on ${typeName(outline, key)}`}
              target={{ on: "attribute", objectType: key, attributeType: attributeType.key }}
              outline={outline}
              onOperation={onOperation}
            />
          )}
          emptyMessage="No type uses it yet."
          columns={[
            {
              key: "type",
              label: "Type",
              cell: (key) => <TypeLink outline={outline} typeKey={key} onSelect={onSelect} />,
            },
            {
              key: "required",
              label: "Required",
              cell: (key) => (bindingOf(outline, key, attributeType.key)?.required ? "Yes" : "No"),
              edit: (key) => ({
                label: "Required",
                value: String(Boolean(bindingOf(outline, key, attributeType.key)?.required)),
                options: YES_NO,
                operations: (value) => [
                  {
                    kind: "setAttributeBinding",
                    objectType: key,
                    attributeType: attributeType.key,
                    required: value === "true",
                  },
                ],
              }),
            },
            {
              key: "readOnly",
              label: "Read-only",
              cell: (key) => (bindingOf(outline, key, attributeType.key)?.readOnly ? "Yes" : "No"),
              edit: (key) => ({
                label: "Read-only",
                value: String(Boolean(bindingOf(outline, key, attributeType.key)?.readOnly)),
                options: YES_NO,
                operations: (value) => [
                  {
                    kind: "setAttributeBinding",
                    objectType: key,
                    attributeType: attributeType.key,
                    readOnly: value === "true",
                  },
                ],
              }),
            },
            {
              key: "state",
              label: "State",
              cell: (key) => {
                const binding = bindingOf(outline, key, attributeType.key);
                return binding && <MarkPill mark={binding.mark} />;
              },
            },
          ]}
        />
        <div className="element-tab-actions">
          <OperationButton id="attribute-type-attach" target={target} outline={outline} onOperation={onOperation}>
            <Icon name="plus" /> Attach to a type…
          </OperationButton>
        </div>
      </section>
    );
  }

  return (
    <section className="element-panel element-panel-empty">
      <EmptyState
        icon={<Icon name="model" size={22} />}
        action={
          <div className="element-tab-actions">
            {outline.applications.length > 0 && (
              <OperationButton id="add-type" target={{ on: "draft" }} outline={outline} onOperation={onOperation}>
                <Icon name="plus" /> Object type
              </OperationButton>
            )}
            <OperationButton id="add-application" target={{ on: "draft" }} outline={outline} onOperation={onOperation}>
              <Icon name="plus" /> Application
            </OperationButton>
            {outline.objectTypes.length > 0 && (
              <button type="button" className="secondary" onClick={() => onSelect({ show: "matrix" })}>
                <Icon name="matrix" /> Relationship matrix
              </button>
            )}
          </div>
        }
      >
        Choose an application, a type, a relation type or an attribute type in the model pane to see it and its
        operations.
      </EmptyState>
    </section>
  );
}

/** A type's binding of an attribute type. */
function bindingOf(outline: ModelDraftOutline, typeKey: string, attributeKey: string) {
  return objectTypeOf(outline, typeKey)?.attributes.find((item) => item.attributeType === attributeKey);
}

/** A view's name with its kind, as a collection's entry may open on it. */
const viewLabel = (view: { name: string; type?: string | null }) =>
  `${view.name} (${(VIEW_KINDS[view.type ?? ""] ?? view.type ?? "view").toLowerCase()})`;

/** The view an entry opens on, in words: its kind, then its name. */
function openingLabel(view?: { name: string; type?: string | null }) {
  return view ? `${(VIEW_KINDS[view.type ?? ""] ?? view.type ?? "view").toLowerCase()} · ${view.name}` : "—";
}

/** A relation matrix named in a table: its glyph in its row type's hue, then its name. */
export function MatrixTag({
  outline,
  view,
}: {
  outline: ModelDraftOutline;
  view: { name: string; collection?: string | null };
}) {
  return (
    <span className="type-link matrix-tag">
      <HueTile hue={view.collection ? draftTypeHue(outline, view.collection) : undefined} glyph="matrix" size={18} />
      {view.name}
    </span>
  );
}

/** An entry of a navigation group in a table: a collection links to its type; a matrix is named. */
function EntryTag({
  outline,
  application,
  entry,
  onSelect,
}: {
  outline: ModelDraftOutline;
  application: OutlineApplication;
  entry: NavigationEntryRef;
  onSelect: (selection: EditorSelection) => void;
}) {
  if (entry.kind === "collection") return <TypeLink outline={outline} typeKey={entry.key} onSelect={onSelect} />;
  const view = application.views.find((item) => item.key === entry.key);
  return view ? <MatrixTag outline={outline} view={view} /> : <>{entry.key}</>;
}

/** A group's entries as chips: its types, which link to them, and its matrices. */
function EntryChips({
  outline,
  application,
  group,
  onSelect,
}: {
  outline: ModelDraftOutline;
  application: OutlineApplication;
  group: OutlineNavigationGroup;
  onSelect: (selection: EditorSelection) => void;
}) {
  return (
    <span className="type-links">
      {groupEntries(application, group.key).map((entry) => (
        <EntryTag
          key={entryRefId(entry)}
          outline={outline}
          application={application}
          entry={entry}
          onSelect={onSelect}
        />
      ))}
    </span>
  );
}

/** A type in a table: its tile and name, choosing it shows the type. */
export function TypeLink({
  outline,
  typeKey,
  onSelect,
  application,
  dashed,
}: {
  outline: ModelDraftOutline;
  typeKey: string;
  onSelect: (selection: EditorSelection) => void;
  /** The application the type opens on. */
  application?: string;
  /** A dashed tile: a type the application borrows. */
  dashed?: boolean;
}) {
  return (
    <button
      type="button"
      className="link-button type-link"
      onClick={() => onSelect({ show: "type", key: typeKey, ...(application ? { application } : {}) })}
    >
      <HueTile
        hue={draftTypeHue(outline, typeKey)}
        icon={objectTypeOf(outline, typeKey)?.icon ?? undefined}
        size={18}
        dashed={dashed}
      />
      {typeName(outline, typeKey)}
    </button>
  );
}

export function Missing({ what }: { what: string }) {
  return (
    <section className="element-panel element-panel-empty">
      <p className="muted">This {what} is no longer in the draft. An undo or another editor may have removed it.</p>
    </section>
  );
}
