// The guide's checks (guide/AGENTS.md). One command each, from guide/:
//   npm run check          the static checks: banned terms and the product name (needs no build)
//   npm run check:terms | check:brand
//   npm run check:links    links and anchors in the built site (run `npm run build` first)
//   npm run verify         build, then every check including links
//   node tools/check.mjs coverage   every inventory entry is named on a page or excluded (CP; not in verify yet)
// Each check prints what it found and exits 1 when it found a problem.
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = "/Users/krisztian/Documents/Projects/rdm-engine/guide";
const CONTENT = join(ROOT, "src", "content", "docs");
const DIST = process.env.GUIDE_OUT ? resolve(ROOT, process.env.GUIDE_OUT) : join(ROOT, "dist");
const BASE = "/docs";
// Paths the engine itself serves beside the documentation: links to them are not files in the built site.
const ENGINE_PATHS = ["/docs/api", "/openapi.json", "/health", "/api/"];
// The application's own start page, which the shared header links to (exact path only).
const APP_PATHS = ["/"];

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
function terms() {
  const subjects = pages().map((page) => ({ where: page.where, text: page.text }));
  for (const { where, text } of subjects) {
    const body = text.replace(/\{\/\*[\s\S]*?\*\/\}/g, "");
    for (const [pattern, what] of BANNED) {
      const found = body.match(new RegExp(pattern.source, pattern.flags + "g"));
      if (found) fail("terms", where, `${what}: ${[...new Set(found)].join(", ")}`);
    }
  }
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
      const engineOwned = APP_PATHS.includes(path) || ENGINE_PATHS.some((engine) => path === engine || path.startsWith(engine.endsWith("/") ? engine : `${engine}/`));
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

// --- coverage of the inventory ----------------------------------------------------------------------

// guide/tools/inventory.py writes guide/_coverage/inventory/<kind>.json from the code. An entry is covered when
// its key (or an alias) stands on a page exactly, or one of its labels stands on a page, ignoring case and only
// as a whole word (a label starting with "/" is a path: its {placeholders} are compared without their names and it
// must not run on into a longer path). An entry with `context` counts a label or alias only on a page that also
// names one of the context words. An entry is excluded by a line `kind key — reason` in
// guide/_coverage/exclusions.md. Prints the counts per kind and section, writes inventory/uncovered.md, and fails
// while anything is uncovered.
const INVENTORY = join(ROOT, "_coverage", "inventory");
const EXCLUSIONS = join(ROOT, "_coverage", "exclusions.md");
const SECTION_ORDER = ["run", "administer", "model", "use", "integrate", "about"];

const escapeRegExp = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const normalPath = (text) => text.replace(/\{[^}]*\}/g, "{}");

function labelPattern(label) {
  const isPath = label.startsWith("/");
  const text = escapeRegExp(isPath ? normalPath(label) : label).replace("\\{\\}", "\\{\\}");
  const before = /^\w/.test(label) ? "(?<![A-Za-z0-9_])" : "";
  const after = isPath ? "(?![A-Za-z0-9_\\-{/])" : /\w$/.test(label) ? "(?![A-Za-z0-9_])" : "";
  return new RegExp(`${before}${text}${after}`, "i");
}

function exclusions() {
  const found = new Map();
  if (!existsSync(EXCLUSIONS)) return found;
  for (const line of readFileSync(EXCLUSIONS, "utf8").split("\n")) {
    if (!line.trim() || /^[#>]/.test(line)) continue;
    const match = line.match(/^(\S+)\s+(.+?)\s+—\s+(.+)$/);
    if (match) found.set(`${match[1]} ${match[2]}`, match[3]);
    else fail("coverage", "exclusions.md", `not "kind key — reason": ${line}`);
  }
  return found;
}

function coverage() {
  if (!existsSync(INVENTORY) || !readdirSync(INVENTORY).some((name) => name.endsWith(".json"))) {
    fail("coverage", "_coverage/inventory", "no inventory; run backend/.venv/bin/python guide/tools/inventory.py first");
    return;
  }
  const texts = pages().map((page) => ({ where: page.where, raw: page.text, flat: normalPath(page.text), low: page.text.toLowerCase() }));
  const excluded = exclusions();
  const entries = walk(INVENTORY, [".json"]).flatMap((file) => JSON.parse(readFileSync(file, "utf8")));
  const unused = new Set(excluded.keys());
  const table = new Map();
  const uncovered = [];
  for (const item of entries) {
    const cell = table.get(`${item.kind}\t${item.section}`) ?? { total: 0, covered: 0, excluded: 0, uncovered: 0 };
    table.set(`${item.kind}\t${item.section}`, cell);
    cell.total += 1;
    const reason = excluded.get(`${item.kind} ${item.key}`);
    unused.delete(`${item.kind} ${item.key}`);
    if (reason !== undefined) {
      cell.excluded += 1;
      continue;
    }
    // A management operation is documented by the API reference at /docs/api, generated from the code with its summary;
    // the Integrate pages explain the concepts and link there, so the guide does not name every path.
    if (item.kind === "management-api" && item.summary) {
      cell.covered += 1;
      continue;
    }
    const context = (item.context ?? []).map((word) => word.toLowerCase());
    const patterns = [...(item.labels ?? []), ...(item.aliases ?? [])].map(labelPattern);
    const hit = texts.some(
      (page) =>
        page.raw.includes(item.key) ||
        (patterns.length > 0 && (!context.length || context.some((word) => page.low.includes(word))) && patterns.some((pattern) => pattern.test(page.flat))),
    );
    if (hit) cell.covered += 1;
    else {
      cell.uncovered += 1;
      uncovered.push(item);
    }
  }
  for (const key of unused) notes.push(`coverage: exclusion matches no inventory entry: ${key}`);

  const rows = [...table.entries()]
    .map(([name, cell]) => ({ kind: name.split("\t")[0], section: name.split("\t")[1], ...cell }))
    .sort((a, b) => a.kind.localeCompare(b.kind) || SECTION_ORDER.indexOf(a.section) - SECTION_ORDER.indexOf(b.section));
  const widths = [16, 10, 7, 8, 9, 10];
  const line = (cells) => cells.map((value, i) => String(value).padEnd(widths[i])).join(" ");
  notes.push(line(["kind", "section", "total", "covered", "excluded", "uncovered"]));
  for (const row of rows) notes.push(line([row.kind, row.section, row.total, row.covered, row.excluded, row.uncovered]));
  const sum = (field) => rows.reduce((total, row) => total + row[field], 0);
  notes.push(line(["all", "", sum("total"), sum("covered"), sum("excluded"), sum("uncovered")]));

  const out = ["# Uncovered inventory entries", "", `Written by \`node tools/check.mjs coverage\`. ${uncovered.length} of ${entries.length} entries.`, ""];
  for (const section of SECTION_ORDER) {
    const inSection = uncovered.filter((item) => item.section === section);
    if (!inSection.length) continue;
    out.push(`## ${section} (${inSection.length})`, "");
    for (const kind of [...new Set(inSection.map((item) => item.kind))].sort()) {
      const ofKind = inSection.filter((item) => item.kind === kind);
      out.push(`### ${kind} (${ofKind.length})`, "");
      for (const item of ofKind) {
        const labels = item.labels?.length ? ` — ${item.labels.map((label) => `"${label}"`).join(", ")}` : "";
        out.push(`- \`${item.key}\`${labels}${item.summary ? `: ${item.summary}` : ""} (${item.source})`);
      }
      out.push("");
    }
  }
  mkdirSync(INVENTORY, { recursive: true });
  writeFileSync(join(ROOT, "_coverage/notes/D-MODEL/uncovered.md"), out.join("\n"));
  if (uncovered.length) fail("coverage", "inventory", `${uncovered.length} entries are neither on a page nor excluded; see _coverage/inventory/uncovered.md`);
}

// --- running --------------------------------------------------------------------------------------

const CHECKS = { terms, brand, links, coverage };
const STATIC = ["terms", "brand"];

const [, , command, argument] = process.argv;
const selected = command === "all" ? STATIC : command in CHECKS ? [command] : null;
if (!selected) {
  console.error(`usage: node tools/check.mjs <${["all", ...Object.keys(CHECKS)].join(" | ")}>`);
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
