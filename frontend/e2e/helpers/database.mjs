// A browser runner's own PostgreSQL database, cloned from a seed on the development server
// (0.9.0-alpha.1 PG2): `scripts/postgres.sh start` first. See backend/tests/browser_seeds.py.
import { execFileSync } from "node:child_process";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const backend = resolve(root, "backend");
const python = resolve(backend, ".venv/bin/python");

function seeds(args) {
  try {
    return execFileSync(python, ["tests/browser_seeds.py", ...args], {
      cwd: backend,
      stdio: ["ignore", "pipe", "pipe"],
    }).toString();
  } catch (error) {
    throw new Error(`tests/browser_seeds.py ${args.join(" ")} failed:\n${error.stderr?.toString() ?? error.message}`);
  }
}

/**
 * Clone `seed` ("schema", "starter" or "volume") into a new database for this runner.
 * @param {"schema" | "starter" | "volume"} seed
 * @param {{model?: string, scale?: string | number}} [options] - the model file the runner
 *   starts with ("starter"), or where to write the volume model and the scale ("volume").
 * @returns {{databaseUrl: string, payload: object, drop: () => void}}
 */
export function cloneDatabase(seed, options = {}) {
  const args = ["clone", seed];
  if (options.model) args.push("--model", options.model);
  if (options.scale !== undefined) args.push("--scale", String(options.scale));
  const { database_url: databaseUrl, ...payload } = JSON.parse(seeds(args).trim().split("\n").at(-1));
  let dropped = false;
  return {
    databaseUrl,
    payload,
    drop() {
      if (dropped) return;
      dropped = true;
      try { seeds(["drop", databaseUrl]); } catch (error) { console.error(error.message); }
    },
  };
}
