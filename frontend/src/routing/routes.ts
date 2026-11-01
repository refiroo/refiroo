/**
 * The URL is the route. These translate between `window.location` and `RouteState` in both
 * directions, validating application, view and object-type keys against the active model so a
 * hand-edited or stale URL falls back to a valid route rather than rendering an empty screen.
 */

import type {
  ApplicationDefinition,
  ApplicationRoute,
  ChangeKind,
  EditorSelection,
  EngineModel,
  ChangeEntryKind,
  ChangePeriod,
  ChangesRoute,
  HomeRoute,
  JourneyRef,
  NotificationsRoute,
  MoveAddress,
  MoveChoice,
  RouteState,
  SettingsRoute,
  ViewDefinition,
  ModelTab,
  WorkspaceTab,
} from "@/types";
import { DEFAULT_COLLECTION_QUERY, DEFAULT_WORKSPACE } from "@/model/defaults";
import { applicationFor, objectTypeFor, relationshipFilterFields } from "@/model/lookup";
import { listSortFields } from "@/model/fields";
import { navigationGroupFor } from "@/model/collections";

const MATRIX_STATES = ["one", "several", "inactive", "historyOnly", "none"] as const;
/** The relation matrix shows at most this many named columns at once (D10). */
export const MATRIX_MAX_COLUMNS = 20;

/** A matrix's shown columns and state filter; the state needs named columns, as the API does. */
function matrixQuery(query: URLSearchParams) {
  const columnIds = [...new Set(query.getAll("matrixColumn").filter(Boolean))].slice(0, MATRIX_MAX_COLUMNS);
  const state = MATRIX_STATES.find((value) => value === query.get("matrixState"));
  return {
    ...(columnIds.length ? { matrixColumnIds: columnIds } : {}),
    ...(columnIds.length && state ? { matrixState: state } : {}),
  };
}

function viewDefaults(view: ViewDefinition | undefined) {
  return {
    ...DEFAULT_COLLECTION_QUERY,
    sort: (view?.type === "table" ? view.config.defaultSort : undefined) ?? DEFAULT_COLLECTION_QUERY.sort,
    pageSize: view?.config.pageSize ?? DEFAULT_COLLECTION_QUERY.pageSize,
  };
}

const CHANGE_KINDS: readonly ChangeKind[] = ["added", "changed", "removed"];

/**
 * A change set review from its URL. The type is checked against the model the URL is parsed with;
 * the change set's pinned model may differ, and the screen drops a type that model lacks.
 */
function changeReviewRoute(
  model: EngineModel,
  applicationKey: string,
  workspaceKey: string,
  changeSetId: string,
  query: URLSearchParams,
): Extract<RouteState, { kind: "changeSetChanges" }> {
  const tab = query.get("tab") === "relationships" ? "relationships" : "records";
  const typeKey = query.get("type") ?? undefined;
  const knownType =
    typeKey && (tab === "records" ? model.objectTypes : model.relationTypes).some((type) => type.key === typeKey);
  return {
    kind: "changeSetChanges",
    applicationKey,
    workspaceKey,
    changeSetId,
    tab,
    changeKinds: CHANGE_KINDS.filter((kind) => query.getAll("kind").includes(kind)),
    ...(knownType ? { typeKey } : {}),
    ...(tab === "relationships" && query.get("containment") === "true" ? { containment: true } : {}),
    ...(query.get("anchor") ? { anchor: query.get("anchor")! } : {}),
    ...journeyIn(query),
  };
}

/** A change set review opened on its records, with no filter. */
const JOURNEY_PREFIX = "ai-task:";

/** The journey a URL carries (`journey=ai-task:<id>`), else nothing. */
export function journeyIn(query: URLSearchParams): { journey?: JourneyRef } {
  const value = query.get("journey")?.trim();
  const taskId = value?.startsWith(JOURNEY_PREFIX) ? value.slice(JOURNEY_PREFIX.length) : "";
  return taskId ? { journey: { kind: "aiTask", taskId } } : {};
}

/** The workspace an editor or migration was opened from (`workspace=<key>`, 0.16 WM1). */
function forWorkspaceIn(query: URLSearchParams): { forWorkspace?: string } {
  const value = query.get("workspace")?.trim();
  return value ? { forWorkspace: value } : {};
}

function withForWorkspace(path: string, workspaceKey: string | undefined) {
  if (!workspaceKey) return path;
  return `${path}${path.includes("?") ? "&" : "?"}workspace=${encodeURIComponent(workspaceKey)}`;
}

/** The query parameter for a journey, to add to a path with or without a query. */
function withJourney(path: string, journey: JourneyRef | undefined) {
  if (!journey) return path;
  return `${path}${path.includes("?") ? "&" : "?"}journey=${encodeURIComponent(`${JOURNEY_PREFIX}${journey.taskId}`)}`;
}

export function changeReviewFor(
  applicationKey: string,
  workspaceKey: string,
  changeSetId: string,
): Extract<RouteState, { kind: "changeSetChanges" }> {
  return { kind: "changeSetChanges", applicationKey, workspaceKey, changeSetId, tab: "records", changeKinds: [] };
}

/** The change set a route shows its data in, if any. */
export function routeChangeSetId(route: RouteState) {
  return route.kind === "list" || route.kind === "detail" || route.kind === "group" || route.kind === "changeSetChanges"
    ? route.changeSetId
    : undefined;
}

/** The publication a route shows its data in, if any. */
export function routePublicationId(route: RouteState) {
  return route.kind === "list" || route.kind === "detail" || route.kind === "group" ? route.publicationId : undefined;
}

export function isSettingsRoute(route: RouteState): route is SettingsRoute {
  return route.kind === "settings";
}

/** An application's data in a workspace: neither a settings page, home, someone's changes nor notices. */
export function isApplicationRoute(route: RouteState): route is ApplicationRoute {
  return (
    route.kind !== "settings" && route.kind !== "home" && route.kind !== "changes" && route.kind !== "notifications"
  );
}

export const HOME: HomeRoute = { kind: "home" };
export const NOTIFICATIONS: NotificationsRoute = { kind: "notifications" };

const CHANGE_ENTRY_KINDS: readonly ChangeEntryKind[] = ["record", "relationship", "change-set", "publication", "model"];
const PERIODS: readonly ChangePeriod[] = ["day", "week", "month"];

/** One person's or client's changes from `/changes?actorId=…` (0.12 Z6, D345). */
function changesRoute(parts: string[], query: URLSearchParams): ChangesRoute | undefined {
  const actorId = query.get("actorId")?.trim();
  if (parts.length !== 1 || parts[0] !== "changes" || !actorId) return undefined;
  const what = query.get("kind") as ChangeEntryKind | null;
  const period = query.get("period") as ChangePeriod | null;
  const inWorkspace = query.get("workspace")?.trim();
  return {
    kind: "changes",
    actorId,
    ...(inWorkspace ? { inWorkspace } : {}),
    ...(what && CHANGE_ENTRY_KINDS.includes(what) ? { what } : {}),
    ...(period && PERIODS.includes(period) ? { period } : {}),
  };
}

function changesPath(route: ChangesRoute) {
  const query = new URLSearchParams({ actorId: route.actorId });
  if (route.inWorkspace) query.set("workspace", route.inWorkspace);
  if (route.what) query.set("kind", route.what);
  if (route.period) query.set("period", route.period);
  return `/changes?${query}`;
}

/**
 * A settings page from its path below `/settings`, or from an address the settings area replaced:
 * `/models` (with `releaseId` or `draftId`) and `/workspaces[/{key}]`. The router writes the
 * canonical URL back on first load, so an old link lands on its page without a second entry.
 */
/** The settings pages with no selection of their own; About is the fallback. */
const SINGLE_PAGES = [
  "appearance",
  "account",
  "notifications",
  "deployment",
  "operations",
  "consumer-apis",
  "api-reference",
  "roles",
  "signing-keys",
  "mail",
  "ai",
  "agent-access",
] as const;
const isSinglePage = (page: string): page is (typeof SINGLE_PAGES)[number] =>
  (SINGLE_PAGES as readonly string[]).includes(page);

function settingsRoute(parts: string[], query: URLSearchParams): SettingsRoute | undefined {
  if (parts[0] === "models") {
    const draftId = query.get("draftId")?.trim();
    const releaseId = query.get("releaseId")?.trim();
    if (draftId) return { kind: "settings", page: "model", draftId };
    return releaseId ? { kind: "settings", page: "model", releaseId } : { kind: "settings", page: "model" };
  }
  if (parts[0] === "workspaces")
    return parts[1]
      ? { kind: "settings", page: "workspaces", workspaceKey: parts[1] }
      : { kind: "settings", page: "workspaces" };
  if (parts[0] !== "settings") return undefined;
  const [, page, kind, id] = parts;
  if (isSinglePage(page)) return { kind: "settings", page };
  if (page === "workspaces") {
    if (!kind) return { kind: "settings", page };
    const workspaceTab = WORKSPACE_TABS.find((item) => item === id && item !== "overview");
    return workspaceTab
      ? { kind: "settings", page, workspaceKey: kind, workspaceTab }
      : { kind: "settings", page, workspaceKey: kind };
  }
  if (page === "jobs") return kind ? { kind: "settings", page, jobId: kind } : { kind: "settings", page };
  if (page === "ai-tasks" && kind) return { kind: "settings", page, taskId: kind };
  if (page === "people") return kind ? { kind: "settings", page, userId: kind } : { kind: "settings", page };
  if (page === "groups") return kind ? { kind: "settings", page, groupId: kind } : { kind: "settings", page };
  if (page === "clients") return kind ? { kind: "settings", page, clientId: kind } : { kind: "settings", page };
  if (page === "sign-in") return kind ? { kind: "settings", page, providerKey: kind } : { kind: "settings", page };
  if (page === "moves")
    return kind ? { kind: "settings", page, ...moveAddress(kind, query) } : { kind: "settings", page };
  // Import profiles were "Imports" until 2026-10-14; the old address opens the same page.
  if (page === "import-profiles" || page === "imports")
    return kind
      ? { kind: "settings", page: "import-profiles", profileKey: kind }
      : { kind: "settings", page: "import-profiles" };
  if (page === "webhooks") {
    if (!kind) return { kind: "settings", page };
    if (id !== "deliveries") return { kind: "settings", page, subscriptionId: kind };
    const [deliveryId, eventId] = parts.slice(4);
    return {
      kind: "settings",
      page,
      subscriptionId: kind,
      tab: "deliveries",
      ...(deliveryId ? { deliveryId } : {}),
      ...(deliveryId && eventId ? { eventId } : {}),
    };
  }
  if (page === "model") {
    const from = modelTabIn(query.get("from"));
    if (kind === "releases" && id)
      return { kind: "settings", page, releaseId: id, ...(from ? { modelTab: from } : {}) };
    if (kind === "models" && id) {
      const modelTab = MODEL_TABS.find((item) => item === parts[4] && item !== "overview");
      return { kind: "settings", page, modelKey: id, ...(modelTab ? { modelTab } : {}) };
    }
    if (kind === "migrations" && id)
      return { kind: "settings", page, migrationJobId: id, ...forWorkspaceIn(query), ...journeyIn(query) };
    if (kind === "drafts" && id && parts[4] === "editor") {
      return {
        kind: "settings",
        page,
        draftId: id,
        editor: editorSelection(query),
        ...journeyIn(query),
        ...forWorkspaceIn(query),
      };
    }
    if (kind === "drafts" && id) return { kind: "settings", page, draftId: id, ...(from ? { modelTab: from } : {}) };
    return { kind: "settings", page };
  }
  return { kind: "settings", page: "about" };
}

/** The move editor's address from its query; one naming no workspaces opens Moves (D138). */
function moveAddress(mappingKey: string, query: URLSearchParams): { move?: MoveAddress } {
  const from = query.get("from")?.trim();
  const to = query.get("to")?.trim();
  if (!from || !to) return {};
  const move: MoveAddress = { mappingKey, from, to };
  const jobId = query.get("job")?.trim();
  if (jobId) move.jobId = jobId;
  const selection = parseSelection(query.get("select"));
  if (selection) move.selection = selection;
  if (query.get("mode") === "move") move.mode = "move";
  if (query.get("view") === "report") move.view = "report";
  const reason = query.get("reason")?.trim();
  if (reason) move.reason = reason;
  const row = query.get("row")?.trim();
  if (row) move.row = row;
  return { move };
}

/** What moves, as the address holds it: JSON of the editor's choice; anything else is the default. */
function parseSelection(text: string | null): MoveChoice | undefined {
  if (!text) return undefined;
  try {
    const value = JSON.parse(text) as MoveChoice;
    if (value?.kind === "all") return { kind: "all" };
    if (value?.kind === "subtree" && typeof value.objectId === "string" && typeof value.objectTypeKey === "string")
      return {
        kind: "subtree",
        objectId: value.objectId,
        objectTypeKey: value.objectTypeKey,
        ...(typeof value.name === "string" ? { name: value.name } : {}),
      };
    if (value?.kind === "types" && Array.isArray(value.types))
      return {
        kind: "types",
        types: value.types
          .filter((item) => item && typeof item.objectTypeKey === "string")
          .map((item) => ({
            objectTypeKey: item.objectTypeKey,
            filters: (Array.isArray(item.filters) ? item.filters : []).filter(
              (filter) => typeof filter?.field === "string" && typeof filter.operator === "string",
            ),
          })),
      };
    return undefined;
  } catch {
    return undefined;
  }
}

function movePath(move: MoveAddress) {
  const query = new URLSearchParams({ from: move.from, to: move.to });
  if (move.jobId) query.set("job", move.jobId);
  if (move.selection) query.set("select", JSON.stringify(move.selection));
  if (move.mode === "move") query.set("mode", "move");
  if (move.view) query.set("view", move.view);
  if (move.reason) query.set("reason", move.reason);
  if (move.row) query.set("row", move.row);
  return `/settings/moves/${encodeURIComponent(move.mappingKey)}?${query}`;
}

const EDITOR_ELEMENTS = ["type", "application", "relationType", "attributeType"] as const;
export const MODEL_TABS: readonly ModelTab[] = ["overview", "releases", "drafts", "structure"];
/** The tab Back returns to from an opened release or draft when the address names none. */
const MODEL_BACK_TAB = { releaseId: "releases", draftId: "drafts" } as const;
const modelTabIn = (value: string | null | undefined) => MODEL_TABS.find((item) => item === value);
export const WORKSPACE_TABS: readonly WorkspaceTab[] = ["overview", "access", "approval", "activity"];
const CONSUMER_API_TABS = ["types", "fields", "operations", "filters", "schema", "example"] as const;

function editorSelection(query: URLSearchParams): EditorSelection {
  const show = query.get("show");
  const key = query.get("key")?.trim();
  if (show === "matrix") return { show };
  const sheet = query.get("sheet");
  if (show === "column" && key && sheet) return { show, sheet, key };
  const block = Number(query.get("block"));
  if (show === "list" && sheet && Number.isInteger(block) && block >= 0 && query.get("block"))
    return { show, sheet, block };
  if (show === "consumerApi" && key) {
    const tab = CONSUMER_API_TABS.find((item) => item === query.get("tab"));
    return tab ? { show, key, tab } : { show, key };
  }
  const element = EDITOR_ELEMENTS.find((item) => item === show);
  if (!element || !key) return {};
  const mode = EDITOR_MODES.find((item) => item === query.get("mode"));
  return element === "type" && mode ? { show: element, key, mode } : { show: element, key };
}

const EDITOR_MODES = ["preview", "layout"] as const;

/** The model editor's address for a draft, with what its centre shows. */
function editorPath(draftId: string, editor: EditorSelection): string {
  const base = `/settings/model/drafts/${encodeURIComponent(draftId)}/editor`;
  const { show } = editor;
  if (!show) return base;
  if (show === "matrix") return `${base}?show=matrix`;
  if (show === "column")
    return `${base}?show=column&sheet=${encodeURIComponent(editor.sheet)}&key=${encodeURIComponent(editor.key)}`;
  if (show === "list") return `${base}?show=list&sheet=${encodeURIComponent(editor.sheet)}&block=${editor.block}`;
  const mode =
    editor.show === "type" && editor.mode
      ? `&mode=${editor.mode}`
      : editor.show === "consumerApi" && editor.tab
        ? `&tab=${editor.tab}`
        : "";
  return `${base}?show=${show}&key=${encodeURIComponent(editor.key)}${mode}`;
}

function settingsPath(route: SettingsRoute) {
  if (route.page === "workspaces" && route.workspaceKey) {
    const base = `/settings/workspaces/${encodeURIComponent(route.workspaceKey)}`;
    return route.workspaceTab && route.workspaceTab !== "overview" ? `${base}/${route.workspaceTab}` : base;
  }
  if (route.page === "webhooks" && route.subscriptionId) {
    const base = `/settings/webhooks/${encodeURIComponent(route.subscriptionId)}`;
    if (route.tab !== "deliveries") return base;
    if (!route.deliveryId) return `${base}/deliveries`;
    const opened = `${base}/deliveries/${encodeURIComponent(route.deliveryId)}`;
    return route.eventId ? `${opened}/${encodeURIComponent(route.eventId)}` : opened;
  }
  if (route.page === "jobs" && route.jobId) return `/settings/jobs/${encodeURIComponent(route.jobId)}`;
  if (route.page === "ai-tasks" && route.taskId) return `/settings/ai-tasks/${encodeURIComponent(route.taskId)}`;
  if (route.page === "people" && route.userId) return `/settings/people/${encodeURIComponent(route.userId)}`;
  if (route.page === "groups" && route.groupId) return `/settings/groups/${encodeURIComponent(route.groupId)}`;
  if (route.page === "clients" && route.clientId) return `/settings/clients/${encodeURIComponent(route.clientId)}`;
  if (route.page === "sign-in" && route.providerKey)
    return `/settings/sign-in/${encodeURIComponent(route.providerKey)}`;
  if (route.page === "moves" && route.move) return movePath(route.move);
  if (route.page === "import-profiles" && route.profileKey)
    return `/settings/import-profiles/${encodeURIComponent(route.profileKey)}`;
  if (route.page === "model" && route.draftId && route.editor)
    return withForWorkspace(withJourney(editorPath(route.draftId, route.editor), route.journey), route.forWorkspace);
  // An opened release or draft keeps the tab it was opened from, unless that is where Back goes anyway.
  const modelFrom = (back: ModelTab) =>
    route.page === "model" && route.modelTab && route.modelTab !== back ? `?from=${route.modelTab}` : "";
  if (route.page === "model" && route.draftId)
    return `/settings/model/drafts/${encodeURIComponent(route.draftId)}${modelFrom(MODEL_BACK_TAB.draftId)}`;
  if (route.page === "model" && route.releaseId)
    return `/settings/model/releases/${encodeURIComponent(route.releaseId)}${modelFrom(MODEL_BACK_TAB.releaseId)}`;
  if (route.page === "model" && route.modelKey) {
    const base = `/settings/model/models/${encodeURIComponent(route.modelKey)}`;
    return route.modelTab && route.modelTab !== "overview" ? `${base}/${route.modelTab}` : base;
  }
  if (route.page === "model" && route.migrationJobId)
    return withJourney(
      withForWorkspace(`/settings/model/migrations/${encodeURIComponent(route.migrationJobId)}`, route.forWorkspace),
      route.journey,
    );
  return `/settings/${route.page}`;
}

export function defaultRoute(
  model: EngineModel,
  workspaceKey = DEFAULT_WORKSPACE,
): Extract<RouteState, { kind: "list" }> {
  const application = model.applications[0];
  return {
    kind: "list",
    applicationKey: application?.key ?? "",
    viewKey: application?.defaultView ?? "",
    workspaceKey,
    ...viewDefaults(application?.views.find((view) => view.key === application.defaultView)),
  };
}

export function parseRoute(
  model: EngineModel,
  defaultWorkspaceKey = DEFAULT_WORKSPACE,
  location: Pick<Location, "pathname" | "search"> = window.location,
): RouteState {
  const parts = location.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  const query = new URLSearchParams(location.search);
  // The bare address is home (0.12 HM1, D331); naming a workspace still opens it.
  if (!parts.length && !query.get("workspaceKey")?.trim()) return HOME;
  const changes = changesRoute(parts, query);
  if (changes) return changes;
  if (parts.length === 1 && parts[0] === "notifications") return NOTIFICATIONS;
  const workspaceKey = query.get("workspaceKey")?.trim() || defaultWorkspaceKey;
  const changeSetId = query.get("changeSetId")?.trim() || undefined;
  const publicationId = changeSetId ? undefined : query.get("publicationId")?.trim() || undefined;
  if (
    parts[0] === "apps" &&
    parts[2] === "change-sets" &&
    parts[3] &&
    parts[4] === "changes" &&
    applicationFor(model, parts[1])
  )
    return changeReviewRoute(model, parts[1], workspaceKey, parts[3], query);
  if (parts[0] === "apps" && parts[2] === "change-sets" && applicationFor(model, parts[1]))
    return { kind: "changeSets", applicationKey: parts[1], workspaceKey };
  if (parts[0] === "apps" && parts[2] === "publications" && applicationFor(model, parts[1]))
    return { kind: "publications", applicationKey: parts[1], workspaceKey };
  if (
    parts[0] === "apps" &&
    parts[2] === "groups" &&
    parts[3] &&
    navigationGroupFor(applicationFor(model, parts[1]), parts[3])
  )
    return {
      kind: "group",
      applicationKey: parts[1],
      groupKey: parts[3],
      workspaceKey,
      ...(changeSetId ? { changeSetId } : {}),
      ...(publicationId ? { publicationId } : {}),
    };
  const settings = settingsRoute(parts, query);
  if (settings) return settings;
  if (parts[0] === "apps" && parts[2] === "views" && parts[3]) {
    const application = applicationFor(model, parts[1]);
    const view = application?.views.find((view) => view.key === parts[3]);
    if (view) {
      const candidateSort = query.get("sort");
      const requestedPageSize = Number(query.get("pageSize"));
      const tableConfig = view.type === "table" ? view.config : undefined;
      // Every column sorts (S4R3 revision), plus the view's further declared sort fields.
      const objectType =
        view.type === "table" && view.objectTypeKey ? objectTypeFor(model, view.objectTypeKey) : undefined;
      const allowedSorts = new Set(
        (objectType && tableConfig
          ? listSortFields(model, [objectType], tableConfig.columns, tableConfig.sortFields, true)
          : []
        ).flatMap((field) => [field, `-${field}`]),
      );
      // A relationship of the listed type filters whether or not the view declares it (0.16 AG4).
      const relationships = new Set(
        view.type === "table" && view.objectTypeKey ? relationshipFilterFields(model, view.objectTypeKey) : [],
      );
      const filters = Array.from(query.entries())
        .filter(([key]) => key.startsWith("filter."))
        .flatMap(([key, value]) => {
          const separator = key.lastIndexOf(".");
          const field = key.slice("filter.".length, separator);
          const operator = key.slice(separator + 1);
          // A live list also filters by the two stamps without declaring them (0.16 AG4); a change set or
          // publication records none.
          const stamp = !changeSetId && !publicationId && ["createdAt", "updatedAt"].includes(field);
          return field &&
            operator &&
            (stamp || relationships.has(field) || (tableConfig?.filterFields ?? []).includes(field))
            ? [{ field, operator, value }]
            : [];
        });
      return {
        kind: "list",
        applicationKey: parts[1],
        viewKey: parts[3],
        workspaceKey,
        ...(changeSetId ? { changeSetId } : {}),
        ...(publicationId ? { publicationId } : {}),
        search: query.get("search") ?? "",
        sort:
          candidateSort && allowedSorts.has(candidateSort)
            ? candidateSort
            : (tableConfig?.defaultSort ?? DEFAULT_COLLECTION_QUERY.sort),
        pageSize:
          Number.isInteger(requestedPageSize) && requestedPageSize >= 1 && requestedPageSize <= 100
            ? requestedPageSize
            : view.config.pageSize,
        filters,
        ...(query.get("parentObjectId") && query.get("parentObjectTypeKey")
          ? {
              parentObjectId: query.get("parentObjectId")!,
              parentObjectTypeKey: query.get("parentObjectTypeKey")!,
            }
          : {}),
        ...(view.type === "mappingGrid" && ["mapped", "unmapped", "ambiguous"].includes(query.get("mappingState") ?? "")
          ? { mappingState: query.get("mappingState") as "mapped" | "unmapped" | "ambiguous" }
          : {}),
        ...(view.type === "mappingGrid" && query.get("proposed") === "true" ? { mappingProposed: true } : {}),
        ...(view.type === "relationMatrix" ? matrixQuery(query) : {}),
        ...(query.get("anchor") ? { anchor: query.get("anchor")! } : {}),
      };
    }
  }
  if (parts[0] === "apps" && parts[2] === "objects" && parts[3] && parts[4]) {
    const application = applicationFor(model, parts[1]);
    if (application?.objectTypeKeys.includes(parts[3])) {
      return {
        kind: "detail",
        applicationKey: parts[1],
        objectTypeKey: parts[3],
        objectId: parts[4],
        workspaceKey,
        ...(changeSetId ? { changeSetId } : {}),
        ...(publicationId ? { publicationId } : {}),
      };
    }
  }
  return { ...defaultRoute(model, defaultWorkspaceKey), workspaceKey };
}

/** What an application address names that a model lacks (0.11 M5, D48). */
export type MissingElement =
  | { kind: "application"; applicationKey: string }
  | { kind: "view"; applicationKey: string; key: string }
  | { kind: "objectType"; applicationKey: string; key: string }
  | { kind: "group"; applicationKey: string; key: string };

/**
 * The element of an application address the model has no place for: an application, a collection
 * (view), a kind of record or a navigation group. Undefined when the model has it, or when the
 * address is not an application page. `parseRoute` falls back to the default route for these; the
 * shell says what was asked for instead of opening that route silently.
 */
export function missingElement(
  model: EngineModel,
  location: Pick<Location, "pathname"> = window.location,
): MissingElement | undefined {
  const parts = location.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  if (parts[0] !== "apps" || !parts[1]) return undefined;
  const application = applicationFor(model, parts[1]);
  if (!application) return { kind: "application", applicationKey: parts[1] };
  if (parts[2] === "views" && parts[3] && !application.views.some((view) => view.key === parts[3]))
    return { kind: "view", applicationKey: parts[1], key: parts[3] };
  if (parts[2] === "objects" && parts[3] && !application.objectTypeKeys.includes(parts[3]))
    return { kind: "objectType", applicationKey: parts[1], key: parts[3] };
  if (parts[2] === "groups" && parts[3] && !navigationGroupFor(application, parts[3]))
    return { kind: "group", applicationKey: parts[1], key: parts[3] };
  return undefined;
}

/** The workspace an address names, or `fallback` when it names none. */
export function addressWorkspaceKey(fallback: string, location: Pick<Location, "search"> = window.location) {
  return new URLSearchParams(location.search).get("workspaceKey")?.trim() || fallback;
}

export function routePath(route: RouteState) {
  if (route.kind === "home") return "/";
  if (route.kind === "changes") return changesPath(route);
  if (route.kind === "notifications") return "/notifications";
  if (route.kind === "settings") return settingsPath(route);
  const app = encodeURIComponent(route.applicationKey);
  const query = new URLSearchParams({ workspaceKey: route.workspaceKey });
  if (route.kind === "changeSets") return `/apps/${app}/change-sets?${query}`;
  if (route.kind === "changeSetChanges") {
    if (route.tab !== "records") query.set("tab", route.tab);
    route.changeKinds.forEach((kind) => query.append("kind", kind));
    if (route.typeKey) query.set("type", route.typeKey);
    if (route.containment) query.set("containment", "true");
    if (route.anchor) query.set("anchor", route.anchor);
    return withJourney(
      `/apps/${app}/change-sets/${encodeURIComponent(route.changeSetId)}/changes?${query}`,
      route.journey,
    );
  }
  if (route.kind === "publications") return `/apps/${app}/publications?${query}`;
  if (route.changeSetId) query.set("changeSetId", route.changeSetId);
  if (route.publicationId) query.set("publicationId", route.publicationId);
  if (route.kind === "group") return `/apps/${app}/groups/${encodeURIComponent(route.groupKey)}?${query}`;
  if (route.kind === "list") {
    if (route.search) query.set("search", route.search);
    route.filters.forEach(({ field, operator, value }) => query.append(`filter.${field}.${operator}`, value));
    query.set("sort", route.sort);
    query.set("pageSize", String(route.pageSize));
    if (route.parentObjectId && route.parentObjectTypeKey) {
      query.set("parentObjectId", route.parentObjectId);
      query.set("parentObjectTypeKey", route.parentObjectTypeKey);
    }
    if (route.mappingState) query.set("mappingState", route.mappingState);
    if (route.mappingProposed) query.set("proposed", "true");
    route.matrixColumnIds?.forEach((id) => query.append("matrixColumn", id));
    if (route.matrixState && route.matrixColumnIds?.length) query.set("matrixState", route.matrixState);
    if (route.anchor) query.set("anchor", route.anchor);
    return `/apps/${app}/views/${encodeURIComponent(route.viewKey)}?${query}`;
  }
  return `/apps/${app}/objects/${encodeURIComponent(route.objectTypeKey)}/${encodeURIComponent(route.objectId)}?${query}`;
}

export function viewRoute(
  application: ApplicationDefinition,
  viewKey: string,
  workspaceKey = DEFAULT_WORKSPACE,
): Extract<RouteState, { kind: "list" }> {
  const view = application.views.find((item) => item.key === viewKey);
  return { kind: "list", applicationKey: application.key, viewKey, workspaceKey, ...viewDefaults(view) };
}
