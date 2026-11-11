/**
 * A test that logs an error or a warning fails (0.17 RF7). React's own warnings (invalid nesting, a
 * duplicate key, an update outside `act`), a caught render error and a request nobody expected all
 * reach `console.error` or `console.warn`; a passing run with them in its output is not accepted.
 *
 * A test that causes one on purpose says so, once, in the test: `expectConsoleError(/pattern/)`
 * (`expectConsoleWarn` for a warning) before the action. The message is then required: a test that
 * names a message nothing logged fails too. There is no list of allowed messages anywhere else.
 *
 * Loaded by the Vitest setup of every project (`vite.config.ts`).
 */

import { afterEach, beforeEach, vi } from "vitest";

type Level = "error" | "warn";
type Expectation = { level: Level; pattern: RegExp | string; matched: boolean };

type Guard = { inTest: boolean; logged: { level: Level; text: string }[]; expected: Expectation[] };
// On `globalThis`, so the setup file's hooks and the test file's `expectConsoleError` share one state.
const holder = globalThis as typeof globalThis & { __consoleGuard?: Guard };
const state: Guard = (holder.__consoleGuard ??= { inTest: false, logged: [], expected: [] });

const original = { error: console.error, warn: console.warn };

/** The message as the console prints it: `%s`-style placeholders filled in, `%c` styles dropped. */
function format(args: unknown[]) {
  const [first, ...rest] = args;
  const text = (value: unknown) => (value instanceof Error ? `${value.name}: ${value.message}` : String(value));
  if (typeof first !== "string") return args.map(text).join(" ");
  const filled = first.replace(/%([sdifoOjc%])/g, (placeholder, kind: string) => {
    if (kind === "%") return "%";
    if (!rest.length) return placeholder;
    const value = rest.shift();
    return kind === "c" ? "" : text(value);
  });
  return [filled, ...rest.map(text)].join(" ");
}

function record(level: Level) {
  return (...args: unknown[]) => {
    // Output outside a test (a late timer after the file's last test) is shown as it always was.
    if (!state.inTest) return void original[level](...args);
    // React's messages hold `%s` placeholders: the formatted text is what a pattern is matched against.
    state.logged.push({ level, text: format(args) });
  };
}

const matches = (pattern: RegExp | string, text: string) =>
  typeof pattern === "string" ? text.includes(pattern) : pattern.test(text);

function expectConsole(level: Level, pattern: RegExp | string) {
  state.expected.push({ level, pattern, matched: false });
}

/** This test logs an error matching `pattern` on purpose (an error boundary's catch, a refused request). */
export const expectConsoleError = (pattern: RegExp | string) => expectConsole("error", pattern);
/** This test logs a warning matching `pattern` on purpose. */
export const expectConsoleWarn = (pattern: RegExp | string) => expectConsole("warn", pattern);

beforeEach(() => {
  state.inTest = true;
  state.logged = [];
  state.expected = [];
  vi.spyOn(console, "error").mockImplementation(record("error"));
  vi.spyOn(console, "warn").mockImplementation(record("warn"));
});

// Registered first, so it runs last (after-hooks run in reverse): a component unmounted by a cleanup
// hook logs its last messages before the check.
afterEach(() => {
  state.inTest = false;
  const { logged, expected } = state;
  state.logged = [];
  state.expected = [];
  // `restoreAllMocks` in a test would have put the console back already: put the originals back anyway.
  vi.mocked(console.error).mockRestore?.();
  vi.mocked(console.warn).mockRestore?.();
  const unexpected = logged.filter((entry) => {
    const named = expected.find((item) => item.level === entry.level && matches(item.pattern, entry.text));
    if (named) named.matched = true;
    return !named;
  });
  const missing = expected.filter((item) => !item.matched);
  const problems = [
    ...unexpected.map((entry) => `console.${entry.level}: ${entry.text}`),
    ...missing.map((item) => `expected console.${item.level} matching ${String(item.pattern)}, none was logged`),
  ];
  if (problems.length)
    throw new Error(
      `The test wrote to the console (a test that does so on purpose says it with expectConsoleError):\n${problems.join("\n---\n")}`,
    );
});
