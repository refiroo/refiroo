// The guide's checks (guide/AGENTS.md). One command each, from guide/:
//   npm run check          the static checks: banned terms and the product name (needs no build)
//   npm run check:terms | check:brand
//   npm run check:links    links and anchors in the built site (run `npm run build` first)
//   npm run verify         build, then every check including links
// Each check prints what it found and exits 1 when it found a problem.
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const CONTENT = join(ROOT, "src", "content", "docs");
const DIST = process.env.GUIDE_OUT ? resolve(ROOT, process.env.GUIDE_OUT) : join(ROOT, "dist");
const BASE = "/docs";
// Paths the engine itself serves beside the documentation: links to them are not files in the built site.
const ENGINE_PATHS = ["/docs/api", "/openapi.json", "/health", "/api/"];

const problems = [];
const notes = [];
const fail = (check, where, message) => problems.push(`${check}: ${where}: ${message}`);

function walk(directory, extensions) {
  if (!existsSync(directory)) return [];
  return readdirSync(directory, { recursive: true })
    .map((entry) => join(directory, String(entry)))
    .filter((path) => statSync(path).isFile() && extensions.some((extension) => path.endsWith(extension)))
    .sort();
}

function readPage(path) {
  const text = readFileSync(path, "utf8");
  const match = text.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  const where = relative(ROOT, path);
  const front = {};
  for (const field of ["title", "description"]) {
    const line = match?.[1].match(new RegExp(`^${field}:\\s*(.*)$`, "m"));
    if (line) front[field] = line[1].replace(/^["']|["']$/g, "");
  }
  return { path, where, text, front, body: match ? match[2] : text };
}

const pages = () => walk(CONTENT, [".md", ".mdx"]).map(readPage);

// --- banned terms ---------------------------------------------------------------------------------

// Package and decision IDs, journey and capability IDs, and delivery history have no place in what a
// reader sees (the writing rules). Release notes and upgrade pages are the only place for versions.
const BANNED = [
  [/\b(?:[A-Z]{1,4}-)?D\d{1,3}\b/, "a decision ID"],
  [/\b(?:DOC|AP|AG|AO|AI|DP|WM|UA|PG|HM|SP|WP|SC)\d{1,2}[A-Za-z]?\b/, "a package ID"],
  // Function keys (F2, Shift+F10) are keys a reader presses, not IDs.
  [/(?<![+\w])(?!F(?:[1-9]|1[0-2])\b)\b[A-Z]\d{1,2}[a-z]?\b/, "a package, journey or capability ID"],
  [/\b(?:Base|Product|Release)\s0\.\d+/, "delivery history (a release number)"],
  [/\b[Ss]ince\s(?:version\s|release\s)?0\.\d+/, "delivery history (\"since 0.x\")"],
];
const PRIVATE_TERMS = join(ROOT, "tools", "private-terms.txt");

const normalWord = (word) => word.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]/g, "");
const termHash = (words) => createHash("sha256").update(words.map(normalWord).join(" ")).digest("hex");

// The private-model names are kept as SHA-256 hashes of the lower-case words, so the list does not name
// what it forbids. `node tools/check.mjs hash-term "two words"` prints the line to add.
function privateHashes() {
  if (!existsSync(PRIVATE_TERMS)) return new Set();
  return new Set(
    readFileSync(PRIVATE_TERMS, "utf8")
      .split("\n")
      .map((line) => line.replace(/#.*/, "").trim())
      .filter(Boolean),
  );
}

function terms() {
  const hashes = privateHashes();
  const subjects = pages().map((page) => ({ where: page.where, text: page.text }));
  for (const { where, text } of subjects) {
    const body = text.replace(/\{\/\*[\s\S]*?\*\/\}/g, "");
    for (const [pattern, what] of BANNED) {
      const found = body.match(new RegExp(pattern.source, pattern.flags + "g"));
      if (found) fail("terms", where, `${what}: ${[...new Set(found)].join(", ")}`);
    }
    const words = body.split(/[^A-Za-z0-9]+/).filter(Boolean);
    for (let size = 1; size <= 4; size += 1) {
      for (let at = 0; at + size <= words.length; at += 1) {
        if (hashes.has(termHash(words.slice(at, at + size)))) fail("terms", where, "a private-model name (matched by hash)");
      }
    }
  }
  notes.push(`terms: ${hashes.size} private-model name(s) on the list (tools/private-terms.txt)`);
}

// --- the product name -----------------------------------------------------------------------------

function brand() {
  const subjects = pages().map((page) => ({ where: page.where, text: page.text }));
  for (const { where, text } of subjects) {
    const body = text.replace(/\{\/\*[\s\S]*?\*\/\}/g, "");
    for (const spelling of new Set(body.match(/refiroo/gi) ?? [])) {
      if (spelling !== "refiroo") fail("brand", where, `"${spelling}" must be written "refiroo", in lower case, even at the start of a sentence`);
    }
    if (/\bRDM Engine\b/.test(body)) fail("brand", where, '"RDM Engine" is the old name: write "refiroo", or "the engine" in technical text');
  }
}

// --- links and anchors in the built site ----------------------------------------------------------

function links() {
  if (!existsSync(DIST)) {
    fail("links", "dist", "the site is not built; run `npm run build` first");
    return;
  }
  const files = walk(DIST, [".html"]);
  const ids = new Map();
  const idsOf = (file) => {
    if (!ids.has(file)) ids.set(file, new Set([...readFileSync(file, "utf8").matchAll(/\sid=["']([^"']+)["']/g)].map((m) => m[1])));
    return ids.get(file);
  };
  const fileFor = (path) => {
    // A path inside the built site (base removed): a file, or a directory with an index.
    const candidate = join(DIST, decodeURIComponent(path));
    if (existsSync(candidate) && statSync(candidate).isFile()) return candidate;
    const index = join(candidate, "index.html");
    return existsSync(index) ? index : null;
  };
  let checked = 0;
  for (const file of files) {
    const here = `${BASE}/${relative(DIST, file).replace(/index\.html$/, "")}`;
    const html = readFileSync(file, "utf8");
    for (const [, attribute, target] of html.matchAll(/\s(href|src)=["']([^"']*)["']/g)) {
      if (!target || /^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(target)) continue;
      checked += 1;
      const url = new URL(target, `http://guide.invalid${here}`);
      let path = url.pathname;
      const engineOwned = ENGINE_PATHS.some((engine) => path === engine || path.startsWith(engine.endsWith("/") ? engine : `${engine}/`));
      if (engineOwned) continue;
      if (!path.startsWith(`${BASE}/`) && path !== BASE) {
        fail("links", relative(DIST, file), `${attribute} "${target}" leaves the guide for a path the engine does not serve`);
        continue;
      }
      path = path.slice(BASE.length) || "/";
      const targetFile = fileFor(path);
      if (!targetFile) {
        fail("links", relative(DIST, file), `${attribute} "${target}" points to nothing`);
        continue;
      }
      if (attribute === "href" && url.hash.length > 1 && targetFile.endsWith(".html") && !idsOf(targetFile).has(decodeURIComponent(url.hash.slice(1)))) {
        fail("links", relative(DIST, file), `"${target}" points to an anchor that does not exist`);
      }
    }
  }
  notes.push(`links: ${checked} local links and sources in ${files.length} built pages`);
}

// --- running --------------------------------------------------------------------------------------

const CHECKS = { terms, brand, links };
const STATIC = ["terms", "brand"];

const [, , command, argument] = process.argv;
if (command === "hash-term") {
  if (!argument) {
    console.error('usage: node tools/check.mjs hash-term "the name"');
    process.exit(2);
  }
  console.log(termHash(argument.split(/[^A-Za-z0-9]+/).filter(Boolean)));
  process.exit(0);
}
const selected = command === "all" ? STATIC : command in CHECKS ? [command] : null;
if (!selected) {
  console.error(`usage: node tools/check.mjs <${["all", ...Object.keys(CHECKS), "hash-term"].join(" | ")}>`);
  process.exit(2);
}
for (const name of selected) CHECKS[name]();
for (const note of notes) console.log(note);
if (problems.length) {
  console.error(problems.join("\n"));
  console.error(`\n${problems.length} problem(s) in ${selected.join(", ")}.`);
  process.exit(1);
}
console.log(`ok: ${selected.join(", ")} (${pages().length} page(s))`);
