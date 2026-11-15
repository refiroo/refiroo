/**
 * The questions of the workbook's readings (0.17 PL3b, CE1): the two names an unpivot adds, and the
 * heading column's name with the list it makes the parent. Each is a titled popover under the element
 * it concerns (`AnchoredPopover`) and sends nothing itself: its answer goes back to the page, which
 * sends one request. The model editor's column and list panels and the canvas ask them; the canvas's
 * other popovers (`CanvasAsks`) are built from the same `Frame` and `Actions`.
 */

import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from "react";
import { AnchoredPopover } from "@/ui/AnchoredPopover";

const POPOVER = "popover control-popover editor-popover canvas-popover";

export function Frame({
  anchor,
  title,
  onClose,
  children,
}: {
  anchor: HTMLElement;
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <AnchoredPopover
      anchor={anchor}
      title={title}
      onClose={onClose}
      className={POPOVER}
      titleClassName="editor-popover-title"
    >
      {children}
    </AnchoredPopover>
  );
}

export function Actions({ onClose, submit, disabled }: { onClose: () => void; submit: string; disabled?: boolean }) {
  return (
    <div className="editor-popover-actions">
      <button type="button" className="secondary" onClick={onClose}>
        Cancel
      </button>
      <button type="submit" className="primary" disabled={disabled}>
        {submit}
      </button>
    </div>
  );
}

/** The object types to choose from, as a select: the heading question's parent and the unpivot's target. */
function TypeSelect({
  id,
  value,
  types,
  onChange,
  children,
}: {
  id: string;
  value: string;
  types: readonly { key: string; name: string }[];
  onChange: (key: string) => void;
  children?: ReactNode;
}) {
  return (
    <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
      {types.map((item) => (
        <option key={item.key} value={item.key}>
          {item.name}
        </option>
      ))}
      {children}
    </select>
  );
}

/**
 * The names of the two columns a wide table gains when its columns are read as rows. With `choose`
 * the popover also asks which columns: the editor's panels start from one column or a list, where the
 * canvas has them chosen already.
 */
export function UnpivotPopover({
  anchor,
  count,
  choose,
  initial,
  targets,
  onSubmit,
  onClose,
}: {
  anchor: HTMLElement;
  /** How many columns were chosen, when they were chosen before the question. */
  count?: number;
  /** The columns to choose from, and the ones ticked at first. */
  choose?: { headers: readonly string[]; ticked: readonly string[] };
  initial: { nameColumn: string; valueColumn: string };
  /** The object types the new columns can land on, and the one chosen at first; the canvas has its own. */
  targets?: { types: readonly { key: string; name: string }[]; initial: string };
  onSubmit: (names: { nameColumn: string; valueColumn: string }, columns: string[], typeKey?: string) => void;
  onClose: () => void;
}) {
  const [target, setTarget] = useState(targets?.initial ?? "");
  const [nameColumn, setName] = useState(initial.nameColumn);
  const [valueColumn, setValue] = useState(initial.valueColumn);
  const [ticked, setTicked] = useState<readonly string[]>(choose?.ticked ?? []);
  const id = useId();
  const columns = choose ? (choose.headers.filter((header) => ticked.includes(header)) as string[]) : [];
  const ready =
    nameColumn.trim() !== "" &&
    valueColumn.trim() !== "" &&
    nameColumn.trim() !== valueColumn.trim() &&
    (!choose || columns.length > 1);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (ready)
      onSubmit(
        { nameColumn: nameColumn.trim(), valueColumn: valueColumn.trim() },
        columns,
        targets ? target : undefined,
      );
  };
  return (
    <Frame anchor={anchor} title={choose ? "Read columns as rows" : `Read ${count} columns as rows`} onClose={onClose}>
      <form className="editor-popover-form" onSubmit={submit}>
        {choose && (
          <fieldset>
            <legend>The columns to read as rows</legend>
            {choose.headers.map((header) => (
              <label key={header} className="checkbox">
                <input
                  type="checkbox"
                  checked={ticked.includes(header)}
                  onChange={(event) =>
                    setTicked(event.target.checked ? [...ticked, header] : ticked.filter((item) => item !== header))
                  }
                />
                {header}
              </label>
            ))}
          </fieldset>
        )}
        {targets && (
          <>
            <label htmlFor={`${id}-target`}>The new columns are added to</label>
            <TypeSelect id={`${id}-target`} value={target} types={targets.types} onChange={setTarget} />
          </>
        )}
        <p className="muted">Each filled cell becomes a row of its own, with two new columns:</p>
        <label htmlFor={`${id}-name`}>The column's header goes in</label>
        <input id={`${id}-name`} autoFocus value={nameColumn} onChange={(event) => setName(event.target.value)} />
        <label htmlFor={`${id}-value`}>The cell goes in</label>
        <input id={`${id}-value`} value={valueColumn} onChange={(event) => setValue(event.target.value)} />
        <Actions onClose={onClose} submit="Read as rows" disabled={!ready} />
      </form>
    </Frame>
  );
}

const NEW_LIST = "\u0000new";

/** Rows holding only one column are headings: the new column's name and the list that is their parent. */
export function HeadingPopover({
  anchor,
  column,
  initialInto,
  parents,
  initialParent,
  onSubmit,
  onClose,
}: {
  anchor: HTMLElement;
  column: string;
  initialInto: string;
  parents: readonly { key: string; name: string }[];
  initialParent?: string;
  onSubmit: (answer: { into: string; parent: { typeKey: string } | { newName: string } }) => void;
  onClose: () => void;
}) {
  const [into, setInto] = useState(initialInto);
  const [parent, setParent] = useState(initialParent ?? parents[0]?.key ?? NEW_LIST);
  const [newName, setNewName] = useState(initialInto);
  const id = useId();
  const first = useRef<HTMLInputElement>(null);
  useEffect(() => first.current?.focus(), []);
  const creating = parent === NEW_LIST;
  const ready = into.trim() !== "" && (!creating || newName.trim() !== "");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (ready) onSubmit({ into: into.trim(), parent: creating ? { newName: newName.trim() } : { typeKey: parent } });
  };
  return (
    <Frame anchor={anchor} title={`Rows holding only ${column} are headings`} onClose={onClose}>
      <form className="editor-popover-form" onSubmit={submit}>
        <p className="muted">
          Such a row is not a record: its text is the parent of the rows beneath it, until the next heading.
        </p>
        <label htmlFor={`${id}-into`}>The heading goes in a new column called</label>
        <input id={`${id}-into`} ref={first} value={into} onChange={(event) => setInto(event.target.value)} />
        <label htmlFor={`${id}-parent`}>and names the parent in</label>
        <TypeSelect id={`${id}-parent`} value={parent} types={parents} onChange={setParent}>
          <option value={NEW_LIST}>A new object type…</option>
        </TypeSelect>
        {creating && (
          <>
            <label htmlFor={`${id}-new`}>Name of the new object type</label>
            <input id={`${id}-new`} value={newName} onChange={(event) => setNewName(event.target.value)} />
          </>
        )}
        <Actions onClose={onClose} submit="Read headings" disabled={!ready} />
      </form>
    </Frame>
  );
}
