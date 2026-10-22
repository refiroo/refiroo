// 0.9 U3 browser evidence: the Settings area against a real backend, at 1440px and 390px. Settings
// opened from the gear in two applications, in the same top bar, and left with each application's
// tab back to where it was; every page;
// every address the settings area replaced; the default table density from Appearance seen in two
// views of different object types, with a view's own choice winning; and the keyboard order.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

let harness;
const checks = [];
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

const PAGES = [
  ["About", "/settings/about", (page) => page.getByRole("region", { name: "Database" })],
  ["Appearance", "/settings/appearance", (page) => page.getByRole("group", { name: "Table density" })],
  ["Workspaces", "/settings/workspaces", (page) => page.getByRole("navigation", { name: "Workspace catalogue" })],
  ["Model", "/settings/model", (page) => page.getByRole("navigation", { name: "Model catalogue" })],
  ["Deployment", "/settings/deployment", (page) => page.getByRole("region", { name: "Capability groups" })],
];

const VIEWS = [
  ["/apps/rdm-master/views/domains?workspaceKey=default", "Domain 00"],
  ["/apps/rdm-systems/views/systems?workspaceKey=default", "System 00"],
];

try {
  harness = await bootHarness({ modelAdmin: true, workspaceAdmin: true });
  const { page, browser, uiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}.png`), fullPage: true });
  const path = () => new URL(page.url()).pathname;
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const activeRelease = (await api("/workspaces/default/model")).releaseId;

  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    const suffix = width === 390 ? "narrow" : "wide";

    // 1. Settings from the gear in two applications, in the same top bar; the tab of the
    //    application it came from returns to that view with its query.
    for (const [view, record] of VIEWS) {
      await page.goto(`${uiUrl}${view}&search=0`);
      await page.getByRole("button", { name: record, exact: true }).waitFor();
      const from = page.url();
      const tabs = page.getByRole("navigation", { name: "Applications" }).getByRole("button");
      const appTabs = await tabs.allInnerTexts();
      const current = await page
        .locator('nav[aria-label="Applications"] [aria-current="page"]')
        .evaluate((tab) => tab.textContent.trim());
      const appBar = await page.getByRole("banner").boundingBox();
      // The current page is marked by the tabs' ink underline (an icon has no text weight to compare).
      const mark = (element) => {
        const style = getComputedStyle(element);
        return `${style.borderBottomColor} ${style.borderBottomWidth}`;
      };
      const appCurrent = await page.locator('nav[aria-label="Applications"] [aria-current="page"]').evaluate(mark);
      const settingsIcon = page.getByRole("banner").getByRole("link", { name: "Settings", exact: true });
      const iconBefore = await settingsIcon.boundingBox();
      await settingsIcon.click();
      await page.getByRole("heading", { level: 1, name: "About" }).waitFor();
      expect(path() === "/settings/about", `${suffix}: gear opened ${page.url()}`);
      expect(
        JSON.stringify(await tabs.allInnerTexts()) === JSON.stringify(appTabs),
        `${suffix}: settings top bar tabs differ from the application's`,
      );
      expect((await page.locator('nav[aria-label="Applications"] [aria-current]').count()) === 0, "a tab is current");
      expect(
        (await page.getByRole("banner").getByRole("link", { name: "Settings" }).getAttribute("aria-current")) ===
          "page",
        "Settings link not current",
      );
      const settingsBar = await page.getByRole("banner").boundingBox();
      // One top bar on every page (2026-10-15): the Settings icon keeps its place and width.
      const settingsTab = page.getByRole("banner").getByRole("link", { name: "Settings", exact: true });
      const iconAfter = await settingsTab.boundingBox();
      expect(
        Math.abs(iconAfter.x - iconBefore.x) < 1 && Math.abs(iconAfter.width - iconBefore.width) < 1,
        `${suffix}: the Settings icon moved or changed width (${JSON.stringify([iconBefore, iconAfter])})`,
      );
      const settingsCurrent = await settingsTab.evaluate(mark);
      expect(
        settingsCurrent === appCurrent,
        `${suffix}: Settings is marked ${settingsCurrent}, a current tab ${appCurrent}`,
      );
      if (width === 1440) {
        // The tabs keep 36px from the product mark (UA4 revision).
        const before = await page.locator(".global-header > .product-mark").last().boundingBox();
        const tab = await tabs.first().boundingBox();
        const gap = Math.round(tab.x - (before.x + before.width));
        expect(gap === 36, `settings: the tabs start ${gap}px after the item before them, not 36px`);
      }
      expect(
        settingsBar.height === appBar.height,
        `${suffix}: top bar height ${settingsBar.height} vs ${appBar.height}`,
      );
      expect((await page.getByRole("link", { name: "Back to applications" }).count()) === 0, "a second bar's Back");
      expect((await page.getByLabel("Current context").count()) === 0, "data-context band shown");
      expect((await page.getByRole("combobox", { name: "Workspace", exact: true }).count()) === 0, "switcher shown");
      // Settings has no way back of its own: the application tabs and the product mark leave it
      // (2026-10-15, one top bar on every page).
      expect(
        (await page
          .getByRole("banner")
          .getByRole("link", { name: /^Back to / })
          .count()) === 0,
        "a way back shown",
      );
      if (width === 390) {
        // On a phone the top bar has no tabs (0.10 N1): the product mark leaves Settings.
        await page.getByRole("banner").locator(".product-mark").first().click();
        await page.waitForURL((url) => !url.pathname.startsWith("/settings"));
      } else {
        await tabs.filter({ hasText: current }).click();
        await page.getByRole("button", { name: record, exact: true }).waitFor();
        expect(
          new URL(page.url()).pathname === new URL(from).pathname,
          `${suffix}: the application's tab returned to ${page.url()}, not ${from}`,
        );
      }
    }
    checks.push(
      `${suffix}: the gear opens Settings in the same top bar (same tabs and height, tabs 36px after the product name at 1440px, none current, Settings a current tab marked as the application's is) from two applications; each application's tab returns to its view with its query`,
    );

    // 2. Every page, through the rail (wide) or the navigation drawer (narrow).
    await page.goto(`${uiUrl}/settings/about`);
    for (const [label, address, ready] of PAGES) {
      if (width === 390) {
        expect((await page.getByRole("navigation", { name: "Settings" }).isVisible()) === false, "rail shown at 390px");
        await page.getByRole("button", { name: /^Settings: / }).click();
        const drawer = page.getByRole("dialog", { name: "Settings navigation" });
        await drawer.getByRole("link", { name: label, exact: true }).click();
        await drawer.waitFor({ state: "detached" });
        await page.getByRole("button", { name: `Settings: ${label}` }).waitFor();
      } else {
        const link = page.getByRole("navigation", { name: "Settings" }).getByRole("link", { name: label, exact: true });
        await link.click();
        await page.waitForURL(`**${address}`);
        expect((await link.getAttribute("aria-current")) === "page", `${label} not marked current`);
      }
      await page.getByRole("heading", { level: 1, name: label, exact: true }).waitFor();
      await ready(page).waitFor();
      expect(path() === address, `${suffix}: ${label} at ${page.url()}`);
      const scroll = await overflow();
      expect(scroll <= 0, `${suffix}: ${label} scrolls horizontally by ${scroll}px`);
      await shot(`u3-${label.toLowerCase()}-${suffix}`);
    }
    await page.goto(`${uiUrl}/settings/model/releases/${activeRelease}`);
    await page.getByRole("button", { name: "Export JSON" }).waitFor();
    // A release opens in Settings › Model beside its catalogue, on a phone with the way back to it
    // (0.11 M6, the layout left after the rework).
    await (
      width === 390
        ? page.getByRole("button", { name: "All models" })
        : page.getByRole("navigation", { name: "Model catalogue" })
    ).waitFor();
    await page.goto(`${uiUrl}/settings/workspaces/default`);
    await page.getByRole("button", { name: "Open workspace" }).waitFor();
    await page
      .getByRole(width === 390 ? "button" : "navigation", {
        name: width === 390 ? "All workspaces" : "Workspace catalogue",
      })
      .waitFor();
    checks.push(
      `${suffix}: every settings page, a release's page and a workspace's page open at their own URLs without horizontal scroll`,
    );
  }
  await page.setViewportSize({ width: 1440, height: 900 });

  // About and Deployment read the deployment: the engine version, the active release, the settings.
  await page.goto(`${uiUrl}/settings/about`);
  const system = await api("/system");
  const engine = page.getByRole("region", { name: "Engine" });
  await engine.getByText(system.engine.version, { exact: true }).waitFor();
  await page.getByRole("region", { name: "Database" }).getByText(system.database.revision, { exact: true }).waitFor();
  await page.getByRole("button", { name: "Open release" }).click();
  await page.waitForURL(`**/settings/model/releases/${system.activeModelRelease.id}`);
  await page.goto(`${uiUrl}/settings/deployment`);
  const runtime = page.getByRole("region", { name: "Runtime" });
  await runtime.getByRole("row", { name: /RDM_CURSOR_SIGNING_KEY/ }).waitFor();
  const cursorKey = system.settings.find((setting) => setting.name === "RDM_CURSOR_SIGNING_KEY");
  const keyRow = await runtime.getByRole("row", { name: /RDM_CURSOR_SIGNING_KEY/ }).innerText();
  expect(keyRow.includes(cursorKey.source === "environment" ? "Set" : "Not set"), `cursor key row: ${keyRow}`);
  const databaseRow = await runtime.getByRole("row", { name: /DATABASE_URL/ }).innerText();
  expect(!/:[^/@]+@/.test(databaseRow), `database URL shows a password: ${databaseRow}`);
  expect(
    (await page.getByRole("region", { name: "Capability groups" }).innerText()).includes(
      "MODEL_ADMIN_MUTATIONS_ENABLED",
    ),
    "capability group names its setting",
  );
  checks.push(
    "About shows the engine version, revision and active release from GET /system; Deployment shows secrets as set or not and the database URL without a password",
  );

  // 3. Every replaced address lands on its page, rewritten in place.
  for (const [old, address, heading] of [
    ["/models", "/settings/model", "Model"],
    [`/models?releaseId=${activeRelease}`, `/settings/model/releases/${activeRelease}`, undefined],
    ["/workspaces", "/settings/workspaces", "Workspaces"],
    ["/workspaces/default", "/settings/workspaces/default", undefined],
    ["/settings", "/settings/about", "About"],
  ]) {
    await page.goto(`${uiUrl}${old}`);
    await page.waitForURL(`**${address}`);
    if (heading) await page.getByRole("heading", { level: 1, name: heading, exact: true }).waitFor();
    expect(path() === address && !new URL(page.url()).search, `${old} landed on ${page.url()}`);
  }
  checks.push("/models (with a release), /workspaces (with a workspace) and /settings land on their settings pages");

  // 4. Compact on Appearance is the default in two views of different object types; a view's own
  //    choice in its Display menu wins over it.
  await page.goto(`${uiUrl}/settings/appearance`);
  await page.getByRole("group", { name: "Table density" }).getByText("Compact").click();
  for (const [view, record] of VIEWS) {
    await page.goto(`${uiUrl}${view}`);
    await page.getByRole("button", { name: record, exact: true }).waitFor();
    expect((await page.locator(".object-table.density-compact").count()) === 1, `${view}: default density not compact`);
  }
  await page.getByRole("button", { name: /^Display/ }).click();
  const density = page.getByRole("combobox", { name: "Density" });
  expect((await density.inputValue()) === "default", "view density does not start at the default");
  expect(
    (await density.locator("option:checked").innerText()).includes("Compact"),
    "default option does not name Compact",
  );
  await density.selectOption("comfortable");
  await page.keyboard.press("Escape");
  expect((await page.locator(".object-table.density-compact").count()) === 0, "a view's own Comfortable did not win");
  await page.goto(`${uiUrl}${VIEWS[0][0]}`);
  await page.getByRole("button", { name: VIEWS[0][1], exact: true }).waitFor();
  expect((await page.locator(".object-table.density-compact").count()) === 1, "the other view lost the default");
  await shot("u3-density-compact-wide");
  checks.push(
    "Compact on Appearance compacts two views of different object types; one view's own Comfortable wins only there",
  );

  // 5. Keyboard order: skip link, top bar (home, the applications, Settings, Account), the settings
  //    navigation with the rail's resize handle, then the content.
  await page.goto(`${uiUrl}/settings/deployment`);
  await page.getByRole("region", { name: "Capability groups" }).waitFor();
  await page.evaluate(() => document.activeElement?.blur());
  const tabNames = await page.getByRole("navigation", { name: "Applications" }).getByRole("button").allInnerTexts();
  const productName = (await page.locator(".product-mark strong").innerText()).trim();
  const expected = [
    "other:Skip to main content",
    `topbar:${productName} home`,
    ...tabNames.map((name) => `topbar:${name.trim()}`),
    "topbar:Settings",
    "topbar:Account",
    "navigation:About",
    "navigation:Appearance",
    "navigation:Workspaces",
    "navigation:Model",
    "navigation:Deployment",
    "navigation:Operations",
    "navigation:Import profiles",
    "navigation:Copy and move",
    "navigation:Jobs",
    "navigation:Consumer APIs",
    "navigation:Webhooks",
    "navigation:API reference",
    "navigation:Resize settings navigation",
  ];
  const order = [];
  for (let index = 0; index <= expected.length; index += 1) {
    await page.keyboard.press("Tab");
    order.push(
      await page.evaluate(() => {
        const element = document.activeElement;
        const region = element.closest("header")
          ? "topbar"
          : element.closest("nav")
            ? "navigation"
            : element.closest("main")
              ? "main"
              : "other";
        return `${region}:${element.getAttribute("aria-label") || element.textContent.trim()}`;
      }),
    );
  }
  expect(
    expected.every((item, index) => order[index] === item) && order[expected.length].startsWith("main:"),
    `keyboard order: ${order.join(" → ")}`,
  );
  // Back past the resize handle, Integration's three pages, Data operations' three, Operations and
  // Deployment to Model, and open it.
  for (let index = 0; index < 10; index += 1) await page.keyboard.press("Shift+Tab");
  await page.keyboard.press("Enter");
  await page.getByRole("heading", { level: 1, name: "Model" }).waitFor();
  checks.push(`keyboard order: ${order.join(" → ")}; Enter on a navigation link opens its page`);

  // 6. A popover open does not swallow the first click on the page (UA0): with Account open, one
  //    click on an application tab or a settings navigation link closes it and navigates; a click
  //    on plain text only closes it. Playwright refuses to click under an underlay or an inert page.
  const account = page.getByRole("dialog", { name: "Account" });
  const openAccount = async () => {
    await page.getByRole("banner").getByRole("button", { name: "Account" }).click();
    await account.waitFor();
  };
  const click = { timeout: 3000 };
  await page.goto(`${uiUrl}${VIEWS[0][0]}`);
  await page.getByRole("button", { name: VIEWS[0][1], exact: true }).waitFor();
  const tabs = page.getByRole("navigation", { name: "Applications" }).getByRole("button");
  const other = tabs.and(page.locator(":not([aria-current])")).first();
  const otherName = (await other.innerText()).trim();
  await openAccount();
  await other.click(click);
  await page.waitForFunction(
    (name) =>
      [...document.querySelectorAll('nav[aria-label="Applications"] [aria-current="page"]')].some(
        (tab) => tab.textContent.trim() === name,
      ),
    otherName,
    click,
  );
  expect((await account.count()) === 0, "Account stayed open after a tab click");
  await openAccount();
  await page.getByRole("heading", { level: 1 }).first().click(click);
  await account.waitFor({ state: "detached", ...click });
  await page.goto(`${uiUrl}/settings/about`);
  await page.getByRole("heading", { level: 1, name: "About" }).waitFor();
  await openAccount();
  // The page is no longer hidden while a popover is open; axe reads both together.
  const popoverAxe = await runAxe(page, [], "u3-account-open");
  if (popoverAxe.violations.length) failures.push(`u3-account-open:\n${formatViolations(popoverAxe.violations)}`);
  await page.getByRole("navigation", { name: "Settings" }).getByRole("link", { name: "Deployment" }).click(click);
  await page.waitForURL("**/settings/deployment", click);
  expect((await account.count()) === 0, "Account stayed open after a settings link click");
  checks.push(
    `with Account open, one click on the ${otherName} tab or the Deployment link closes it and navigates; a click on the heading closes it; axe with Account open: ${popoverAxe.violations.length} violations`,
  );

  await page.goto(`${uiUrl}/settings/deployment`);
  await page.getByRole("region", { name: "Capability groups" }).waitFor();

  const result = await runAxe(page, [], "u3-deployment");
  if (result.violations.length) failures.push(`u3-deployment:\n${formatViolations(result.violations)}`);
  checks.push(`axe u3-deployment: ${result.violations.length} violations`);

  const report = {
    browser: browser.version(),
    viewports: ["1440x900", "390x844"],
    checks,
    failures,
    passed: !failures.length,
  };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`U3 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("U3 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
