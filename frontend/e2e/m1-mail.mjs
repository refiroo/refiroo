// 0.12 M1 browser evidence: Settings › Integration › Mail against a real backend and a harness SMTP
// server (helpers/smtp-server.mjs), on two models (the starter, and the starter under another
// product name), at 1440px and 390px, light and dark. As the harness person, by keyboard: the page
// says mail is not set up; a server is saved (the port follows the connection; a login without
// encryption is refused before anything is sent); a test message arrives at the server; a recipient
// the server refuses and a server that cannot be reached each say what failed; the outbox lists
// what the engine queued (rows written from outside the API: no route queues mail yet, SP3 and I6
// are the first producers) and narrows to the failed one with its reason; the settings are removed
// through their confirmation. Axe on each state; screenshots; no horizontal page scroll at 390px.
import { writeFile } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { startSmtp } from "./helpers/smtp-server.mjs";

const MODELS = [{ name: "starter" }, { name: "renamed", product: "Northfield Reference Data" }];
const backend = resolve(import.meta.dirname, "..", "..", "backend");

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

/** Messages the engine queued and finished, written from outside the API into the run's database. */
function writeOutbox(databaseUrl) {
  const code = `
import os, sqlalchemy as sa
engine = sa.create_engine(os.environ["DATABASE_URL"])
rows = [
    ("sent", "activation", "grace@example.org", "Your account", 1, None, None),
    ("failed", "password-reset", "gone@example.org", "Choose a new password", 1,
     "127.0.0.1:25 refused the address: 550 5.1.1 no such mailbox", "recipient"),
]
with engine.begin() as connection:
    for status, kind, to, subject, attempts, error, error_kind in rows:
        connection.execute(sa.text(
            "INSERT INTO mail_outbox (public_id, kind, to_address, subject, status, attempts, last_error, "
            "last_error_kind, created_at, next_attempt_at, finished_at) "
            "VALUES (gen_random_uuid()::text, :kind, :to, :subject, :status, :attempts, :error, :error_kind, "
            "now() - interval '1 hour', now() - interval '1 hour', now() - interval '59 minutes')"),
            dict(kind=kind, to=to, subject=subject, status=status, attempts=attempts, error=error, error_kind=error_kind))
`;
  execFileSync(resolve(backend, ".venv/bin/python"), ["-c", code], {
    cwd: backend,
    env: { ...process.env, DATABASE_URL: databaseUrl },
  });
}

async function walk(configuration) {
  const smtp = await startSmtp();
  const harness = await bootHarness({
    transformModel: configuration.product
      ? (model) => {
          model.product.name = configuration.product;
        }
      : undefined,
  });
  try {
    const { uiUrl, api, output, browser, databaseUrl } = harness;
    const tag = configuration.name;
    const overflow = (target) => target.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    const shot = (target, name) => target.screenshot({ path: resolve(output, `${tag}-${name}.png`), fullPage: true });

    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    page.on("pageerror", (error) => failures.push(`${tag}: ${error.message}`));

    // 1. Mail is under Integration; nothing is set up.
    await page.goto(`${uiUrl}/settings/mail`);
    await page.getByRole("heading", { level: 1, name: "Mail" }).waitFor();
    await page.getByRole("navigation", { name: "Settings" }).getByRole("link", { name: "Mail" }).waitFor();
    await page.getByText("Mail is not set up", { exact: true }).waitFor();
    await page.getByText(/No messages yet/).waitFor();
    expect(
      await page.getByRole("button", { name: "Send test message" }).isDisabled(),
      `${tag}: no test before a server is saved`,
    );
    expect(
      (await page.getByLabel("Port", { exact: true }).inputValue()) === "587",
      `${tag}: the port starts at STARTTLS's`,
    );
    await shot(page, "not-set-up");
    await axe(page, `${tag}-not-set-up`);
    checks.push(
      `${tag}: Mail listed under Integration; nothing set up, nothing sent, no test before a server is saved`,
    );

    // 2. A server saved by keyboard; a login without encryption is refused before anything is sent.
    await page.getByLabel("Server", { exact: true }).focus();
    await page.keyboard.type("127.0.0.1");
    await page.getByLabel("Connection", { exact: true }).selectOption("none");
    expect(
      (await page.getByLabel("Port", { exact: true }).inputValue()) === "25",
      `${tag}: the port follows the connection`,
    );
    await page.getByLabel("Port", { exact: true }).fill(String(smtp.port));
    await page.getByLabel("User name", { exact: true }).fill("mailer");
    await page.getByText(/A login is not sent over an unencrypted connection/).waitFor();
    expect(
      await page.getByRole("button", { name: "Save" }).isDisabled(),
      `${tag}: Save refused while a login would travel unencrypted`,
    );
    await shot(page, "insecure-login");
    await axe(page, `${tag}-insecure-login`);
    await page.getByLabel("User name", { exact: true }).fill("");
    await page.getByLabel("From address", { exact: true }).focus();
    await page.keyboard.type("refiroo@example.org");
    await page.keyboard.press("Enter");
    await page.getByRole("button", { name: "Remove settings…" }).waitFor();
    const saved = await api("/mail-settings");
    expect(
      saved.configured && saved.port === smtp.port && saved.username === null && !saved.passwordSet,
      `${tag}: the settings were saved`,
    );
    checks.push(
      `${tag}: a server saved by keyboard; the port followed the connection; a login without encryption refused`,
    );

    // 3. A test message arrives; a refused recipient and an unreachable server each say what failed.
    await page.getByLabel("Send to", { exact: true }).focus();
    await page.keyboard.type("ada@example.org");
    await page.keyboard.press("Enter");
    await page.getByRole("status").filter({ hasText: "The server accepted the message for ada@example.org" }).waitFor();
    expect(
      smtp.messages.length === 1 && /Subject: .*test message/i.test(smtp.messages[0]),
      `${tag}: the test message reached the server`,
    );
    expect(smtp.messages[0].includes(saved.applicationUrl), `${tag}: the test message shows where links point`);
    await shot(page, "test-sent");
    await axe(page, `${tag}-test-sent`);

    smtp.refuse("gone@example.org", 550, "5.1.1 no such mailbox");
    await page.getByLabel("Send to", { exact: true }).fill("gone@example.org");
    await page.keyboard.press("Enter");
    await page.getByRole("alert").filter({ hasText: "The server refused the address" }).waitFor();
    await page
      .getByText(/550 5\.1\.1 no such mailbox/)
      .first()
      .waitFor();
    await shot(page, "test-refused");
    await axe(page, `${tag}-test-refused`);

    await page.getByLabel("Port", { exact: true }).fill("9");
    await page.getByRole("button", { name: "Save" }).click();
    await page.getByRole("button", { name: "Remove settings…" }).waitFor();
    await page.getByLabel("Send to", { exact: true }).fill("ada@example.org");
    await page.keyboard.press("Enter");
    await page.getByRole("alert").filter({ hasText: "The server could not be reached" }).waitFor();
    checks.push(`${tag}: a test message delivered; a refused address and an unreachable server each named what failed`);
    await page.getByLabel("Port", { exact: true }).fill(String(smtp.port));
    await page.getByRole("button", { name: "Save" }).click();
    await page
      .getByText(/Mail settings saved/)
      .last()
      .waitFor();

    // 4. The outbox: what the engine queued, narrowed to the failed message and its reason.
    writeOutbox(databaseUrl);
    await page.getByRole("button", { name: "Refresh" }).focus();
    await page.keyboard.press("Enter");
    await page.getByRole("row", { name: /grace@example\.org/ }).waitFor();
    const failed = page.getByRole("row", { name: /gone@example\.org/ });
    await failed.getByText("Failed", { exact: true }).waitFor();
    await failed.getByText(/550 5\.1\.1 no such mailbox/).waitFor();
    await shot(page, "messages");
    await axe(page, `${tag}-messages`);
    await page.getByRole("combobox", { name: /^State/ }).selectOption("failed");
    await page.getByRole("row", { name: /grace@example\.org/ }).waitFor({ state: "detached" });
    await page.getByRole("row", { name: /gone@example\.org/ }).waitFor();
    const rows = await page.getByRole("row").allInnerTexts();
    expect(rows.length === 2, `${tag}: only the failed message is listed, found ${JSON.stringify(rows)}`);
    checks.push(`${tag}: the outbox lists a sent and a failed message; narrowed to Failed, with its reason`);

    // 5. Dark and a phone.
    const dark = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: "dark" });
    const night = await dark.newPage();
    night.setDefaultTimeout(15000);
    await night.goto(`${uiUrl}/settings/mail`);
    await night.getByRole("button", { name: "Remove settings…" }).waitFor();
    await shot(night, "dark");
    await axe(night, `${tag}-dark`);
    await dark.close();
    const narrow = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
    const phone = await narrow.newPage();
    phone.setDefaultTimeout(15000);
    await phone.goto(`${uiUrl}/settings/mail`);
    await phone.getByRole("button", { name: "Remove settings…" }).waitFor();
    await phone.getByRole("row", { name: /gone@example\.org/ }).waitFor();
    expect((await overflow(phone)) <= 0, `${tag}: Mail scrolls sideways at 390px`);
    await shot(phone, "narrow");
    await axe(phone, `${tag}-narrow`);
    await narrow.close();
    checks.push(`${tag}: dark; 390px without horizontal page scroll`);

    // 6. The settings removed through their confirmation.
    await page.getByRole("button", { name: "Remove settings…" }).focus();
    await page.keyboard.press("Enter");
    const confirm = page.getByRole("alertdialog", { name: "Remove the mail settings?" });
    await confirm.waitFor();
    expect(
      await confirm.getByRole("button", { name: "Cancel" }).evaluate((el) => el === document.activeElement),
      `${tag}: Cancel has focus`,
    );
    await shot(page, "remove");
    await axe(page, `${tag}-remove`);
    await page.keyboard.press("Tab");
    await page.keyboard.press("Enter");
    await confirm.waitFor({ state: "detached" });
    await page.getByText("Mail is not set up", { exact: true }).waitFor();
    expect(!(await api("/mail-settings")).configured, `${tag}: the settings were removed`);
    checks.push(`${tag}: removal confirmed by keyboard; Mail is not set up again`);

    await context.close();
    const report = { browser: browser.version(), model: tag, checks, failures, passed: !failures.length };
    await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
    console.log(`M1 browser evidence (${tag}): ${output}`);
  } finally {
    harness.cleanup();
    smtp.stop();
  }
}

try {
  for (const configuration of MODELS) await walk(configuration);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("M1 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
