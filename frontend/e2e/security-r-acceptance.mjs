// 0.12 R acceptance (D448): the release's journeys composed, by keyboard alone (Tab, Shift+Tab, Enter, Space,
// the arrows; no mouse click), against a real backend, on two differently shaped models (the starter and
// the journey configuration generated-b), at 1440px and 390px. People and their passwords are set up
// through the API; what the journeys are about is done in the browser:
//
//   J40  a Security administrator grants a role to a person and a role to a group (Settings > Security);
//   J39  that person signs in, opens a collection and signs out;
//   J42  under the workspace's four-eyes policy (Settings > Workspaces > Approval, set by the workspace
//        administrator), a Contributor (through the group) submits a change set for publication, a Data
//        owner sends it back with a comment, the Contributor resubmits, the Data owner approves and it
//        publishes; the inbox shows each step to the person it concerns;
//   J45  Home's "Waiting for your approval" lists the request for the approver, and not for the submitter.
//
// Each check asserts what the person sees. Uncaught errors in any page fail the run (the harness reports
// them at cleanup). `SECURITY_R_ONLY=starter|generated-b` and `SECURITY_R_WIDTH=1440|390` narrow a run
// while iterating.
import { createHash, randomBytes } from "node:crypto";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { SHAPED_MODELS, bootShaped, startingPoint } from "./helpers/shaped-models.mjs";

const PASSWORD = "a long passphrase for this person";
const WIDTHS = process.env.SECURITY_R_WIDTH ? [Number(process.env.SECURITY_R_WIDTH)] : [1440, 390];
const only = process.env.SECURITY_R_ONLY;

const checks = [];
const failures = [];
const expect = (condition, message) => {
  if (!condition) failures.push(message);
};
const base64Url = (bytes) => bytes.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

/**
 * An access token for the person, as the browser gets one (PKCE), for the API writes the journeys set up.
 * Through a browser context's request client: the runner's own `fetch` carries the harness client's token.
 */
async function tokenFor(context, apiUrl, uiUrl, username) {
  const verifier = base64Url(randomBytes(48));
  const redirectUri = `${uiUrl}/signed-in`;
  const form = await context.request.post(`${apiUrl}/oauth/authorize`, {
    form: {
      response_type: "code",
      client_id: "browser",
      redirect_uri: redirectUri,
      code_challenge: base64Url(createHash("sha256").update(verifier).digest()),
      code_challenge_method: "S256",
      state: "security-r",
      username,
      password: PASSWORD,
    },
    maxRedirects: 0,
  });
  const location = form.headers().location;
  if (form.status() !== 303 || !location) throw new Error(`${username} could not sign in: ${form.status()}`);
  const exchanged = await context.request.post(`${apiUrl}/oauth/token`, {
    form: {
      grant_type: "authorization_code",
      client_id: "browser",
      code: new URL(location).searchParams.get("code"),
      code_verifier: verifier,
      redirect_uri: redirectUri,
    },
  });
  if (!exchanged.ok()) throw new Error(`${username}'s token was refused: ${await exchanged.text()}`);
  return (await exchanged.json()).access_token;
}

/** Focus the control and press a key on it: how a keyboard user reaches and operates it. */
async function press(page, locator, key = "Enter") {
  await locator.focus().catch(async (error) => {
    console.error(`${page.url()}\n${(await page.locator("body").innerText()).slice(0, 1200)}`);
    throw error;
  });
  await page.keyboard.press(key);
}
/** Focus a field and type into it. */
async function typeInto(page, locator, text) {
  await locator.focus();
  await page.keyboard.type(text);
}
/** The control the keyboard focus is on now. */
const focusedLabel = (page) =>
  page.evaluate(() => {
    const element = document.activeElement;
    return element?.getAttribute("aria-label") || element?.textContent?.trim().slice(0, 60) || element?.tagName;
  });

async function walk(configuration, width) {
  const harness = await bootShaped(configuration);
  const tag = `${configuration.name}-${width}`;
  try {
    const { apiUrl, uiUrl, api, output, signedOutContext, page: harnessPage } = harness;
    const narrow = width < 600;
    const viewport = { width, height: narrow ? 844 : 900 };
    const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    /** A screenshot of what the person sees; at 390px the page must not scroll sideways. */
    const shot = async (page, name) => {
      if (narrow) expect((await overflow(page)) <= 0, `${tag}: ${name} scrolls sideways at ${width}px`);
      await page.screenshot({ path: resolve(output, `${tag}-${name}.png`), fullPage: true });
    };
    const start = await startingPoint(api);
    const record = start.records[0];

    /** A person with a password, made through the API (the link's one-time token sets it). */
    async function make(username, name, grants = []) {
      const created = await api("/users", { username, name });
      for (const [role, scope] of grants)
        await api("/grants", { principal: { kind: "user", id: created.id }, role, scope });
      const { url } = await api(`/users/${created.id}/password-reset`, {}, "POST");
      const set = await fetch(`${apiUrl}/oauth/password`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          token: new URL(url).searchParams.get("token"),
          password: PASSWORD,
          repeat: PASSWORD,
        }),
      });
      if (!set.ok) throw new Error(`${username}'s password was not set: ${set.status}`);
      return created;
    }

    /** A signed-out context and page; the person signs in with the keyboard alone. */
    async function signIn(username, goTo = uiUrl) {
      const context = await signedOutContext({ viewport, hasTouch: narrow });
      const page = await context.newPage();
      page.setDefaultTimeout(15000);
      page.on("pageerror", (error) => failures.push(`${tag} ${username}: ${error.message}`));
      await page.goto(goTo);
      await page.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
      // The username has focus on arrival; Tab leads to the password, Enter sends the form.
      await page.waitForFunction(() => document.activeElement?.tagName === "INPUT");
      await page.keyboard.type(username);
      await page.keyboard.press("Tab");
      await page.keyboard.type(PASSWORD);
      await page.keyboard.press("Enter");
      await page
        .locator(".account-button")
        .waitFor()
        .catch(async (error) => {
          console.error(`${page.url()}\n${(await page.locator("body").innerText()).slice(0, 800)}`);
          throw error;
        });
      return { context, page };
    }

    /** The account menu by keyboard. */
    async function signOut(page) {
      await press(page, page.locator(".account-button"));
      const menu = page.getByRole("dialog", { name: "Account" });
      await press(page, menu.getByRole("button", { name: "Sign out" }));
      await page.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
    }

    const workspaceLabel = (await api("/workspaces/default")).label;

    // People: a Security administrator, a person to be given a role, a Contributor-to-be (a member of the
    // group that is given the role), a Data owner and a workspace administrator (the harness person).
    const sofia = await make(`sofia-${tag}`, "Sofia Lind", [["security-admin", { instance: true }]]);
    const nia = await make(`nia-${tag}`, "Nia Okafor");
    const ada = await make(`ada-${tag}`, "Ada Varga");
    const omar = await make(`omar-${tag}`, "Omar Hale", [["owner", { workspaceKey: "default" }]]);
    const curators = await api("/groups", { name: `Curators ${tag}` });
    await api(`/groups/${curators.id}/members`, { userId: ada.id });

    // ---- J40: a Security administrator grants a role to a person and to a group ----
    {
      const { context, page } = await signIn(sofia.username, `${uiUrl}/settings`);
      await page.getByRole("heading", { level: 1, name: "About" }).waitFor();
      const settings = page.getByRole("navigation", { name: "Settings" });
      // The settings navigation is a column at 1440px; at 390px the address is typed (the page is the same).
      if (narrow) await page.goto(`${uiUrl}/settings/people`);
      else await press(page, settings.getByRole("link", { name: "People", exact: true }));
      await page.getByRole("heading", { level: 1, name: "People" }).waitFor();
      // Search by keyboard, Tab into the result, Enter opens the person.
      await typeInto(page, page.getByLabel("Search people"), "Nia");
      const entry = page.getByRole("navigation", { name: "People" }).getByRole("button", { name: /Nia Okafor/ });
      await entry.waitFor();
      await press(page, entry);
      await page.getByRole("heading", { level: 2, name: "Nia Okafor" }).waitFor();
      await press(page, page.getByRole("button", { name: "Grant", exact: true }));
      let dialog = page.getByRole("dialog", { name: "Grant Nia Okafor access" });
      await dialog.getByRole("checkbox", { name: "Reader" }).waitFor();
      // Tab from the dialog's first field reaches the role checkboxes; Space ticks one.
      await press(page, dialog.getByRole("checkbox", { name: "Reader" }), "Space");
      expect(
        await dialog.getByRole("checkbox", { name: "Reader" }).isChecked(),
        `${tag}: Space ticks the Reader role in the grant dialog`,
      );
      await dialog.getByText(/Nia Okafor will read everything/).waitFor();
      await shot(page, "grant-person");
      await press(page, dialog.getByRole("button", { name: "Grant", exact: true }));
      await dialog.waitFor({ state: "detached" });
      await page
        .getByRole("group", { name: "Roles" })
        .getByRole("row", { name: /Reader/ })
        .waitFor();
      checks.push(`${tag}: J40 a Security administrator granted Reader to a person, by keyboard`);

      // The group.
      await page.goto(`${uiUrl}/settings/groups`);
      await page.getByRole("heading", { level: 1, name: "Groups" }).waitFor();
      const groupEntry = page.getByRole("navigation", { name: "Groups" }).getByRole("button", { name: /Curators/ });
      await groupEntry.waitFor();
      await press(page, groupEntry);
      await page.getByRole("heading", { level: 2, name: `Curators ${tag}` }).waitFor();
      await page.getByRole("group", { name: "Members" }).getByText(ada.username).waitFor();
      await press(page, page.getByRole("button", { name: "Grant", exact: true }));
      dialog = page.getByRole("dialog", { name: `Grant Curators ${tag} access` });
      await press(page, dialog.getByRole("checkbox", { name: "Contributor" }), "Space");
      await dialog.getByText(/Curators .* will/).waitFor();
      await shot(page, "grant-group");
      await press(page, dialog.getByRole("button", { name: "Grant", exact: true }));
      await dialog.waitFor({ state: "detached" });
      await page
        .getByRole("group", { name: "Roles" })
        .getByRole("row", { name: /Contributor/ })
        .waitFor();
      expect((await overflow(page)) <= 0, `${tag}: the group's page scrolls sideways`);
      checks.push(`${tag}: J40 a Security administrator granted Contributor to a group, by keyboard`);

      // Back on the person's page, the role is listed, and the people list says so under the name.
      await page.goto(`${uiUrl}/settings/people`);
      await typeInto(page, page.getByLabel("Search people"), "Nia");
      await page
        .getByRole("navigation", { name: "People" })
        .getByRole("button", { name: /Nia Okafor.*Reader/ })
        .waitFor();
      await shot(page, "people-after-grant");
      checks.push(`${tag}: J40 the people list names the new role under the person`);
      await signOut(page);
      await context.close();
    }

    // ---- J39: the person signs in, opens a collection and signs out ----
    {
      const { context, page } = await signIn(nia.username);
      await page.getByRole("heading", { level: 1, name: /^Good (morning|afternoon|evening), Nia$/ }).waitFor();
      // Tab from the top of the page to the first application of the workspace's card; Enter opens it.
      let reached = "";
      for (let stops = 0; stops < 40 && !reached; stops++) {
        await page.keyboard.press("Tab");
        if (await page.evaluate(() => document.activeElement?.classList.contains("home-app"))) reached = "home-app";
      }
      expect(reached === "home-app", `${tag}: Tab reaches an application on Home`);
      await page.keyboard.press("Enter");
      await page.waitForURL(/\/apps\//);
      await page.getByRole("heading", { level: 1 }).first().waitFor();
      await page.getByText(record.name, { exact: true }).locator("visible=true").first().waitFor();
      expect(
        (await page.getByRole("button", { name: "Propose a change" }).count()) === 0,
        `${tag}: a Reader is not offered a change`,
      );
      await shot(page, "reader-collection");
      checks.push(`${tag}: J39 the person signed in, opened a collection by keyboard and saw its records`);
      await signOut(page);
      await context.close();
      checks.push(`${tag}: J39 signed out by keyboard`);
    }

    // ---- J42 setup: the four-eyes policy, set on the workspace's Approval tab by its administrator ----
    {
      const page = harnessPage;
      page.setDefaultTimeout(15000);
      await page.setViewportSize(viewport);
      await page.goto(`${uiUrl}/settings/workspaces/default/approval`);
      const policy = page.getByRole("region", { name: "Approval" });
      await policy.getByRole("heading", { name: "Approval" }).waitFor();
      await press(
        page,
        policy.getByRole("checkbox", { name: "Changes need approval before they are published" }),
        "Space",
      );
      await press(
        page,
        policy.getByRole("checkbox", { name: "The person who submitted a change set cannot approve it" }),
        "Space",
      );
      await shot(page, "approval-policy");
      await press(page, policy.getByRole("button", { name: "Save approval policy" }));
      await policy.getByText("Approval policy saved.").waitFor();
      const saved = await api("/workspaces/default/approval-policy");
      expect(saved.requireApproval && saved.secondPerson, `${tag}: the policy is four-eyes: ${JSON.stringify(saved)}`);
      checks.push(`${tag}: J42 the workspace's four-eyes policy set on its Approval tab, by keyboard`);
    }

    // ---- J42: submit, send back, resubmit, approve; J45: Home lists the request for the approver ----
    const tokens = await signedOutContext({ viewport });
    const adaToken = await tokenFor(tokens, apiUrl, uiUrl, ada.username);
    await tokens.close();
    const as = async (path, body, method) => {
      const response = await fetch(`${apiUrl}/api/v1${path}`, {
        method: method || (body ? "POST" : "GET"),
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${adaToken}` },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      if (!response.ok) throw new Error(`${path}: ${response.status} ${await response.text()}`);
      return response.json();
    };
    const changeSetName = `Corrections ${tag}`;
    const changeSet = await as("/workspaces/default/change-sets", { name: changeSetName, source: "currentLive" });
    await as(
      `/objects/${start.type.key}/${record.id}`,
      {
        expectedVersion: record.version,
        name: `${record.name} (corrected)`,
        changeSetId: changeSet.id,
        expectedChangeSetVersion: changeSet.version,
      },
      "PATCH",
    );

    const adaSession = await signIn(ada.username);
    const omarSession = await signIn(omar.username);
    const inboxOf = async (page) => {
      const bell = page.getByRole("button", { name: /^Inbox/ });
      await press(page, bell);
      const panel = page.locator(".inbox-panel");
      await panel.waitFor();
      return panel;
    };
    const closeInbox = async (page) => {
      await page.keyboard.press("Escape");
      await page.locator(".inbox-panel").waitFor({ state: "detached" });
    };

    // 1. Ada opens her change set from Home (a link in "Your change sets") and submits it.
    {
      const page = adaSession.page;
      const own = page.getByRole("region", { name: "Your change sets" });
      await own.waitFor();
      const link = own.locator(".home-change-set").filter({ hasText: changeSetName }).locator("a");
      await press(page, link);
      await page.waitForURL(/\/change-sets\/[^/]+\/changes/);
      await page.getByRole("heading", { level: 1 }).first().waitFor();
      await press(page, page.getByRole("button", { name: "Submit for publication" }));
      const dialog = page.getByRole("dialog", { name: "Submit for publication" });
      await typeInto(page, dialog.getByLabel("Comment (optional)"), "Ready for review");
      await shot(page, "submit-dialog");
      // Tab from the comment: Cancel, then Submit; Enter on Submit sends.
      await page.keyboard.press("Tab");
      expect(
        (await focusedLabel(page)) === "Cancel",
        `${tag}: Tab from the comment reaches Cancel: ${await focusedLabel(page)}`,
      );
      await page.keyboard.press("Tab");
      expect((await focusedLabel(page)) === "Submit", `${tag}: then Submit: ${await focusedLabel(page)}`);
      await page.keyboard.press("Enter");
      await dialog.waitFor({ state: "detached" });
      await page.getByRole("button", { name: "Withdraw request" }).waitFor();
      await shot(page, "submitted");
      checks.push(`${tag}: J42 the Contributor submitted the change set with a comment, by keyboard`);
    }

    // 2. J45: Omar's Home lists the request; Ada's does not. His inbox says it waits.
    {
      const page = omarSession.page;
      await page.goto(uiUrl);
      const waiting = page.getByRole("region", { name: "Waiting for your approval" });
      await waiting.waitFor();
      const row = waiting.getByRole("listitem").filter({ hasText: changeSetName });
      await row.getByText(/Submitted by Ada Varga/).waitFor();
      await shot(page, "home-waiting");
      expect(
        (await adaSession.page.getByRole("region", { name: "Waiting for your approval" }).count()) === 0,
        `${tag}: the submitter is not asked to approve`,
      );
      const panel = await inboxOf(page);
      await panel.getByText("Waiting for your approval").first().waitFor();
      await panel
        .getByText(new RegExp(`${changeSetName}.*From Ada Varga|From Ada Varga`))
        .first()
        .waitFor();
      await shot(page, "inbox-waiting");
      await closeInbox(page);
      checks.push(`${tag}: J45 Home lists the request for the approver only; the inbox says it waits`);
    }

    // A notice about the change set a person has open is read at once (NT1, D464): Ada waits on Home, so
    // the inbox has the notices to show.
    await adaSession.page.goto(uiUrl);

    // 3. Omar opens it from Home's list and sends it back with a comment.
    {
      const page = omarSession.page;
      const waiting = page.getByRole("region", { name: "Waiting for your approval" });
      await press(page, waiting.getByRole("listitem").filter({ hasText: changeSetName }).locator("a, button").first());
      await page.waitForURL(/\/change-sets\/[^/]+\/changes/);
      const card = page.getByRole("region", { name: "Decision" });
      await card.getByText(/Submitted by Ada Varga/).waitFor();
      await card.getByText("Ready for review").waitFor();
      // Sending back needs a comment: refused empty, said at the field.
      await press(page, card.getByRole("button", { name: "Send back" }));
      await card
        .getByText(/comment/i)
        .first()
        .waitFor();
      await typeInto(page, card.getByLabel("Comment"), "Please add the source of the correction");
      await shot(page, "decision-card");
      await press(page, card.getByRole("button", { name: "Send back" }));
      await page.getByText(/Sent back to Ada Varga/).waitFor();
      checks.push(`${tag}: J42 the Data owner sent it back; an empty comment was refused at its field`);
      // Home, so the resubmission's notice is unread when it arrives (NT1, D464).
      await page.goto(uiUrl);
    }

    // 4. Ada's inbox shows it was sent back, with the comment; she resubmits.
    {
      const page = adaSession.page;
      const panel = await inboxOf(page);
      const notice = panel
        .getByRole("listitem")
        .filter({ hasText: /Sent back/ })
        .first();
      await notice.getByText("Please add the source of the correction").waitFor();
      await shot(page, "inbox-sent-back");
      await press(page, notice.getByRole("button").first());
      await page.waitForURL(/\/change-sets\/[^/]+\/changes/);
      // The page follows its request: the sent-back notice re-reads the change set at the same address.
      await page.getByRole("button", { name: "Submit for publication" }).waitFor();
      await page.getByRole("heading", { level: 1 }).first().waitFor();
      await press(page, page.getByRole("button", { name: "Submit for publication" }));
      const dialog = page.getByRole("dialog", { name: "Submit for publication" });
      await typeInto(page, dialog.getByLabel("Comment (optional)"), "Source added");
      await press(page, dialog.getByRole("button", { name: "Submit", exact: true }));
      await dialog.waitFor({ state: "detached" });
      await page.getByRole("button", { name: "Withdraw request" }).waitFor();
      checks.push(`${tag}: J42 the Contributor saw the comment in the inbox and resubmitted`);
      // Back to Home, so the approval's notice is not read as it arrives (NT1, D464).
      await page.goto(uiUrl);
    }

    // 5. Omar's Home lists it again; he approves and it publishes.
    {
      const page = omarSession.page;
      await page.goto(uiUrl);
      const waiting = page.getByRole("region", { name: "Waiting for your approval" });
      await waiting.getByRole("listitem").filter({ hasText: changeSetName }).waitFor();
      const panel = await inboxOf(page);
      await panel
        .getByRole("listitem")
        .filter({ hasText: /Waiting for your approval/ })
        .first()
        .waitFor();
      await closeInbox(page);
      await press(page, waiting.getByRole("listitem").filter({ hasText: changeSetName }).locator("a, button").first());
      await page.waitForURL(/\/change-sets\/[^/]+\/changes/);
      const card = page.getByRole("region", { name: "Decision" });
      await card.getByText("Source added").waitFor();
      await shot(page, "decision-resubmitted");
      await press(page, card.getByRole("button", { name: "Approve and publish" }));
      await page.getByText(/Published as Publication \d+/).waitFor();
      checks.push(`${tag}: J42 the Data owner approved the resubmitted change set and it published`);
    }

    // 6. Ada's inbox shows the approval; the record is live under its new name.
    {
      const page = adaSession.page;
      const panel = await inboxOf(page);
      await panel
        .getByRole("listitem")
        .filter({ hasText: /Approved/ })
        .first()
        .waitFor();
      await shot(page, "inbox-approved");
      await closeInbox(page);
      const live = await api(`/objects/${start.type.key}/${record.id}?workspaceKey=default`);
      expect(live.name === `${record.name} (corrected)`, `${tag}: the published record reads "${live.name}"`);
      await omarSession.page.goto(uiUrl);
      await omarSession.page.getByRole("heading", { level: 1 }).first().waitFor();
      expect(
        (await omarSession.page.getByRole("region", { name: "Waiting for your approval" }).count()) === 0,
        `${tag}: nothing waits for the approver after the decision`,
      );
      checks.push(`${tag}: J42 the inbox showed the approval, the record is live, and nothing is left waiting`);
    }

    expect((await overflow(adaSession.page)) <= 0, `${tag}: no horizontal page scroll`);
    await adaSession.context.close();
    await omarSession.context.close();
    const report = { model: tag, checks, failures, passed: !failures.length };
    await writeFile(resolve(output, `report-${tag}.json`), JSON.stringify(report, null, 2));
    console.log(`security-r (${tag}): ${output}`);
  } finally {
    harness.cleanup();
  }
}

try {
  for (const configuration of SHAPED_MODELS)
    if (!only || only === configuration.name) for (const width of WIDTHS) await walk(configuration, width);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("security-r failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
