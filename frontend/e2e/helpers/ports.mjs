// Free ports for the runners' servers, taken without a race. A port the operating system just gave out
// can be given to the next caller as soon as it is closed, so two runners starting together could be
// handed the same one. A port is therefore reserved before it is used: a file named for it, created
// exclusively, in one folder every runner shares, holding the owner's process number. A reservation ends
// with its owner's process; a reservation whose owner has ended is taken over.
import { closeSync, mkdirSync, openSync, readFileSync, rmSync, writeSync } from "node:fs";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { resolve } from "node:path";

// The lanes command gives each runner a temporary folder of its own; every runner shares this one.
export const RESERVATIONS = process.env.RDM_PORTS_DIR ?? resolve(tmpdir(), "rdm-test-ports");
const held = new Set();
let cleaning = false;

/** True when the process exists (a process that is not ours answers EPERM and still exists). */
export function alive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error.code === "EPERM";
  }
}

function release() {
  for (const port of held) rmSync(resolve(RESERVATIONS, String(port)), { force: true });
  held.clear();
}

/** Reserve `port` for this process. False when another live process holds it. */
export function reserve(port, directory = RESERVATIONS) {
  mkdirSync(directory, { recursive: true });
  const file = resolve(directory, String(port));
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const handle = openSync(file, "wx");
      writeSync(handle, String(process.pid));
      closeSync(handle);
      if (directory === RESERVATIONS) {
        held.add(port);
        if (!cleaning) {
          cleaning = true;
          process.on("exit", release);
        }
      }
      return true;
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      const owner = Number.parseInt(readFileSync(file, "utf8"), 10);
      if (owner === process.pid || (Number.isFinite(owner) && alive(owner))) return false;
      rmSync(file, { force: true }); // its owner has ended
    }
  }
  return false;
}

/** Let go of a reservation early. */
export function unreserve(port, directory = RESERVATIONS) {
  held.delete(port);
  rmSync(resolve(directory, String(port)), { force: true });
}

async function operatingSystemPort() {
  const server = createServer();
  await new Promise((done, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", done);
  });
  const { port } = server.address();
  await new Promise((done) => server.close(done));
  return port;
}

/** A port that is free and that no other runner has reserved; reserved for this process until it ends. */
export async function reservePort() {
  for (let attempt = 0; attempt < 50; attempt++) {
    const port = await operatingSystemPort();
    if (reserve(port)) return port;
  }
  throw new Error("No free port could be reserved: 50 ports the system offered were reserved by other runners.");
}

/** True when nothing listens on `port` at 127.0.0.1 (a bind, not a connection attempt). */
export async function isFree(port) {
  const server = createServer();
  try {
    await new Promise((done, reject) => {
      server.once("error", reject);
      server.listen(port, "127.0.0.1", done);
    });
  } catch {
    return false;
  }
  await new Promise((done) => server.close(done));
  return true;
}
