/**
 * The model editor's Consumer APIs tab (0.10 A4c, D57, D59): the draft's consumer API definitions
 * in the left pane, and the selected one in the centre with its tabs: Types and related, Fields,
 * Operations, Filters, and two documents an integration takes from it, the Schema and a Message
 * example (D56, as the user asked at acceptance). Every change is one consumer kind (D51) sent from a
 * table's cell, a row's menu or a dialog of the editor's one `OperationDialog`; undo is the bar's.
 *
 * The definition is read from the server after every step (`GET …/consumer-apis/{key}`), with its
 * contract against what the active release's consumers read; the served types come from its schema.
 */

import { useEffect, useState, type ReactNode } from "react";
import { api, consumerApiDocumentPath } from "@/api/client";
import { downloadFrom } from "@/api/download";
import { DownloadLink } from "@/ui/DownloadLink";
import { errorMessage } from "@/api/errors";
import type {
  ConsumerApiDocumentKind,
  ConsumerApiTab,
  EditorSelection,
  ModelDraftConsumerApi,
  ModelDraftOutline,
  OutlineConsumerApi,
} from "@/types";
import { EmptyState } from "@/ui/EmptyState";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { Tabs } from "@/ui/Tabs";
import { useToast } from "@/ui/Toast";
import {
  alsoMatchThroughOf,
  customEventsOf,
  earlierVersionsOf,
  exposesOf,
  includeNames,
  parentSpecOf,
  parentTypesOf,
  SERVED_OPTIONS,
  writeParent,
  FILTER_OPTION_LABELS,
  FILTER_VERBS,
  fieldsOf,
  filtersOf,
  formatDefault,
  formatPairs,
  listsOf,
  matchRulesOf,
  offers,
  parseDefault,
  perTypeEvents,
  pointer,
  publicNamesOf,
  relatedOf,
  type RelatedRow,
  renameMember,
  ROLE_OPTIONS,
  schemaTypeLabel,
  setField,
  sortOptions,
  toggleOperation,
  viaLabel,
  xrefRuleCount,
} from "@/features/model-editor/consumer";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { SettingsTable } from "@/features/model-editor/SettingsTable";
import { EditorTable } from "@/features/model-editor/EditorTable";
import { Header, Missing, OperationButton } from "@/features/model-editor/ElementPanel";
import { Facts } from "@/features/model-editor/Facts";
import { EditorTree, type TreeRow } from "@/features/model-editor/ModelPane";
import type { RunStep } from "@/features/model-editor/OperationDialog";
import { OperationsMenu, type OnOperation } from "@/features/model-editor/OperationsMenu";
import { operationById, operationsFor, type OperationTarget } from "@/features/model-editor/operations";
import { EditInPlaceValue } from "@/ui/EditInPlace";
import { consumerApiOf, isReleased, typeName } from "@/features/model-editor/outline";

const SECTIONS: { tab: ConsumerApiTab; label: string; count?: keyof OutlineConsumerApi["counts"] }[] = [
  { tab: "types", label: "Types and related", count: "related" },
  { tab: "fields", label: "Fields", count: "fields" },
  { tab: "operations", label: "Operations", count: "lists" },
  { tab: "filters", label: "Filters", count: "filters" },
];

/** The contract state of a definition as a pill: what its consumers would notice (D55). */
export function ContractPill({ item }: { item: OutlineConsumerApi }) {
  if (!item.contract) return null;
  return item.contract.classification === "version_required" ? (
    <StatusPill tone="error">Needs v{(item.contractVersion ?? 1) + 1}</StatusPill>
  ) : null;
}

export function consumerRows(outline: ModelDraftOutline, selection: EditorSelection): TreeRow[] {
  const rows: TreeRow[] = [];
  for (const item of outline.consumerApis) {
    rows.push({
      id: `consumerApi:${item.key}`,
      level: 1,
      label: item.name,
      note: `v${item.contractVersion ?? 1}`,
      mark: item.mark,
      badge: <ContractPill item={item} />,
      icon: "api",
      selection: { show: "consumerApi", key: item.key },
    });
    if (selection.show === "consumerApi" && selection.key === item.key)
      for (const section of SECTIONS)
        rows.push({
          id: `consumerApi:${item.key}:${section.tab}`,
          level: 2,
          label: section.label,
          note: section.count === undefined ? undefined : String(item.counts[section.count]),
          selection: { show: "consumerApi", key: item.key, tab: section.tab },
        });
  }
  return rows;
}

export function ConsumerApiPane({
  outline,
  selection,
  onSelect,
  onMenu,
}: {
  outline: ModelDraftOutline;
  selection: EditorSelection;
  onSelect: (selection: EditorSelection) => void;
  onMenu: (selection: EditorSelection) => void;
}) {
  return (
    <>
      {outline.consumerApis.length === 0 && (
        <p className="muted model-editor-empty">No consumer API yet. Add one with ＋ to expose types to consumers.</p>
      )}
      <EditorTree
        label="Consumer APIs"
        outline={outline}
        rows={() => consumerRows(outline, selection)}
        selection={selection}
        canDrag={false}
        onSelect={onSelect}
        onMenu={onMenu}
      />
      <p className="muted model-editor-pane-note">
        Consumers read the active release. A change here reaches them after Install and activate.
      </p>
    </>
  );
}

/** What a document is for, in the integrator's terms (D56). */
const DOCUMENTS: Record<"schema" | "example", { title: string; file: string; about: string }> = {
  schema: {
    title: "Schema",
    file: "schema.json",
    about:
      "The JSON Schema of the message consumers receive. An integration validates messages against it or generates its types from it.",
  },
  example: {
    title: "Message example",
    file: "example.json",
    about:
      "One message as Get by ID would answer it, valid against the schema. An integration uses it as a test fixture or to agree the format with a partner. No record is read: the values come from each field's type.",
  },
};

export function ConsumerApiPanel({
  draftId,
  outline,
  selection,
  onSelect,
  menuOpen,
  onMenuOpenChange,
  onOperation,
  run,
}: {
  draftId: string;
  outline: ModelDraftOutline;
  selection: Extract<EditorSelection, { show: "consumerApi" }>;
  onSelect: (selection: EditorSelection) => void;
  menuOpen: boolean;
  onMenuOpenChange: (open: boolean) => void;
  onOperation: OnOperation;
  run: RunStep;
}) {
  const item = consumerApiOf(outline, selection.key);
  const tab = selection.tab ?? "fields";
  const [read, setRead] = useState<{
    version: number;
    key: string;
    data: ModelDraftConsumerApi;
    schema?: Record<string, unknown>;
  }>();
  const [loadError, setLoadError] = useState("");
  const [attempt, setAttempt] = useState(0);
  // Switching XREF off takes its match rules with it, so it asks first.
  const [confirmXref, setConfirmXref] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .modelDraftConsumerApi(draftId, selection.key)
      .then(async (data) => {
        const schema = data.valid
          ? await api.modelDraftConsumerApiDocument(draftId, selection.key, "schema").catch(() => undefined)
          : undefined;
        if (!cancelled) {
          setRead({ version: outline.version, key: selection.key, data, schema });
          setLoadError("");
        }
      })
      .catch((cause) => {
        if (!cancelled) setLoadError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [draftId, selection.key, outline.version, attempt]);

  if (!item) return <Missing what="consumer API" />;
  if (loadError)
    return (
      <InlineError
        message={loadError}
        onRetry={() => {
          setLoadError("");
          setAttempt((value) => value + 1);
        }}
      />
    );
  if (!read || read.key !== selection.key) return <Skeleton lines={6} label="Loading the consumer API" />;

  const definition = read.data.definition;
  const key = item.key;
  const version = item.contractVersion ?? 1;
  const target: OperationTarget = { on: "consumerApi", consumerApi: key, definition };
  const editing = { outline, run };
  const showTab = (next: string) => onSelect({ show: "consumerApi", key, tab: next as ConsumerApiTab });
  const itemTarget = (path: string, label: string, index: number, count: number, value: unknown): OperationTarget => ({
    on: "consumerItem",
    consumerApi: key,
    pointer: path,
    label,
    index,
    count,
    value,
    definition,
  });
  const itemMenu = (path: string, label: string, index: number, count: number, value: unknown) => (
    <OperationsMenu
      label={`Operations for ${label}`}
      target={itemTarget(path, label, index, count, value)}
      outline={outline}
      onOperation={onOperation}
    />
  );
  /** A cell whose value is chosen in a dialog with a selector (the user: no field name typed by hand). */
  const chooserCell = (id: string, name: string, target: OperationTarget, shown: ReactNode) => {
    const choose = operationById(id);
    return choose && operationsFor(target, outline).includes(choose) ? (
      <EditInPlaceValue layout="row" name={name} onEdit={() => onOperation(choose, target)}>
        <span className="attribute-value">{shown}</span>
      </EditInPlaceValue>
    ) : (
      shown
    );
  };
  const add = (id: string, children: ReactNode) => (
    <OperationButton id={id} target={target} outline={outline} onOperation={onOperation}>
      {children}
    </OperationButton>
  );
  /** The Served column of a related table: Always or On request, changed in place (CA1, PP-D30). */
  const servedColumn = (container: string) => ({
    key: "served",
    label: "Served",
    cell: (row: RelatedRow) => SERVED_OPTIONS.find((option) => option.value === row.served)?.label ?? row.served,
    edit: (row: RelatedRow) => ({
      label: "Served",
      value: row.served,
      options: [...SERVED_OPTIONS],
      operations: (value: string) => [
        {
          kind: "setConsumerApiPart",
          consumerApi: key,
          pointer: `${container}${pointer(row.output, "served")}`,
          value: value === "onRequest" ? "onRequest" : null,
        },
      ],
    }),
  });
  const properties = (read.schema?.properties ?? {}) as Record<string, Record<string, unknown>>;
  const defs = (read.schema?.$defs ?? {}) as Record<string, Record<string, unknown>>;
  const contract = item.contract;
  // The previous version stays served beside the new one unless the author says otherwise (DF3).
  const raise = (keep = true) =>
    void run([{ kind: "raiseConsumerApiVersion", consumerApi: key, ...(keep ? {} : { keep: false }) }]);
  const contractNotice =
    contract?.classification === "version_required" ? (
      <Notice
        tone="warning"
        title={`Needs contract version ${version + 1}`}
        actions={
          <>
            <button type="button" className="primary" onClick={() => raise()}>
              Raise to version {version + 1}
            </button>
            <button type="button" className="secondary" onClick={() => raise(false)}>
              Raise and stop serving version {version}
            </button>
          </>
        }
      >
        Consumers of version {version} would notice:{" "}
        {contract.diagnostics
          .filter((d) => d.severity === "error")
          .map((d) => d.message.replace(/; raise contractVersion.*$/, ""))
          .join("; ")}
        . Raise the version to release the change, or undo it. Version {version} stays served beside the new one until
        you stop it, as the active release serves it today; an API the active release does not have keeps no earlier
        version. Activation is refused until then.
      </Notice>
    ) : null;

  const typesTab = () => {
    const earlier = earlierVersionsOf(definition);
    const names = publicNamesOf(definition);
    const related = relatedOf(definition);
    return (
      <div className="element-tab">
        {contractNotice}
        <h3 className="element-subheading">Settings</h3>
        <SettingsTable
          scope="consumer-settings"
          label={`Settings of ${item.name}`}
          settings={[
            {
              key: "contractVersion",
              label: "Contract version",
              hint: "raise it when a change would break what consumers read",
              value: `v${version}`,
              edit: {
                label: "Contract version",
                value: String(version),
                operations: (value) =>
                  Number.isInteger(Number(value)) && Number(value) > version
                    ? [{ kind: "raiseConsumerApiVersion", consumerApi: key, version: Number(value) }]
                    : [
                        {
                          kind: "setConsumerApiPart",
                          consumerApi: key,
                          pointer: "/contractVersion",
                          value: Number.isInteger(Number(value)) ? Number(value) : value,
                        },
                      ],
              },
            },
          ]}
          outline={outline}
          run={run}
          onOperation={onOperation}
        />
        <h3 className="element-subheading">Earlier versions</h3>
        <p className="muted">
          Consumers of an earlier version go on reading the current data in that version&apos;s shape until you stop
          serving it. The sunset day is announced in the <code>Sunset</code> header; it is not enforced.
        </p>
        <EditorTable
          editing={editing}
          scope="consumer-earlier"
          label={`Earlier versions of ${item.name}`}
          noun={["earlier version", "earlier versions"]}
          rows={earlier}
          rowKey={(row) => String(row.version)}
          emptyMessage="None: raising the contract version keeps the previous one here."
          columns={[
            { key: "version", label: "Version", cell: (row) => <strong>v{row.version}</strong> },
            { key: "deprecated", label: "Superseded", cell: (row) => row.deprecated ?? "—" },
            {
              key: "sunset",
              label: "Sunset day",
              cell: (row) => row.sunset ?? "—",
              edit: (row) => ({
                label: "Sunset day (YYYY-MM-DD)",
                value: row.sunset ?? "",
                optional: true,
                operations: (value) => [
                  { kind: "setConsumerApiSunset", consumerApi: key, version: row.version, sunset: value || null },
                ],
              }),
            },
            {
              key: "stop",
              label: "Serving",
              cell: (row) => (
                <OperationButton
                  id="consumer-version-stop"
                  target={itemTarget(
                    pointer("earlierVersions", row.index),
                    `version ${row.version}`,
                    row.index,
                    earlier.length,
                    row.value,
                  )}
                  outline={outline}
                  onOperation={onOperation}
                >
                  Stop serving
                </OperationButton>
              ),
            },
          ]}
        />
        <h3 className="element-subheading">Exposed types</h3>
        <EditorTable
          editing={editing}
          scope="consumer-types"
          label={`Types ${item.name} exposes`}
          noun={["type", "types"]}
          rows={item.exposes}
          rowKey={(row) => row.objectType}
          menu={(row) =>
            itemMenu(
              pointer("exposes", item.exposes.indexOf(row)),
              `the exposed type ${typeName(outline, row.objectType)}`,
              item.exposes.indexOf(row),
              item.exposes.length,
              row.objectType,
            )
          }
          emptyMessage="No type exposed."
          columns={[
            { key: "type", label: "Type", cell: (row) => typeName(outline, row.objectType) },
            {
              key: "publicName",
              label: "Public name",
              cell: (row) => (
                <>
                  <code>{row.publicName}</code>
                  {!names[row.objectType] && <span className="muted"> · default</span>}
                </>
              ),
              edit: (row) => ({
                label: "Public name",
                value: names[row.objectType] ?? "",
                optional: true,
                operations: (value) =>
                  "publicNames" in definition
                    ? [
                        {
                          kind: "setConsumerApiPart",
                          consumerApi: key,
                          pointer: pointer("publicNames", row.objectType),
                          value: value || null,
                        },
                      ]
                    : value
                      ? [
                          {
                            kind: "setConsumerApiPart",
                            consumerApi: key,
                            pointer: "/publicNames",
                            value: { [row.objectType]: value },
                          },
                        ]
                      : [],
              }),
            },
          ]}
        />
        <div className="element-tab-actions">
          {add(
            "consumer-expose",
            <>
              <Icon name="plus" /> Expose a type
            </>,
          )}
        </div>
        <h3 className="element-subheading">Related records</h3>
        <EditorTable
          editing={editing}
          scope="consumer-related"
          label={`Related records ${item.name} serves`}
          noun={["related block", "related blocks"]}
          rows={related}
          rowKey={(row) => row.output}
          menu={(row) =>
            itemMenu(
              pointer("object", "related", row.output),
              `related block ${row.output}`,
              row.index,
              related.length,
              row.value,
            )
          }
          emptyMessage="No related records: add a block to serve records reached by a relation."
          columns={[
            {
              key: "output",
              label: "Output",
              cell: (row) => <strong>{row.output}</strong>,
              edit: (row) => ({
                label: "Output name",
                value: row.output,
                operations: (value) => renameMember(key, "/object/related", row.output, value, row.value, row.index),
              }),
            },
            { key: "via", label: "Via", cell: (row) => viaLabel(outline, row.via) },
            {
              key: "serves",
              label: "Serves",
              cell: (row) => {
                const property = properties[row.output];
                if (!property) return "—";
                return property.type === "array" ? "a list" : "one or null";
              },
            },
            {
              key: "fields",
              label: "Fields",
              cell: (row) =>
                chooserCell(
                  "consumer-related-fields",
                  "Fields",
                  itemTarget(
                    pointer("object", "related", row.output),
                    `related block ${row.output}`,
                    row.index,
                    related.length,
                    row.value,
                  ),
                  <code>{formatPairs(row.fields)}</code>,
                ),
            },
            servedColumn(pointer("object", "related")),
          ]}
        />
        <div className="element-tab-actions">
          {add(
            "consumer-add-related",
            <>
              <Icon name="plus" /> Add related
            </>,
          )}
        </div>
        <p className="muted">
          An on-request block is served only when the request names it in <code>include</code>.
        </p>
      </div>
    );
  };

  const fieldsTab = () => {
    const fields = fieldsOf(definition);
    const shape = (definition.object ?? {}) as Record<string, unknown>;
    const extras = ["parent", "path", "hierarchy"].filter((name) => shape[name]);
    const parent = parentSpecOf(definition);
    return (
      <div className="element-tab">
        {contractNotice}
        <EditorTable
          editing={editing}
          scope="consumer-fields"
          label={`Fields of ${item.name}`}
          noun={["field", "fields"]}
          rows={fields}
          rowKey={(row) => row.output}
          menu={(row) =>
            itemMenu(
              pointer("object", "fields", row.output),
              `field ${row.output}`,
              row.index,
              fields.length,
              row.value,
            )
          }
          emptyMessage="No fields."
          columns={[
            {
              key: "output",
              label: "Output name",
              cell: (row) => <strong>{row.output}</strong>,
              edit: (row) => ({
                label: "Output name",
                value: row.output,
                operations: (value) => renameMember(key, "/object/fields", row.output, value, row.value, row.index),
              }),
            },
            {
              key: "role",
              label: "Role",
              cell: (row) => (row.role ? <span className="consumer-role">{row.role}</span> : "—"),
              edit: (row) => ({
                label: "Role",
                value: row.role,
                options: ROLE_OPTIONS,
                operations: (role) => setField(key, row, { role }),
              }),
            },
            {
              key: "sources",
              label: "Sources (first non-empty)",
              // Chosen in order from a picklist of what the exposed types offer (the user, A4c).
              cell: (row) =>
                row.role === "id" ? (
                  <span className="muted">the object ID</span>
                ) : (
                  chooserCell(
                    "consumer-field-sources",
                    "Sources",
                    itemTarget(
                      pointer("object", "fields", row.output),
                      `field ${row.output}`,
                      row.index,
                      fields.length,
                      row.value,
                    ),
                    <code>{row.sources.join(", ")}</code>,
                  )
                ),
            },
            {
              key: "type",
              label: "Served type",
              cell: (row) => <code>{schemaTypeLabel(properties[row.output], defs)}</code>,
            },
            {
              key: "default",
              label: "Default",
              cell: (row) => (row.default === undefined ? "—" : <code>{formatDefault(row.default)}</code>),
              edit: (row) => ({
                label: "Default",
                value: formatDefault(row.default),
                optional: true,
                operations: (value) => setField(key, row, { default: parseDefault(value) }),
              }),
            },
          ]}
        />
        <div className="element-tab-actions">
          {add(
            "consumer-add-field",
            <>
              <Icon name="plus" /> Add field
            </>,
          )}
          {add("consumer-object-extras", "Parent, path and hierarchy…")}
        </div>
        <p className="muted">
          {extras.length ? `Also served: ${extras.join(", ")}.` : "Parent, path and hierarchy are not served."} Role
          fields are served first, in role order; the others in this order.
        </p>
        {parent && parentSection(parent)}
      </div>
    );
  };

  /** The parent a record shows: its fields, which take the attributes of the parent types, and the
   * related blocks of its own, served as the object's are (CA1). */
  const parentSection = (parent: NonNullable<ReturnType<typeof parentSpecOf>>) => {
    const owners = parentTypesOf(outline, exposesOf(definition));
    const blocks = relatedOf(definition, "parent");
    const container = pointer("object", "parent", "related");
    return (
      <section aria-labelledby="consumer-parent" className="consumer-parent">
        <h3 id="consumer-parent" className="element-subheading">
          Parent
        </h3>
        <EditorTable
          editing={editing}
          scope="consumer-parent"
          label={`Parent of ${item.name}`}
          noun={["parent", "parents"]}
          rows={[parent]}
          rowKey={() => "parent"}
          emptyMessage=""
          columns={[
            {
              key: "output",
              label: "Output name",
              cell: (row) => <strong>{row.output}</strong>,
              edit: (row) => ({
                label: "Output name",
                value: row.output,
                operations: (value) => [
                  {
                    kind: "setConsumerApiPart",
                    consumerApi: key,
                    pointer: pointer("object", "parent"),
                    value: writeParent(definition, { output: value }),
                  },
                ],
              }),
            },
            {
              key: "fields",
              label: "Fields",
              cell: (row) =>
                chooserCell(
                  "consumer-parent-fields",
                  "Fields",
                  target,
                  <code>
                    {formatPairs(
                      Object.fromEntries(row.fields.map((field) => [field.output, field.sources.join(" or ")])),
                    )}
                  </code>,
                ),
            },
          ]}
        />
        <p className="muted">
          Fields offered: the attributes of the parent types
          {owners.length ? ` (${owners.map((type) => typeName(outline, type)).join(", ")})` : ""}. A source a parent
          type doesn&apos;t have is served as <code>null</code>.
        </p>
        <h4 className="element-subheading">Parent&apos;s related records</h4>
        <EditorTable
          editing={editing}
          scope="consumer-parent-related"
          label={`Related records of the parent of ${item.name}`}
          noun={["related block", "related blocks"]}
          rows={blocks}
          rowKey={(row) => row.output}
          menu={(row) =>
            itemMenu(
              pointer("object", "parent", "related", row.output),
              `the parent's related block ${row.output}`,
              row.index,
              blocks.length,
              row.value,
            )
          }
          emptyMessage="No related records on the parent."
          columns={[
            {
              key: "output",
              label: "Output name",
              cell: (row) => <strong>{row.output}</strong>,
              edit: (row) => ({
                label: "Output name",
                value: row.output,
                operations: (value) => renameMember(key, container, row.output, value, row.value, row.index),
              }),
            },
            { key: "via", label: "Via", cell: (row) => viaLabel(outline, row.via) },
            {
              key: "fields",
              label: "Fields",
              cell: (row) =>
                chooserCell(
                  "consumer-related-fields",
                  "Fields",
                  itemTarget(
                    pointer("object", "parent", "related", row.output),
                    `the parent's related block ${row.output}`,
                    row.index,
                    blocks.length,
                    row.value,
                  ),
                  <code>{formatPairs(row.fields)}</code>,
                ),
            },
            servedColumn(container),
          ]}
        />
        <div className="element-tab-actions">
          {add(
            "consumer-add-parent-related",
            <>
              <Icon name="plus" /> Add related
            </>,
          )}
        </div>
        <p className="muted">
          One level: the parent has no parent of its own. Use path and hierarchy for the ancestor names.
        </p>
      </section>
    );
  };

  const operationsTab = () => {
    const lists = listsOf(definition);
    const rules = matchRulesOf(definition);
    const through = alsoMatchThroughOf(definition);
    const events = customEventsOf(definition);
    const filters = filtersOf(definition, outline);
    const offered: {
      id: "objects" | "xref" | "resolve" | "perType";
      name: string;
      about: string;
      on: boolean;
      disabled?: boolean;
    }[] = [
      { id: "objects", name: "Get by ID", about: "GET …/objects/{id}", on: offers(definition, "objects") },
      {
        id: "xref",
        name: "XREF",
        about: "GET …/xref?query=… finds records by their codes and names",
        on: offers(definition, "xref"),
      },
      {
        id: "resolve",
        name: "Resolve",
        about: "POST …/resolve: many lookups in one request; needs Get by ID and XREF",
        on: offers(definition, "resolve"),
        disabled: !offers(definition, "resolve") && !(offers(definition, "objects") && offers(definition, "xref")),
      },
      {
        id: "perType",
        name: "Events per type",
        about: `${exposesOf(definition).join("-changed, ")}-changed: created, updated, deleted`,
        on: perTypeEvents(definition),
      },
    ];
    return (
      <div className="element-tab">
        {contractNotice}
        <fieldset className="consumer-offered">
          <legend className="element-subheading">Offered</legend>
          {offered.map((operation) => (
            <label key={operation.id} className="checkbox consumer-operation">
              <input
                type="checkbox"
                role="switch"
                checked={operation.on}
                disabled={operation.disabled}
                onChange={(event) => {
                  if (operation.id === "xref" && !event.target.checked && xrefRuleCount(definition) > 0)
                    setConfirmXref(true);
                  else void run(toggleOperation(key, definition, operation.id, event.target.checked));
                }}
              />
              <span>
                <strong>{operation.name}</strong> <span className="muted">{operation.about}</span>
              </span>
            </label>
          ))}
          <p className="muted">
            No longer offering an operation needs a higher contract version; offering one more does not.
          </p>
        </fieldset>
        {includeNames(definition).length > 0 && (
          <section aria-labelledby="consumer-include" className="consumer-include">
            <h3 id="consumer-include" className="element-subheading">
              Include
            </h3>
            <p className="muted">
              Written by the engine from the Served column, nothing to edit here. The <code>include</code> parameter
              accepts:
            </p>
            <ul>
              {includeNames(definition).map((name) => (
                <li key={name}>
                  <code>{name}</code>
                </li>
              ))}
            </ul>
          </section>
        )}
        {confirmXref && (
          <ConfirmDialog
            title="Stop offering XREF?"
            confirmLabel="Stop offering XREF"
            onCancel={() => setConfirmXref(false)}
            onConfirm={() => {
              setConfirmXref(false);
              void run(toggleOperation(key, definition, "xref", false));
            }}
          >
            <p>
              Its {xrefRuleCount(definition)} match rules go with it
              {offers(definition, "resolve") ? ", and Resolve stops too, since it answers through XREF" : ""}. Undo puts
              them back; switching XREF on again starts it with no rules.
            </p>
          </ConfirmDialog>
        )}
        <h3 className="element-subheading">Lists</h3>
        <EditorTable
          editing={editing}
          scope="consumer-lists"
          label={`Lists of ${item.name}`}
          noun={["list", "lists"]}
          rows={lists}
          rowKey={(row) => row.key}
          menu={(row) =>
            itemMenu(pointer("operations", "lists", row.key), `list ${row.key}`, row.index, lists.length, row.value)
          }
          emptyMessage="No lists."
          columns={[
            { key: "key", label: "Key", cell: (row) => <code>{row.key}</code> },
            { key: "of", label: "Of", cell: (row) => typeName(outline, row.of) },
            {
              key: "within",
              label: "Within",
              cell: (row) =>
                row.within ? (
                  <>
                    filter <code>{row.within}</code>
                  </>
                ) : (
                  "—"
                ),
              edit: (row) => ({
                label: "Within the filter",
                value: row.within ?? "",
                options: [{ value: "", label: "None" }, ...filters.map((f) => ({ value: f.name, label: f.name }))],
                operations: (value) => [
                  {
                    kind: "setConsumerApiPart",
                    consumerApi: key,
                    pointer: pointer("operations", "lists", row.key, "within"),
                    value: value ? { filter: value } : null,
                  },
                ],
              }),
            },
            {
              key: "sortBy",
              label: "Sorted by",
              cell: (row) => (row.sortBy ? <code>{row.sortBy}</code> : <span className="muted">name</span>),
              edit: (row) => ({
                label: "Sorted by",
                value: row.sortBy ?? "",
                options: sortOptions(outline, row.of, row.sortBy),
                operations: (value) => [
                  {
                    kind: "setConsumerApiPart",
                    consumerApi: key,
                    pointer: pointer("operations", "lists", row.key, "sortBy"),
                    value: value || null,
                  },
                ],
              }),
            },
          ]}
        />
        <div className="element-tab-actions">
          {add(
            "consumer-add-list",
            <>
              <Icon name="plus" /> Add list
            </>,
          )}
        </div>
        {offers(definition, "xref") && (
          <>
            <h3 className="element-subheading">XREF match rules</h3>
            <EditorTable
              editing={editing}
              scope="consumer-rules"
              label={`XREF match rules of ${item.name}`}
              noun={["rule", "rules"]}
              rows={rules}
              rowKey={(row) => String(row.index)}
              menu={(row) =>
                itemMenu(
                  pointer("operations", "xref", "matchOn", row.index),
                  `the rule on ${row.field}`,
                  row.index,
                  rules.length,
                  row.value,
                )
              }
              emptyMessage="No rules: XREF is offered and finds nothing until a rule is added."
              columns={[
                { key: "field", label: "Field", cell: (row) => <code>{row.field}</code> },
                ...(["exact", "contains"] as const).map((weight) => ({
                  key: weight,
                  label: weight === "exact" ? "Exact" : "Contains",
                  cell: (row: (typeof rules)[number]) => (row[weight] === undefined ? "—" : row[weight]),
                  edit: (row: (typeof rules)[number]) => ({
                    label: `${weight === "exact" ? "Exact" : "Contains"} weight`,
                    value: row[weight] === undefined ? "" : String(row[weight]),
                    optional: true,
                    operations: (value: string) => [
                      {
                        kind: "setConsumerApiPart",
                        consumerApi: key,
                        pointer: pointer("operations", "xref", "matchOn", row.index, weight),
                        value: value ? Number(value) : null,
                      },
                    ],
                  }),
                })),
              ]}
            />
            {through.length > 0 && (
              <EditorTable
                scope="consumer-through"
                label={`Rules matching through a related block in ${item.name}`}
                noun={["rule", "rules"]}
                rows={through}
                rowKey={(row) => String(row.index)}
                menu={(row) =>
                  itemMenu(
                    pointer("operations", "xref", "alsoMatchThrough", row.index),
                    `the match through ${row.related}`,
                    row.index,
                    through.length,
                    row.value,
                  )
                }
                emptyMessage=""
                columns={[
                  { key: "related", label: "Also match through", cell: (row) => <code>{row.related}</code> },
                  { key: "firstOf", label: "First of", cell: (row) => row.firstOf },
                  {
                    key: "prefer",
                    label: "Prefers",
                    cell: (row) =>
                      chooserCell(
                        "consumer-through-prefer",
                        "Preferred types",
                        itemTarget(
                          pointer("operations", "xref", "alsoMatchThrough", row.index),
                          `the match through ${row.related}`,
                          row.index,
                          through.length,
                          row.value,
                        ),
                        row.preferTypes.length ? row.preferTypes.map((t) => typeName(outline, t)).join(", ") : "—",
                      ),
                  },
                ]}
              />
            )}
            <div className="element-tab-actions">
              {add(
                "consumer-add-rule",
                <>
                  <Icon name="plus" /> Add XREF rule
                </>,
              )}
              {add("consumer-add-through", "Add a match through a related block…")}
            </div>
          </>
        )}
        <h3 className="element-subheading">Custom events</h3>
        <EditorTable
          scope="consumer-events"
          label={`Custom events of ${item.name}`}
          noun={["event", "events"]}
          rows={events}
          rowKey={(row) => String(row.index)}
          menu={(row) =>
            itemMenu(
              pointer("operations", "events", "custom", row.index),
              `event ${row.key}`,
              row.index,
              events.length,
              row.value,
            )
          }
          emptyMessage="No custom events."
          columns={[
            { key: "key", label: "Key", cell: (row) => <code>{row.key}</code> },
            {
              key: "types",
              label: "Types",
              cell: (row) => row.objectTypes.map((t) => typeName(outline, t)).join(", "),
            },
            { key: "changes", label: "Changes", cell: (row) => row.changes.join(", ") },
            { key: "watch", label: "Watches", cell: (row) => (row.watch.length ? row.watch.join(", ") : "any change") },
          ]}
        />
        <div className="element-tab-actions">
          {add(
            "consumer-add-event",
            <>
              <Icon name="plus" /> Add custom event
            </>,
          )}
        </div>
      </div>
    );
  };

  const filtersTab = () => {
    const filters = filtersOf(definition, outline);
    return (
      <div className="element-tab">
        {contractNotice}
        <EditorTable
          editing={editing}
          scope="consumer-filters"
          label={`Filters of ${item.name}`}
          noun={["filter", "filters"]}
          rows={filters}
          rowKey={(row) => row.name}
          menu={(row) =>
            itemMenu(pointer("filters", row.name), `filter ${row.name}`, row.index, filters.length, row.value)
          }
          emptyMessage="No filters."
          columns={[
            { key: "name", label: "Name", cell: (row) => <code>{row.name}</code> },
            { key: "verb", label: "Verb", cell: (row) => FILTER_VERBS.find((v) => v.value === row.verb)?.label ?? "—" },
            { key: "reads", label: "What it reads", cell: (row) => row.reads },
            {
              key: "matchOn",
              label: "Matches on",
              cell: (row) =>
                row.verb === "byType"
                  ? "—"
                  : chooserCell(
                      "consumer-filter-match",
                      "Matches on",
                      itemTarget(
                        pointer("filters", row.name),
                        `filter ${row.name}`,
                        row.index,
                        filters.length,
                        row.value,
                      ),
                      row.matchOn.length ? (
                        <code>{row.matchOn.join(", ")}</code>
                      ) : (
                        <span className="muted">the defaults</span>
                      ),
                    ),
            },
            {
              key: "options",
              label: "Options",
              cell: (row) => row.options.map((o) => FILTER_OPTION_LABELS[o]).join(" · ") || "—",
            },
          ]}
        />
        <div className="element-tab-actions">
          {add(
            "consumer-add-filter",
            <>
              <Icon name="plus" /> Add filter
            </>,
          )}
        </div>
        <p className="muted">
          A filter's name is its query parameter: <code>?name=…</code>
        </p>
      </div>
    );
  };

  const documentTab = (document: "schema" | "example") => {
    return (
      <div className="element-tab">
        {contractNotice}
        <ConsumerDocument
          draftId={draftId}
          consumerApi={key}
          document={document}
          version={outline.version}
          valid={read.data.valid}
        />
        {document === "schema" && contract && (
          <section aria-labelledby="consumer-contract" className="consumer-contract">
            <h3 id="consumer-contract" className="element-subheading">
              Against what consumers read now
            </h3>
            {contract.diagnostics.length ? (
              <ul>
                {contract.diagnostics.map((d, index) => (
                  <li key={`${d.path}:${index}`} className={d.severity === "error" ? "consumer-breaking" : undefined}>
                    {d.message}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">Compatible: consumers of version {version} notice nothing they rely on.</p>
            )}
            <p className="muted">
              The whole API, with its operations and parameters, is in the OpenAPI document:{" "}
              <DownloadLink
                href={consumerApiDocumentPath(draftId, key, "openapi")}
                save={() =>
                  downloadFrom(consumerApiDocumentPath(draftId, key, "openapi"), `${key}-v${version}-openapi.json`)
                }
              >
                download the draft's OpenAPI
              </DownloadLink>
              .
            </p>
          </section>
        )}
      </div>
    );
  };

  return (
    <section className="element-panel consumer-api-panel" aria-labelledby="element-title">
      <Header
        tile={
          <span className="consumer-api-tile" aria-hidden="true">
            <Icon name="api" size={20} />
          </span>
        }
        title={item.name}
        outline={outline}
        rename={(name) => run([{ kind: "setConsumerApiPart", consumerApi: key, pointer: "/name", value: name }])}
        mark={item.mark}
        facts={
          <Facts
            label="About this consumer API"
            facts={[
              {
                icon: "link",
                label: <code>{`/api/consumer/${key}/v${version}`}</code>,
                title: "Where consumers read it",
              },
              { icon: "number", label: `Contract version ${version}` },
              contract
                ? contract.classification === "compatible"
                  ? { icon: "check", label: "Compatible with what consumers read" }
                  : { icon: "state-conflict", label: `Needs contract version ${version + 1}` }
                : { icon: "state-conflict", label: "Checked once the draft is valid" },
              isReleased(item.mark)
                ? {
                    icon: "state-conflict",
                    label: "Released: a new key moves its address",
                    title: "Consumers of the old key get 404 once the draft is active (D55)",
                  }
                : { icon: "pencil", label: "Key editable" },
            ]}
          />
        }
      >
        <button type="button" className="secondary" onClick={() => showTab("schema")}>
          <Icon name="document" /> Schema
        </button>
        <button type="button" className="secondary" onClick={() => showTab("example")}>
          <Icon name="document" /> Message example
        </button>
        <OperationsMenu
          label={`Operations for ${item.name}`}
          target={target}
          outline={outline}
          onOperation={onOperation}
          isOpen={menuOpen}
          onOpenChange={onMenuOpenChange}
        />
      </Header>
      {item.description && <p className="element-place">{item.description}</p>}
      <Tabs
        label={`${item.name} definition`}
        selected={tab}
        onChange={showTab}
        tabs={[
          { id: "types", label: "Types and related", content: typesTab() },
          { id: "fields", label: `Fields (${item.counts.fields})`, content: fieldsTab() },
          { id: "operations", label: "Operations", content: operationsTab() },
          { id: "filters", label: `Filters (${item.counts.filters})`, content: filtersTab() },
          { id: "schema", label: "Schema", content: documentTab("schema") },
          { id: "example", label: "Message example", content: documentTab("example") },
        ]}
      />
    </section>
  );
}

/** One of the documents, with Copy and Download, written by the server from the draft (D56). */
function ConsumerDocument({
  draftId,
  consumerApi,
  document,
  version,
  valid,
}: {
  draftId: string;
  consumerApi: string;
  document: Extract<ConsumerApiDocumentKind, "schema" | "example">;
  version: number;
  valid: boolean;
}) {
  const toast = useToast();
  const [text, setText] = useState<{ at: string; body: string }>();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const at = `${document}:${consumerApi}:${version}`;
  useEffect(() => {
    if (!valid) return;
    let cancelled = false;
    api
      .modelDraftConsumerApiDocument(draftId, consumerApi, document)
      .then((body) => {
        if (!cancelled) setText({ at, body: JSON.stringify(body, null, 2) });
      })
      .catch((cause) => {
        if (!cancelled) setError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [draftId, consumerApi, document, valid, at, attempt]);
  const about = DOCUMENTS[document];
  if (!valid)
    return (
      <EmptyState icon={<Icon name="state-conflict" />}>
        The draft has issues, so the {about.title.toLowerCase()} cannot be written. Fix them or undo the last step, and
        it comes back.
      </EmptyState>
    );
  if (error)
    return (
      <InlineError
        message={error}
        onRetry={() => {
          setError("");
          setAttempt((value) => value + 1);
        }}
      />
    );
  return (
    <section className="consumer-document" aria-labelledby={`consumer-${document}`}>
      <div className="consumer-document-head">
        <h3 id={`consumer-${document}`} className="element-subheading">
          {about.title}
        </h3>
        <button
          type="button"
          className="secondary"
          disabled={!text}
          onClick={() =>
            void navigator.clipboard
              .writeText(text?.body ?? "")
              .then(() => toast(`${about.title} copied.`))
              .catch(() => toast("Copying is not available here; select the text instead."))
          }
        >
          <Icon name="copy" /> Copy
        </button>
        <DownloadLink
          className="secondary"
          href={consumerApiDocumentPath(draftId, consumerApi, document)}
          save={() =>
            downloadFrom(consumerApiDocumentPath(draftId, consumerApi, document), `${consumerApi}-${about.file}`)
          }
        >
          <Icon name="download" /> Download {about.file}
        </DownloadLink>
      </div>
      <p className="muted">{about.about}</p>
      {text?.at === at ? (
        <pre className="consumer-document-body" tabIndex={0} aria-label={about.title}>
          {text.body}
        </pre>
      ) : (
        <Skeleton lines={8} label={`Loading the ${about.title.toLowerCase()}`} />
      )}
    </section>
  );
}
