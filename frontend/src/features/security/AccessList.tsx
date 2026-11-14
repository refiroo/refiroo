/**
 * A workspace's Access as one line per principal (0.12): the person, group or client on the left and
 * the roles it holds here as chips on the right, a dashed "+" to grant it another. Chips are coloured
 * by the kind of role; a chip's trash button (on hover or focus, always shown on touch) removes it.
 */

import { useMemo, useRef, useState } from "react";
import type { Grant, RouteState } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { Icon } from "@/ui/Icon";
import { SearchField } from "@/ui/SearchField";
import { initials } from "@/ui/SettingsParts";
import { RouteLink } from "@/ui/RouteLink";
import { routePath } from "@/routing/routes";
import { groupByPrincipal, grantHeld, holdsRole, rolesPresent, type AccessRow } from "./accessGroups";
import { GrantChip } from "./GrantChip";
import type { PickedPrincipal } from "./PrincipalPicker";

type Kind = Grant["principal"]["kind"];
const KIND: Record<Kind, string> = { user: "Person", group: "Group", client: "Client" };
const KIND_ICON = { user: "user", group: "users", client: "api" } as const;

const LEGEND: { label: string; hue: string }[] = [
  { label: "Reader", hue: "8" },
  { label: "Contributor", hue: "7" },
  { label: "Steward", hue: "1" },
  { label: "Data owner", hue: "4" },
  { label: "Administration", hue: "3" },
  { label: "Consumer API", hue: "2" },
];

export function AccessList({
  label,
  grants,
  removing,
  hasMore,
  onRemove,
  onAdd,
  onNavigate,
  focusFallback,
}: {
  label: string;
  /** Every grant loaded so far, ordered by principal. */
  grants: readonly Grant[];
  removing?: string;
  hasMore: boolean;
  /** Removes a grant; resolves true when it is gone. */
  onRemove: (grant: Grant) => Promise<boolean>;
  onAdd: (principal: PickedPrincipal, opener: HTMLElement) => void;
  onNavigate: (route: RouteState) => void;
  /** Where focus goes when the row of a removed grant is gone. */
  focusFallback: () => void;
}) {
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [kind, setKind] = useState<"" | Kind>("");
  const [confirming, setConfirming] = useState<Grant>();
  const listRef = useRef<HTMLUListElement>(null);

  const rows = useMemo(() => groupByPrincipal(grants), [grants]);
  const roles = useMemo(() => rolesPresent(grants), [grants]);
  const needle = search.trim().toLowerCase();
  const shown = rows.filter(
    (row) =>
      (!needle || row.principal.name.toLowerCase().includes(needle)) &&
      (!kind || row.principal.kind === kind) &&
      (!role || holdsRole(row, role)),
  );

  function routeOf(principal: Grant["principal"]): RouteState {
    if (principal.kind === "user") return { kind: "settings", page: "people", userId: principal.id };
    if (principal.kind === "group") return { kind: "settings", page: "groups", groupId: principal.id };
    return { kind: "settings", page: "clients", clientId: principal.id };
  }

  async function confirmRemove(grant: Grant) {
    const done = await onRemove(grant);
    setConfirming(undefined);
    if (!done) return;
    const rowKey = `${grant.principal.kind}:${grant.principal.id}`;
    // After the list has re-rendered: to the row's "+", or to the Grant button when the row is gone.
    window.setTimeout(() => {
      const add = Array.from(listRef.current?.querySelectorAll<HTMLElement>("[data-add]") ?? []).find(
        (element) => element.dataset.add === rowKey,
      );
      if (add) add.focus();
      else focusFallback();
    }, 0);
  }

  function chip(row: AccessRow, grant: Grant) {
    const held = grantHeld(grant);
    return (
      <GrantChip
        key={grant.id}
        grant={grant}
        note={grant.scope.instance ? "Granted for the whole instance" : undefined}
        extra={grant.scope.instance && <small>· whole instance</small>}
        removeLabel={`Remove ${held} from ${row.principal.name}`}
        removing={removing === grant.id}
        onRemove={grant.scope.instance ? undefined : () => setConfirming(grant)}
      />
    );
  }

  return (
    <>
      <div className="access-toolbar">
        <SearchField
          className="access-search"
          value={search}
          onChange={setSearch}
          label="Search people, groups, clients"
          placeholder="Search people, groups, clients"
        />
        <label className="toolbar-field access-filter">
          <span>Role</span>
          <select value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="">All</option>
            {roles.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="toolbar-field access-filter">
          <span>Kind</span>
          <select value={kind} onChange={(event) => setKind(event.target.value as "" | Kind)}>
            <option value="">All</option>
            <option value="user">People</option>
            <option value="group">Groups</option>
            <option value="client">Clients</option>
          </select>
        </label>
        <ul className="access-legend" aria-label="Colours of roles">
          {LEGEND.map((item) => (
            <li key={item.label} className="access-chip access-legend-chip" data-hue={item.hue}>
              {item.label}
            </li>
          ))}
        </ul>
      </div>
      {shown.length ? (
        <ul ref={listRef} className="access-list" aria-label={label}>
          {shown.map((row) => {
            const route = routeOf(row.principal);
            return (
              <li key={row.key} className="access-row">
                <div className="access-who">
                  <span className="access-avatar" data-kind={row.principal.kind} aria-hidden="true">
                    {row.principal.kind === "user" ? (
                      initials(row.principal.name)
                    ) : (
                      <Icon name={KIND_ICON[row.principal.kind]} size={16} />
                    )}
                  </span>
                  <div className="access-who-text">
                    <RouteLink href={routePath(route)} onNavigate={() => onNavigate(route)}>
                      {row.principal.name}
                    </RouteLink>
                    <span className="access-kind">{KIND[row.principal.kind]}</span>
                  </div>
                </div>
                <ul className="access-chips" aria-label={`Roles of ${row.principal.name}`}>
                  {row.grants.map((grant) => chip(row, grant))}
                  <li>
                    <button
                      type="button"
                      className="access-add"
                      data-add={row.key}
                      aria-label={`Add a role for ${row.principal.name}`}
                      onClick={(event) => onAdd(row.principal, event.currentTarget)}
                    >
                      <Icon name="plus" size={14} />
                    </button>
                  </li>
                </ul>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="admin-hint">{hasMore ? "No one loaded so far matches." : "No one matches."}</p>
      )}
      {confirming && (
        <ConfirmDialog
          title={`Remove ${grantHeld(confirming)} from ${confirming.principal.name}?`}
          confirmLabel="Remove grant"
          pending={removing === confirming.id}
          onCancel={() => setConfirming(undefined)}
          onConfirm={() => void confirmRemove(confirming)}
        >
          <p>
            {confirming.principal.name} will no longer hold {grantHeld(confirming)} in this workspace.
          </p>
        </ConfirmDialog>
      )}
    </>
  );
}
