/**
 * The grants a page is about, as a ruled table with "Grant" (0.12 SP1, SP2): a person's (where,
 * role, narrowing, through a group or directly), a group's or client's (where, role or consumer
 * API, narrowing) and a workspace's Access as one line per principal with its roles as chips (AccessList). A
 * grant made to the page's subject is removed here; one reaching it through a group links to the group, and an instance grant on Access to its holder. A stale narrowing is said (D296).
 *
 * On a person's, group's or client's page (0.17 ST1) the grants are grouped by where they apply: a row for every
 * workspace, then one per workspace by name, each holding its roles and consumer APIs as coloured chips (a
 * person's grant through a group says so in its chip and links to the group; only the page's own grants have a
 * trash button, always shown, and removing needs no confirmation), and a "+" opening the holder's access in that
 * place to set. A removal and a saved dialog each say so in a toast with Undo, which makes the change again the
 * other way round.
 */

import { useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { security } from "@/api/securityClient";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { routePath } from "@/routing/routes";
import type { Grant, GrantPage, RouteState, SettingsRoute } from "@/types";
import type { Hue } from "@/model/hues";
import { InlineError } from "@/ui/InlineError";
import { Icon } from "@/ui/Icon";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { Section } from "@/ui/Section";
import { SettingRow, SettingsEmpty, SettingsGroup, SettingsPanel, SettingsTile, LogFoot } from "@/ui/SettingsParts";
import { Skeleton } from "@/ui/Skeleton";
import { useToast } from "@/ui/Toast";
import { AccessList } from "./AccessList";
import { groupByPlace } from "./accessGroups";
import { GrantChip } from "./GrantChip";
import { GrantDialog } from "./GrantDialog";
import { recreation, type GrantChange } from "./grantPlan";
import type { PickedPrincipal } from "./PrincipalPicker";
import { grantHeld, grantWhere } from "./securityText";
import { useSettingsRead } from "@/features/settings/useSystem";

/** Every workspace's label by key, retired ones included, for naming where a grant applies. */
const allWorkspaces = () => api.workspaces({ status: "all", pageSize: 500 });

/** Every workspace's label by key, as the Security pages name workspaces. */
export function useWorkspaceLabels(): ReadonlyMap<string, string> {
  const { data } = useSettingsRead(allWorkspaces);
  return new Map(data?.items.map((workspace) => [workspace.key, workspace.label]));
}

function principalRoute(principal: Grant["principal"]): SettingsRoute {
  if (principal.kind === "user") return { kind: "settings", page: "people", userId: principal.id };
  if (principal.kind === "group") return { kind: "settings", page: "groups", groupId: principal.id };
  return { kind: "settings", page: "clients", clientId: principal.id };
}

export function GrantsSection({
  subject,
  title = "Roles",
  description,
  load,
  deps,
  onNavigate,
  headingLevel = 2,
  className,
  onChanged,
  hue,
}: {
  /** Whose grants these are, or the workspace whose access they are. */
  subject: { principal: PickedPrincipal } | { workspace: { key: string; label: string } };
  title?: string;
  description?: string;
  load: (cursor?: string) => Promise<GrantPage>;
  deps: unknown[];
  onNavigate: (route: RouteState) => void;
  headingLevel?: 2 | 3;
  className?: string;
  /** After a grant is made or removed here, for a page whose other parts name the access. */
  onChanged?: () => void;
  /** The colour of the page's Settings group, for the empty state of a person's, group's or client's roles. */
  hue?: Hue;
}) {
  const feed = useCursorFeed(load, deps);
  const labels = useWorkspaceLabels();
  const [granting, setGranting] = useState(false);
  /** The principal a row's "+" opened the dialog for, and the button to return focus to. */
  const [grantingFor, setGrantingFor] = useState<{
    principal: PickedPrincipal;
    opener: HTMLElement;
    /** A place row's "+": the workspace the grant is made in. */
    place?: { key: string; label: string };
  }>();
  const [removing, setRemoving] = useState<string>();
  const [error, setError] = useState<{ title: string; message: string }>();
  const grantRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();
  const principal = "principal" in subject ? subject.principal : undefined;
  const workspace = "workspace" in subject ? subject.workspace : undefined;

  const place = (grant: Grant) => (grant.scope.instance ? "in every workspace" : `in ${grantWhere(grant, labels)}`);
  /** "client 1 now reads RDM API in default." / "Ana no longer holds Reader in every workspace." */
  const heldSentence = (grant: Grant, now: boolean) =>
    grant.role
      ? `${grant.principal.name} ${now ? "now holds" : "no longer holds"} ${grant.role.name} ${place(grant)}.`
      : `${grant.principal.name} ${now ? "now reads" : "no longer reads"} ${grant.consumerApi?.name ?? grant.consumerApi?.key} ${place(grant)}.`;

  /** A grant this page may remove: made to its subject, or made in its workspace. */
  const removable = (grant: Grant) => (principal ? grant.principal.id === principal.id : !grant.scope.instance);

  /** Takes a change back: deletes what it added and makes again, in the same place, what it removed. */
  async function undo(change: GrantChange) {
    setError(undefined);
    try {
      for (const grant of change.added) await security.deleteGrant(grant.id);
      for (const grant of change.removed) await security.createGrant(recreation(grant));
    } catch (cause) {
      setError({ title: "The change was not undone", message: errorMessage(cause) });
    }
    feed.reload();
    onChanged?.();
  }

  const undoAction = (change: GrantChange) => ({ actions: [{ label: "Undo", onPress: () => void undo(change) }] });

  async function remove(grant: Grant): Promise<boolean> {
    setRemoving(grant.id);
    setError(undefined);
    try {
      await security.deleteGrant(grant.id);
      feed.setItems((items) => items.filter((item) => item.id !== grant.id));
      onChanged?.();
      toast(heldSentence(grant, false), undoAction({ added: [], removed: [grant] }));
      return true;
    } catch (cause) {
      setError({ title: "The grant was not removed", message: errorMessage(cause) });
      return false;
    } finally {
      setRemoving(undefined);
    }
  }

  /** What a saved dialog says: the one grant made or removed, or how many of each. */
  function changeText({ added, removed }: GrantChange) {
    const [first] = added.length ? added : removed;
    if (!first) return "";
    if (added.length + removed.length === 1) return heldSentence(first, Boolean(added.length));
    const count = (items: Grant[], word: string) => (items.length ? [`${items.length} ${word}`] : []);
    return `${first.principal.name}’s access changed: ${[...count(added, "added"), ...count(removed, "removed")].join(", ")}.`;
  }

  function holder(grant: Grant) {
    const route = principalRoute(grant.principal);
    return (
      <RouteLink href={routePath(route)} onNavigate={() => onNavigate(route)}>
        {grant.principal.name}
      </RouteLink>
    );
  }

  const dialog = (granting || grantingFor) && (
    <GrantDialog
      who={grantingFor?.principal ?? principal}
      workspace={workspace ?? grantingFor?.place}
      onClose={() => {
        setGranting(false);
        setGrantingFor(undefined);
        (grantingFor?.opener ?? grantRef.current)?.focus();
      }}
      onChanged={(change) => {
        setGranting(false);
        setGrantingFor(undefined);
        const text = changeText(change);
        if (text) toast(text, undoAction(change));
        feed.reload();
        onChanged?.();
        (grantingFor?.opener ?? grantRef.current)?.focus();
      }}
    />
  );
  const grantButton = (
    <button ref={grantRef} type="button" className="secondary" onClick={() => setGranting(true)}>
      <Icon name="plus" /> Grant
    </button>
  );
  const removeError = error && (
    <Notice tone="error" title={error.title}>
      {error.message}
    </Notice>
  );

  if (!workspace)
    return (
      <SettingsGroup title={title} description={description} action={grantButton} className={className}>
        {removeError}
        {feed.error ? (
          <InlineError message={feed.error} onRetry={feed.retry} />
        ) : feed.loading && !feed.items.length ? (
          <Skeleton label="Loading roles" lines={3} />
        ) : !feed.items.length ? (
          <SettingsPanel>
            <SettingsEmpty icon="shield" hue={hue}>
              {principal?.kind === "client"
                ? "No access yet. Grant a role or a consumer API."
                : "No roles yet. Grant one to give access."}
            </SettingsEmpty>
          </SettingsPanel>
        ) : (
          <SettingsPanel label={title}>
            {groupByPlace(feed.items, labels).map((row) => (
              <SettingRow
                key={row.key}
                under
                className="grant-place"
                lead={<SettingsTile icon={row.instance ? "globe" : "workspace"} hue={hue} />}
                name={row.label}
                help={row.instance ? "Applies in every workspace, including new ones." : undefined}
              >
                {(["roles", "apis"] as const).map((kind) => {
                  const grants = row.grants.filter((grant) => (kind === "roles") === Boolean(grant.role));
                  if (!grants.length && !(kind === "roles" && principal)) return null;
                  return (
                    <div key={kind} className="grant-place-kind">
                      {kind === "apis" && <span className="grant-place-label">Consumer APIs</span>}
                      <ul
                        className="access-chips"
                        aria-label={`${kind === "roles" ? "Roles" : "Consumer APIs"} in ${row.label}`}
                      >
                        {grants.map((grant) => {
                          const own = principal ? grant.principal.id === principal.id : true;
                          const held = grantHeld(grant);
                          return (
                            <GrantChip
                              key={grant.id}
                              grant={grant}
                              label={grant.role ? undefined : (grant.consumerApi?.name ?? grant.consumerApi?.key)}
                              extra={
                                principal?.kind === "user" &&
                                !own && <small className="grant-via">· through {holder(grant)}</small>
                              }
                              removeLabel={`Remove ${held} ${place(grant)}`}
                              removing={removing === grant.id}
                              onRemove={removable(grant) ? () => void remove(grant) : undefined}
                            />
                          );
                        })}
                        {principal && kind === (row.grants.some((grant) => !grant.role) ? "apis" : "roles") && (
                          <li>
                            <button
                              type="button"
                              className="access-add"
                              aria-label={`Grant ${principal.name} more ${row.instance ? "in every workspace" : `in ${row.label}`}`}
                              onClick={(event) =>
                                setGrantingFor({
                                  principal,
                                  opener: event.currentTarget,
                                  place: row.instance ? undefined : { key: row.key, label: row.label },
                                })
                              }
                            >
                              <Icon name="plus" size={14} />
                            </button>
                          </li>
                        )}
                      </ul>
                    </div>
                  );
                })}
              </SettingRow>
            ))}
          </SettingsPanel>
        )}
        {feed.hasMore && (
          <LogFoot shown={feed.items.length} noun="roles" onMore={feed.loadMore} loading={feed.loading} />
        )}
        {dialog}
      </SettingsGroup>
    );

  return (
    <Section
      title={title}
      description={description}
      headingLevel={headingLevel}
      className={className}
      actions={grantButton}
    >
      {removeError}
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : feed.loading && !feed.items.length ? (
        <p className="admin-hint">Loading roles…</p>
      ) : !feed.items.length ? (
        <p className="admin-hint">No one has a role in this workspace yet.</p>
      ) : (
        <AccessList
          label={title}
          grants={feed.items}
          removing={removing}
          hasMore={feed.hasMore}
          onRemove={remove}
          onAdd={(who, opener) => setGrantingFor({ principal: who, opener })}
          onNavigate={onNavigate}
          focusFallback={() => grantRef.current?.focus()}
        />
      )}
      {feed.hasMore && (
        <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Load more roles
        </button>
      )}
      {dialog}
    </Section>
  );
}
