/**
 * Text the assistant wrote, as people read it: paragraphs at blank lines, "- " lines as a list, and
 * **bold** and `code` inside a line. Anything else stays text; nothing is ever read as HTML.
 */

import type { ReactNode } from "react";

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

export function AssistantText({ text }: { text: string }) {
  const blocks: { list: boolean; lines: string[] }[] = [];
  for (const raw of text.replace(/\r\n?/g, "\n").split("\n")) {
    if (!raw.trim()) {
      blocks.push({ list: false, lines: [] });
      continue;
    }
    const bullet = BULLET.test(raw);
    const last = blocks[blocks.length - 1];
    if (bullet) {
      if (last?.list) last.lines.push(raw.replace(BULLET, ""));
      else blocks.push({ list: true, lines: [raw.replace(BULLET, "")] });
    } else if (last && !last.list && last.lines.length > 0) last.lines.push(raw.trim());
    else blocks.push({ list: false, lines: [raw.trim()] });
  }
  return (
    <>
      {blocks
        .filter((block) => block.lines.length > 0)
        .map((block, index) =>
          block.list ? (
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
