/**
 * Text the assistant wrote, as people read it: paragraphs at blank lines, "- " lines as a list, a
 * markdown table ("| a | b |" lines under a "|---|---|" line) as the app's ruled table, and
 * **bold** and `code` inside a line. Anything else stays text; nothing is ever read as HTML.
 */

import type { ReactNode } from "react";
import { SettingsTable } from "./SettingsTable";

const BULLET = /^\s*(?:[-*•]|\d+[.)])\s+/;

function inline(line: string): ReactNode[] {
  return line
    .split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
    .filter(Boolean)
    .map((part, index) => {
      if (part.startsWith("**") && part.endsWith("**") && part.length > 4)
        return <strong key={index}>{part.slice(2, -2)}</strong>;
      if (part.startsWith("`") && part.endsWith("`") && part.length > 2)
        return <code key={index}>{part.slice(1, -1)}</code>;
      return part;
    });
}

const ROW = /^\s*\|.*\|\s*$/;
const RULE = /^\s*\|(?:\s*:?-{2,}:?\s*\|)+\s*$/;

function cells(line: string): string[] {
  return line
    .trim()
    .slice(1, -1)
    .split("|")
    .map((cell) => cell.trim());
}

type Block = { kind: "p" | "list" | "table"; lines: string[] };

export function AssistantText({ text }: { text: string }) {
  const blocks: Block[] = [];
  const rawLines = text.replace(/\r\n?/g, "\n").split("\n");
  rawLines.forEach((raw, at) => {
    if (!raw.trim()) {
      blocks.push({ kind: "p", lines: [] });
      return;
    }
    const last = blocks[blocks.length - 1];
    if (last?.kind === "table" && RULE.test(raw) && last.lines.length === 1) return;
    if (last?.kind === "table" && ROW.test(raw)) {
      last.lines.push(raw);
      return;
    }
    if (ROW.test(raw) && RULE.test(rawLines[at + 1] ?? "")) {
      blocks.push({ kind: "table", lines: [raw] });
      return;
    }
    if (BULLET.test(raw)) {
      if (last?.kind === "list") last.lines.push(raw.replace(BULLET, ""));
      else blocks.push({ kind: "list", lines: [raw.replace(BULLET, "")] });
    } else if (last?.kind === "p" && last.lines.length > 0) last.lines.push(raw.trim());
    else blocks.push({ kind: "p", lines: [raw.trim()] });
  });
  return (
    <>
      {blocks
        .filter((block) => block.lines.length > 0)
        .map((block, index) =>
          block.kind === "table" ? (
            <NoteTable key={index} lines={block.lines} />
          ) : block.kind === "list" ? (
            <ul key={index}>
              {block.lines.map((line, at) => (
                <li key={at}>{inline(line)}</li>
              ))}
            </ul>
          ) : (
            <p key={index}>{inline(block.lines.join(" "))}</p>
          ),
        )}
    </>
  );
}

/** The header row, then the body rows; a row's first cell is its head, the others carry their column's name for the phone layout. */
function NoteTable({ lines }: { lines: string[] }) {
  const [head, ...body] = lines.map(cells);
  return (
    <SettingsTable
      label={head.filter(Boolean).join(", ") || "Table"}
      columns={head.map((name, at) => name || `Column ${at + 1}`)}
    >
      {body.map((row, at) => (
        <tr key={at}>
          {head.map((name, column) =>
            column === 0 ? (
              <th key={column} scope="row">
                {inline(row[column] ?? "")}
              </th>
            ) : (
              <td key={column} data-label={name}>
                {inline(row[column] ?? "")}
              </td>
            ),
          )}
        </tr>
      ))}
    </SettingsTable>
  );
}
