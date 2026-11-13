// 0.16 AP13 browser evidence: always a way out, against a real backend with a stand-in for the Claude Code session
// (`helpers/way-out-stand-in.py`, set as AI_AGENT_COMMAND), on the starter and on generated-b (the runner derives its
// probe type from whichever model it booted on and names none of their keys). Each state of a task that had no way
// on: a turn that failed (its reason shown, the words going to the same session), a turn stopped before any proposal
// (stopped, words), a correction stopped (back at the proposal with a note), a loaded change set that is wrong (words
// discard it and the session loads again), a load stopped (nothing loaded, back at the proposal), a published task
// (the model and the records offered onward), a discarded one, and a task that is not there. Keyboard on one model,
// pointer on the other; axe on each state; light and dark; 1440px and 390px without sideways scroll.
// Brought up to date (0.14 + 0.17 release review, RF2-RF6): a new task whose session has said nothing shows the session's "Starting", so the wait is on the Working on it section.
import assert from "node:assert/strict";
import { rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { bootShaped, SHAPED_MODELS } from "./helpers/shaped-models.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { goDark } from "./helpers/theme.mjs";
import { workspaceAction } from "./helpers/workspaceMenu.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const PLAN = resolve(tmpdir(), `ap13-plan-${process.pid}.json`);
const SESSION = `${resolve(root, "backend/.venv/bin/python")} ${resolve(import.meta.dirname, "helpers/way-out-stand-in.py")} ${PLAN}`;
const checks = [];

async function accessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
  checks.push(`axe ${name}: 0 violations`);
}
const overflow = (target) => target.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);

const LABEL = "zz-way-label";
const ITEM = "zz-way-item";

/** The booted model with one probe type added to its first application, named by nothing in either model. */
function shaped(source, tag, withType) {
  const model = structuredClone(source);
  model.schemaVersion = "0.10";
  if (withType) {
    if (!model.attributeTypes.some((item) => item.key === LABEL))
      model.attributeTypes.push({ key: LABEL, name: LABEL });
    model.objectTypes.push({
      key: ITEM,
      name: "Way item",
      pluralName: "Way items",
      displayAttributeTypeKey: LABEL,
      attributes: [{ attributeTypeKey: LABEL, order: 10 }],
      features: { rootCreatable: true },
    });
    model.applications[0].objectTypeKeys.push(ITEM);
  }
  model.release = { ...model.release, version: `${model.release.version}-${tag}` };
  return model;
}

async function release(api, model, name) {
  const draft = await api("/model-drafts", { name, model });
  return (await api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version })).id;
}

const stopButton = (page) => page.getByLabel(/^(Working on it|Loading)$/).getByRole("button", { name: "Stop" });

const setPlan = (plan) => writeFile(PLAN, JSON.stringify(plan));

async function asking(page, uiUrl, application, words, keyboard) {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto(`${uiUrl}/apps/${application.key}/views/${application.defaultView}?workspaceKey=way-ws`);
  await workspaceAction(page, "Change this model…", { keyboard });
  const dialog = page.getByRole("dialog", { name: "Change this model" });
  await dialog.waitFor();
  await dialog.getByLabel("What should change?").fill(words);
  await dialog.getByRole("button", { name: "Ask the assistant" }).click();
  await page.waitForURL(/\/settings\/ai-tasks\//);
}

async function send(page, label, words, keyboard, name = "Send to the assistant") {
  await page.getByLabel(label).fill(words);
  const button = page.getByRole("button", { name });
  if (keyboard) {
    await button.focus();
    await page.keyboard.press("Enter");
  } else await button.click();
}

async function scenario(configuration, index) {
  const label = configuration.name;
  const keyboard = index === 0;
  const harness = await bootShaped(configuration, { backendEnv: { AI_AGENT_COMMAND: SESSION } });
  const { page, api, apiUrl, uiUrl, output } = harness;
  const shot = (name) => page.screenshot({ path: resolve(output, `ap13-${label}-${name}.png`), fullPage: true });
  const phoneCheck = async (heading, name) => {
    const phone = await page.context().newPage();
    await phone.setViewportSize({ width: 390, height: 844 });
    await phone.goto(page.url());
    await phone.getByRole("heading", { name: heading }).first().waitFor();
    assert.ok((await overflow(phone)) <= 0, `${label}: ${name} overflows at 390px`);
    await phone.screenshot({ path: resolve(output, `ap13-${label}-${name}-390.png`), fullPage: true });
    await accessible(phone, `ap13-${label}-${name}-390`);
    await phone.close();
  };
  try {
    const base = await api("/model");
    const application = base.applications[0];
    const start = await release(api, shaped(base, "way-0", false), "Way start");
    await api("/workspaces", { key: "way-ws", label: "Way workspace", modelReleaseId: start });
    const final = shaped(base, "way-final", true);
    const plan = {
      address: apiUrl,
      workspace: "way-ws",
      final,
      name: "Way load",
      batch: [
        {
          op: "create",
          applicationKey: application.key,
          objectTypeKey: ITEM,
          name: "Way item",
          attributes: [{ attributeTypeKey: LABEL, value: "W1" }],
        },
      ],
    };
    const changeSets = async (name) =>
      (await api("/workspaces/way-ws/change-sets?pageSize=100")).items.filter((item) => item.name === name);
    const proposal = page.getByRole("heading", { name: "The assistant’s proposal" });

    // ---- 1. a turn that failed: why, and words that go on ----
    await setPlan({ ...plan, fail: true });
    await asking(page, uiUrl, application, "Add a way item type.", keyboard);
    await page.getByRole("heading", { name: "The assistant stopped" }).waitFor();
    assert.match(await page.locator("main").innerText(), /could not build a model from these words/);
    await shot("failed");
    await accessible(page, `ap13-${label}-failed`);
    await phoneCheck("The assistant stopped", "failed");
    await goDark(page);
    await accessible(page, `ap13-${label}-failed-dark`);
    await page.emulateMedia({ colorScheme: "light" });
    await page.evaluate(() => delete document.documentElement.dataset.theme);
    await setPlan(plan);
    await send(page, "Tell the assistant how to go on", "Add it as a plain type with one name field.", keyboard);
    await proposal.waitFor();
    checks.push(
      `${label}: a failed turn shows its reason and the person's words go on in the same session to a proposal`,
    );

    // ---- 2. a correction stopped: back at the proposal, with a note ----
    const taskUrl = page.url();
    await setPlan({ ...plan, hold: "propose" });
    await send(page, "Tell the assistant what to change", "Call the type Thing instead.", keyboard);
    await page.getByText("The assistant is designing the model and the load").waitFor();
    await stopButton(page).click();
    await proposal.waitFor();
    await page.getByText(/You stopped the assistant\. Its last proposal is as it was/).waitFor();
    await shot("stopped-proposal");
    await accessible(page, `ap13-${label}-stopped-proposal`);
    checks.push(`${label}: Stop during a correction returns to the last proposal with a note`);

    // ---- 3. a load stopped: nothing loaded, back at the proposal ----
    await setPlan({ ...plan, hold: "load", name: "Way stop" });
    await page.getByLabel("The assistant’s proposal").getByRole("button", { name: "Accept the model" }).click();
    await stopButton(page).waitFor();
    await page.waitForTimeout(3000);
    await stopButton(page).click();
    await proposal.waitFor();
    await page.getByText(/What it had loaded was undone/).waitFor();
    assert.equal((await changeSets("Way stop")).length, 0, "the stopped load left no change set");
    await shot("stopped-load");
    checks.push(`${label}: Stop during a load leaves no change set and returns to the proposal that was accepted`);

    // ---- 4. a load that is wrong: words discard it and the session loads again ----
    await setPlan({ ...plan, name: "Way load" });
    await page.getByLabel("The assistant’s proposal").getByRole("button", { name: "Accept the model" }).click();
    await page.getByRole("heading", { name: "Loaded into the change set “Way load”" }).waitFor();
    const [first] = await changeSets("Way load");
    assert.ok(first, "the load made its change set");
    await shot("loaded");
    await accessible(page, `ap13-${label}-loaded`);
    await page.getByLabel("Not what you wanted? Tell the assistant").fill("Name the item Second.");
    const again = page.getByRole("button", { name: "Discard and load again" });
    if (keyboard) {
      await again.focus();
      await page.keyboard.press("Enter");
    } else await again.click();
    const confirm = page.getByRole("alertdialog");
    await confirm.getByText(/any edits you made in it/).waitFor();
    await accessible(page, `ap13-${label}-discard-dialog`);
    await confirm.getByRole("button", { name: "Discard and load again" }).click();
    await page.getByLabel("Working on it").waitFor();
    await page.getByRole("heading", { name: "Loaded into the change set “Way load”" }).waitFor();
    const held = await changeSets("Way load");
    assert.equal(held.length, 1, "one change set is left");
    assert.notEqual(held[0].id, first.id, "the first change set was discarded and a new one made");
    checks.push(`${label}: words on a loaded change set discard it and the same session loads a new one`);

    // ---- 5. published: the way onward ----
    const second = held[0];
    const current = await api("/workspaces/way-ws/model");
    const fresh = await api(`/change-sets/${second.id}`);
    await api("/workspaces/way-ws/model/activation", {
      releaseId: fresh.modelReleaseId,
      expectedVersion: current.version,
      expectedReleaseId: current.releaseId,
    });
    await api(`/change-sets/${second.id}/publication`, {
      expectedChangeSetVersion: fresh.version,
      expectedActivePublicationId: null,
    });
    await page.goto(taskUrl);
    await page.getByRole("heading", { name: "Published: “Way load”" }).waitFor();
    assert.equal(await page.getByRole("button", { name: "Discard the change set" }).count(), 0);
    assert.equal(await page.getByLabel("Not what you wanted? Tell the assistant").count(), 0, "the session has ended");
    await shot("published");
    await accessible(page, `ap13-${label}-published`);
    await phoneCheck("Something not right?", "published");
    const onward = page.getByRole("button", { name: keyboard ? "Ask about these records…" : "Change this model…" });
    if (keyboard) {
      await onward.focus();
      await page.keyboard.press("Enter");
      await page.getByRole("dialog", { name: "Load a workbook" }).waitFor();
    } else {
      await onward.click();
      await page.getByRole("dialog", { name: "Change this model" }).waitFor();
    }
    await accessible(page, `ap13-${label}-onward-dialog`);
    await page.keyboard.press("Escape");
    checks.push(`${label}: a published task says so, offers the model and the records, and its session has ended`);

    // ---- 6. a turn stopped before any proposal: stopped, words, discard ----
    await setPlan({ ...plan, hold: "propose" });
    await asking(page, uiUrl, application, "Add another way item type.", !keyboard);
    // The session has said nothing yet, so the page reports its own state, "Starting", not the engine's phase.
    await page.getByRole("heading", { name: "Working on it" }).waitFor();
    await stopButton(page).click();
    await page.getByRole("heading", { name: "You stopped the assistant" }).waitFor();
    await shot("stopped");
    await accessible(page, `ap13-${label}-stopped`);
    await setPlan(plan);
    await page.getByRole("button", { name: "Go on as it was" }).click();
    await proposal.waitFor();
    checks.push(`${label}: a turn stopped before any proposal is stopped, takes words and goes on`);

    // ---- 6b. what the stand-in cannot reach: the page is given the state, the engine answers where it can ----
    const context = page.context();
    const taskId = page.url().split("/ai-tasks/")[1].split(/[?#]/)[0];
    const reroute = (pattern, change) =>
      context.route(pattern, async (route) => {
        if (route.request().method() !== "GET") return route.fallback();
        const response = await route.fetch();
        await route.fulfill({ response, json: await change(await response.json(), route) });
      });
    const taskRoute = new RegExp(`/api/v1/ai/tasks/${taskId}$`);
    const press = async (button) => {
      if (keyboard) {
        await button.focus();
        await page.keyboard.press("Enter");
      } else await button.click();
    };

    // a saved layout that no longer fits: its note, and Read it with the assistant
    await reroute(taskRoute, (body) => ({
      ...body,
      check: null,
      canTell: true,
      design: { ...body.design, stage: "load", agentSession: undefined },
      notes: [{ kind: "warning", text: "The saved layout does not fit the workbook", at: new Date().toISOString() }],
    }));
    let retried;
    await context.route(new RegExp(`/api/v1/ai/tasks/${taskId}/retry$`), (route) => {
      retried = route.request().postDataJSON();
      return route.abort("failed");
    });
    await page.reload();
    await page.getByRole("heading", { name: "The saved layout does not fit this file" }).waitFor();
    assert.match(await page.locator("main").innerText(), /The saved layout does not fit the workbook/);
    await shot("unfit-layout");
    await accessible(page, `ap13-${label}-unfit-layout`);
    await phoneCheck("The saved layout does not fit this file", "unfit-layout");
    await press(page.getByRole("button", { name: "Read it with the assistant" }));
    assert.ok(
      retried && Number.isInteger(retried.expectedVersion) && !("words" in retried),
      "it asked the engine to go on",
    );
    // The request was aborted: the page says so and keeps the way on.
    await page.getByText("That did not work").waitFor();
    assert.equal(await page.getByRole("button", { name: "Read it with the assistant" }).count(), 1, "the way on stays");
    assert.equal(await page.getByRole("button", { name: "Back to the workspace" }).count(), 1, "the way out stays");
    await context.unroute(taskRoute);
    await context.unroute(new RegExp(`/api/v1/ai/tasks/${taskId}/retry$`));
    checks.push(
      `${label}: [client only: the task is rerouted] a saved layout that no longer fits shows its note, and Read it with the assistant asks the engine and says so when the request fails`,
    );

    // a permission lost during the task: who can load, no Accept
    const permissionRoute = /\/api\/v1\/me\/permissions/;
    await reroute(permissionRoute, (body) => ({
      ...body,
      actionGroups: body.actionGroups.filter((group) => group.key !== "change-sets"),
    }));
    await page.reload();
    await proposal.waitFor();
    assert.equal(await page.getByRole("button", { name: "Accept the model" }).count(), 0, "Accept is not offered");
    await page.getByText(/Loading needs Work in change sets in/).waitFor();
    assert.match(await page.locator("main").innerText(), /Someone who does can load it from this page/);
    await shot("no-permission");
    await accessible(page, `ap13-${label}-no-permission`);
    await phoneCheck("The assistant’s proposal", "no-permission");
    await press(page.getByRole("button", { name: "Copy the link to this task" }));
    await context.unroute(permissionRoute);
    await page.reload();
    await page.getByLabel("The assistant’s proposal").getByRole("button", { name: "Accept the model" }).waitFor();
    checks.push(
      `${label}: [client only: the permissions are rerouted] without Work in change sets the proposal names who can load and offers the link, not Accept`,
    );

    // ---- 7. a loaded task discarded ----
    await page.getByLabel("The assistant’s proposal").getByRole("button", { name: "Accept the model" }).click();
    await page.getByRole("heading", { name: "Loaded into the change set “Way load”" }).waitFor();
    // a reshape step the engine would refuse: its own check of the release, shown on the task with the words box
    const without = await release(api, shaped(base, "way-no", false), "Way without the item");
    const thisTask = page.url().split("/ai-tasks/")[1].split(/[?#]/)[0];
    const loadedRoute = new RegExp(`/api/v1/ai/tasks/${thisTask}$`);
    const diffRoute = /\/api\/v1\/model-releases\/[^/]+\/diff/;
    await reroute(loadedRoute, (body) => ({ ...body, result: { ...body.result, thenReleaseId: without } }));
    await context.route(diffRoute, async (route) => {
      const url = route
        .request()
        .url()
        .replace(/model-releases\/[^/]+\/diff/, `model-releases/${without}/diff`);
      await route.fulfill({ response: await route.fetch({ url }) });
    });
    await page.reload();
    await page.getByText("The engine would refuse the next step").waitFor();
    assert.ok(await page.getByLabel("Not what you wanted? Tell the assistant").isVisible(), "the words box is there");
    await shot("refused-step");
    await accessible(page, `ap13-${label}-refused-step`);
    const phoneRefused = await context.newPage();
    await phoneRefused.setViewportSize({ width: 390, height: 844 });
    await phoneRefused.goto(page.url());
    await phoneRefused.getByText("The engine would refuse the next step").waitFor();
    assert.ok((await overflow(phoneRefused)) <= 0, `${label}: the refused step overflows at 390px`);
    await accessible(phoneRefused, `ap13-${label}-refused-step-390`);
    await phoneRefused.close();
    if (keyboard) {
      await page.getByLabel("Not what you wanted? Tell the assistant").focus();
      await page.keyboard.type("Keep the type.");
    }
    await context.unroute(loadedRoute);
    await context.unroute(diffRoute);
    await page.reload();
    await page.getByRole("heading", { name: "Loaded into the change set “Way load”" }).waitFor();
    checks.push(
      `${label}: [client only: the check is rerouted] a reshape step the engine would refuse is shown on the task with the words box`,
    );

    await page.getByRole("button", { name: "Discard the change set" }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Discard" }).click();
    await page.getByRole("heading", { name: "Discarded" }).waitFor();
    assert.equal((await changeSets("Way load")).length, 0, "the change set went with the task");
    await shot("discarded");
    await accessible(page, `ap13-${label}-discarded`);
    checks.push(`${label}: discarding a loaded task removes its change set and says it was discarded`);

    // ---- 8. a task that is not here ----
    await page.goto(`${uiUrl}/settings/ai-tasks/no-such-task`);
    await page.getByRole("heading", { name: "This task is no longer here" }).waitFor();
    await shot("not-here");
    await accessible(page, `ap13-${label}-not-here`);
    await page.getByRole("button", { name: "Go to the workspaces" }).click();
    await page.waitForURL(/\/settings\/workspaces/);
    checks.push(`${label}: an unknown or expired task says so and leads to the workspaces`);
  } catch (error) {
    await page.screenshot({ path: resolve(output, `ap13-${label}-failure.png`), fullPage: true }).catch(() => {});
    console.error(
      await page
        .locator("main")
        .innerText()
        .catch(() => ""),
    );
    console.error(
      JSON.stringify(
        (await api("/ai/tasks").catch(() => ({ items: [] }))).items.map((t) => [t.state, t.notes, t.design?.stage]),
      ).slice(0, 3000),
    );
    console.error(harness.log().slice(-3000));
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (AP13 ${label}): ${output}`);
}

try {
  let index = 0;
  for (const configuration of SHAPED_MODELS) await scenario(configuration, index++);
  console.log(`AP13 always a way out: ${checks.length} checks passed`);
  for (const check of checks) console.log(`- ${check}`);
} catch (error) {
  console.error("AP13 browser evidence failed:", error);
  process.exitCode = 1;
} finally {
  await rm(PLAN, { force: true });
}
