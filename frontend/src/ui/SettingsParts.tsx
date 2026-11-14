/**
 * The parts every Settings page is drawn from (0.17 ST1, PP-D60 to PP-D67): a group that says what it is about
 * beside its panels, a panel of rows, a row with its control, the header of an opened item, the tools above a
 * list and the foot under a log. Styles: `styles/settings-family.css`.
 */

import { useId, type ReactNode } from "react";
import type { Hue } from "@/model/hues";
import { HUE_SLOTS } from "@/model/hues";
import { Icon, type IconName } from "@/ui/Icon";

/** A stable hue for a named thing that has none of its own (a person, a client, a group): by its text. */
export function hueOf(text: string): Hue {
  let sum = 0;
  for (let at = 0; at < text.length; at += 1) sum = (sum * 31 + text.charCodeAt(at)) % 9973;
  return ((sum % HUE_SLOTS) + 1) as Hue;
}

/**
 * A person's, a client's or a group's initials: the first letters of the first and last words of the
 * name. Only letters count (0.17 SH1): a bracketed note such as "(temporary)" is not part of the name,
 * and a word with no letter in it gives none, so "Name (temporary)" reads N and not N(. A name with no
 * letter at all (a client named "42") keeps its first two characters as its mark (0.17.2 FX1, D5).
 */
export function initials(name: string): string {
  const of = (text: string) => {
    const words = text.split(/\s+/).filter((word) => /\p{L}/u.test(word));
    const ends = words.length > 1 ? [words[0], words[words.length - 1]] : words;
    return ends.map((word) => word.match(/\p{L}/u)?.[0].toUpperCase() ?? "").join("");
  };
  // A name that is only a bracketed note still gets its letters.
  return of(name.replace(/[([{][^)\]}]*[)\]}]/gu, " ")) || of(name) || name.trim().slice(0, 2).toUpperCase();
}

/** A coloured tile holding a glyph: a row's lead, a page's mark. Decorative. */
export function SettingsTile({ icon, hue, size = 36 }: { icon: IconName; hue?: Hue; size?: 32 | 36 | 44 | 48 }) {
  return (
    <span className={`settings-tile settings-tile-${size}`} data-hue={hue} aria-hidden="true">
      <Icon name={icon} size={size >= 44 ? 22 : 16} />
    </span>
  );
}

/** A person's (or a client's) initials in their colour. Decorative: the name stands beside it. */
export function NameMark({ name, hue, size = 36 }: { name: string; hue?: Hue; size?: 36 | 64 }) {
  return (
    <span className={`name-mark name-mark-${size}`} data-hue={hue ?? hueOf(name)} aria-hidden="true">
      {initials(name)}
    </span>
  );
}

/**
 * A group of a settings page: its title and what it is about on the left, with the group's own action under
 * them (PP-D63), and its panels on the right. `stacked` is for a group holding a table: the heading above,
 * `tools` (filters, Refresh) at the heading's right, the body as wide as the page.
 */
export function SettingsGroup({
  title,
  description,
  action,
  tools,
  stacked = false,
  className,
  children,
}: {
  title: ReactNode;
  description?: ReactNode;
  /** The group's own action, such as Add role: a secondary button. */
  action?: ReactNode;
  /** Filters and Refresh of a stacked group. */
  tools?: ReactNode;
  stacked?: boolean;
  className?: string;
  children?: ReactNode;
}) {
  const headingId = useId();
  return (
    <section
      className={["settings-group", stacked && "settings-group-stacked", className].filter(Boolean).join(" ")}
      aria-labelledby={headingId}
    >
      <div className="settings-group-about">
        <div className="settings-group-text">
          <h2 id={headingId}>{title}</h2>
          {description && <div className="settings-group-description">{description}</div>}
          {action && !stacked && <div className="settings-group-action">{action}</div>}
        </div>
        {(tools || (action && stacked)) && (
          <div className="settings-group-tools">
            {tools}
            {stacked && action}
          </div>
        )}
      </div>
      <div className="settings-group-body">{children}</div>
    </section>
  );
}

/** A raised panel holding rows, a table or a set of fields; `note` and `foot` close it. */
export function SettingsPanel({
  children,
  note,
  foot,
  className,
  label,
}: {
  children: ReactNode;
  /** One muted sentence under the rows. */
  note?: ReactNode;
  /** The panel's foot: the state at the left, Cancel and Save at the right (fields saved together). */
  foot?: ReactNode;
  className?: string;
  /** Names the panel where its group's heading does not (a second panel of a group). */
  label?: string;
}) {
  return (
    <div
      className={["settings-panel", className].filter(Boolean).join(" ")}
      role={label ? "group" : undefined}
      aria-label={label}
    >
      {children}
      {note && <p className="settings-panel-note">{note}</p>}
      {foot && <div className="settings-panel-foot">{foot}</div>}
    </div>
  );
}

/**
 * One row of a panel: an optional lead (a tile, a mark), the name with a line of help, and at the right its
 * control or value (a switch, a choice, a button, text). `fact` is a read-only pair with the name muted;
 * `under` puts a wide control under the text at every width; `keep` holds a switch at the right on a phone.
 */
export function SettingRow({
  lead,
  name,
  help,
  children,
  fact = false,
  under = false,
  keep = false,
  className,
}: {
  lead?: ReactNode;
  name: ReactNode;
  help?: ReactNode;
  /** The control or the value. */
  children?: ReactNode;
  fact?: boolean;
  under?: boolean;
  /** A small control (a switch) stays at the row's right on a phone too. */
  keep?: boolean;
  className?: string;
}) {
  const classes = [
    "setting-row",
    fact && "setting-row-fact",
    under && "setting-row-under",
    keep && "setting-row-keep",
    lead && "has-lead",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={classes}>
      {lead}
      <div className="setting-row-text">
        <div className="setting-row-name">{name}</div>
        {help && <div className="setting-row-help">{help}</div>}
      </div>
      {children !== undefined && children !== null && children !== false && (
        <div className="setting-row-value">{children}</div>
      )}
    </div>
  );
}

/** A panel with nothing in it yet: one sentence, a tile in the page's colour and the action that fills it. */
export function SettingsEmpty({
  icon,
  hue,
  children,
  action,
}: {
  icon?: IconName;
  hue?: Hue;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="settings-empty">
      {icon && <SettingsTile icon={icon} hue={hue} size={44} />}
      <p>{children}</p>
      {action && <div className="settings-empty-action">{action}</div>}
    </div>
  );
}

/**
 * The header of an opened item (a person, a client, a workspace): its mark, its name as the page's `h1`, a line
 * of facts and pills, and its actions (at most two shown, the rest in a ⋯ menu, PP-D63), on a band in its colour.
 */
export function ItemHeader({
  lead,
  hue,
  title,
  meta,
  actions,
}: {
  lead?: ReactNode;
  hue?: Hue;
  /** The `h1`, or the name's editor in place. */
  title: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="item-header" data-hue={hue}>
      {lead}
      <div className="item-header-text">
        {title}
        {meta && <div className="item-header-meta">{meta}</div>}
      </div>
      {actions && <div className="item-header-actions">{actions}</div>}
    </header>
  );
}

/** The tools above a list: the search, the states as chips, and a count at the right. */
export function SettingsTools({ children, count }: { children: ReactNode; count?: ReactNode }) {
  return (
    <div className="settings-tools">
      {children}
      {count !== undefined && <span className="settings-tools-count">{count}</span>}
    </div>
  );
}

/** A chip that narrows a list or a log to one state; `hue` gives its marker the kind's colour. */
export function FilterChip({
  selected,
  onSelect,
  hue,
  children,
}: {
  selected: boolean;
  onSelect: () => void;
  hue?: Hue;
  children: ReactNode;
}) {
  return (
    <button type="button" className="filter-chip" aria-pressed={selected} onClick={onSelect}>
      {hue && <span className="kind-dot" data-hue={hue} aria-hidden="true" />}
      {children}
    </button>
  );
}

/** A kind of thing in a log, with its colour's marker before its name (PP-D67). */
export function Kind({ hue, children }: { hue?: Hue; children: ReactNode }) {
  return (
    <span className="kind">
      <span className="kind-dot" data-hue={hue} aria-hidden="true" />
      {children}
    </span>
  );
}

/** Under a log or a long list: how many are shown of how many, and Show more (PP-D64). */
export function LogFoot({
  shown,
  total,
  noun,
  onMore,
  loading = false,
}: {
  shown: number;
  /** Unknown while the server gives no total. */
  total?: number;
  /** What is counted, plural: "calls". */
  noun: string;
  /** Present while more can be read. */
  onMore?: () => void;
  loading?: boolean;
}) {
  return (
    <div className="log-foot">
      <span role="status">
        {total !== undefined
          ? `${shown.toLocaleString()} of ${total.toLocaleString()} ${noun}`
          : `${shown.toLocaleString()} ${noun}`}
      </span>
      {onMore && (
        <button type="button" className="secondary" onClick={onMore} disabled={loading}>
          {loading ? "Loading…" : "Show more"}
        </button>
      )}
    </div>
  );
}

/** Totals above a log: each a number over its name, with a marker in its colour; `bad` marks a failure count. */
export function LogTotals({
  label,
  totals,
}: {
  label: string;
  totals: { key: string; value: ReactNode; name: string; hue?: Hue; bad?: boolean }[];
}) {
  return (
    <dl className="log-totals settings-panel" aria-label={label}>
      {totals.map((total) => (
        <div key={total.key} className={total.bad ? "log-total bad" : "log-total"} data-hue={total.hue}>
          <dd>{total.value}</dd>
          <dt>{total.name}</dt>
        </div>
      ))}
    </dl>
  );
}
