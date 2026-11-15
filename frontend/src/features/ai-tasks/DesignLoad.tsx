/**
 * "What the load does" (0.13 AB): the engine's summary of the dry run of the assistant's items, which
 * accepting loads exactly. The figures, a table per type whose rows open to example records with the
 * cells they came from, the engine's findings, and the parts of the file folded.
 */

import { useState } from "react";
import { count, counted } from "@/lib/count";
import type { AiTaskLoad, AiTaskLoadExample, AiTaskLoadFinding, AiTaskLoadPart } from "@/types";
import { Card } from "@/ui/Card";
import { Disclosure } from "@/ui/Disclosure";
import { Notice } from "@/ui/Notice";
import { SettingsTable } from "@/ui/SettingsTable";
import type { ModelNames } from "./aiTaskDesign";
import { shown } from "./aiTaskText";

const FIGURES: { key: string; value: (load: AiTaskLoad) => number; label: (load: AiTaskLoad) => string }[] = [
  { key: "new", value: (l) => l.figures.recordsNew, label: () => "records new" },
  { key: "matched", value: (l) => l.figures.recordsMatched, label: () => "existing records matched" },
  {
    key: "links",
    value: (l) => l.figures.relationshipsNew,
    // The figure is what the load counts: the links of new records to their parents are in it.
    label: (l) => (l.figures.parentLinksNew ? "relationships new, with the links to parents" : "relationships new"),
  },
  { key: "refused", value: (l) => l.figures.refused, label: () => "refused" },
  {
    key: "rows",
    value: (l) => l.figures.rowsRead,
    label: (l) => (l.sheets.length > 0 ? `rows read from ${counted(l.sheets.length, "sheet")}` : "rows read"),
  },
];

/** A cell range as the file shows it: `Sheet!Q8:S247`. */
const range = (part: AiTaskLoadPart) => {
  const from = `${part.firstColumn}${part.firstRow}`;
  const to = `${part.lastColumn}${part.lastRow}`;
  return `${part.sheet}!${from}${from === to ? "" : `:${to}`}`;
};

/** Where a name appears twice: how many records sit at the top level and under which parents. */
function twice(finding: AiTaskLoadFinding, names: ModelNames): string {
  const places = new Map<string, number>();
  for (const parent of finding.parents) {
    const place = parent ? `under ${parent.name}` : "at the top level";
    places.set(place, (places.get(place) ?? 0) + 1);
  }
  const where = [...places].map(([place, n]) => (n > 1 ? `${n} ${place}` : `one ${place}`)).join(", ");
  return `“${finding.name}” is ${count(finding.count)} ${names.typePlural(finding.objectTypeKey)}: ${where}.`;
}

function Example({ example, names }: { example: AiTaskLoadExample; names: ModelNames }) {
  const values = example.values.map((v) => `${names.attribute(v.attributeTypeKey)}: ${shown(v.value)}`).join(" · ");
  return (
    <li>
      <strong>{example.name ?? "A record"}</strong>
      {example.action === "refused" ? (
        <> — refused: {example.error?.message ?? example.error?.code ?? "refused"}</>
      ) : (
        <> — {{ created: "new", updated: "found, changed", unchanged: "found, unchanged" }[example.action]}</>
      )}
      {values && <span className="load-values"> {values}</span>}
      {example.links.map((link, at) => (
        <span key={at} className="load-link">
          {" "}
          {link.direction === "incoming" ? "←" : "→"} {names.relation(link.relationTypeKey, link.direction)}{" "}
          {link.name ?? names.type(link.objectTypeKey)}
        </span>
      ))}
      {example.ref && <code className="load-source"> {example.ref}</code>}
    </li>
  );
}

export function DesignLoad({
  load,
  names,
  stale = false,
  moves = false,
}: {
  load: AiTaskLoad;
  names: ModelNames;
  /** The draft changed after the check: accepting checks every record again first. */
  stale?: boolean;
  /** The proposal moves records: accepting installs the model and loads nothing, the migration moves them. */
  moves?: boolean;
}) {
  const [open, setOpen] = useState<Set<string>>(new Set());
  const toggle = (key: string) =>
    setOpen((now) => {
      const next = new Set(now);
      if (!next.delete(key)) next.add(key);
      return next;
    });
  const sheets = [...new Set(load.parts.map((part) => part.sheet))];
  return (
    <Card as="section" title="What the load does" className="task-table">
      <p>
        The engine checked every record and relationship below against the model and your data, writing nothing.{" "}
        {moves
          ? "Accepting loads none of it: the records move by the migration you confirm first."
          : "Accepting loads exactly this."}
      </p>
      {stale && (
        <Notice tone="warning">
          The draft changed after this check. Accepting checks every record again first and loads nothing if any is
          refused.
        </Notice>
      )}
      <ul className="load-figures" aria-label="The load in figures">
        {FIGURES.map((figure) => (
          <li key={figure.key}>
            <strong>{count(figure.value(load))}</strong>
            <span>{figure.label(load)}</span>
          </li>
        ))}
      </ul>
      <SettingsTable
        label="What the load does to each type"
        columns={["Type", "New", "Matched", "Changed", "Refused", "Linked to"]}
      >
        {load.types.flatMap((type) => {
          const expanded = open.has(type.objectTypeKey);
          const label = names.type(type.objectTypeKey);
          return [
            <tr
              key={type.objectTypeKey}
              className={`load-type${expanded ? " is-open" : ""}`}
              tabIndex={0}
              aria-expanded={type.examples.length > 0 ? expanded : undefined}
              aria-label={`${label}: ${counted(type.new, "new record")}, ${counted(type.matched, "matched")}`}
              onClick={() => type.examples.length > 0 && toggle(type.objectTypeKey)}
              onKeyDown={(event) => {
                if (type.examples.length === 0 || (event.key !== "Enter" && event.key !== " ")) return;
                event.preventDefault();
                toggle(type.objectTypeKey);
              }}
            >
              <th scope="row" data-label="Type">
                {type.examples.length > 0 && (
                  <span className="load-chevron" aria-hidden="true">
                    {expanded ? "⌄" : "›"}
                  </span>
                )}
                {label}
              </th>
              <td data-label="New">{count(type.new)}</td>
              <td data-label="Matched">{count(type.matched)}</td>
              <td data-label="Changed">{count(type.changed)}</td>
              <td data-label="Refused">{count(type.refused)}</td>
              <td data-label="Linked to">{type.linkedTo.map((key) => names.type(key)).join(", ") || "—"}</td>
            </tr>,
            ...(expanded
              ? [
                  <tr key={`${type.objectTypeKey}-examples`} className="load-examples">
                    <td colSpan={6}>
                      <ul className="task-sheet-list" aria-label={`Examples of ${label}`}>
                        {type.examples.map((example) => (
                          <Example key={example.index} example={example} names={names} />
                        ))}
                      </ul>
                    </td>
                  </tr>,
                ]
              : []),
          ];
        })}
      </SettingsTable>
      {(load.relationships.length > 0 || !!load.figures.parentLinksNew) && (
        <p className="task-reason">
          Relationships:{" "}
          {[
            ...load.relationships.map(
              (r) =>
                `${names.relation(r.relationTypeKey)} ${count(r.new)} new${r.matched ? `, ${count(r.matched)} found` : ""}`,
            ),
            ...(load.figures.parentLinksNew
              ? [`${counted(load.figures.parentLinksNew, "link")} of new records to their parents`]
              : []),
          ].join("; ")}
          .
        </p>
      )}
      {load.figures.refused > 0 && (
        <Notice tone="warning" title={`${counted(load.figures.refused, "item")} refused`}>
          <ul className="task-sheet-list">
            {load.refused.slice(0, 10).map((item) => (
              <li key={item.index}>
                {item.ref && <code>{item.ref}</code>} {item.message ?? item.code}
              </li>
            ))}
          </ul>
        </Notice>
      )}
      {load.findings.map((finding) => (
        <Notice key={`${finding.objectTypeKey}-${finding.name}`} tone="info" title="One name twice in one type">
          {twice(finding, names)}
        </Notice>
      ))}
      {load.parts.length > 0 && (
        <Disclosure
          variant="button"
          label="Where each part of the file goes"
          openLabel="Hide where each part of the file goes"
        >
          {sheets.map((sheet) => (
            <div key={sheet}>
              <strong>Sheet “{sheet}”</strong>
              <ul className="task-sheet-list">
                {load.parts
                  .filter((part) => part.sheet === sheet)
                  .map((part, at) => (
                    <li key={at}>
                      <code>{range(part)}</code>{" "}
                      {part.objectTypeKey
                        ? names.typePlural(part.objectTypeKey)
                        : `${names.relation(part.relationTypeKey)} relationships`}{" "}
                      ({counted(part.items, "item")})
                    </li>
                  ))}
              </ul>
            </div>
          ))}
          {load.partsTotal > load.parts.length && (
            <p className="task-reason">{count(load.partsTotal - load.parts.length)} more parts are not listed.</p>
          )}
        </Disclosure>
      )}
    </Card>
  );
}
