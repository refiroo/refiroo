/**
 * What the side panel's Settings show for each kind of element (0.13 ED): the value as it reads, the
 * control that changes it, and the operation behind it. A single choice is changed in place; several
 * attributes or a period open the operation's dialog (`operations.ts`).
 */

import type {
  ModelDraftOutline,
  OutlineApplication,
  OutlineAttributeType,
  OutlineObjectType,
  OutlineRelationType,
} from "@/types";
import { YES_NO } from "@/features/model-editor/EditableCell";
import type { Setting } from "@/features/model-editor/SettingsTable";
import { attributeTypeOf, relationTypeOf } from "@/features/model-editor/outline";

const attributeName = (outline: ModelDraftOutline, key: string) => attributeTypeOf(outline, key)?.name ?? key;
const names = (values: string[], name: (key: string) => string) =>
  values.length ? values.map(name).join(", ") : "None";

export function typeSettings(outline: ModelDraftOutline, type: OutlineObjectType): Setting[] {
  const target = { on: "objectType" as const, objectType: type.key };
  const period = type.effectivePeriod;
  return [
    {
      key: "display",
      label: "Display attribute",
      hint: "names a record in lists and links",
      value: type.displayAttribute ? attributeName(outline, type.displayAttribute) : "None: the record's name",
      operation: { id: "type-display-attribute", target },
    },
    {
      key: "period",
      label: "Effective period",
      hint: "when a record is in force",
      value: period
        ? `${attributeName(outline, period.startAttributeTypeKey)} to ${attributeName(outline, period.endAttributeTypeKey)}`
        : "None",
      operation: { id: "type-effective-period", target },
    },
    {
      key: "atLeastOne",
      label: "At least one of",
      hint: "attributes of which a record needs one filled",
      value: names(type.atLeastOneOf ?? [], (key) => attributeName(outline, key)),
      operation: { id: "type-at-least-one", target },
    },
    {
      key: "parents",
      label: "Parent relationships",
      hint: "place a record under a parent",
      value: names(type.parentRelationTypeKeys ?? [], (key) => relationTypeOf(outline, key)?.name ?? key),
      operation: { id: "type-parent-relations", target },
    },
  ];
}

export function attributeTypeSettings(attributeType: OutlineAttributeType): Setting[] {
  const target = { on: "attributeType" as const, attributeType: attributeType.key };
  const bound = (value: number | null | undefined) => (value === null || value === undefined ? "None" : String(value));
  const property = (name: string, value: unknown) => [
    { kind: "setAttributeTypeProperty", attributeType: attributeType.key, property: name, value },
  ];
  return [
    ...(["integer", "decimal"].includes(attributeType.valueType ?? "")
      ? [
          {
            key: "minimum",
            label: "Minimum",
            value: bound(attributeType.minimum),
            operation: { id: "attribute-type-limits", target },
          },
          {
            key: "maximum",
            label: "Maximum",
            value: bound(attributeType.maximum),
            operation: { id: "attribute-type-limits", target },
          },
        ]
      : []),
    {
      key: "hidden",
      label: "Hidden",
      hint: "left off record screens and forms",
      value: attributeType.hidden ? "Yes" : "No",
      edit: {
        label: "Hidden",
        value: String(Boolean(attributeType.hidden)),
        options: YES_NO,
        operations: (value) => property("hidden", value === "true" ? true : null),
      },
    },
    {
      key: "helpText",
      label: "Help text",
      hint: "shown under the field",
      value: attributeType.helpText || "None",
      edit: {
        label: "Help text",
        value: attributeType.helpText ?? "",
        optional: true,
        operations: (value) => property("helpText", value || null),
      },
    },
  ];
}

export function relationTypeSettings(relationType: OutlineRelationType): Setting[] {
  return [
    {
      key: "oriented",
      label: "Oriented",
      hint: "deleting a record also deletes the records it owns through required relationships of this type",
      value: relationType.isOriented === false ? "No" : "Yes",
      edit: {
        label: "Oriented",
        value: String(relationType.isOriented !== false),
        options: YES_NO,
        operations: (value) => [
          {
            kind: "setRelationTypeProperty",
            relationType: relationType.key,
            property: "isOriented",
            value: value === "true",
          },
        ],
      },
    },
  ];
}

export function applicationSettings(application: OutlineApplication): Setting[] {
  return [
    {
      key: "defaultView",
      label: "Default view",
      hint: "the view that opens first",
      value:
        application.views.find((view) => view.key === application.defaultView)?.name ??
        application.defaultView ??
        "None",
      edit: {
        label: "Default view",
        value: application.defaultView ?? "",
        options: application.views.map((view) => ({ value: view.key, label: view.name })),
        operations: (value) => [
          { kind: "setApplicationProperty", applicationKey: application.key, property: "defaultView", value },
        ],
      },
    },
  ];
}
