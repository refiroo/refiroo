/**
 * Settings › Security › Groups (0.12 SP1, U8; 0.17 ST1): local groups as a full-width list, searched by
 * name (D300); a row opens the group as a page of its own (PP-D61). A group's page renames it and changes its description in place, or deletes it, lists the roles granted to it (they apply to
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
import { formatServerDayTime, formatServerTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { routePath } from "@/routing/routes";
import type { Hue } from "@/model/hues";
import type { Group, GroupMember, RouteState, SettingsRoute, SignInProvider } from "@/types";
import { Choice } from "@/ui/Choice";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { SearchField } from "@/ui/SearchField";
import { EntityList } from "@/ui/EntityList";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SelectionCheckbox } from "@/ui/SelectionCheckbox";
import {
  ItemHeader,
  LogFoot,
  SettingsEmpty,
  SettingsGroup,
  SettingsPanel,
  SettingsTile,
  SettingsTools,
} from "@/ui/SettingsParts";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { TextInPlace } from "@/ui/TextInPlace";
import { useToast } from "@/ui/Toast";
import { Trail } from "@/ui/Trail";
import { settingsHead } from "@/ui/settingsNavigation";
import { GrantsSection } from "./GrantsSection";
import { AddMembersDialog } from "./AddMembersDialog";

type GroupsRoute = Extract<SettingsRoute, { page: "groups" }>;

const GROUPS: GroupsRoute = { kind: "settings", page: "groups" };

const members = (count: number) => `${count} member${count === 1 ? "" : "s"}`;

/** A group's count: a provider group's are only those seen at a sign-in (D364). */
const memberLine = (group: Group) =>
  group.source ? (group.members ? `${group.members} seen` : "Nobody seen yet") : members(group.members);

/** Groups read in a page of this size. */
const LIST_PAGE = 50;

export function GroupsPage({ route, onNavigate }: { route: GroupsRoute; onNavigate: (route: RouteState) => void }) {
  const [creating, setCreating] = useState(false);
  const newButtonRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();

  return (
    <>
      {route.groupId ? (
        <GroupDetail
          key={route.groupId}
          groupId={route.groupId}
          onNavigate={onNavigate}
          onDeleted={(group) => {
            toast(`The group ${group.name} was deleted. Its roles no longer apply to its members.`);
            onNavigate(GROUPS);
          }}
        />
      ) : (
        <GroupList newButtonRef={newButtonRef} onNew={() => setCreating(true)} onNavigate={onNavigate} />
      )}
      {creating && (
        <GroupDialog
          onClose={() => {
            setCreating(false);
            newButtonRef.current?.focus();
          }}
          onCreated={(group) => {
            setCreating(false);
            onNavigate({ ...GROUPS, groupId: group.id });
            toast(`The group ${group.name} was created. Add members and grant it a role.`);
          }}
        />
      )}
    </>
  );
}

/** The list a group is chosen from: search and the rows. */
function GroupList({
  newButtonRef,
  onNew,
  onNavigate,
}: {
  newButtonRef: React.RefObject<HTMLButtonElement | null>;
  onNew: () => void;
  onNavigate: (route: RouteState) => void;
}) {
  const [search, setSearch] = useState("");
  const q = useDebouncedValue(search.trim());
  const feed = useCursorFeed<Group>((cursor) => security.groups({ q, cursor, pageSize: LIST_PAGE }), [q]);
  const head = settingsHead("groups");
  const shown = feed.items.length;
  return (
    <SettingsLayout
      {...head}
      title="Groups"
      description="People grouped to hold roles together: a role granted to a group applies to every member, and stops applying when they leave it."
      actions={
        <button ref={newButtonRef} className="primary" onClick={onNew}>
          <Icon name="plus" /> New group
        </button>
      }
    >
      <SettingsTools
        count={
          feed.loading && !shown ? undefined : `${shown}${feed.hasMore ? "+" : ""} ${shown === 1 ? "group" : "groups"}`
        }
      >
        <SearchField label="Search groups" placeholder="Group name" value={search} onChange={setSearch} clearOnEscape />
      </SettingsTools>
      <SettingsPanel>
        <EntityList
          label="groups"
          statusTrack="0px"
          groups={[
            {
              key: "groups",
              title: "Groups",
              count: `${shown}${feed.hasMore ? "+" : ""}`,
              loading: feed.loading && !shown,
              error: feed.error && !shown ? feed.error : undefined,
              onRetry: feed.retry,
              onEnd: feed.hasMore ? feed.loadMore : undefined,
              loadingMore: feed.loading && shown > 0,
              rows: feed.items.map((group) => ({
                key: group.id,
                title: group.name,
                subtitle: group.description ?? "",
                lead: <SettingsTile icon="users" hue={head.hue} />,
                facts: [
                  { label: "Members", value: memberLine(group) },
                  { label: "From", value: group.source ? group.source.provider.name : "Added here" },
                ],
                onOpen: () => onNavigate({ ...GROUPS, groupId: group.id }),
              })),
            },
          ]}
          empty={q ? `No group matches “${q}”.` : "No groups yet."}
        />
      </SettingsPanel>
    </SettingsLayout>
  );
}

function GroupDetail({
  groupId,
  onNavigate,
  onDeleted,
}: {
  groupId: string;
  onNavigate: (route: RouteState) => void;
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

  /** A name or description changed in place: a stale version reloads the group and says so; Undo puts the old text back. */
  async function saveGroup(change: { name?: string; description?: string }) {
    if (!group) return;
    const body = (from: Group, next: { name?: string; description?: string }) => ({
      expectedVersion: from.version,
      name: next.name ?? from.name,
      description: (next.description ?? from.description ?? "") || null,
    });
    try {
      const updated = await security.updateGroup(group.id, body(group, change));
      setGroup(updated);
      return async () => {
        const restored = await security.updateGroup(
          updated.id,
          body(updated, { name: group.name, description: group.description ?? "" }),
        );
        setGroup(restored);
      };
    } catch (cause) {
      if (!isApiError(cause, "VERSION_CONFLICT"))
        throw new Error(refusalMessage(cause, { name: "Name", description: "Description" }), { cause });
      const current = await security.group(group.id).catch(() => undefined);
      if (current) setGroup(current);
      throw new Error("Someone changed this group while you were editing. It is shown as it is now; change it again.", {
        cause,
      });
    }
  }

  const reload = () => void security.group(groupId).then(setGroup);

  const head = settingsHead("groups");
  const trail = <Trail back={{ label: "Groups", onClick: () => onNavigate(GROUPS), href: routePath(GROUPS) }} />;
  if (loadError)
    return (
      <SettingsLayout trail={trail} title="Group">
        <InlineError message={loadError} onRetry={() => setLoadToken((token) => token + 1)} />
      </SettingsLayout>
    );
  if (!group)
    return (
      <SettingsLayout trail={trail} title="Group">
        <Skeleton label="Loading group" lines={4} />
      </SettingsLayout>
    );

  return (
    <SettingsLayout
      trail={trail}
      header={
        <ItemHeader
          hue={head.hue}
          lead={<SettingsTile icon="users" hue={head.hue} size={48} />}
          title={
            <TextInPlace
              heading
              headingLevel={1}
              value={group.name}
              label="Name"
              maxLength={200}
              savedText="Renamed."
              onSave={(name) => saveGroup({ name })}
            />
          }
          meta={
            <>
              <TextInPlace
                value={group.description ?? ""}
                label="Description"
                optional
                maxLength={2000}
                onSave={(description) => saveGroup({ description })}
              />
              <span>{memberLine(group)}</span>
              {group.source && (
                <>
                  <StatusPill tone="neutral" marker={false}>
                    From {group.source.provider.name}
                  </StatusPill>
                  <StatusPill tone="neutral" marker={false}>
                    Claim value <span className="mono">{group.source.claimValue}</span>
                  </StatusPill>
                </>
              )}
            </>
          }
          actions={
            <button className="danger-ghost" onClick={() => setDeleting(true)}>
              Delete group
            </button>
          }
        />
      }
    >
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
        hue={head.hue}
      />
      <GroupMembers group={group} hue={head.hue} onNavigate={onNavigate} onChanged={reload} />
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
    </SettingsLayout>
  );
}

function GroupMembers({
  group,
  hue,
  onNavigate,
  onChanged,
}: {
  group: Group;
  hue: Hue;
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
    <SettingsGroup
      stacked
      title={seen ? "Members seen" : "Members"}
      description={
        seen
          ? "The people the provider named in this group at their last sign-in."
          : "Everyone here holds the roles granted to the group."
      }
      action={
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
        feed.loading ? (
          <Skeleton label="Loading members" lines={3} />
        ) : (
          <SettingsPanel>
            <SettingsEmpty icon="user" hue={hue}>
              {seen ? "Nobody in this group has signed in yet." : "No members yet."}
            </SettingsEmpty>
          </SettingsPanel>
        )
      ) : (
        <SettingsPanel>
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
                    <td
                      className="when"
                      data-label="Last seen in this group"
                      title={member.seenAt ? formatServerTime(member.seenAt) : undefined}
                    >
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
          <LogFoot
            shown={feed.items.length}
            total={feed.hasMore ? undefined : group.members === feed.items.length ? group.members : undefined}
            noun={feed.items.length === 1 ? "member" : "members"}
            onMore={feed.hasMore ? feed.loadMore : undefined}
            loading={feed.loading}
          />
        </SettingsPanel>
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
    </SettingsGroup>
  );
}

function GroupDialog({ onClose, onCreated }: { onClose: () => void; onCreated: (group: Group) => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [source, setSource] = useState<"local" | "provider">("local");
  const [providers, setProviders] = useState<SignInProvider[]>([]);
  const [provider, setProvider] = useState("");
  const [claimValue, setClaimValue] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const fromProvider = source === "provider";
  const changed = !!name.trim() || !!description.trim();

  // A new group can stand for a provider's group; offered only when a provider uses groups (D364).
  useEffect(() => {
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
  }, []);

  async function save() {
    setPending(true);
    setError("");
    try {
      onCreated(
        await security.createGroup({
          name: name.trim(),
          ...(description.trim() ? { description: description.trim() } : {}),
          ...(fromProvider ? { source: { provider, claimValue: claimValue.trim() } } : {}),
        }),
      );
    } catch (cause) {
      setError(refusalMessage(cause, { name: "Name", description: "Description" }));
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal
      title="New group"
      eyebrow="People and access"
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
        {providers.length > 0 && (
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
          <button className="primary" disabled={pending || !name.trim() || (fromProvider && !claimValue.trim())}>
            {pending ? "Adding…" : "Add group"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
