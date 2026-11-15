import { useEffect, useMemo, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { counted } from "@/lib/count";
import { formatServerDate } from "@/lib/dates";
import { ModelSummary } from "@/features/model-admin/ModelSummary";
import {
  parseStructure,
  type Structure,
  type StructureApplication,
  type StructureAttribute,
  type StructureObjectType,
} from "@/features/model-admin/structureParse";
import { applicationHue, objectTypeHue } from "@/model/hues";
import { newestFirst } from "@/model/newestFirst";
import type { ModelReleaseSummary } from "@/types";
import type { EngineModel } from "@/types";
import { ControlPopover } from "@/ui/ControlPopover";
import { Icon } from "@/ui/Icon";
import { RecordChip } from "@/ui/RecordChip";
import { SettingsTable } from "@/ui/SettingsTable";
import { StatusPill } from "@/ui/StatusPill";
import { HueTile } from "@/ui/HueTile";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";

const ATTRIBUTE_PREVIEW = 6;

/** The raw model per release id; a release is immutable, so a read never goes stale. */
const models = new Map<string, Record<string, unknown>>();

/** For tests: forgets the cached models. */
export function clearModelStructureCache() {
  models.clear();
}

type Loaded =
  | { id: string; state: "loading" }
  | { id: string; state: "error"; message: string }
  | { id: string; state: "ready"; model: Record<string, unknown> };

/** The hue helpers read `objectTypes[].key` and `applications[].key`; the structure has both. */
function hueModel(structure: Structure, model: Record<string, unknown>) {
  return {
    objectTypes: structure.objectTypeKeys.map((key) => ({ key })),
    applications: (Array.isArray(model.applications) ? model.applications : []).map((item) => ({
      key: (item as { key?: unknown })?.key,
    })),
  } as unknown as EngineModel;
}

function attributeRules(attribute: StructureAttribute) {
  const rules: string[] = [];
  if (attribute.required) rules.push("required");
  if (attribute.minimum !== undefined || attribute.maximum !== undefined)
    rules.push(`${attribute.minimum ?? "…"} to ${attribute.maximum ?? "…"}`);
  if (attribute.unique) rules.push("unique");
  if (attribute.readOnly) rules.push("read only");
  return rules;
}

function Attributes({ attributes }: { attributes: StructureAttribute[] }) {
  const [all, setAll] = useState(false);
  const shown = all ? attributes : attributes.slice(0, ATTRIBUTE_PREVIEW);
  return (
    <section className="structure-block" aria-label="Attributes">
      <h4>
        Attributes <span className="structure-block-count">{attributes.length}</span>
      </h4>
      {attributes.length === 0 ? (
        <p className="structure-empty">No attributes.</p>
      ) : (
        <SettingsTable label="Attributes" columns={["Attribute", "Type", "Rules"]}>
          {shown.map((attribute) => {
            const rules = attributeRules(attribute);
            return (
              <tr key={attribute.key}>
                <th scope="row">
                  {attribute.name}
                  <code className="structure-key">{attribute.key}</code>
                </th>
                <td data-label="Type">{attribute.valueType}</td>
                <td data-label="Rules">
                  {rules.length === 0 ? (
                    <span className="muted">—</span>
                  ) : (
                    <span className="structure-rules">
                      {rules.map((rule) => (
                        <StatusPill key={rule} tone="neutral" marker={false}>
                          {rule}
                        </StatusPill>
                      ))}
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </SettingsTable>
      )}
      {!all && attributes.length > ATTRIBUTE_PREVIEW && (
        <button type="button" className="link-button" onClick={() => setAll(true)}>
          + {attributes.length - ATTRIBUTE_PREVIEW} more
        </button>
      )}
    </section>
  );
}

function Relations({ type, hues }: { type: StructureObjectType; hues: EngineModel }) {
  return (
    <section className="structure-block" aria-label="Relations">
      <h4>
        Relations <span className="structure-block-count">{type.relations.length}</span>
      </h4>
      {type.relations.length === 0 ? (
        <p className="structure-empty">No allowed relations.</p>
      ) : (
        <SettingsTable label="Relations" columns={["Relation", "Other type", "Reads in reverse"]}>
          {type.relations.map((relation) => (
            <tr key={`${relation.relationTypeKey}:${relation.direction}:${relation.otherTypeKey}`}>
              <th scope="row">
                {relation.name}{" "}
                <span className="muted" aria-label={relation.direction === "out" ? "to" : "from"}>
                  {relation.direction === "out" ? "→" : "←"}
                </span>
              </th>
              <td data-label="Other type">
                <RecordChip hue={objectTypeHue(hues, relation.otherTypeKey)}>{relation.otherTypeName}</RecordChip>
              </td>
              <td data-label="Reads in reverse">{relation.reverseName ?? <span className="muted">—</span>}</td>
            </tr>
          ))}
        </SettingsTable>
      )}
    </section>
  );
}

function TypeRow({ type, hues }: { type: StructureObjectType; hues: EngineModel }) {
  const [open, setOpen] = useState(false);
  return (
    <li className="structure-type">
      <button type="button" className="structure-type-head" aria-expanded={open} onClick={() => setOpen(!open)}>
        <HueTile hue={objectTypeHue(hues, type.key)} icon={type.icon} size={20} />
        <span className="structure-type-name">
          {type.name} <code>{type.key}</code>
        </span>
        <span className="structure-count">
          {counted(type.attributes.length, "attribute")} · {counted(type.relations.length, "relation")}
        </span>
        <Icon name={open ? "chevron-down" : "chevron-right"} size={16} />
      </button>
      {open && (
        <div className="structure-detail">
          <Attributes attributes={type.attributes} />
          <Relations type={type} hues={hues} />
        </div>
      )}
    </li>
  );
}

function ApplicationRow({
  application,
  hues,
  startOpen,
}: {
  application: StructureApplication;
  hues: EngineModel;
  startOpen: boolean;
}) {
  const [open, setOpen] = useState(startOpen);
  return (
    <section className="structure-app">
      <button type="button" className="structure-app-head" aria-expanded={open} onClick={() => setOpen(!open)}>
        <Icon name={open ? "chevron-down" : "chevron-right"} size={16} />
        <HueTile hue={applicationHue(hues, application.key)} icon={application.icon} size={22} />
        <span className="structure-app-name">
          <strong>{application.name}</strong>
          <span>
            {" "}
            · {counted(application.objectTypes.length, "object type")} · {counted(application.viewCount, "view")}
          </span>
        </span>
      </button>
      {open && (
        <ul className="structure-types list-reset">
          {application.objectTypes.map((type) => (
            <TypeRow key={type.key} type={type} hues={hues} />
          ))}
        </ul>
      )}
    </section>
  );
}

/** The Structure tab: one release's applications, object types, attributes and relations, read only. */
export function ModelStructure({ releases }: { releases: ModelReleaseSummary[] }) {
  const ordered = useMemo(() => newestFirst(releases, "installedAt"), [releases]);
  const latestId = ordered[0]?.id;
  const [picked, setPicked] = useState<string>();
  const releaseId = picked && ordered.some((item) => item.id === picked) ? picked : latestId;
  const [loaded, setLoaded] = useState<Loaded>();
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!releaseId) return;
    if (models.has(releaseId)) return;
    let cancelled = false;
    api
      .modelRelease(releaseId, true)
      .then((release) => {
        if (cancelled) return;
        const model = release.model ?? {};
        models.set(releaseId, model);
        setLoaded({ id: releaseId, state: "ready", model });
      })
      .catch((cause: unknown) => {
        if (!cancelled) setLoaded({ id: releaseId, state: "error", message: errorMessage(cause) });
      });
    return () => {
      cancelled = true;
    };
  }, [releaseId, attempt]);

  const release = ordered.find((item) => item.id === releaseId);
  const cached = releaseId ? models.get(releaseId) : undefined;
  const current: Loaded | undefined = cached
    ? { id: release?.id ?? "", state: "ready", model: cached }
    : loaded && loaded.id === releaseId
      ? loaded
      : undefined;
  const structure = current?.state === "ready" ? parseStructure(current.model) : undefined;

  if (!release) return <p className="structure-empty">This model has no releases.</p>;

  return (
    <div className="model-structure">
      <div className="structure-toolbar">
        <span className="structure-picker-label">Release</span>
        {ordered.length > 1 ? (
          <ControlPopover
            label="Release"
            header={false}
            placement="bottom start"
            className="release-popover"
            triggerClassName="secondary toolbar-button release-trigger"
            trigger={
              <>
                <span className="release-trigger-version">{release.version}</span>
                {release.id === latestId && <span className="structure-latest">latest</span>}
                <Icon name="chevron-down" size={14} />
              </>
            }
          >
            {(close) => (
              <div
                role="listbox"
                aria-label="Releases"
                className="release-list"
                onKeyDown={(event) => {
                  if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
                  const rows = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('[role="option"]'));
                  const at = rows.indexOf(document.activeElement as HTMLElement);
                  const next = rows[at + (event.key === "ArrowDown" ? 1 : -1)];
                  event.preventDefault();
                  next?.focus();
                }}
              >
                {ordered.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    role="option"
                    aria-selected={item.id === release.id}
                    className="release-option"
                    autoFocus={item.id === release.id}
                    onClick={() => {
                      setPicked(item.id);
                      close();
                    }}
                  >
                    <span className="release-option-check">
                      {item.id === release.id && <Icon name="check" size={14} />}
                    </span>
                    <span className="release-option-version">{item.version}</span>
                    <span className="release-option-date">{formatServerDate(item.installedAt)}</span>
                    {item.id === latestId && <span className="structure-latest">latest</span>}
                    {item.workspaces.length > 0 && (
                      <span className="structure-latest">Active in {item.workspaces.length}</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </ControlPopover>
        ) : (
          <span className="release-single">
            <span className="release-trigger-version">{release.version}</span>
            {release.id === latestId && <span className="structure-latest">latest</span>}
          </span>
        )}
        <span className="structure-note">Read only. Open a release to compare it or export it.</span>
      </div>
      {(!current || current.state === "loading") && <Skeleton label="Loading the structure" lines={5} />}
      {current?.state === "error" && (
        <InlineError
          message={current.message}
          onRetry={() => {
            setLoaded(undefined);
            setAttempt((value) => value + 1);
          }}
        />
      )}
      {current?.state === "ready" &&
        (structure ? (
          <>
            <ModelSummary model={current.model} />
            <div className="structure-apps">
              {structure.applications.map((application, index) => (
                <ApplicationRow
                  key={`${release.id}:${application.key}`}
                  application={application}
                  hues={hueModel(structure, current.model)}
                  startOpen={index === 0}
                />
              ))}
            </div>
          </>
        ) : (
          <Notice tone="info" title="Structure not available">
            This release uses schema {release.schemaVersion}; its structure can be read as raw JSON on the release page.
          </Notice>
        ))}
    </div>
  );
}
