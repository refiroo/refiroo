/**
 * The editor's centre (0.10 A4a): the selected element with its operations. A type shows its key,
 * where it stands, its attributes and its relations; an application its types and navigation
 * groups; a relation type or an attribute type where it is used. Every operation is the descriptor
 * table's (D38), offered by the element's menu and by the menus of its rows.
 */

import type { ReactNode } from "react";
import type { EditorSelection, ModelDraftOutline, OutlineMark } from "@/types";
import { HueTile } from "@/ui/HueTile";
import { Icon } from "@/ui/Icon";
import { SettingsTable } from "@/ui/SettingsTable";
import { Tabs } from "@/ui/Tabs";
import { MarkPill } from "@/features/model-editor/MarkPill";
import { Facts, type Fact } from "@/features/model-editor/Facts";
import { EmptyState } from "@/ui/EmptyState";
import { OperationsMenu, type OnOperation } from "@/features/model-editor/OperationsMenu";
export type { OnOperation };
import { DRAG_ATTRIBUTE } from "@/features/model-editor/ModelPane";
import {
  cardinalityLabel,
  operationById,
  operationsFor,
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
  children,
}: {
  tile?: ReactNode;
  title: string;
  mark?: OutlineMark;
  facts: ReactNode;
  children?: ReactNode;
}) {
  return (
    <header className="element-header">
      {tile}
      <div className="element-title">
        <h2 id="element-title">
          {title} {mark && <MarkPill mark={mark} />}
        </h2>
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
}) {
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
          mark={type.mark}
          facts={keyFacts(type.key, type.mark)}
        >
          <OperationButton id="type-rename" target={target} outline={outline} onOperation={onOperation}>
            Rename
          </OperationButton>
          <OperationButton id="type-move" target={target} outline={outline} onOperation={onOperation}>
            Move to…
          </OperationButton>
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
                  {type.attributes.length ? (
                    <SettingsTable
                      label={`Attributes of ${type.name}`}
                      columns={["Attribute", "Value type", "Rules", "Shared with", "State", "Actions"]}
                    >
                      {type.attributes.map((attribute) => {
                        const rowTarget: OperationTarget = {
                          on: "attribute",
                          objectType: type.key,
                          attributeType: attribute.attributeType,
                        };
                        const rules = [
                          attribute.required && "Required",
                          attribute.unique && "Unique",
                          attribute.readOnly && "Read-only",
                        ].filter(Boolean);
                        return (
                          <tr
                            key={attribute.attributeType}
                            draggable={canDrag}
                            className={canDrag ? "draggable-row" : undefined}
                            onDragStart={(event) => {
                              event.dataTransfer.setData(DRAG_ATTRIBUTE, `${type.key}\u0000${attribute.attributeType}`);
                              event.dataTransfer.effectAllowed = "move";
                            }}
                          >
                            <th scope="row">
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
                            </th>
                            <td data-label="Value type">{valueTypeLabel(attribute.valueType)}</td>
                            <td data-label="Rules">{rules.length ? rules.join(" · ") : "—"}</td>
                            <td data-label="Shared with">
                              {attribute.sharedWith.length
                                ? attribute.sharedWith.map((key) => typeName(outline, key)).join(", ")
                                : "—"}
                            </td>
                            <td data-label="State">
                              <MarkPill mark={attribute.mark} />
                            </td>
                            <td className="element-row-menu">
                              <OperationsMenu
                                label={`Operations for ${attribute.name}`}
                                target={rowTarget}
                                outline={outline}
                                onOperation={onOperation}
                              />
                            </td>
                          </tr>
                        );
                      })}
                    </SettingsTable>
                  ) : (
                    <p className="muted">{type.name} has no attributes yet.</p>
                  )}
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
                  {relations.length ? (
                    <SettingsTable
                      label={`Relations of ${type.name}`}
                      columns={["Relation", "From → to", "Cardinality", "State", "Actions"]}
                    >
                      {relations.map((relation) => {
                        const relationType = relationTypeOf(outline, relation.relationType);
                        const rowTarget: OperationTarget = {
                          on: "relation",
                          relationType: relation.relationType,
                          from: relation.from,
                          to: relation.to,
                        };
                        return (
                          <tr key={`${relation.relationType}:${relation.from}:${relation.to}`}>
                            <th scope="row">
                              {relation.from === type.key
                                ? relationType?.name
                                : (relationType?.reverseName ?? relationType?.name)}
                              {relation.containment && <span className="muted"> · containment</span>}
                            </th>
                            <td data-label="From → to">
                              {typeName(outline, relation.from)} → {typeName(outline, relation.to)}
                            </td>
                            <td data-label="Cardinality">
                              {cardinalityLabel(relation.cardinality)}
                              {relation.required ? " · required" : ""}
                            </td>
                            <td data-label="State">
                              <MarkPill mark={relation.mark} />
                            </td>
                            <td className="element-row-menu">
                              <OperationsMenu
                                label={`Operations for ${relationType?.name ?? relation.relationType} from ${typeName(outline, relation.from)}`}
                                target={rowTarget}
                                outline={outline}
                                onOperation={onOperation}
                              />
                            </td>
                          </tr>
                        );
                      })}
                    </SettingsTable>
                  ) : (
                    <p className="muted">{type.name} takes part in no relation yet.</p>
                  )}
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
        <Header title={application.name} mark={application.mark} facts={keyFacts(application.key, application.mark)}>
          <OperationButton id="application-add-type" target={target} outline={outline} onOperation={onOperation}>
            <Icon name="plus" /> Object type
          </OperationButton>
          {menu(`Operations for ${application.name}`, target)}
        </Header>
        <h3 className="element-subheading">Object types</h3>
        {application.objectTypeKeys.length ? (
          <ul className="element-list">
            {application.objectTypeKeys.map((key) => (
              <li key={key}>
                <button type="button" className="link-button" onClick={() => onSelect({ show: "type", key })}>
                  <HueTile
                    hue={draftTypeHue(outline, key)}
                    icon={objectTypeOf(outline, key)?.icon ?? undefined}
                    size={20}
                  />
                  {typeName(outline, key)}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No object types yet.</p>
        )}
        <h3 className="element-subheading">Navigation groups</h3>
        {application.navigation.groups.length ? (
          <SettingsTable
            label={`Navigation groups of ${application.name}`}
            columns={["Group", "Collections", "Starts", "State", "Actions"]}
          >
            {application.navigation.groups.map((group) => (
              <tr key={group.key}>
                <th scope="row">
                  {group.label} <code className="element-key">{group.key}</code>
                </th>
                <td data-label="Collections">
                  {group.collections.map((key) => typeName(outline, key)).join(", ") || "None yet"}
                </td>
                <td data-label="Starts">{group.collapsed ? "Folded" : "Open"}</td>
                <td data-label="State">
                  <MarkPill mark={group.mark} />
                </td>
                <td className="element-row-menu">
                  <OperationsMenu
                    label={`Operations for the group ${group.label}`}
                    target={{ on: "group", applicationKey: application.key, group: group.key }}
                    outline={outline}
                    onOperation={onOperation}
                  />
                </td>
              </tr>
            ))}
          </SettingsTable>
        ) : (
          <p className="muted">No navigation groups: every collection stands at the top of the sidebar.</p>
        )}
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
          mark={relationType.mark}
          facts={keyFacts(relationType.key, relationType.mark)}
        >
          {menu(`Operations for ${relationType.name}`, target)}
        </Header>
        <p className="element-place">
          Reverse name: {relationType.reverseName ?? "—"}
          {relationType.containment ? " · a containment relation: it places a record under its parent" : ""}
        </p>
        <h3 className="element-subheading">Allowed between</h3>
        {pairs.length ? (
          <ul className="element-list">
            {pairs.map((pair) => (
              <li key={`${pair.from}:${pair.to}`}>
                {typeName(outline, pair.from)} → {typeName(outline, pair.to)} · {cardinalityLabel(pair.cardinality)}{" "}
                <MarkPill mark={pair.mark} />
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No pair of types allows it yet. Allow it from a type's Relations or the matrix.</p>
        )}
      </section>
    );
  }

  if (selection.show === "attributeType") {
    const attributeType = attributeTypeOf(outline, selection.key);
    if (!attributeType) return <Missing what="attribute type" />;
    const target: OperationTarget = { on: "attributeType", attributeType: attributeType.key };
    const features = Object.entries(attributeType.features)
      .filter(([, on]) => on === true)
      .map(([name]) => name);
    return (
      <section className="element-panel" aria-labelledby="element-title">
        <Header
          title={attributeType.name}
          mark={attributeType.mark}
          facts={keyFacts(attributeType.key, attributeType.mark)}
        >
          {menu(`Operations for ${attributeType.name}`, target)}
        </Header>
        <p className="element-place">
          {valueTypeLabel(attributeType.valueType)}
          {features.length ? ` · ${features.join(", ")}` : ""}
        </p>
        <h3 className="element-subheading">Attached to</h3>
        {attributeType.boundBy.length ? (
          <ul className="element-list">
            {attributeType.boundBy.map((key) => (
              <li key={key}>
                <button type="button" className="link-button" onClick={() => onSelect({ show: "type", key })}>
                  {typeName(outline, key)}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No type uses it yet. Attach it from a type's Attributes.</p>
        )}
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

function Missing({ what }: { what: string }) {
  return (
    <section className="element-panel element-panel-empty">
      <p className="muted">This {what} is no longer in the draft. An undo or another editor may have removed it.</p>
    </section>
  );
}
