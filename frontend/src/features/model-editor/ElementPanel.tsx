/**
 * The editor's centre (0.10 A4a): the selected element with its operations. A type shows its key,
 * where it stands, its attributes and its relations; an application its types and navigation
 * groups; a relation type or an attribute type where it is used. Every operation is the descriptor
 * table's (D38), offered by the element's menu and by the menus of its rows.
 */

import type { ReactNode } from "react";
import type { EditorSelection, ModelDraftOutline, OutlineMark, OutlineRelation } from "@/types";
import { HueTile } from "@/ui/HueTile";
import { Icon } from "@/ui/Icon";
import { Tabs } from "@/ui/Tabs";
import { MarkPill } from "@/features/model-editor/MarkPill";
import { EditorTable, type EditorColumn } from "@/features/model-editor/EditorTable";
import { YES_NO } from "@/features/model-editor/EditableCell";
import { describeCandidates } from "@/features/model-editor/candidates";
import { EditInPlaceValue } from "@/ui/EditInPlace";
import { EditableText } from "@/features/model-editor/EditableText";
import type { RunStep, StepOutcome } from "@/features/model-editor/OperationDialog";
import { Facts, type Fact } from "@/features/model-editor/Facts";
import { EmptyState } from "@/ui/EmptyState";
import { OperationsMenu, type OnOperation } from "@/features/model-editor/OperationsMenu";
export type { OnOperation };
import { DRAG_ATTRIBUTE } from "@/features/model-editor/ModelPane";
import {
  CARDINALITIES,
  cardinalityLabel,
  operationById,
  operationsFor,
  VALUE_TYPES,
  valueTypeLabel,
  type OperationTarget,
} from "@/features/model-editor/operations";
import {
  applicationOf,
  applicationsOf,
  attributeTypeOf,
  draftTypeHue,
  isReleased,
  objectTypeOf,
  placeOf,
  relationTypeOf,
  relationsOf,
  typeName,
} from "@/features/model-editor/outline";

function Header({
  tile,
  title,
  mark,
  facts,
  rename,
  outline,
  children,
}: {
  tile?: ReactNode;
  title: string;
  mark?: OutlineMark;
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
          after={mark && <MarkPill mark={mark} />}
        />
        {facts}
      </div>
      <div className="element-actions">{children}</div>
    </header>
  );
}

function OperationButton({
  id,
  target,
  outline,
  onOperation,
  children,
}: {
  id: string;
  target: OperationTarget;
  outline: ModelDraftOutline;
  onOperation: OnOperation;
  children: ReactNode;
}) {
  const item = operationById(id);
  if (!item || !operationsFor(target, outline).includes(item)) return null;
  return (
    <button type="button" className="secondary" onClick={() => onOperation(item, target)}>
      {children}
    </button>
  );
}

/** An element's key, and whether it can still change (A-D6): fixed once released, labels always free. */
const keyFacts = (key: string, mark: OutlineMark | undefined, extra: Fact[] = []) => (
  <Facts
    label="About this element"
    facts={[
      { icon: "type", label: <code>{key}</code>, title: "Key" },
      isReleased(mark)
        ? { icon: "lock", label: "Key fixed: released", title: "Released, so the key is fixed; labels still change" }
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
}: {
  outline: ModelDraftOutline;
  selection: EditorSelection;
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
    const apps = applicationsOf(outline, type.key);
    const relations = relationsOf(outline, type.key);
    return (
      <section className="element-panel" aria-labelledby="element-title">
        <Header
          tile={<HueTile hue={draftTypeHue(outline, type.key)} icon={type.icon ?? undefined} size={40} />}
          title={type.name}
          outline={outline}
          rename={(name) => run([{ kind: "setLabel", element: { objectType: type.key }, name }])}
          mark={type.mark}
          facts={keyFacts(type.key, type.mark)}
        >
          {menu(`Operations for ${type.name}`, target)}
        </Header>
        <p className="element-place">
          {placeOf(outline, type)}
          {apps.length ? ` · in ${apps.map((a) => a.name).join(", ")}` : " · in no application"}
        </p>
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
        <h3 className="element-subheading">Object types</h3>
        <EditorTable
          editing={editing}
          scope="application-types"
          label={`Object types of ${application.name}`}
          noun={["object type", "object types"]}
          rows={application.objectTypeKeys}
          rowKey={(key) => key}
          menu={(key) => (
            <OperationsMenu
              label={`Operations for ${typeName(outline, key)}`}
              target={{ on: "objectType", objectType: key }}
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
        <div className="element-tab-actions">
          <OperationButton id="application-add-type" target={target} outline={outline} onOperation={onOperation}>
            <Icon name="plus" /> Object type
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
              cell: (group) => group.label,
              edit: (group) => ({
                label: "Label",
                value: group.label,
                operations: (label) => [
                  { kind: "setNavigationGroup", applicationKey: application.key, group: group.key, label },
                ],
              }),
            },
            {
              key: "collections",
              label: "Collections",
              cell: (group) =>
                group.collections.length ? (
                  <span className="type-links">
                    {group.collections.map((key) => (
                      <TypeLink key={key} outline={outline} typeKey={key} onSelect={onSelect} />
                    ))}
                  </span>
                ) : (
                  "None yet"
                ),
            },
            {
              key: "starts",
              label: "Starts",
              cell: (group) => (group.collapsed ? "Folded" : "Open"),
              edit: (group) => ({
                label: "Starts",
                value: String(group.collapsed),
                options: [
                  { value: "false", label: "Open" },
                  { value: "true", label: "Folded" },
                ],
                operations: (value) => [
                  {
                    kind: "setNavigationGroup",
                    applicationKey: application.key,
                    group: group.key,
                    collapsed: value === "true",
                  },
                ],
              }),
            },
            { key: "state", label: "State", cell: (group) => <MarkPill mark={group.mark} /> },
          ]}
        />
        {application.navigation.ungrouped.length > 0 && application.navigation.groups.length > 0 && (
          <p className="muted">
            In no group: {application.navigation.ungrouped.map((key) => typeName(outline, key)).join(", ")}.
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
          facts={keyFacts(attributeType.key, attributeType.mark, [
            { icon: "type", label: valueTypeLabel(attributeType.valueType), title: "Value type" },
            ...features.map((name) => ({ icon: "check" as const, label: name[0].toUpperCase() + name.slice(1) })),
          ])}
        >
          {menu(`Operations for ${attributeType.name}`, target)}
        </Header>
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

/** A type in a table: its tile and name, choosing it shows the type. */
function TypeLink({
  outline,
  typeKey,
  onSelect,
}: {
  outline: ModelDraftOutline;
  typeKey: string;
  onSelect: (selection: EditorSelection) => void;
}) {
  return (
    <button type="button" className="link-button type-link" onClick={() => onSelect({ show: "type", key: typeKey })}>
      <HueTile
        hue={draftTypeHue(outline, typeKey)}
        icon={objectTypeOf(outline, typeKey)?.icon ?? undefined}
        size={18}
      />
      {typeName(outline, typeKey)}
    </button>
  );
}

function Missing({ what }: { what: string }) {
  return (
    <section className="element-panel element-panel-empty">
      <p className="muted">This {what} is no longer in the draft. An undo or another editor may have removed it.</p>
    </section>
  );
}
