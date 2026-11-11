/**
 * Settings › Security › Groups (0.12 SP1, U8): local groups beside the selected one, searched by
 * name (D300). A group's page renames or deletes it, lists the roles granted to it (they apply to
 * every member) and its members, with Add a member and Remove. A group from a sign-in provider (I3,
 * D364) is listed under its provider; its members are those the provider named at their last
 * sign-in ("Members seen"), changed in the provider, never here, and New group can make one ahead of
 * anyone's sign-in so its roles are ready. Deleting a group, or removing a member, that would leave
 * no active Security administrator is refused by the engine (`LAST_SECURITY_ADMINISTRATOR`), shown
 * as worded.
 */

import { useEffect, useRef, useState } from "react";
import { errorMessage, isApiError, refusalMessage } from "@/api/errors";
import { security } from "@/api/securityClient";
import { formatServerDayTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { routePath } from "@/routing/routes";
import type { Group, GroupMember, RouteState, SettingsRoute, SignInProvider } from "@/types";
import { CatalogueEntry, CatalogueLayout } from "@/ui/CatalogueLayout";
import { CatalogueWindow } from "@/ui/CatalogueWindow";
import { Choice } from "@/ui/Choice";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { SearchField } from "@/ui/SearchField";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SelectionCheckbox } from "@/ui/SelectionCheckbox";
import { SettingsTable } from "@/ui/SettingsTable";
import { StatusPill } from "@/ui/StatusPill";
import { useToast } from "@/ui/Toast";
import { GrantsSection } from "./GrantsSection";
import { AddMembersDialog } from "./AddMembersDialog";

type GroupsRoute = Extract<SettingsRoute, { page: "groups" }>;

const GROUPS: GroupsRoute = { kind: "settings", page: "groups" };

const members = (count: number) => `${count} member${count === 1 ? "" : "s"}`;

/** A group's count: a provider group's are only those seen at a sign-in (D364). */
const memberLine = (group: Group) =>
  group.source ? (group.members ? `${group.members} seen` : "Nobody seen yet") : members(group.members);

/** Where a group comes from, for its entry: a provider's groups name the provider (D364). */
const sourceLine = (group: Group) => (group.source ? `From ${group.source.provider.name} · ` : "");

/** Groups read in a page of this size. */
const CATALOGUE_PAGE = 50;

export function GroupsPage({ route, onNavigate }: { route: GroupsRoute; onNavigate: (route: RouteState) => void }) {
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Group | "new">();
  // Read the open group again after a rename, so its page shows the new name (I3: SP1 kept the old).
  const [renamed, setRenamed] = useState(0);
  const newButtonRef = useRef<HTMLButtonElement>(null);
  const q = useDebouncedValue(search.trim());
  const list = useCursorWindow<Group>((selector) => security.groups({ q, ...selector, pageSize: CATALOGUE_PAGE }), [q]);
  const toast = useToast();

  const changed = () => list.reload();

  const catalogue = (
    <nav className="model-catalogue security-catalogue" aria-label="Groups">
      <section>
        <SearchField label="Search groups" placeholder="Group name" value={search} onChange={setSearch} clearOnEscape />
        <CatalogueWindow
          list={list}
          label="Groups"
          noun={["group", "groups"]}
          pageSize={CATALOGUE_PAGE}
          loadingText="Loading groups…"
          emptyText={q ? `No group matches “${q}”.` : "No groups yet."}
          entry={(group) => (
            <CatalogueEntry
              icon="users"
              title={group.name}
              subtitle={`${sourceLine(group)}${memberLine(group)}${group.description ? ` · ${group.description}` : ""}`}
              current={route.groupId === group.id}
              onSelect={() => onNavigate({ ...GROUPS, groupId: group.id })}
            />
          )}
        />
      </section>
    </nav>
  );

  return (
    <SettingsLayout
      eyebrow="Security"
      title="Groups"
      description="People grouped to hold roles together: a role granted to a group applies to every member, and stops applying when they leave it."
      actions={
        <button ref={newButtonRef} className="primary" onClick={() => setEditing("new")}>
          <Icon name="plus" /> New group
        </button>
      }
    >
      <CatalogueLayout
        catalogue={catalogue}
        hasSelection={!!route.groupId}
        backLabel="All groups"
        onBack={() => onNavigate(GROUPS)}
      >
        {route.groupId ? (
          <GroupDetail
            key={`${route.groupId}:${renamed}`}
            groupId={route.groupId}
            onNavigate={onNavigate}
            onRename={(group) => setEditing(group)}
            onChanged={changed}
            onDeleted={(group) => {
              toast(`The group ${group.name} was deleted. Its roles no longer apply to its members.`);
              list.reload();
              onNavigate(GROUPS);
            }}
          />
        ) : (
          <div className="panel-state">Choose a group.</div>
        )}
      </CatalogueLayout>
      {editing && (
        <GroupDialog
          group={editing === "new" ? undefined : editing}
          onClose={() => {
            setEditing(undefined);
            newButtonRef.current?.focus();
          }}
          onSaved={(group, created) => {
            setEditing(undefined);
            if (created) {
              list.reload();
              onNavigate({ ...GROUPS, groupId: group.id });
              toast(`The group ${group.name} was created. Add members and grant it a role.`);
            } else {
              changed();
              setRenamed((count) => count + 1);
              toast("Saved.");
            }
          }}
        />
      )}
    </SettingsLayout>
  );
}

function GroupDetail({
  groupId,
  onNavigate,
  onRename,
  onChanged,
  onDeleted,
}: {
  groupId: string;
  onNavigate: (route: RouteState) => void;
  onRename: (group: Group) => void;
  onChanged: (group: Group) => void;
  onDeleted: (group: Group) => void;
}) {
  const [group, setGroup] = useState<Group>();
  const [loadError, setLoadError] = useState("");
  const [loadToken, setLoadToken] = useState(0);
  const [deleting, setDeleting] = useState(false);
  const [pending, setPending] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  useEffect(() => {
    let current = true;
    security.group(groupId).then(
      (loaded) => {
        if (!current) return;
        setGroup(loaded);
        setLoadError("");
      },
      (cause) => current && setLoadError(errorMessage(cause)),
    );
    return () => {
      current = false;
    };
  }, [groupId, loadToken]);

  async function remove() {
    if (!group) return;
    setPending(true);
    setDeleteError("");
    try {
      await security.deleteGroup(group.id);
      onDeleted(group);
    } catch (cause) {
      setDeleteError(errorMessage(cause));
      setPending(false);
    }
  }

  const reload = () =>
    void security.group(groupId).then((loaded) => {
      setGroup(loaded);
      onChanged(loaded);
    });

  if (loadError) return <InlineError message={loadError} onRetry={() => setLoadToken((token) => token + 1)} />;
  if (!group) return <div className="panel-state">Loading group…</div>;

  return (
    <div className="model-editor-stack security-detail">
      <header className="model-detail-header">
        <div>
          <p className="eyebrow">Group</p>
          <h2>{group.name}</h2>
          <p>{group.description ? `${group.description} · ${memberLine(group)}` : memberLine(group)}</p>
          {group.source && (
            <div className="security-pills">
              <StatusPill tone="neutral" marker={false}>
                From {group.source.provider.name}
              </StatusPill>
              <StatusPill tone="neutral" marker={false}>
                Claim value <span className="mono">{group.source.claimValue}</span>
              </StatusPill>
            </div>
          )}
        </div>
      </header>
      <div className="model-actions">
        <button className="secondary" onClick={() => onRename(group)}>
          Rename…
        </button>
        <button className="danger-ghost" onClick={() => setDeleting(true)}>
          Delete group
        </button>
      </div>
      {group.source && (
        <Notice tone="info" title="Members come from the sign-in provider">
          They are updated each time a person signs in with {group.source.provider.name}. Someone in this group who has
          not signed in since it was named is not listed yet. Change membership in {group.source.provider.name}; grant
          roles here.
        </Notice>
      )}
      <GrantsSection
        subject={{ principal: { kind: "group", id: group.id, name: group.name } }}
        description="A role granted to the group applies to every member."
        load={(cursor) => security.grantsOf(group.id, cursor)}
        deps={[group.id]}
        onNavigate={onNavigate}
      />
      <GroupMembers group={group} onNavigate={onNavigate} onChanged={reload} />
      {deleting && (
        <ConfirmDialog
          title={`Delete ${group.name}?`}
          confirmLabel="Delete group"
          pending={pending}
          error={deleteError}
          onCancel={() => {
            setDeleting(false);
            setDeleteError("");
          }}
          onConfirm={() => void remove()}
        >
          <p>
            The group, its memberships and the roles granted to it are removed. Its {members(group.members)} keep any
            roles granted to them directly.
          </p>
        </ConfirmDialog>
      )}
    </div>
  );
}

function GroupMembers({
  group,
  onNavigate,
  onChanged,
}: {
  group: Group;
  onNavigate: (route: RouteState) => void;
  onChanged: () => void;
}) {
  const feed = useCursorFeed((cursor) => security.members(group.id, cursor), [group.id]);
  const [adding, setAdding] = useState(false);
  // The members ticked for removal together (0.12 SP1b, D402); a reload drops those who left.
  const [ticked, setTicked] = useState<ReadonlySet<string>>(new Set());
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const addRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();

  async function remove(members: GroupMember[]) {
    setError("");
    setPending(true);
    try {
      const result = await security.removeMembers(
        group.id,
        members.map((member) => member.id),
      );
      const gone = new Set(
        result.items.flatMap((item) => (item.outcome === "removed" && item.member ? [item.member.id] : [])),
      );
      feed.setItems((items) => items.filter((item) => !gone.has(item.id)));
      setTicked((current) => new Set([...current].filter((id) => !gone.has(id))));
      onChanged();
      toast(
        gone.size === 1
          ? `${members.find((member) => gone.has(member.id))?.name ?? "One person"} left ${group.name}.`
          : `${gone.size} people left ${group.name}.`,
      );
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  const seen = !!group.source;
  const shownTicked = feed.items.filter((member) => ticked.has(member.id));
  const all = feed.items.length > 0 && shownTicked.length === feed.items.length;
  const toggle = (id: string) =>
    setTicked((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  return (
    <Section
      title={seen ? "Members seen" : "Members"}
      actions={
        !seen && (
          <button ref={addRef} type="button" className="secondary" onClick={() => setAdding(true)}>
            <Icon name="plus" /> Add members
          </button>
        )
      }
    >
      {error && (
        <Notice tone="error" title="Nobody was removed">
          {error}
        </Notice>
      )}
      {!seen && shownTicked.length > 0 && (
        <div className="selection-bar" role="group" aria-label="Selected members">
          <div className="selection-bar-row">
            <strong className="selection-count">
              {shownTicked.length} {shownTicked.length === 1 ? "member" : "members"} selected
            </strong>
            <div className="selection-actions">
              <button
                type="button"
                className="ghost danger-action"
                disabled={pending}
                onClick={() => void remove(shownTicked)}
              >
                Remove {shownTicked.length} from the group
              </button>
            </div>
            <button type="button" className="ghost selection-clear" onClick={() => setTicked(new Set())}>
              Clear
            </button>
          </div>
        </div>
      )}
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : !feed.items.length ? (
        <p className="admin-hint">
          {feed.loading ? "Loading members…" : seen ? "Nobody in this group has signed in yet." : "No members yet."}
        </p>
      ) : (
        <SettingsTable
          label="Members"
          columns={
            seen
              ? ["Person", "E-mail", "Status", "Last seen in this group"]
              : [
                  {
                    key: "select",
                    content: (
                      <SelectionCheckbox
                        label="Select every member shown"
                        state={all ? "all" : shownTicked.length ? "some" : "none"}
                        onSelect={() => setTicked(all ? new Set() : new Set(feed.items.map((member) => member.id)))}
                      />
                    ),
                  },
                  "Person",
                  "E-mail",
                  "Status",
                  { hidden: "Actions" },
                ]
          }
        >
          {feed.items.map((member) => {
            const route: SettingsRoute = { kind: "settings", page: "people", userId: member.id };
            const name = (
              <RouteLink href={routePath(route)} onNavigate={() => onNavigate(route)}>
                {member.name}
              </RouteLink>
            );
            return (
              <tr key={member.id} className={ticked.has(member.id) ? "checked-row" : undefined}>
                {seen ? (
                  <th scope="row">{name}</th>
                ) : (
                  <>
                    <td className="selection-column">
                      <SelectionCheckbox
                        label={`Select ${member.name}`}
                        state={ticked.has(member.id) ? "all" : "none"}
                        onSelect={() => toggle(member.id)}
                      />
                    </td>
                    <th scope="row">{name}</th>
                  </>
                )}
                <td data-label="E-mail">{member.email}</td>
                <td data-label="Status">{member.active ? "Active" : "Deactivated"}</td>
                {seen ? (
                  <td data-label="Last seen in this group">
                    {member.seenAt ? formatServerDayTime(member.seenAt) : "—"}
                  </td>
                ) : (
                  <td className="grant-action">
                    <button
                      type="button"
                      className="ghost"
                      disabled={pending}
                      aria-label={`Remove ${member.name} from ${group.name}`}
                      onClick={() => void remove([member])}
                    >
                      Remove
                    </button>
                  </td>
                )}
              </tr>
            );
          })}
        </SettingsTable>
      )}
      {feed.hasMore && (
        <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Load more members
        </button>
      )}
      {adding && (
        <AddMembersDialog
          group={group}
          onClose={() => {
            setAdding(false);
            addRef.current?.focus();
          }}
          onAdded={(result) => {
            setAdding(false);
            feed.reload();
            onChanged();
            const left = result.items.filter((item) => item.outcome === "deactivated").length;
            toast(
              `${result.changed} ${result.changed === 1 ? "person" : "people"} added to ${group.name}.` +
                (left ? ` ${left} deactivated ${left === 1 ? "person was" : "people were"} left out.` : ""),
            );
            addRef.current?.focus();
          }}
        />
      )}
    </Section>
  );
}

function GroupDialog({
  group,
  onClose,
  onSaved,
}: {
  group?: Group;
  onClose: () => void;
  onSaved: (group: Group, created: boolean) => void;
}) {
  const [name, setName] = useState(group?.name ?? "");
  const [description, setDescription] = useState(group?.description ?? "");
  const [source, setSource] = useState<"local" | "provider">("local");
  const [providers, setProviders] = useState<SignInProvider[]>([]);
  const [provider, setProvider] = useState("");
  const [claimValue, setClaimValue] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const fromProvider = source === "provider";
  const changed = name.trim() !== (group?.name ?? "") || description.trim() !== (group?.description ?? "");

  // A new group can stand for a provider's group; offered only when a provider uses groups (D364).
  useEffect(() => {
    if (group) return;
    let current = true;
    security.signInProviders().then(
      (page) => {
        if (!current) return;
        const usable = page.items.filter((item) => item.groupsClaim);
        setProviders(usable);
        setProvider((chosen) => chosen || (usable[0]?.key ?? ""));
      },
      () => undefined,
    );
    return () => {
      current = false;
    };
  }, [group]);

  async function save() {
    setPending(true);
    setError("");
    try {
      if (group)
        onSaved(
          await security.updateGroup(group.id, {
            expectedVersion: group.version,
            name: name.trim(),
            description: description.trim() || null,
          }),
          false,
        );
      else
        onSaved(
          await security.createGroup({
            name: name.trim(),
            ...(description.trim() ? { description: description.trim() } : {}),
            ...(fromProvider ? { source: { provider, claimValue: claimValue.trim() } } : {}),
          }),
          true,
        );
    } catch (cause) {
      setError(
        isApiError(cause, "VERSION_CONFLICT")
          ? "Someone changed this group while you were editing. Close the dialog to see it as it is now."
          : refusalMessage(cause, { name: "Name", description: "Description" }),
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal
      title={group ? `Rename ${group.name}` : "New group"}
      eyebrow="Security"
      size="compact"
      busy={pending}
      dirty={changed}
      onClose={onClose}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <label>
          Name
          <input autoFocus required maxLength={200} value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label>
          Description (optional)
          <input maxLength={2000} value={description} onChange={(event) => setDescription(event.target.value)} />
        </label>
        {!group && providers.length > 0 && (
          <fieldset className="form-field">
            <legend>Members</legend>
            <Choice
              name="group-source"
              value={source}
              options={[
                ["local", "Added here"],
                ["provider", "From a sign-in provider"],
              ]}
              onChange={setSource}
            />
          </fieldset>
        )}
        {fromProvider && (
          <div className="dialog-pair">
            <label>
              Provider
              <select value={provider} onChange={(event) => setProvider(event.target.value)}>
                {providers.map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Claim value
              <input
                className="mono"
                required
                maxLength={200}
                value={claimValue}
                onChange={(event) => setClaimValue(event.target.value)}
              />
            </label>
          </div>
        )}
        {fromProvider && (
          <p className="admin-hint">
            The value the provider's groups claim holds for this group (Entra ID sends the group's object ID). Made
            ahead, its roles are ready before anyone in it signs in.
          </p>
        )}
        {error && (
          <Notice tone="error" title="Not saved">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button
            className="primary"
            disabled={pending || !changed || !name.trim() || (fromProvider && !claimValue.trim())}
          >
            {pending ? "Saving…" : group ? "Save" : "Create group"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
