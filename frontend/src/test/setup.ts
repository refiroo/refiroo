import "@testing-library/jest-dom/vitest";
// First, so its after-hook runs last: a component unmounted by `cleanup` has logged by then.
import "./consoleGuard";
import { cleanup, configure } from "@testing-library/react";
import { afterEach } from "vitest";

// What the person may do is read once per page load (0.12 Z5); each test starts afresh, read
// through the test's own mock of the API client. Registered first so it runs after `cleanup`
// (after-hooks run in reverse): a page still mounted would read again with this test's mock.
afterEach(async () => (await import("@/state/permissions")).resetPermissionsForTests());
// A preference one test saved (an open section, a hidden column) does not reach the next. Under Node 22
// jsdom's storage keeps it across a file's tests; Node 26 leaves `localStorage` undefined without
// `--localstorage-file`, so the app saved nothing and the leak did not show there.
afterEach(() => {
  globalThis.localStorage?.clear?.();
  globalThis.sessionStorage?.clear?.();
});
afterEach(cleanup);

// findBy… and waitFor wait 5 s, not the library's 1 s: on a loaded CI runner a list or stream can take
// longer than a second to arrive, and a different test failed each run (CL1, 2026-11-08).
configure({ asyncUtilTimeout: 5000 });
