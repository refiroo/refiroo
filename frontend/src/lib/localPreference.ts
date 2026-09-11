import { useState } from "react";

export function readLocalPreference<T>(key: string, fallback: T, validate: (value: unknown) => value is T): T {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return fallback;
    const value: unknown = JSON.parse(raw);
    return validate(value) ? value : fallback;
  } catch {
    return fallback;
  }
}

export function writeLocalPreference(key: string, value: unknown) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Preferences are optional; the interaction remains usable when storage is blocked.
  }
}

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
