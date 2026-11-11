// 0.12 M1 browser evidence: Settings › Integration › Mail against a real backend and a harness SMTP
// server (helpers/smtp-server.mjs), on two models (the starter, and the differently shaped journey configuration generated-b), at 1440px and 390px, light and dark. As the harness person, by keyboard: the page
// says mail is not set up; a server is saved (the port follows the connection; a login without
// encryption is refused before anything is sent); a test message arrives at the server; a recipient
// the server refuses and a server that cannot be reached each say what failed; the outbox lists
// what the engine queued (rows written from outside the API, so each state is shown whatever the
// producers SP3 and I6 queue in the other runners) and narrows to the failed one with its reason; the settings are removed
// through their confirmation. Axe on each state; screenshots; no horizontal page scroll at 390px.
// 0.13 MS: the Microsoft 365 form (section 7, `microsoftForm`): the four "Sign in with" entries, the Entra
// checklist and the other clouds opened, at 1440px and 390px, light and dark, each with axe, the menu reached by
// keyboard, only the chosen entry's fields visible and no sideways scroll at 390px. `M1_M365_ONLY=1` runs only that
// section; `M1_MODELS=starter` limits the models. Section 7b (`microsoftSaved`): a saved Microsoft 365 configuration
// (secret, then certificate) opens on its entry with the credential kept, not shown; switching entry and back.
// 0.13 release review: the Settings navigation also lists "Notification email", so the Mail link is found by its exact name.
import { writeFile } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { SHAPED_MODELS, bootShaped } from "./helpers/shaped-models.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { startSmtp } from "./helpers/smtp-server.mjs";

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
    # Still being tried: its next try is an hour away, so the sender leaves it alone.
    connection.execute(sa.text(
        "INSERT INTO mail_outbox (public_id, kind, to_address, subject, status, attempts, last_error, "
        "last_error_kind, created_at, next_attempt_at) "
        "VALUES (gen_random_uuid()::text, 'activation', 'waiting@example.org', 'Your account', 'pending', 2, "
        "'The server could not be reached', 'connection', now() - interval '10 minutes', now() + interval '1 hour')"))
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

const SIGN_IN = {
  secret: { label: "Client secret", fields: ["Tenant ID", "Application (client) ID", "Client secret"] },
  certificate: { label: "Certificate", fields: ["Tenant ID", "Application (client) ID", "Certificate"] },
  direct: { label: "Managed identity – this tenant", fields: ["Identity client ID"] },
  federated: {
    label: "Managed identity – hosted in another tenant",
    fields: ["Tenant ID", "Application (client) ID", "Identity client ID"],
  },
};
const SIGN_IN_FIELDS = ["Tenant ID", "Application (client) ID", "Client secret", "Certificate", "Identity client ID"];

/** 7. The Microsoft 365 form: four ways to sign in, the Entra steps and the other clouds, in four looks. */
async function microsoftForm(harness, tag) {
  const { uiUrl, output, browser } = harness;
  for (const [width, height, scheme] of [
    [1440, 900, "light"],
    [1440, 900, "dark"],
    [390, 844, "light"],
    [390, 844, "dark"],
  ]) {
    const look = `${tag}-m365-${width}-${scheme}`;
    const context = await browser.newContext({
      viewport: { width, height },
      colorScheme: scheme,
      hasTouch: width < 600,
    });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    page.on("pageerror", (error) => failures.push(`${look}: ${error.message}`));
    const shot = (name) => page.screenshot({ path: resolve(output, `${look}-${name}.png`), fullPage: true });
    const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    const check = async (name) => {
      if (width < 600) expect((await overflow()) <= 0, `${look}-${name}: scrolls sideways at 390px`);
      await shot(name);
      await axe(page, `${look}-${name}`);
    };
    await page.goto(`${uiUrl}/settings/mail`);
    await page.getByRole("heading", { level: 1, name: "Mail" }).waitFor();
    await page.getByLabel("Send mail through", { exact: true }).selectOption("microsoft365");
    // The menu is reached by keyboard: Tab from the method choice lands on it.
    await page.getByLabel("Send mail through", { exact: true }).focus();
    await page.keyboard.press("Tab");
    expect(
      await page.getByLabel("Sign in with", { exact: true }).evaluate((el) => el === document.activeElement),
      `${look}: Sign in with is the next stop after the method choice`,
    );
    const menu = await page.getByLabel("Sign in with", { exact: true }).locator("option").allInnerTexts();
    expect(
      JSON.stringify(menu) === JSON.stringify(Object.values(SIGN_IN).map((entry) => entry.label)),
      `${look}: the menu lists the four entries, found ${JSON.stringify(menu)}`,
    );
    for (const [entry, { label, fields }] of Object.entries(SIGN_IN)) {
      await page.getByLabel("Sign in with", { exact: true }).selectOption(entry);
      const shown = [];
      for (const field of SIGN_IN_FIELDS) {
        if (await page.getByLabel(field, { exact: true }).isVisible()) shown.push(field);
      }
      expect(
        JSON.stringify(shown) === JSON.stringify(fields),
        `${look}-${entry}: shows ${JSON.stringify(shown)}, expected ${JSON.stringify(fields)}`,
      );
      expect(
        (await page.getByLabel("Server", { exact: true }).count()) === 0,
        `${look}-${entry}: SMTP fields are hidden`,
      );
      await check(entry);
      checks.push(`${look}: ${label}: only ${fields.join(", ")} shown; axe; screenshot`);
    }
    // The Entra steps of a managed identity entry, and the other clouds.
    await page.getByLabel("Sign in with", { exact: true }).selectOption("direct");
    const steps = page.getByText("What to set up in Microsoft Entra", { exact: true });
    await steps.click();
    await page.getByText(/Mail.Send.* app role/).waitFor();
    await check("direct-entra-steps");
    await page.getByLabel("Sign in with", { exact: true }).selectOption("federated");
    await page.getByText(/add a federated credential for the identity/).waitFor();
    await check("federated-entra-steps");
    await page.getByText(/Other Microsoft clouds/).click();
    await page.getByLabel("Token address", { exact: true }).waitFor();
    await check("other-clouds");
    checks.push(
      `${look}: the Entra steps (both managed identity entries) and the other clouds opened; axe; screenshots`,
    );
    await context.close();
  }
}

/** A throwaway RSA key and self-signed certificate as one PEM text, for a saved certificate. */
function demoCertificatePem() {
  const out = execFileSync(
    "openssl",
    ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "/dev/stdout", "-out", "/dev/stdout", "-subj", "/CN=refiroo-demo", "-days", "365"],
    { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] },
  );
  return out;
}

/** 7b. A Microsoft 365 configuration already saved: the form opens on it, the credential is kept, not shown. */
async function microsoftSaved(harness, tag) {
  const { uiUrl, api, output, browser } = harness;
  const demo = {
    method: "microsoft365",
    tenantId: "11111111-2222-3333-4444-555555555555",
    clientId: "66666666-7777-8888-9999-000000000000",
    fromAddress: "mail@example.org",
  };
  for (const credential of ["secret", "certificate"]) {
    const current = await api("/mail-settings");
    const body = { ...demo, ...(current.version ? { expectedVersion: current.version } : {}) };
    if (credential === "secret") body.clientSecret = "demo-secret-value-not-real";
    else body.certificate = demoCertificatePem();
    await api("/mail-settings", body, "PUT");
    for (const [width, height, scheme] of [
      [1440, 900, "light"],
      [390, 844, "dark"],
    ]) {
      const look = `${tag}-m365-saved-${credential}-${width}-${scheme}`;
      const context = await browser.newContext({ viewport: { width, height }, colorScheme: scheme, hasTouch: width < 600 });
      const page = await context.newPage();
      page.setDefaultTimeout(15000);
      page.on("pageerror", (error) => failures.push(`${look}: ${error.message}`));
      const check = async (name) => {
        if (width < 600) {
          const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
          expect(over <= 0, `${look}-${name}: scrolls sideways at 390px`);
        }
        await page.screenshot({ path: resolve(output, `${look}-${name}.png`), fullPage: true });
        await axe(page, `${look}-${name}`);
      };
      await page.goto(`${uiUrl}/settings/mail`);
      await page.getByRole("heading", { level: 1, name: "Mail" }).waitFor();
      await page.getByRole("button", { name: "Remove settings…" }).waitFor();
      expect(
        (await page.getByLabel("Send mail through", { exact: true }).inputValue()) === "microsoft365",
        `${look}: the method is Microsoft 365`,
      );
      expect(
        (await page.getByLabel("Sign in with", { exact: true }).inputValue()) === credential,
        `${look}: the menu opens on ${credential}`,
      );
      expect((await page.getByLabel("Tenant ID", { exact: true }).inputValue()) === demo.tenantId, `${look}: tenant ID shown`);
      expect((await page.getByLabel("Server", { exact: true }).count()) === 0, `${look}: SMTP fields are hidden`);
      const field = page.getByLabel(credential === "secret" ? "Client secret" : "Certificate", { exact: true });
      expect((await field.inputValue()) === "", `${look}: the credential is not shown`);
      expect(
        (await field.getAttribute("placeholder"))?.startsWith("Saved"),
        `${look}: the credential field says it is saved`,
      );
      if (credential === "secret") {
        expect(
          !(await page.content()).includes("demo-secret-value-not-real"),
          `${look}: the secret value is not in the page`,
        );
      } else {
        await page.getByText(/Saved: thumbprint/).waitFor();
        expect(!(await page.content()).includes("PRIVATE KEY"), `${look}: no key in the page`);
      }
      expect(await page.getByRole("button", { name: "Save" }).isDisabled(), `${look}: Save is off before any change`);
      await check("opened");
      // Switching the entry and back keeps the saved credential.
      await page.getByLabel("Sign in with", { exact: true }).selectOption("direct");
      expect((await page.getByLabel("Identity client ID", { exact: true }).count()) === 1, `${look}: switched to the managed identity`);
      await check("switched");
      await page.getByLabel("Sign in with", { exact: true }).selectOption(credential);
      expect(
        (await field.getAttribute("placeholder"))?.startsWith("Saved"),
        `${look}: back on ${credential} the credential is still kept`,
      );
      await check("switched-back");
      checks.push(`${look}: opens on the saved entry, the credential kept and not shown, switch and back; axe; screenshots`);
      await context.close();
    }
  }
  await api("/mail-settings", undefined, "DELETE");
}

async function walk(configuration) {
  const smtp = await startSmtp();
  const harness = await bootShaped(configuration);
  try {
    const { uiUrl, api, output, browser, databaseUrl } = harness;
    const tag = configuration.name;
    const overflow = (target) => target.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    const shot = (target, name) => target.screenshot({ path: resolve(output, `${tag}-${name}.png`), fullPage: true });

    if (process.env.M1_M365_ONLY) {
      await microsoftForm(harness, tag);
      await microsoftSaved(harness, tag);
      await writeFile(
        resolve(output, "report.json"),
        JSON.stringify({ browser: browser.version(), model: tag, checks, failures, passed: !failures.length }, null, 2),
      );
      console.log(`M1 Microsoft 365 evidence (${tag}): ${output}`);
      return;
    }
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    page.on("pageerror", (error) => failures.push(`${tag}: ${error.message}`));

    // 1. Mail is under Integration; nothing is set up.
    await page.goto(`${uiUrl}/settings/mail`);
    await page.getByRole("heading", { level: 1, name: "Mail" }).waitFor();
    await page.getByRole("navigation", { name: "Settings" }).getByRole("link", { name: "Mail", exact: true }).waitFor();
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
    expect(
      (await page
        .getByRole("row", { name: /grace@example\.org/ })
        .getByRole("button")
        .count()) === 0,
      `${tag}: a sent message has nothing to stop`,
    );
    const waiting = page.getByRole("row", { name: /waiting@example\.org/ });
    await waiting.getByText("Waiting", { exact: true }).waitFor();
    await waiting.getByRole("button", { name: "Stop sending" }).click();
    const stopDialog = page.getByRole("alertdialog", { name: "Stop sending this message?" });
    await stopDialog.waitFor();
    expect(
      await stopDialog.getByRole("button", { name: "Keep trying" }).evaluate((el) => el === document.activeElement),
      `${tag}: Keep trying has focus`,
    );
    await shot(page, "stop");
    await axe(page, `${tag}-stop`);
    await stopDialog.getByRole("button", { name: "Stop sending" }).click();
    await page
      .getByRole("row", { name: /waiting@example\.org/ })
      .getByText("Stopped by an administrator")
      .waitFor();
    expect(
      smtp.messages.every((m) => !m.includes("waiting@example.org")),
      `${tag}: nothing was sent to it`,
    );
    checks.push(`${tag}: a waiting message was stopped after a confirmation; it shows failed with the reason`);
    await page.getByRole("combobox", { name: /^State/ }).selectOption("failed");
    await page.getByRole("row", { name: /grace@example\.org/ }).waitFor({ state: "detached" });
    await page.getByRole("row", { name: /gone@example\.org/ }).waitFor();
    const rows = await page.getByRole("row").allInnerTexts();
    expect(rows.length === 3, `${tag}: only the failed messages are listed, found ${JSON.stringify(rows)}`);
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
    await microsoftForm(harness, tag);
    await microsoftSaved(harness, tag);
    const report = { browser: browser.version(), model: tag, checks, failures, passed: !failures.length };
    await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
    console.log(`M1 browser evidence (${tag}): ${output}`);
  } finally {
    harness.cleanup();
    smtp.stop();
  }
}

try {
  const only = process.env.M1_MODELS?.split(",");
  for (const configuration of SHAPED_MODELS) if (!only || only.includes(configuration.name)) await walk(configuration);
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
