// Free ports for the runners' servers, taken without a race. A port the operating system just gave out
// can be given to the next caller as soon as it is closed, so two runners starting together could be
// handed the same one. A port is therefore reserved before it is used: a file named for it, created
// exclusively, in one folder every runner shares, holding the owner's process number. A reservation ends
// with its owner's process; a reservation whose owner has ended is taken over.
import { closeSync, mkdirSync, openSync, readFileSync, rmSync, statSync, writeSync } from "node:fs";
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

// A reservation file exists for a moment before its owner's process number is written into it: an empty
// or unreadable file is a reservation being made, so it is waited for, and given up as stale only when it
// has stayed empty for STALE_AFTER_MS.
const EMPTY_WAIT_MS = 1000;
const STALE_AFTER_MS = 5000;
const sleep = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);

/** The process number in `file`: a number, "empty" while it is being written, or "gone" when it was removed. */
function ownerOf(file) {
  const waitUntil = Date.now() + EMPTY_WAIT_MS;
  for (;;) {
    let text;
    try {
      text = readFileSync(file, "utf8");
    } catch (error) {
      if (error.code === "ENOENT") return "gone";
      throw error;
    }
    const owner = Number.parseInt(text, 10);
    if (Number.isFinite(owner)) return owner;
    if (Date.now() >= waitUntil) {
      try {
        if (Date.now() - statSync(file).mtimeMs < STALE_AFTER_MS) return "empty";
      } catch {
        return "gone";
      }
      return "stale";
    }
    sleep(10);
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
  for (let attempt = 0; attempt < 3; attempt++) {
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
      const owner = ownerOf(file);
      if (owner === "gone") continue; // released meanwhile: take it
      if (owner === "empty") return false; // still being made by another process
      if (owner !== "stale" && (owner === process.pid || alive(owner))) return false;
      rmSync(file, { force: true }); // its owner has ended, or it never got its process number
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
