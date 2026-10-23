/**
 * A browser as a person recognises it, "Firefox on macOS", from the name it gave the engine when it
 * signed in (0.12 I2). Anything not recognised is shown as it was sent.
 */

const BROWSERS: [RegExp, string][] = [
  [/Edg\//, "Edge"],
  [/OPR\/|Opera/, "Opera"],
  [/Firefox\//, "Firefox"],
  [/Chrome\/|CriOS\//, "Chrome"],
  [/Safari\//, "Safari"],
];

const SYSTEMS: [RegExp, string][] = [
  [/iPhone|iPad|iPod/, "iOS"],
  [/Android/, "Android"],
  [/Mac OS X|Macintosh/, "macOS"],
  [/Windows/, "Windows"],
  [/CrOS/, "ChromeOS"],
  [/Linux/, "Linux"],
];

export function browserName(userAgent: string | null): string {
  if (!userAgent) return "Unknown browser";
  const browser = BROWSERS.find(([pattern]) => pattern.test(userAgent))?.[1];
  const system = SYSTEMS.find(([pattern]) => pattern.test(userAgent))?.[1];
  if (!browser) return userAgent;
  return system ? `${browser} on ${system}` : browser;
}

/** Whether a session's browser is on a phone or tablet, for its icon. */
export function onPhone(userAgent: string | null): boolean {
  return userAgent !== null && /iPhone|iPad|iPod|Android|Mobile/.test(userAgent);
}
