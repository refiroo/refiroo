import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// What the person may do is read once per page load (0.12 Z5); each test starts afresh, read
// through the test's own mock of the API client. Registered first so it runs after `cleanup`
// (after-hooks run in reverse): a page still mounted would read again with this test's mock.
afterEach(async () => (await import("@/features/security/permissions")).resetPermissionsForTests());
// A preference one test saved (an open section, a hidden column) does not reach the next. Under Node 22
// jsdom's storage keeps it across a file's tests; Node 26 leaves `localStorage` undefined without
// `--localstorage-file`, so the app saved nothing and the leak did not show there.
afterEach(() => {
  globalThis.localStorage?.clear?.();
  globalThis.sessionStorage?.clear?.();
});
afterEach(cleanup);
