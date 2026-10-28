/**
 * Settings › Account › What you can do (0.12 Z1, restyled from the user's mock-up of 2026-10-28): a
 * card per workspace with the person's roles and, per kind of work, where they may do it. The column
 * labels stand once above the cards on the same grid tracks; they are decorative, because every cell
 * carries its own visually hidden label, so a screen reader hears "Propose changes: ..." in each card.
 * A limited cell is a count that opens a panel inside the card with a line per application. On a
 * phone each card is a `<dl>`.
 */

import { useEffect, useId, useRef, useState, type ReactNode, type RefObject } from "react";
import { workspaceHue } from "@/features/home/homeText";
import { appPath, openApplication, openWorkspace, workspacePathOf, type Navigate } from "@/features/home/openWorkspace";
import { RoleChip } from "@/features/security/RoleChip";
import { grantHeld } from "@/features/security/securityText";
import { useMediaQuery } from "@/lib/hooks/useMediaQuery";
import type { Hue } from "@/model/hues";
import type { Grant } from "@/types";
import { Icon } from "@/ui/Icon";
import { RouteLink } from "@/ui/RouteLink";
import { WorkspaceTile } from "@/ui/WorkspaceTile";

/** What a grant's application link needs: its hue (`model/hues`), where it opens and its record types. */
export interface AppInfo {
  key: string;
  defaultView: string;
  hue?: Hue;
  /** Names of the record types in the application. */
  recordTypes: string[];
}

export type AppsByName = ReadonlyMap<string, AppInfo>;

/** The width at which the table becomes a list. */
const NARROW = "(max-width: 480px)";
/** The width the seven columns need, two counts included; narrower, each workspace stacks. */
const TABLE_WIDTH = 960;

/** Whether the section is too narrow for the table: its own width, not the window's, since the
 * settings navigation takes part of a tablet's or a small laptop's screen. */
function useNarrowSection(): [RefObject<HTMLDivElement | null>, boolean] {
  const ref = useRef<HTMLDivElement>(null);
  const phone = useMediaQuery(NARROW);
  const [width, setWidth] = useState<number>();
  useEffect(() => {
    const element = ref.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return [ref, width === undefined ? phone : width < TABLE_WIDTH];
}

/** Where a role comes from when through groups: "through the group A", "through the groups A and B". */
export function groupSource(names: readonly string[]): string | undefined {
  if (names.length === 0) return undefined;
  const list = names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}` : names[0];
  return `through the group${names.length > 1 ? "s" : ""} ${list}`;
}

export interface RoleEntry {
  /** A grant standing for the role, with the merged narrowing (none when held for the whole place). */
  grant: Grant;
  groupKeys: ReadonlySet<string> | undefined;
  groupNames: string[];
}

/**
 * One entry per role in a place: a role held for the whole place by any grant takes in its narrower
 * grants; otherwise the narrowings of the grants are merged. A consumer API grant stays its own.
 */
export function roleEntries(grants: readonly Grant[], groups: ReadonlyMap<string, ReadonlySet<string>>): RoleEntry[] {
  const entries = new Map<string, Grant[]>();
  for (const grant of grants) {
    const key = grant.role ? `role:${grant.role.key}` : `grant:${grant.id}`;
    entries.set(key, [...(entries.get(key) ?? []), grant]);
  }
  return [...entries.values()].map((held) => {
    const whole = held.some((grant) => grant.scope.applicationNames.length + grant.scope.recordTypeNames.length === 0);
    const unique = (names: string[]) => [...new Set(names)];
    const grant: Grant = {
      ...held[0],
      scope: {
        ...held[0].scope,
        applicationNames: whole ? [] : unique(held.flatMap((item) => item.scope.applicationNames)),
        recordTypeNames: whole ? [] : unique(held.flatMap((item) => item.scope.recordTypeNames)),
      },
    };
    const keys = new Set(held.flatMap((item) => [...(groups.get(item.id) ?? [])]));
    return {
      grant,
      groupKeys: held.some((item) => groups.has(item.id)) ? keys : undefined,
      groupNames: unique(held.filter((item) => item.principal.kind === "group").map((item) => item.principal.name)),
    };
  });
}

/** The action groups that are about data in a workspace; a grant giving one is a data role. */
const DATA_GROUPS = ["browse", "change-sets", "edit-live", "publish", "approve"];

/** What an instance-wide role lets its holder do, by the action group that gives it. */
const INSTANCE_DOING: Record<string, string> = {
  "security-admin": "Manage people, groups, roles and clients",
  "model-authoring": "Write and release models",
  "model-release": "Write and release models",
  "workspace-admin": "Manage workspaces",
  operations: "Run and watch the service",
  "integration-admin": "Manage clients’ integrations and webhooks",
};

/** The groups of the predefined administrative roles, for a grant whose groups were not read. */
const ROLE_GROUPS: Record<string, string[]> = {
  "security-admin": ["security-admin"],
  "model-admin": ["model-authoring", "model-release"],
  "workspace-admin": ["workspace-admin"],
  operator: ["operations"],
  "integration-admin": ["integration-admin"],
};

/** A plain sentence of what an instance-wide role allows; empty when nothing is known of it. */
export function instanceSentence(entry: RoleEntry): string {
  const known = [...(entry.groupKeys ?? [])].filter((key) => key in INSTANCE_DOING);
  const keys = known.length > 0 ? known : (ROLE_GROUPS[entry.grant.role?.key ?? ""] ?? []);
  return [...new Set(keys.map((key) => INSTANCE_DOING[key]))].join(". ");
}

/** The five columns after the roles, by the action group behind each. */
const READ = "browse";
const PROPOSE = "change-sets";
const CHANGE = "edit-live";

interface Reach {
  everything: boolean;
  applications: string[];
  recordTypes: string[];
}

const limited = (entry: RoleEntry) =>
  entry.grant.scope.applicationNames.length + entry.grant.scope.recordTypeNames.length > 0;
const gives = (entry: RoleEntry, group: string) => entry.groupKeys?.has(group) === true;

/** Whether one of the entries is limited and names the application, so it holds all its record types. */
const heldWhole = (entries: readonly RoleEntry[], name: string) =>
  entries.some((entry) => limited(entry) && entry.grant.scope.applicationNames.includes(name));

/**
 * Where the entries giving `group` allow it: the union of their narrowings, or everything. A record type
 * inside an application held whole is not counted apart, as in the panel (`applicationLines`).
 */
function reach(entries: readonly RoleEntry[], group: string, apps: AppsByName | undefined): Reach | undefined {
  const giving = entries.filter((entry) => gives(entry, group));
  if (giving.length === 0) return undefined;
  if (giving.some((entry) => !limited(entry))) return { everything: true, applications: [], recordTypes: [] };
  const unique = (names: string[]) => [...new Set(names)];
  const applications = unique(giving.flatMap((entry) => entry.grant.scope.applicationNames));
  const inWhole = (type: string) =>
    applications.some((name) => heldWhole(giving, name) && apps?.get(name)?.recordTypes.includes(type));
  return {
    everything: false,
    applications,
    recordTypes: unique(giving.flatMap((entry) => entry.grant.scope.recordTypeNames)).filter((type) => !inWhole(type)),
  };
}

export interface PlaceRow {
  key: string;
  /** Null for the row of roles held for every workspace. */
  workspaceKey: string | null;
  title: string;
  entries: RoleEntry[];
}

/** The rows of the table: the roles held for every workspace first, then workspaces by label. */
export function placeRows(
  grants: readonly Grant[],
  labels: ReadonlyMap<string, string>,
  groups: ReadonlyMap<string, ReadonlySet<string>>,
): { rows: PlaceRow[]; instance: RoleEntry[] } {
  const isData = (grant: Grant) => DATA_GROUPS.some((key) => groups.get(grant.id)?.has(key));
  const byPlace = new Map<string, Grant[]>();
  const instance: Grant[] = [];
  for (const grant of grants) {
    if (grant.scope.instance && !isData(grant)) {
      instance.push(grant);
      continue;
    }
    const key = grant.scope.instance ? "" : (grant.scope.workspaceKey ?? "");
    byPlace.set(key, [...(byPlace.get(key) ?? []), grant]);
  }
  const rows = [...byPlace].map(([key, held]) => ({
    key: key || "instance",
    workspaceKey: key || null,
    title: key ? (labels.get(key) ?? key) : "Every workspace",
    entries: roleEntries(held, groups),
  }));
  rows.sort(
    (a, b) => Number(b.workspaceKey === null) - Number(a.workspaceKey === null) || a.title.localeCompare(b.title),
  );
  return { rows, instance: roleEntries(instance, groups) };
}

const plural = (count: number, one: string, many = `${one}s`) => `${count} ${count === 1 ? one : many}`;

interface LinkContext {
  workspaceKey: string | null;
  apps: AppsByName | undefined;
  onNavigate: Navigate | undefined;
}

function ApplicationName({ name, context }: { name: string; context: LinkContext }) {
  const app = context.apps?.get(name);
  const { workspaceKey, onNavigate } = context;
  if (!app || !workspaceKey || !onNavigate)
    return (
      <span className="account-reach-app" data-hue={app?.hue} title={name}>
        {name}
      </span>
    );
  return (
    <RouteLink
      className="account-reach-app"
      data-hue={app.hue}
      title={name}
      href={appPath(workspaceKey, app)}
      onNavigate={() => openApplication(workspaceKey, app, onNavigate)}
    >
      {name}
    </RouteLink>
  );
}

/** Which view of the card's panel is open: the one a count button opened, or none. */
type View = "propose" | "change";

/** What a count button needs: whether its own view is open, the panel's id and the toggle. */
interface Fold {
  open: boolean;
  id: string;
  onToggle: () => void;
}

/** One cell of a card: "Everything", a count that opens the panel, or nothing. */
function ReachCell({ reach: value, fold }: { reach: Reach | undefined; fold: Fold }) {
  if (!value) return <No />;
  if (value.everything) return <>Everything</>;
  // Any limit is a count that opens the panel, so every limited row works the same way and long
  // names are read in full there, not cut short in a cell (the user, 2026-10-28).
  if (value.applications.length + value.recordTypes.length > 0)
    return (
      <button
        type="button"
        className="account-count"
        aria-expanded={fold.open}
        aria-controls={fold.id}
        onClick={fold.onToggle}
      >
        {[
          value.applications.length > 0 && plural(value.applications.length, "application"),
          value.recordTypes.length > 0 && plural(value.recordTypes.length, "record type"),
        ]
          .filter(Boolean)
          .join(", ")}
        <Icon name="chevron-down" size={14} />
      </button>
    );
  return <No />;
}

function Yes() {
  return (
    <>
      <span className="account-yes" aria-hidden="true">
        ✓
      </span>
      <span className="visually-hidden">Yes</span>
    </>
  );
}

function No() {
  return (
    <>
      <span className="account-no" aria-hidden="true">
        –
      </span>
      <span className="visually-hidden">No</span>
    </>
  );
}

const Tick = ({ on }: { on: boolean }) => (on ? <Yes /> : <No />);

/** The role chips of a place, with where a role comes through a group under them. */
function Roles({ entries }: { entries: readonly RoleEntry[] }) {
  return (
    <>
      <span className="account-roles">
        {entries.map((entry) => (
          <RoleChip key={entry.grant.id} grant={entry.grant}>
            <span className="access-chip-name">{grantHeld(entry.grant)}</span>
          </RoleChip>
        ))}
      </span>
      {entries.map((entry) => {
        const source = groupSource(entry.groupNames);
        return (
          source && (
            <span key={entry.grant.id} className="account-roles-source">
              {grantHeld(entry.grant)} {source}
            </span>
          )
        );
      })}
    </>
  );
}

function PlaceName({ row, onNavigate }: { row: PlaceRow; onNavigate: Navigate | undefined }) {
  const key = row.workspaceKey;
  if (!key) return <span className="account-place-name">{row.title}</span>;
  return (
    <span className="account-place-name" data-hue={workspaceHue(key)}>
      <WorkspaceTile workspaceKey={key} label={row.title} size="small" />
      {onNavigate ? (
        <RouteLink href={workspacePathOf(key)} onNavigate={() => openWorkspace(key, onNavigate)}>
          {row.title}
        </RouteLink>
      ) : (
        row.title
      )}
    </span>
  );
}

interface Line {
  name: string;
  /** Null: all of the application's record types. */
  recordTypes: string[] | null;
  from: string[];
}

/**
 * One line per application the entries' limited roles name, or hold record types of. The panel passes
 * only the entries giving the capability it shows, so each line is that capability's.
 */
export function applicationLines(entries: readonly RoleEntry[], apps: AppsByName | undefined): Line[] {
  const names = new Set<string>();
  for (const entry of entries.filter(limited)) {
    for (const name of entry.grant.scope.applicationNames) names.add(name);
    for (const [name, app] of apps ?? [])
      if (app.recordTypes.some((type) => entry.grant.scope.recordTypeNames.includes(type))) names.add(name);
  }
  return [...names].map((name) => {
    const types = apps?.get(name)?.recordTypes ?? [];
    const covering = entries.filter(
      (entry) =>
        !limited(entry) ||
        entry.grant.scope.applicationNames.includes(name) ||
        entry.grant.scope.recordTypeNames.some((type) => types.includes(type)),
    );
    // The record types column says what the limited roles cover; a role for everything adds to From only.
    const whole = heldWhole(covering, name);
    const some = [
      ...new Set(covering.flatMap((entry) => entry.grant.scope.recordTypeNames.filter((type) => types.includes(type)))),
    ];
    return {
      name,
      recordTypes: whole ? null : some,
      from: covering.map((entry) => grantHeld(entry.grant)),
    };
  });
}

function Detail({ lines, context, narrow }: { lines: Line[]; context: LinkContext; narrow: boolean }) {
  const types = (line: Line) => (line.recordTypes ? line.recordTypes.join(", ") : "All record types");
  if (narrow)
    return (
      <ul className="account-detail-list">
        {lines.map((line) => (
          <li key={line.name}>
            <ApplicationName name={line.name} context={context} />
            <span className="account-muted">
              {types(line)} · from {line.from.join(", ")}
            </span>
          </li>
        ))}
      </ul>
    );
  return (
    <table className="account-detail">
      <thead>
        <tr>
          <th scope="col">Application</th>
          <th scope="col">Record types</th>
          <th scope="col">From</th>
        </tr>
      </thead>
      <tbody>
        {lines.map((line) => (
          <tr key={line.name}>
            <th scope="row">
              <ApplicationName name={line.name} context={context} />
            </th>
            <td>{types(line)}</td>
            <td>{line.from.join(", ")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const VIEWS: Record<View, { group: string; heading: string }> = {
  propose: { group: PROPOSE, heading: "What you may propose in" },
  change: { group: CHANGE, heading: "What you may change live in" },
};

/** The panel inside a card: where the person may do the clicked kind of work, a line per application. */
function Cover({
  row,
  view,
  apps,
  onNavigate,
  narrow,
}: {
  row: PlaceRow;
  view: View;
  apps: AppsByName | undefined;
  onNavigate: Navigate | undefined;
  narrow: boolean;
}) {
  const headingId = useId();
  return (
    <div className="account-cover" role="region" aria-labelledby={headingId}>
      <h3 id={headingId}>
        {VIEWS[view].heading} {row.title}
      </h3>
      <Detail
        lines={applicationLines(
          row.entries.filter((entry) => gives(entry, VIEWS[view].group)),
          apps,
        )}
        narrow={narrow}
        context={{ workspaceKey: row.workspaceKey, apps, onNavigate }}
      />
    </div>
  );
}

/** A cell with its visually hidden column label, so each card reads on its own. */
function Cell({ label, tick, children }: { label: string; tick?: boolean; children: ReactNode }) {
  return (
    <div className={tick ? "account-cell account-tick" : "account-cell"}>
      <span className="visually-hidden">{label}: </span>
      {children}
    </div>
  );
}

function PlaceCard({
  row,
  apps,
  onNavigate,
  narrow,
}: {
  row: PlaceRow;
  apps: ReadonlyMap<string, AppsByName>;
  onNavigate: Navigate | undefined;
  narrow: boolean;
}) {
  const [view, setView] = useState<View | null>(null);
  const open = view !== null;
  const id = useId();
  const placeApps = apps.get(row.workspaceKey ?? "");
  const foldOf = (own: View): Fold => ({
    open: view === own,
    id,
    onToggle: () => setView((now) => (now === own ? null : own)),
  });
  const read = row.entries.some((entry) => gives(entry, READ));
  const propose = reach(row.entries, PROPOSE, placeApps);
  const change = reach(row.entries, CHANGE, placeApps);
  const publish = row.entries.some((entry) => gives(entry, "publish"));
  const approve = row.entries.some((entry) => gives(entry, "approve"));
  // The panel exists only when a count can open it.
  const counted = [propose, change].some(
    (value) => value && !value.everything && value.applications.length + value.recordTypes.length > 0,
  );
  const cover = counted && (
    <div id={id} hidden={!open}>
      {view && <Cover row={row} view={view} apps={placeApps} onNavigate={onNavigate} narrow={narrow} />}
    </div>
  );

  const also = [publish && "Publish", approve && "Approve"].filter(Boolean).join(" · ");

  if (narrow) {
    return (
      <section className="account-place" aria-label={row.title} data-open={open || undefined}>
        <div className="account-place-head">
          <PlaceName row={row} onNavigate={onNavigate} />
          <Roles entries={row.entries} />
        </div>
        <dl>
          <dt>Read</dt>
          <dd>{read ? "Everything" : <No />}</dd>
          <dt>Propose</dt>
          <dd>
            <ReachCell reach={propose} fold={foldOf("propose")} />
          </dd>
          <dt>Change live</dt>
          <dd>
            <ReachCell reach={change} fold={foldOf("change")} />
          </dd>
          <dt>Also</dt>
          <dd>{also || <No />}</dd>
        </dl>
        {cover}
      </section>
    );
  }

  return (
    <section className="account-place" aria-label={row.title} data-open={open || undefined}>
      <div className="account-grid-row">
        <Cell label="Workspace">
          <PlaceName row={row} onNavigate={onNavigate} />
        </Cell>
        <Cell label="Your roles">
          <Roles entries={row.entries} />
        </Cell>
        <Cell label="Read" tick>
          <Tick on={read} />
        </Cell>
        <Cell label="Propose changes">
          <ReachCell reach={propose} fold={foldOf("propose")} />
        </Cell>
        <Cell label="Change live">
          <ReachCell reach={change} fold={foldOf("change")} />
        </Cell>
        <Cell label="Publish" tick>
          <Tick on={publish} />
        </Cell>
        <Cell label="Approve" tick>
          <Tick on={approve} />
        </Cell>
      </div>
      {cover}
    </section>
  );
}

/** The cards, with the column labels once above them. */
function PermissionsCards({
  rows,
  apps,
  onNavigate,
  narrow,
}: {
  rows: PlaceRow[];
  apps: ReadonlyMap<string, AppsByName>;
  onNavigate: Navigate | undefined;
  narrow: boolean;
}) {
  return (
    <div className="account-places">
      {!narrow && (
        <div className="account-columns account-grid-row" aria-hidden="true">
          <span>Workspace</span>
          <span>Your roles</span>
          <span className="account-tick">Read</span>
          <span>Propose changes</span>
          <span>Change live</span>
          <span className="account-tick">Publish</span>
          <span className="account-tick">Approve</span>
        </div>
      )}
      {rows.map((row) => (
        <PlaceCard key={row.key} row={row} apps={apps} onNavigate={onNavigate} narrow={narrow} />
      ))}
    </div>
  );
}

/** The roles held across the instance, each with a sentence of what it allows. */
function InstanceRoles({ entries }: { entries: readonly RoleEntry[] }) {
  const id = useId();
  if (entries.length === 0) return null;
  return (
    <section className="account-instance" aria-labelledby={id}>
      <h3 id={id}>Across the instance</h3>
      <ul>
        {entries.map((entry) => (
          <li key={entry.grant.id}>
            <RoleChip grant={entry.grant}>
              <span className="access-chip-name">{grantHeld(entry.grant)}</span>
            </RoleChip>
            <span>{instanceSentence(entry)}</span>
            {groupSource(entry.groupNames) && <span className="account-muted">{groupSource(entry.groupNames)}</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}

/** The body of the section: the cards, the instance roles and the footer. */
export function PermissionsBody({
  grants,
  labels,
  groups,
  apps,
  onNavigate,
}: {
  grants: readonly Grant[];
  labels: ReadonlyMap<string, string>;
  groups: ReadonlyMap<string, ReadonlySet<string>>;
  apps: ReadonlyMap<string, AppsByName>;
  onNavigate: Navigate | undefined;
}): ReactNode {
  const [ref, narrow] = useNarrowSection();
  const { rows, instance } = placeRows(grants, labels, groups);
  return (
    <div className="account-permissions" ref={ref}>
      {rows.length > 0 && <PermissionsCards rows={rows} apps={apps} onNavigate={onNavigate} narrow={narrow} />}
      <InstanceRoles entries={instance} />
      <p className="account-muted account-permissions-footer">
        {grants.length === 0
          ? "You have no roles yet. Ask a security administrator to give you one."
          : "Reading is never limited. A count opens what each of your roles covers in that workspace. A security administrator gives and removes roles."}
      </p>
    </div>
  );
}

/** "N workspaces · M roles" for the section's heading. */
export function permissionsSummary(
  grants: readonly Grant[],
  labels: ReadonlyMap<string, string>,
  groups: ReadonlyMap<string, ReadonlySet<string>>,
) {
  const { rows } = placeRows(grants, labels, groups);
  const workspaces = rows.filter((row) => row.workspaceKey !== null).length;
  return [workspaces > 0 && plural(workspaces, "workspace"), plural(grants.length, "role")].filter(Boolean).join(" · ");
}
