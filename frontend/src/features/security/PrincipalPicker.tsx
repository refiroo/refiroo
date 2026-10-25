import { useEffect, useState } from "react";
import { security } from "@/api/securityClient";
import { errorMessage } from "@/api/errors";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import type { GrantCreate } from "@/types";
import { ComboBoxField, type SelectionOption } from "@/ui/Selection";

export type PrincipalKind = GrantCreate["principal"]["kind"];

export interface PickedPrincipal {
  kind: PrincipalKind;
  id: string;
  name: string;
}

const KIND_LABEL: Record<PrincipalKind, string> = { user: "Person", group: "Group", client: "Client" };

/**
 * Finds people, groups or clients by name for a grant's "Who", a group's new member or a person's
 * new group (0.12 SP1, D300): each search asks the engine, so a long list is never loaded whole.
 */
export function PrincipalPicker({
  label,
  kinds,
  description,
  exclude,
  onPick,
}: {
  label: string;
  kinds: readonly PrincipalKind[];
  description?: string;
  /** A principal not offered: the person a link moves from. */
  exclude?: string;
  onPick: (principal: PickedPrincipal | undefined) => void;
}) {
  const [text, setText] = useState("");
  const [found, setFound] = useState<(PickedPrincipal & { detail: string })[]>([]);
  const [error, setError] = useState("");
  // The name of the one picked; the combobox writes it (or the option's key) into the input as it
  // selects, which must not read as the person typing something else.
  const [picked, setPicked] = useState<PickedPrincipal>();
  const search = useDebouncedValue(text.trim());
  const kindsKey = kinds.join(",");
  const excluded = exclude;

  useEffect(() => {
    let active = true;
    const wanted = kindsKey.split(",") as PrincipalKind[];
    Promise.all([
      wanted.includes("user")
        ? security.users({ q: search, active: true, pageSize: 10 }).then((page) =>
            page.items.map((item) => ({
              kind: "user" as const,
              id: item.id,
              name: item.name,
              detail: item.username,
            })),
          )
        : [],
      wanted.includes("group")
        ? security.groups({ q: search, pageSize: 10 }).then((page) =>
            page.items.map((item) => ({
              kind: "group" as const,
              id: item.id,
              name: item.name,
              detail: `${item.members} member${item.members === 1 ? "" : "s"}`,
            })),
          )
        : [],
      wanted.includes("client")
        ? security
            .clients({ q: search, pageSize: 10 })
            .then((page) =>
              page.items.map((item) => ({ kind: "client" as const, id: item.id, name: item.name, detail: "" })),
            )
        : [],
    ])
      .then((lists) => {
        if (!active) return;
        setFound(lists.flat().filter((item) => item.id !== excluded));
        setError("");
      })
      .catch((cause) => active && setError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [search, kindsKey, excluded]);

  const options: SelectionOption[] = found.map((item) => ({
    id: `${item.kind}:${item.id}`,
    label: item.name,
    description: [kinds.length > 1 ? KIND_LABEL[item.kind] : "", item.detail].filter(Boolean).join(" · "),
  }));

  return (
    <ComboBoxField
      label={label}
      value={text}
      options={options}
      allowsCustomValue={false}
      description={error || description}
      onChange={(value) => {
        const chosen = found.find((item) => `${item.kind}:${item.id}` === value);
        if (chosen || (picked && value === picked.name)) return;
        setText(value);
        setPicked(undefined);
        onPick(undefined);
      }}
      onSelect={(key) => {
        const chosen = found.find((item) => `${item.kind}:${item.id}` === key);
        if (chosen) {
          const principal = { kind: chosen.kind, id: chosen.id, name: chosen.name };
          setText(chosen.name);
          setPicked(principal);
          onPick(principal);
        }
      }}
    />
  );
}
