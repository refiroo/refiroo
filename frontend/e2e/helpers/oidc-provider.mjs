// The harness's minimal OpenID Connect provider (backend/tests/oidc_provider.py) as a process of
// its own, for the runners that sign people in through a provider (0.12 I3, I4).
import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { createServer } from "node:net";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..", "..", "..");

function freePort() {
  return new Promise((done, fail) => {
    const server = createServer();
    server.once("error", fail);
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      server.close(() => done(port));
    });
  });
}

/** Start the provider on a free port; the caller stops it with `child.kill()`. */
export async function startProvider() {
  const port = await freePort();
  const secret = randomBytes(18).toString("base64url");
  const child = spawn(
    resolve(root, "backend/.venv/bin/python"),
    ["tests/oidc_provider.py", "--port", String(port), "--client-id", "engine", `--client-secret=${secret}`],
    { cwd: resolve(root, "backend"), stdio: ["ignore", "pipe", "pipe"] },
  );
  let log = "";
  child.stdout.on("data", (data) => (log += data));
  child.stderr.on("data", (data) => (log += data));
  const issuer = `http://127.0.0.1:${port}`;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (child.exitCode !== null) throw new Error(`The harness provider exited: ${log}`);
    try {
      if ((await fetch(`${issuer}/.well-known/openid-configuration`)).ok) return { issuer, secret, child };
    } catch {
      /* starting */
    }
    await new Promise((done) => setTimeout(done, 100));
  }
  throw new Error(`The harness provider did not start: ${log}`);
}
