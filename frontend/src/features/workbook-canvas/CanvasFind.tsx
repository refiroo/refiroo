/**
 * Find a list or a field on the canvas (0.17 CE1): type a name, Enter takes the first match (or the one the arrow
 * keys chose), and the page centres the board on it and selects it. Command or Ctrl with K puts the cursor here from
 * anywhere on the page. The matches are read from the draft's outline, so a list the scope leaves off the board is
 * found too.
 */

import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { ModelDraftOutline } from "@/types/modelAdmin";
import { findIn, type FindHit } from "./canvasView";

export function CanvasFind({ outline, onGo }: { outline: ModelDraftOutline; onGo: (hit: FindHit) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [open, setOpen] = useState(false);
  const list = useId();
  const hits = useMemo(() => findIn(outline, query), [outline, query]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!(event.metaKey || event.ctrlKey) || event.altKey || event.key.toLowerCase() !== "k") return;
      event.preventDefault();
      input.current?.focus();
      input.current?.select();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const go = (hit: FindHit | undefined) => {
    if (!hit) return;
    onGo(hit);
    setOpen(false);
    setQuery("");
  };
  const shown = open && query.trim() !== "";
  return (
    <div className="canvas-find">
      <input
        ref={input}
        type="search"
        role="combobox"
        aria-expanded={shown}
        aria-controls={list}
        aria-activedescendant={shown && hits[active] ? `${list}-${active}` : undefined}
        aria-label="Find an object type or attribute"
        placeholder="Find an object type or attribute (⌘K)"
        autoComplete="off"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setActive(0);
          setOpen(true);
        }}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onFocus={() => setOpen(true)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            setActive((now) => Math.max(0, Math.min(hits.length - 1, now + (event.key === "ArrowDown" ? 1 : -1))));
          } else if (event.key === "Enter") {
            event.preventDefault();
            go(hits[active] ?? hits[0]);
          } else if (event.key === "Escape") {
            setQuery("");
            setOpen(false);
            input.current?.blur();
          }
        }}
      />
      {shown && (
        <ul id={list} role="listbox" aria-label="Matches" className="canvas-find-list">
          {hits.length === 0 && <li className="canvas-find-none">Nothing is called that.</li>}
          {hits.map((hit, index) => (
            <li
              key={`${hit.typeKey}:${hit.fieldId ?? ""}`}
              id={`${list}-${index}`}
              role="option"
              aria-selected={index === active}
              className={index === active ? "active" : undefined}
              onMouseDown={(event) => {
                event.preventDefault();
                go(hit);
              }}
            >
              <span>{hit.label}</span>
              <small>
                {hit.fieldId ? `attribute of ${hit.hint}` : `object type${hit.hint ? ` in ${hit.hint}` : ""}`}
              </small>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
