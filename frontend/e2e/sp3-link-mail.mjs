// 0.12 SP3 browser evidence: Settings › Security › People mails a new person's link. Real backend,
// harness SMTP server (helpers/smtp-server.mjs), two models, 1440px and 390px. Without mail set up
// the dialog offers the link to pass on (Add person); with it saved, a person
// with an address is created with the same button, the dialog shows the link and offers "Mail it to
// <address>"; pressed, the dialog says where the link went and shows the newer link once, the server
// receives one message holding that link, and the person's one Make a password link button leads to the
// same dialog. Axe on each dialog; screenshots; no horizontal page scroll at 390px.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { SHAPED_MODELS, bootShaped } from "./helpers/shaped-models.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { startSmtp } from "./helpers/smtp-server.mjs";

const checks = [];
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

async function axe(page, name) {
  const result = await runAxe(page, [], name);
  if (result.violations.length) failures.push(`${name}:\n${formatViolations(result.violations)}`);
  checks.push(`axe ${name}: ${result.violations.length} violations`);
}

/** A message's text with its quoted-printable encoding undone, as a mail program shows it. */
function decoded(message) {
  return message.replace(/=\r\n/g, "").replace(/=([0-9A-F]{2})/g, (_, hex) => String.fromCharCode(parseInt(hex, 16)));
}

/** Waits until the server holds `count` messages (the sender runs in the background). */
async function received(smtp, count) {
  for (let waited = 0; waited < 20000 && smtp.messages.length < count; waited += 250) {
    await new Promise((done) => setTimeout(done, 250));
  }
  return smtp.messages.length >= count;
}

async function walk(configuration) {
  let smtp;
  let harness;
  try {
    smtp = await startSmtp();
    harness = await bootShaped(configuration);
    const { uiUrl, api, output, browser } = harness;
    const tag = configuration.name;
    const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    const shot = (page, name) => page.screenshot({ path: resolve(output, `${tag}-${name}.png`), fullPage: true });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    page.on("pageerror", (error) => failures.push(`${tag}: ${error.message}`));

    async function newPerson(_local, name, email, button) {
      await page.getByRole("button", { name: "New person" }).click();
      const create = page.getByRole("dialog", { name: "New person" });
      await create.getByLabel("Name", { exact: true }).fill(name);
      await create.getByLabel("E-mail", { exact: true }).fill(email);
      await create.getByRole("button", { name: button }).click();
      return page.getByRole("dialog", { name: "Pass on the password link" });
    }

    // 1. Mail not set up: the link to pass on, as before.
    await page.goto(`${uiUrl}/settings/people`);
    await page.getByRole("heading", { level: 1, name: "People" }).waitFor();
    let shown = await newPerson(`ada-${tag}`, `Ada ${tag}`, `ada-${tag}@example.org`, "Add person");
    await shown.getByText(/sets a password with this link/).waitFor();
    expect((await shown.getByText(/was mailed to/).count()) === 0, `${tag}: nothing said mailed without mail`);
    await axe(page, `${tag}-link-not-mailed`);
    await shown.getByRole("button", { name: "I have copied it" }).click();
    expect(smtp.messages.length === 0, `${tag}: nothing sent without mail`);
    checks.push(`${tag}: without mail set up the link is only shown to pass on`);

    // 2. Mail set up: the same dialog mails it.
    await api(
      "/mail-settings",
      { host: "127.0.0.1", port: smtp.port, security: "none", fromAddress: "refiroo@example.org" },
      "PUT",
    );
    await page.goto(`${uiUrl}/settings/people`);
    await page.getByRole("heading", { level: 1, name: "People" }).waitFor();
    shown = await newPerson(`bea-${tag}`, `Bea ${tag}`, `bea-${tag}@example.org`, "Add person");
    await shown.getByText(/sets a password with this link/).waitFor();
    expect(smtp.messages.length === 0, `${tag}: nothing is sent until Mail it is pressed`);
    await shown.getByRole("button", { name: `Mail it to bea-${tag}@example.org` }).click();
    await shown.getByText(new RegExp(`was mailed to bea-${tag}@example.org`)).waitFor();
    const link = await shown.locator("code").innerText();
    await shot(page, "link-mailed");
    await axe(page, `${tag}-link-mailed`);
    await shown.getByRole("button", { name: "I have copied it" }).click();
    expect(await received(smtp, 1), `${tag}: the message reached the server`);
    expect(decoded(smtp.messages[0] ?? "").includes(link.trim()), `${tag}: the mail holds the link the dialog showed`);
    expect(smtp.messages[0]?.includes(`To: bea-${tag}@example.org`), `${tag}: addressed to the person`);
    checks.push(`${tag}: a new person's link mailed; the dialog named the address and the mail held the same link`);

    // 3. Reset password mails a new-password message.
    await page.getByRole("button", { name: "Make a password link" }).click();
    const again = page.getByRole("dialog", { name: "Pass on the password link" });
    await again.getByRole("button", { name: /^Mail it to/ }).click();
    await again.getByText(/was mailed to/).waitFor();
    await again.getByRole("button", { name: "I have copied it" }).click();
    expect(await received(smtp, 2), `${tag}: the second message reached the server`);
    const second = decoded(smtp.messages[1] ?? "");
    expect(second.includes(`To: bea-${tag}@example.org`), `${tag}: the second message is addressed to the person`);
    const secondLink = second.match(/https?:\/\/\S+reset-password\?token=\S+/)?.[0] ?? "";
    expect(
      secondLink !== "" && secondLink !== link.trim(),
      `${tag}: the second message holds a newer link than the first (${secondLink})`,
    );
    checks.push(`${tag}: Make a password link, then Mail it, on a person's page mails it too`);

    // 4. 390px.
    await page.setViewportSize({ width: 390, height: 844 });
    shown = await newPerson(`di-${tag}`, `Di ${tag}`, `di-${tag}@example.org`, "Add person");
    await shown.getByRole("button", { name: /^Mail it to/ }).click();
    await shown.getByText(/was mailed to/).waitFor();
    await shot(page, "link-mailed-390");
    expect((await overflow(page)) <= 0, `${tag}: no horizontal scroll at 390px`);
    await shown.getByRole("button", { name: "I have copied it" }).click();
    expect(await received(smtp, 3), `${tag}: the 390px message reached the server`);
    expect(
      decoded(smtp.messages[2] ?? "").includes(`To: di-${tag}@example.org`),
      `${tag}: the 390px message is addressed to the person`,
    );
    checks.push(`${tag}: the mailed dialog at 390px`);

    await context.close();
    const report = { browser: browser.version(), model: tag, checks, failures, passed: !failures.length };
    await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
    console.log(`SP3 browser evidence (${tag}): ${output}`);
  } finally {
    harness?.cleanup();
    smtp?.stop();
  }
}

try {
  for (const configuration of SHAPED_MODELS) await walk(configuration);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("SP3 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
