import { useState } from "react";

/**
 * What the browser keeps for the person: in `localStorage` (this browser, for good) or, for the
 * `Session` variants, in `sessionStorage` (this tab, until it closes). A value is JSON; one that is
 * missing, unreadable or not what `validate` accepts reads as `fallback`, and a write the browser
 * refuses is dropped: a preference is optional and the interaction stays usable without it.
 */
function read<T>(area: () => Storage, key: string, fallback: T, validate: (value: unknown) => value is T): T {
  try {
    const raw = area().getItem(key);
    if (!raw) return fallback;
    const value: unknown = JSON.parse(raw);
    return validate(value) ? value : fallback;
  } catch {
    return fallback;
  }
}

function write(area: () => Storage, key: string, value: unknown) {
  try {
    area().setItem(key, JSON.stringify(value));
  } catch {
    // Preferences are optional; the interaction remains usable when storage is blocked.
  }
}

export const readLocalPreference = <T>(key: string, fallback: T, validate: (value: unknown) => value is T): T =>
  read(() => window.localStorage, key, fallback, validate);

export const writeLocalPreference = (key: string, value: unknown) => write(() => window.localStorage, key, value);

export const readSessionPreference = <T>(key: string, fallback: T, validate: (value: unknown) => value is T): T =>
  read(() => window.sessionStorage, key, fallback, validate);

export const writeSessionPreference = (key: string, value: unknown) => write(() => window.sessionStorage, key, value);

export function removeLocalPreference(key: string) {
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Reset still applies to the current session when storage is blocked.
  }
}

export function useLocalNumberPreference(key: string, defaultValue: number, min: number, max: number) {
  const valid = (value: unknown): value is number =>
    typeof value === "number" && Number.isFinite(value) && value >= min && value <= max;
  const load = () => readLocalPreference(key, defaultValue, valid);
  const [stored, setStored] = useState<{ key: string; value: number }>(() => ({ key, value: load() }));
  const value = stored.key === key ? stored.value : load();
  const change = (next: number) => {
    const safe = Math.min(max, Math.max(min, Math.round(next)));
    setStored({ key, value: safe });
    writeLocalPreference(key, safe);
  };
  const reset = () => {
    removeLocalPreference(key);
    setStored({ key, value: defaultValue });
  };
  return { value, change, reset };
}
