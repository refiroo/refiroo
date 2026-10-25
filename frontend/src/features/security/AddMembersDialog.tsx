/**
 * Several people added to a group at once (0.12 SP1b, D401; the group members mock-up): searched and
 * ticked, or pasted as a list of usernames and e-mail addresses. The people to add gather as chips
 * below either tab and are added in one request. People already in the group and deactivated people
 * are shown but cannot be ticked; a pasted line nobody has is said so. Searching and checking ask
 * the engine (`dryRun`), so the dialog never loads every person.
 */

import { useEffect, useState } from "react";
import { security } from "@/api/securityClient";
import { errorMessage } from "@/api/errors";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import type { Group, GroupMember, GroupMemberOutcome, GroupMembersResult } from "@/types";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { SearchField } from "@/ui/SearchField";
import { Tabs } from "@/ui/Tabs";

const NOTES: Partial<Record<GroupMemberOutcome["outcome"], string>> = {
  alreadyMember: "Already a member",
  deactivated: "Deactivated",
  notFound: "No person with this username or e-mail",
};

export function AddMembersDialog({
  group,
  onClose,
  onAdded,
}: {
  group: Group;
  onClose: () => void;
  onAdded: (result: GroupMembersResult) => void;
}) {
  const [tab, setTab] = useState("search");
  const [picked, setPicked] = useState<ReadonlyMap<string, GroupMember>>(new Map());
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const toggle = (member: GroupMember) =>
    setPicked((current) => {
      const next = new Map(current);
      if (next.has(member.id)) next.delete(member.id);
      else next.set(member.id, member);
      return next;
    });
  const take = (members: GroupMember[]) =>
    setPicked((current) => {
      const next = new Map(current);
      for (const member of members) next.set(member.id, member);
      return next;
    });
  const count = picked.size;

  async function add() {
    setPending(true);
    setError("");
    try {
      onAdded(await security.addMembers(group.id, { userIds: [...picked.keys()] }));
    } catch (cause) {
      setError(errorMessage(cause));
      setPending(false);
    }
  }

  return (
    <Modal
      title={`Add members to ${group.name}`}
      eyebrow="Security"
      description="Roles granted to the group apply to everyone you add."
      size="wide"
      busy={pending}
      dirty={count > 0}
      onClose={onClose}
    >
      <div className="add-members">
        <Tabs
          label="How to find people"
          selected={tab}
          onChange={setTab}
          tabs={[
            {
              id: "search",
              label: "Search and tick",
              content: <SearchPeople group={group} picked={picked} onToggle={toggle} onTakeAll={take} />,
            },
            { id: "paste", label: "Paste a list", content: <PastePeople group={group} onFound={take} /> },
          ]}
        />
        <div className="add-members-picked" aria-live="polite">
          <p className="admin-hint">
            {count ? `${count} ${count === 1 ? "person" : "people"} to add` : "Nobody ticked yet"}
          </p>
          {count > 0 && (
            <ul className="add-members-chips" aria-label="People to add">
              {[...picked.values()].map((member) => (
                <li key={member.id}>
                  {member.name}
                  <button
                    type="button"
                    className="icon-button icon-button-quiet"
                    aria-label={`Remove ${member.name} from the people to add`}
                    onClick={() => toggle(member)}
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        {error && (
          <Notice tone="error" title="Nobody was added">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="primary" disabled={pending || !count} onClick={() => void add()}>
            {pending ? "Adding…" : count ? `Add ${count} ${count === 1 ? "member" : "members"}` : "Add members"}
          </button>
        </div>
      </div>
    </Modal>
  );
}

/** Search people by name, username or e-mail; each found person says whether they can be added. */
function SearchPeople({
  group,
  picked,
  onToggle,
  onTakeAll,
}: {
  group: Group;
  picked: ReadonlyMap<string, GroupMember>;
  onToggle: (member: GroupMember) => void;
  onTakeAll: (members: GroupMember[]) => void;
}) {
  const [text, setText] = useState("");
  const search = useDebouncedValue(text.trim());
  const [found, setFound] = useState<{ for: string; items: GroupMemberOutcome[] }>();
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    security
      .users({ q: search || undefined, pageSize: 20 })
      .then((page) =>
        page.items.length
          ? security.addMembers(group.id, { userIds: page.items.map((person) => person.id), dryRun: true })
          : { items: [], changed: 0 },
      )
      .then(
        (result) => {
          if (!active) return;
          setFound({ for: search, items: result.items });
          setError("");
        },
        (cause) => active && setError(errorMessage(cause)),
      );
    return () => {
      active = false;
    };
  }, [group.id, search]);
  const items = found?.items ?? [];
  const tickable = items.flatMap((item) =>
    item.outcome === "toAdd" && item.member && !picked.has(item.member.id) ? [item.member] : [],
  );
  return (
    <div className="add-members-tab">
      <SearchField
        label="Search people"
        placeholder="Search people by name, username or e-mail"
        value={text}
        onChange={setText}
      />
      <div className="add-members-found-line">
        <span className="admin-hint">
          {found === undefined
            ? "Searching…"
            : `${items.length} ${items.length === 1 ? "person" : "people"}${found.for ? " match" : ""}${
                items.length === 20 ? " · the first 20; search to narrow" : ""
              }`}
        </span>
        {tickable.length > 0 && (
          <button type="button" className="ghost" onClick={() => onTakeAll(tickable)}>
            Tick all {tickable.length} shown
          </button>
        )}
      </div>
      {error && (
        <Notice tone="error" title="People could not be searched">
          {error}
        </Notice>
      )}
      <ul className="add-members-list" aria-label="People found">
        {items.map((item) => {
          const member = item.member!;
          const blocked = item.outcome !== "toAdd";
          return (
            <li key={member.id}>
              <label className={blocked ? "add-members-person is-blocked" : "add-members-person"}>
                <input
                  type="checkbox"
                  checked={item.outcome === "alreadyMember" || picked.has(member.id)}
                  disabled={blocked}
                  onChange={() => onToggle(member)}
                  aria-label={`Add ${member.name}`}
                />
                <span className="add-members-person-text">
                  <strong>{member.name}</strong>
                  <span>{member.username}</span>
                </span>
                {NOTES[item.outcome] && <span className="admin-hint">{NOTES[item.outcome]}</span>}
              </label>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** A pasted list checked against the people: those it finds go to the people to add. */
function PastePeople({ group, onFound }: { group: Group; onFound: (members: GroupMember[]) => void }) {
  const [text, setText] = useState("");
  const [checked, setChecked] = useState<GroupMemberOutcome[]>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const lines = text
    .split(/[\n,;]+/)
    .map((line) => line.trim())
    .filter(Boolean);

  async function check() {
    setPending(true);
    setError("");
    try {
      const result = await security.addMembers(group.id, { identifiers: lines.slice(0, 500), dryRun: true });
      setChecked(result.items);
      onFound(result.items.flatMap((item) => (item.outcome === "toAdd" && item.member ? [item.member] : [])));
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  const found = checked?.filter((item) => item.outcome === "toAdd").length ?? 0;
  return (
    <div className="add-members-tab">
      <label className="add-members-paste">
        Usernames or e-mail addresses
        <textarea
          rows={6}
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            setChecked(undefined);
          }}
          aria-describedby="add-members-paste-help"
        />
      </label>
      <p id="add-members-paste-help" className="admin-hint">
        One per line, or separated by commas or semicolons, as copied from a spreadsheet or an e-mail; up to 500.
      </p>
      <div>
        <button type="button" className="secondary" disabled={pending || !lines.length} onClick={() => void check()}>
          {pending
            ? "Checking…"
            : lines.length
              ? `Check ${lines.length} ${lines.length === 1 ? "line" : "lines"}`
              : "Check the list"}
        </button>
      </div>
      {error && (
        <Notice tone="error" title="The list could not be checked">
          {error}
        </Notice>
      )}
      {checked && (
        <div className="add-members-checked">
          <p className="admin-hint">
            {checked.length} read · {found} added to the people to add
            {checked.length > found ? ` · ${checked.length - found} not` : ""}
          </p>
          <ul aria-label="Lines checked">
            {checked.map((item) => (
              <li key={item.input} className={item.outcome === "toAdd" ? "is-found" : "is-left"}>
                <span className="add-members-mark" aria-hidden="true">
                  {item.outcome === "toAdd" ? "✓" : item.outcome === "notFound" ? "!" : "–"}
                </span>
                <span className="add-members-person-text">
                  <strong>{item.member?.name ?? item.input}</strong>
                  {item.member && <span>{item.input}</span>}
                </span>
                <span className="admin-hint">
                  {item.outcome === "toAdd" ? "Added to the people to add" : NOTES[item.outcome]}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
