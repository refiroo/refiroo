/**
 * The grants a page is about, as a ruled table with "Grant a role" (0.12 SP1): a person's (where,
 * role, narrowing, through a group or directly), a group's (where, role, narrowing) and a
 * workspace's Access (who, kind, role, narrowing, from this workspace or the whole instance). A
 * grant made to the page's subject is removed here; one reaching it through a group links to the
 * group, and an instance grant on Access to its holder. A stale narrowing is said (D296).
 */

import { useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { security } from "@/api/securityClient";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { routePath } from "@/routing/routes";
import type { Grant, GrantPage, RouteState, SettingsRoute } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { Icon } from "@/ui/Icon";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { Section } from "@/ui/Section";
import { SettingsTable } from "@/ui/SettingsTable";
import { useToast } from "@/ui/Toast";
import { GrantDialog } from "./GrantDialog";
import type { PickedPrincipal } from "./PrincipalPicker";
import { grantNarrowing, grantWhere, staleNote } from "./securityText";
import { useSettingsRead } from "@/features/settings/useSystem";

const KIND: Record<Grant["principal"]["kind"], string> = { user: "Person", group: "Group", client: "Client" };

/** Every workspace's label by key, retired ones included, for naming where a grant applies. */
const allWorkspaces = () => api.workspaces({ status: "all", pageSize: 500 });

function principalRoute(principal: Grant["principal"]): SettingsRoute | undefined {
  if (principal.kind === "user") return { kind: "settings", page: "people", userId: principal.id };
  if (principal.kind === "group") return { kind: "settings", page: "groups", groupId: principal.id };
  return undefined;
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
}) {
  const feed = useCursorFeed(load, deps);
  const { data: workspacePage } = useSettingsRead(allWorkspaces);
  const labels = new Map(workspacePage?.items.map((workspace) => [workspace.key, workspace.label]));
  const [granting, setGranting] = useState(false);
  const [removing, setRemoving] = useState<string>();
  const [error, setError] = useState("");
  const grantRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();
  const principal = "principal" in subject ? subject.principal : undefined;
  const workspace = "workspace" in subject ? subject.workspace : undefined;

  const place = (grant: Grant) => (grant.scope.instance ? "in every workspace" : `in ${grantWhere(grant, labels)}`);

  /** A grant this page may remove: made to its subject, or made in its workspace. */
  const removable = (grant: Grant) => (principal ? grant.principal.id === principal.id : !grant.scope.instance);

  async function remove(grant: Grant) {
    setRemoving(grant.id);
    setError("");
    try {
      await security.deleteGrant(grant.id);
      feed.setItems((items) => items.filter((item) => item.id !== grant.id));
      toast(`${grant.principal.name} no longer holds ${grant.role.name} ${place(grant)}.`);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setRemoving(undefined);
    }
  }

  function holder(grant: Grant) {
    const route = principalRoute(grant.principal);
    return route ? (
      <RouteLink href={routePath(route)} onNavigate={() => onNavigate(route)}>
        {grant.principal.name}
      </RouteLink>
    ) : (
      grant.principal.name
    );
  }

  const columns = workspace
    ? ["Who", "Kind", "Role", "Narrowed to (writes)", "From", { hidden: "Actions" }]
    : principal?.kind === "user"
      ? ["Where", "Role", "Narrowed to (writes)", "Through", { hidden: "Actions" }]
      : ["Where", "Role", "Narrowed to (writes)", { hidden: "Actions" }];

  return (
    <Section
      title={title}
      description={description}
      headingLevel={headingLevel}
      className={className}
      actions={
        <button ref={grantRef} type="button" className="secondary" onClick={() => setGranting(true)}>
          <Icon name="plus" /> Grant a role
        </button>
      }
    >
      {error && (
        <Notice tone="error" title="The grant was not removed">
          {error}
        </Notice>
      )}
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : feed.loading && !feed.items.length ? (
        <p className="admin-hint">Loading roles…</p>
      ) : !feed.items.length ? (
        <p className="admin-hint">
          {workspace ? "No one has a role in this workspace yet." : "No roles yet. Grant one to give access."}
        </p>
      ) : (
        <SettingsTable label={title} columns={columns}>
          {feed.items.map((grant) => {
            const stale = staleNote(grant);
            const narrowed = (
              <td data-label="Narrowed to (writes)">
                {grantNarrowing(grant)}
                {stale && <small className="grant-stale">{stale}</small>}
              </td>
            );
            const action = (
              <td className="grant-action">
                {removable(grant) ? (
                  <button
                    type="button"
                    className="ghost"
                    disabled={removing === grant.id}
                    aria-label={`Remove ${grant.role.name} ${workspace ? `from ${grant.principal.name}` : place(grant)}`}
                    onClick={() => void remove(grant)}
                  >
                    Remove
                  </button>
                ) : null}
              </td>
            );
            return workspace ? (
              <tr key={grant.id}>
                <th scope="row">{holder(grant)}</th>
                <td data-label="Kind">{KIND[grant.principal.kind]}</td>
                <td data-label="Role">{grant.role.name}</td>
                {narrowed}
                <td data-label="From">{grant.scope.instance ? "Whole instance" : "This workspace"}</td>
                {action}
              </tr>
            ) : (
              <tr key={grant.id}>
                <th scope="row">{grantWhere(grant, labels)}</th>
                <td data-label="Role">{grant.role.name}</td>
                {narrowed}
                {principal?.kind === "user" && (
                  <td data-label="Through">
                    {grant.principal.id === principal.id ? "Directly" : <>Group {holder(grant)}</>}
                  </td>
                )}
                {action}
              </tr>
            );
          })}
        </SettingsTable>
      )}
      {feed.hasMore && (
        <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Load more roles
        </button>
      )}
      {granting && (
        <GrantDialog
          who={principal}
          workspace={workspace}
          onClose={() => {
            setGranting(false);
            grantRef.current?.focus();
          }}
          onGranted={(grant) => {
            setGranting(false);
            toast(`${grant.principal.name} now holds ${grant.role.name} ${place(grant)}.`);
            feed.reload();
            grantRef.current?.focus();
          }}
        />
      )}
    </Section>
  );
}
