/**
 * The home page after sign-in (0.12 HM1, D331–D337), on the reworked Account page's pattern: a
 * welcome card beside "Continue where you left off", the workspaces the person may browse as large
 * cards (each on its own model, with its applications and what waits there), and their open change
 * sets across workspaces. Home is outside any workspace, so the top bar shows no applications.
 */

import { useEffect, useState } from "react";
import { HomeSearch } from "@/features/home/HomeSearch";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { TopBar } from "@/app/TopBar";
import { ShellFrame } from "@/app/ShellFrame";
import { useMe } from "@/app/useMe";
import { ChangeTitle } from "@/ui/ChangeTitle";
import { changeWhere, draftStepsTitle, groupDraftSteps, type ChangeItem } from "@/ui/changeText";
import { useHeldAnywhere } from "@/state/permissions";
import { formatServerAgo } from "@/lib/dates";
import { emptyModel } from "@/model/emptyModel";
import { changeReviewFor, missingElement, parseRoute, relocatedPath, routePath } from "@/routing/routes";
import type { Hue } from "@/model/hues";
import type {
  ChangeEntry,
  ChangeEntryKind,
  EngineModel,
  Grant,
  OwnChangeSet,
  OwnWorkspace,
  PublicationRequest,
  RouteState,
} from "@/types";
import { NewFromWorkbookAction } from "@/features/workspaces/NewFromWorkbookAction";
import { HueTile } from "@/ui/HueTile";
import { WorkspaceTile } from "@/ui/WorkspaceTile";
import { Icon, type IconName } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { principalName } from "@/ui/ActorName";
import { RouteLink } from "@/ui/RouteLink";
import { BrandMascot } from "@/ui/ProductMark";
import { Skeleton } from "@/ui/Skeleton";
import { appPath, openApplication, openIn, openWorkspace, workspacePathOf, type Navigate } from "@/state/openWorkspace";
import {
  continueLines,
  forgetContinueAddress,
  readContinueAddress,
  rememberContinueAddress,
  type ContinueAddress,
} from "./continueAddress";
import { greeting, openLabel, ownLabel, quietNote, roleLine, rolePills, roleSummary, summary } from "./homeText";

export function HomePage({ model, onNavigate }: { model: EngineModel; onNavigate: Navigate }) {
  const me = useMe();
  const held = useHeldAnywhere();
  const [workspaces, setWorkspaces] = useState<OwnWorkspace[]>();
  const [grants, setGrants] = useState<Grant[]>([]);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    Promise.resolve()
      .then(() => Promise.all([api.myWorkspaces(), api.myGrants().catch(() => [] as Grant[])]))
      .then(
        ([loaded, mine]) => {
          if (!active) return;
          setWorkspaces(loaded);
          setGrants(mine);
          setError("");
        },
        (cause) => active && setError(errorMessage(cause)),
      );
    return () => {
      active = false;
    };
  }, [attempt]);
  // The top bar outside any workspace: the product and Settings, no applications (as Settings opens
  // for a person with no workspace, Z5).
  const bar = { ...emptyModel(), product: model.product };
  return (
    <ShellFrame
      topBar={
        <TopBar model={bar} onHome={() => undefined} onSelectApplication={() => undefined} onNavigate={onNavigate} />
      }
      main={{ className: "home" }}
    >
      <div className="home-page">
        {error ? (
          <InlineError message={error} onRetry={() => setAttempt((value) => value + 1)} />
        ) : !workspaces || !me ? (
          <Skeleton label="Loading your home page" lines={6} />
        ) : (
          <>
            <div className="home-top">
              <section className="account-panel home-welcome" aria-labelledby="home-title">
                <BrandMascot size={56} />
                <p className="home-eyebrow">Home</p>
                <h1 id="home-title">{greeting(me.name, new Date().getHours())}</h1>
                <p className="home-summary">{summary(workspaces)}</p>
                <HomeSearch workspaces={workspaces} onNavigate={onNavigate} />
                <p className="account-pills">
                  {rolePills(grants, workspaces).map((pill) => (
                    <span key={pill} className="account-pill">
                      {pill}
                    </span>
                  ))}
                </p>
              </section>
              <Continue personId={me.id} workspaces={workspaces} onNavigate={onNavigate} />
            </div>
            {/* What needs the person comes before the workspaces, so it is seen without scrolling (0.17 UX1). */}
            <WaitingApprovals personId={me.id} workspaces={workspaces} onNavigate={onNavigate} />
            <OwnChangeSets workspaces={workspaces} onNavigate={onNavigate} />
            <section className="home-section" aria-labelledby="home-workspaces">
              <div className="home-section-head">
                <h2 id="home-workspaces">Your workspaces</h2>
                <span className="account-muted">
                  {workspaces.length} {workspaces.length === 1 ? "workspace" : "workspaces"}
                </span>
                <NewFromWorkbookAction
                  variant="primary"
                  onNavigate={onNavigate}
                  onOtherWays={() => onNavigate({ kind: "settings", page: "workspaces" })}
                />
              </div>
              <ul className="home-cards">
                {workspaces.map((workspace) => (
                  <WorkspaceCard
                    key={workspace.key}
                    workspace={workspace}
                    role={roleLine(grants, workspace.key)}
                    roleShort={roleSummary(grants, workspace.key)}
                    note={quietNote(held, workspace.key)}
                    onNavigate={onNavigate}
                  />
                ))}
              </ul>
            </section>
            <RecentChanges personId={me.id} workspaces={workspaces} onNavigate={onNavigate} />
          </>
        )}
      </div>
    </ShellFrame>
  );
}

function Continue({
  personId,
  workspaces,
  onNavigate,
}: {
  personId: string;
  workspaces: OwnWorkspace[];
  onNavigate: Navigate;
}) {
  const [address, setAddress] = useState<ContinueAddress | undefined>(() => readContinueAddress(personId));
  // An address the workspace's model no longer has is forgotten, not offered.
  useEffect(() => {
    if (!address) return;
    let active = true;
    api
      .workspaceModel(address.workspaceKey)
      .then((runtime) => api.modelRelease(runtime.releaseId, true))
      .then((release) => {
        const path = new URL(address.path, window.location.origin);
        if (!active || !release.model) return;
        const model = release.model as unknown as EngineModel;
        // A collection a migration moved to another application is offered at its new address.
        const moved = relocatedPath(model, path);
        if (moved) {
          const relocated = { ...address, path: `${moved}${path.search}` };
          rememberContinueAddress(personId, relocated);
          setAddress(relocated);
        } else if (missingElement(model, path)) {
          forgetContinueAddress(personId);
          setAddress(undefined);
        }
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const shown = address && workspaces.some((item) => item.key === address.workspaceKey) ? address : undefined;
  const [recordName, setRecordName] = useState<string>();
  useEffect(() => {
    const record = shown?.record;
    if (!record) return;
    let active = true;
    api
      .object(record.objectTypeKey, record.objectId, shown.workspaceKey, record.changeSetId, record.publicationId)
      .then(
        (item) => active && setRecordName(item.name),
        () => undefined,
      );
    return () => {
      active = false;
    };
  }, [shown]);
  if (!shown) return null;
  const lines = continueLines(shown, recordName);
  return (
    <RouteLink
      className="account-panel home-continue"
      href={shown.path}
      onNavigate={() =>
        openIn(shown.workspaceKey, shown.path, onNavigate, (model) =>
          parseRoute(model, shown.workspaceKey, new URL(shown.path, window.location.origin)),
        )
      }
    >
      <span className="home-continue-icon" aria-hidden="true">
        <Icon name="undo" size={22} />
      </span>
      <span className="home-continue-text">
        <span className="account-muted">Continue where you left off</span>
        <span className="home-continue-title">{lines.title}</span>
        <span className="account-muted">{lines.where}</span>
      </span>
      <Icon name="chevron-right" />
    </RouteLink>
  );
}

function WorkspaceCard({
  workspace,
  role,
  roleShort,
  note,
  onNavigate,
}: {
  workspace: OwnWorkspace;
  role: string;
  /** The same on one line: the first roles and "and n more". */
  roleShort: string;
  note: string | undefined;
  onNavigate: Navigate;
}) {
  const first = workspace.applications[0];
  const changeSets = () => {
    if (first) onNavigate({ kind: "changeSets", applicationKey: first.key, workspaceKey: workspace.key });
  };
  const changeSetsPath = first
    ? `/apps/${encodeURIComponent(first.key)}/change-sets?workspaceKey=${encodeURIComponent(workspace.key)}`
    : undefined;
  const open = workspace.openChangeSets;
  const anything = workspace.ownChangeSets > 0 || (open ?? 0) > 0;
  // The workspace itself: its start, the first application's default view (D339).
  const workspacePath = workspacePathOf(workspace.key);
  const openThis = () => openWorkspace(workspace.key, onNavigate);
  return (
    <li className="account-panel home-card">
      <div className="home-card-head">
        {/* The tile opens the workspace too (0.12 HM1a); the name's link is the one keyboard and
            screen reader users meet, so the tile is out of the tab order and hidden from them. */}
        <RouteLink
          className="home-tile-link"
          aria-hidden="true"
          tabIndex={-1}
          href={workspacePath}
          onNavigate={openThis}
        >
          <WorkspaceTile workspaceKey={workspace.key} label={workspace.label} />
        </RouteLink>
        <div className="home-card-title">
          <h3>
            <RouteLink className="home-card-link" href={workspacePath} onNavigate={openThis}>
              {workspace.label}
            </RouteLink>
            {workspace.isDefault && <span className="account-pill">Default</span>}
          </h3>
        </div>
        <FollowToggle workspace={workspace} />
      </div>
      <div className="home-card-meta">
        <span className="account-muted home-card-model">
          <Icon name="model" size={14} />
          <span className="home-card-line">
            {workspace.model.releaseName} {workspace.model.releaseVersion}
          </span>
        </span>
        {role && (
          <span className="account-muted home-card-line" title={role}>
            <span aria-hidden="true">{roleShort}</span>
            <span className="visually-hidden">{role}</span>
          </span>
        )}
      </div>
      {workspace.applications.length ? (
        <ul className="home-apps" aria-label={`Applications in ${workspace.label}`}>
          {workspace.applications.map((application, index) => (
            <li key={application.key}>
              <RouteLink
                className="home-app"
                href={appPath(workspace.key, application)}
                onNavigate={() => openApplication(workspace.key, application, onNavigate)}
              >
                <HueTile hue={((index % 8) + 1) as Hue} icon={application.icon ?? undefined} size={20} />
                {application.name}
              </RouteLink>
            </li>
          ))}
        </ul>
      ) : (
        <p className="account-muted home-card-unavailable">This version cannot open the workspace's model.</p>
      )}
      {anything && changeSetsPath ? (
        <div className="home-stats">
          <RouteLink className="home-stat" href={changeSetsPath} onNavigate={() => changeSets()}>
            <strong>{workspace.ownChangeSets}</strong>
            <span>{ownLabel(workspace.ownChangeSets)}</span>
            <Icon name="chevron-right" size={16} />
          </RouteLink>
          {open !== null && (
            <RouteLink className="home-stat" href={changeSetsPath} onNavigate={() => changeSets()}>
              <strong>{open}</strong>
              <span>{openLabel(open)}</span>
              <Icon name="chevron-right" size={16} />
            </RouteLink>
          )}
        </div>
      ) : (
        <div className="home-quiet">
          <span className="account-pill success">
            <span className="account-dot" aria-hidden="true" />
            Nothing open here
          </span>
          {note && <span className="account-muted">{note}</span>}
        </div>
      )}
    </li>
  );
}

/**
 * Follow / Following on a workspace's card (0.16 AO3, AO-D38): a pressed toggle. Following puts a notice
 * in the person's inbox when a change set is published in the workspace; what is mailed is chosen on
 * Settings › Notifications. It acts at once and says so when it fails.
 */
export function FollowToggle({ workspace }: { workspace: OwnWorkspace }) {
  // What the person just did wins over what the page loaded.
  const [chosen, setFollowing] = useState<boolean>();
  const following = chosen ?? workspace.following;
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState("");
  async function toggle() {
    setPending(true);
    setFailure("");
    try {
      if (following) await api.unfollowWorkspace(workspace.key);
      else await api.followWorkspace(workspace.key);
      setFollowing(!following);
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }
  return (
    <div className="home-follow">
      <button
        type="button"
        className="secondary home-follow-button"
        aria-pressed={following}
        disabled={pending}
        onClick={() => void toggle()}
      >
        <Icon name="bell" size={16} />
        {following ? "Following" : "Follow"} <span className="visually-hidden">{workspace.label}</span>
      </button>
      {failure && (
        <span className="account-muted" role="alert">
          {failure}
        </span>
      )}
    </div>
  );
}

/**
 * Requests waiting for the person's approval, across the workspaces where they may approve (0.12 A3,
 * HM1 D335); shown only when there is one. Under a second-person policy their own do not count.
 */
export function WaitingApprovals({
  personId,
  workspaces,
  onNavigate,
}: {
  personId: string;
  workspaces: OwnWorkspace[];
  onNavigate: Navigate;
}) {
  const [items, setItems] = useState<PublicationRequest[]>([]);
  useEffect(() => {
    let active = true;
    Promise.all(
      workspaces.map(async (workspace) => {
        try {
          const permissions = await api.myPermissions(workspace.key);
          if (!permissions.actionGroups.some((group) => group.key === "approve")) return [];
          const [page, policy] = await Promise.all([
            api.publicationRequests(workspace.key, { state: "submitted" }),
            api.approvalPolicy(workspace.key).catch(() => undefined),
          ]);
          return policy?.secondPerson ? page.items.filter((item) => item.submitter?.id !== personId) : page.items;
        } catch {
          return [];
        }
      }),
    ).then((lists) => {
      if (active) setItems(lists.flat().sort((left, right) => right.submittedAt.localeCompare(left.submittedAt)));
    });
    return () => {
      active = false;
    };
  }, [personId, workspaces]);
  if (!items.length) return null;
  const firstApplication = new Map(workspaces.map((item) => [item.key, item.applications[0]?.key]));
  const labels = new Map(workspaces.map((item) => [item.key, item.label]));
  return (
    <section className="home-section" aria-labelledby="home-approvals">
      <div className="home-section-head">
        <h2 id="home-approvals">Waiting for your approval</h2>
        <span className="account-muted">Newest first</span>
      </div>
      <div className="account-panel">
        <ul className="account-list">
          {items.map((item) => {
            const application = firstApplication.get(item.workspaceKey);
            return (
              <li key={item.id} className="account-row">
                <span className="account-row-text">
                  <span className="account-row-title">{item.changeSetName || "Untitled change set"}</span>
                  <span className="account-muted">
                    {labels.get(item.workspaceKey) ?? item.workspaceKey} · Submitted by{" "}
                    {item.submitter ? principalName(item.submitter) : "an unknown person"}
                  </span>
                </span>
                <span className="account-muted home-change-set-when">{formatServerAgo(item.submittedAt)}</span>
                {application && (
                  <button
                    type="button"
                    className="secondary"
                    aria-label={`Review ${item.changeSetName || "Untitled change set"}`}
                    onClick={() => onNavigate(changeReviewFor(application, item.workspaceKey, item.changeSetId))}
                  >
                    Review
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

function OwnChangeSets({ workspaces, onNavigate }: { workspaces: OwnWorkspace[]; onNavigate: Navigate }) {
  const [items, setItems] = useState<OwnChangeSet[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const load = (cursor?: string) =>
    api.myChangeSets(cursor).then(
      (page) => {
        setItems((current) => (cursor ? [...current, ...page.items] : page.items));
        setNext(page.nextCursor);
        setLoaded(true);
        setError("");
      },
      (cause) => setError(errorMessage(cause)),
    );
  useEffect(() => {
    let active = true;
    api.myChangeSets().then(
      (page) => {
        if (!active) return;
        setItems(page.items);
        setNext(page.nextCursor);
        setLoaded(true);
      },
      (cause) => active && setError(errorMessage(cause)),
    );
    return () => {
      active = false;
    };
  }, []);
  if (error) return <InlineError message={error} onRetry={() => void load()} />;
  if (!loaded || !items.length) return null;
  const firstApplication = new Map(workspaces.map((item) => [item.key, item.applications[0]?.key]));
  const models = new Map(
    workspaces.map((item) => [item.key, `${item.model.releaseName} ${item.model.releaseVersion}`]),
  );
  return (
    <section className="home-section" aria-labelledby="home-change-sets">
      <div className="home-section-head">
        <h2 id="home-change-sets">Your change sets</h2>
        <span className="account-muted">Open, newest change first</span>
      </div>
      <div className="account-panel">
        <ul className="account-list">
          {items.map((item) => {
            const application = firstApplication.get(item.workspaceKey);
            const name = item.name || "Untitled change set";
            const where = [item.workspaceLabel, models.get(item.workspaceKey)].filter(Boolean).join(" · ");
            const body = (
              <>
                <span className="home-change-set-tile" aria-hidden="true">
                  <Icon name="pencil" />
                </span>
                <span className="account-row-text">
                  <span className="account-row-title">{name}</span>
                  <span className="account-muted">{where}</span>
                </span>
                <span className="account-pill warning">
                  {item.changeCount} {item.changeCount === 1 ? "change" : "changes"}
                </span>
                <span className="account-muted home-change-set-when">{formatServerAgo(item.updatedAt)}</span>
              </>
            );
            return (
              <li key={item.id} className="account-row home-change-set">
                {application ? (
                  <RouteLink
                    className="home-change-set-link"
                    href={`/apps/${encodeURIComponent(application)}/change-sets/${encodeURIComponent(item.id)}/changes?workspaceKey=${encodeURIComponent(item.workspaceKey)}`}
                    onNavigate={() => onNavigate(changeReviewFor(application, item.workspaceKey, item.id))}
                  >
                    {body}
                  </RouteLink>
                ) : (
                  body
                )}
              </li>
            );
          })}
        </ul>
        {next && (
          <div className="account-footer">
            <button type="button" className="secondary" onClick={() => void load(next)}>
              Load more
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

const KIND_ICONS: Record<ChangeEntryKind, IconName> = {
  record: "document",
  relationship: "link",
  "change-set": "pencil",
  publication: "check",
  model: "model",
};

/**
 * The person's five latest changes across workspaces, shown only when there is one (0.12 Z6, D346),
 * with a way to all of them on their Changes page.
 */
function RecentChanges({
  personId,
  workspaces,
  onNavigate,
}: {
  personId: string;
  workspaces: OwnWorkspace[];
  onNavigate: Navigate;
}) {
  const [items, setItems] = useState<ChangeEntry[]>();
  useEffect(() => {
    let active = true;
    api.changes({ actorId: personId, pageSize: 5 }).then(
      (page) => active && setItems(page.items),
      () => active && setItems([]),
    );
    return () => {
      active = false;
    };
  }, [personId]);
  if (!items?.length) return null;
  const firstApplication = new Map(workspaces.map((item) => [item.key, item.applications[0]?.key]));
  const all: RouteState = { kind: "changes", actorId: personId };
  return (
    <section className="home-section" aria-labelledby="home-recent-changes">
      <div className="home-section-head">
        <h2 id="home-recent-changes">Your recent changes</h2>
        <RouteLink className="home-see-all" href={routePath(all)} onNavigate={() => onNavigate(all)}>
          See all your changes
          <Icon name="chevron-right" size={16} />
        </RouteLink>
      </div>
      <div className="account-panel">
        <ul className="account-list">
          {groupDraftSteps(items).map((item) =>
            item.kind === "entry" ? (
              <ChangeRow
                key={item.entry.id}
                entry={item.entry}
                firstApplication={firstApplication}
                onNavigate={onNavigate}
              />
            ) : (
              <DraftStepsRow key={item.key} item={item} firstApplication={firstApplication} onNavigate={onNavigate} />
            ),
          )}
        </ul>
      </div>
    </section>
  );
}

type ApplicationOf = ReadonlyMap<string, string | undefined>;

function ChangeRow({
  entry,
  firstApplication,
  onNavigate,
}: {
  entry: ChangeEntry;
  firstApplication: ApplicationOf;
  onNavigate: Navigate;
}) {
  return (
    <li className="account-row home-change">
      <span className="home-change-tile" data-kind={entry.kind} aria-hidden="true">
        <Icon name={KIND_ICONS[entry.kind]} />
      </span>
      <span className="account-row-text">
        <span className="account-row-title">
          <ChangeTitle
            entry={entry}
            application={entry.workspace ? firstApplication.get(entry.workspace.key) : undefined}
            onNavigate={onNavigate}
          />
        </span>
        <span className="account-muted">{changeWhere(entry).join(" · ")}</span>
      </span>
      <span className="account-muted home-change-set-when">{formatServerAgo(entry.occurredAt)}</span>
    </li>
  );
}

/** The consecutive steps on one model draft as one expandable line with their count. */
function DraftStepsRow({
  item,
  firstApplication,
  onNavigate,
}: {
  item: Extract<ChangeItem, { kind: "draft" }>;
  firstApplication: ApplicationOf;
  onNavigate: Navigate;
}) {
  const [open, setOpen] = useState(false);
  const newest = item.entries[0];
  return (
    <li className="plain-change-group">
      <button
        type="button"
        className="account-row home-change plain-change-group-line"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <span className="home-change-tile" data-kind="model" aria-hidden="true">
          <Icon name={KIND_ICONS.model} />
        </span>
        <span className="account-row-text">
          <span className="account-row-title">{draftStepsTitle(item.entries.length, item.name)}</span>
          <span className="account-muted">{changeWhere(newest).join(" · ")}</span>
        </span>
        <span className="account-muted home-change-set-when">{formatServerAgo(newest.occurredAt)}</span>
        <span aria-hidden="true">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <ul className="account-list plain-change-group-steps">
          {item.entries.map((entry) => (
            <ChangeRow key={entry.id} entry={entry} firstApplication={firstApplication} onNavigate={onNavigate} />
          ))}
        </ul>
      )}
    </li>
  );
}
