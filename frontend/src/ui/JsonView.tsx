import { CopyValue } from "@/ui/CopyValue";

/** JSON text formatted with two-space indents, or `undefined` when the text is not JSON. */
function formatted(value: unknown): string | undefined {
  if (typeof value !== "string") return JSON.stringify(value, null, 2);
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return undefined;
  }
}

// A key (a string followed by a colon), a string, a literal or a number.
const TOKEN = /("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g;

function highlighted(text: string) {
  const parts: React.ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(TOKEN)) {
    const index = match.index ?? 0;
    if (index > last) parts.push(text.slice(last, index));
    const [whole, string, colon, literal] = match;
    const kind = string ? (colon ? "key" : "string") : literal ? "literal" : "number";
    parts.push(
      <span key={index} className={`json-${kind}`}>
        {string ?? whole}
      </span>,
    );
    if (colon) parts.push(colon);
    last = index + whole.length;
  }
  parts.push(text.slice(last));
  return parts;
}

/**
 * A request or response body (U5a): JSON formatted and coloured by kind of token, or the text as it
 * came when it is not JSON; with a copy of what is shown. Scrolls within its frame.
 */
export function JsonView({ label, value }: { label: string; value: unknown }) {
  const json = formatted(value);
  const text = json ?? String(value ?? "");
  return (
    <div className="json-view">
      <div className="json-view-bar">
        <span>{json !== undefined ? "JSON" : "Text"}</span>
        <CopyValue label={label} value={text} buttonOnly />
      </div>
      <pre tabIndex={0} aria-label={label}>
        <code>{json !== undefined ? highlighted(json) : text}</code>
      </pre>
    </div>
  );
}
