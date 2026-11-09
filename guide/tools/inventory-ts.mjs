// The frontend half of the inventory (guide/tools/inventory.py calls this and reads its JSON from stdout).
// It reads the TypeScript sources with the compiler API (from frontend/node_modules) and prints:
//   routes      RouteState kinds, settings pages (with the navigation's label), tab names
//   operations  the model editor's OperationSpec objects: id, target, labels, titles, confirm text, form
//               fields, the DraftOperation kinds and JSON-pointer strings their build uses
//   menus       action menu items (an object with `label` and `onAction`)
//   confirms    ConfirmDialog usages: title, confirmLabel, dismissLabel
//   evidence    per model-editor source file: every property name and string literal (for the gap list)
// Labels are the literal text the code has; a template literal contributes its fixed head.
import { createRequire } from "node:module";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, "..", "..");
const SRC = join(REPO, "frontend", "src");
const require = createRequire(join(REPO, "frontend", "package.json"));
const ts = require("typescript");

const rel = (file) => relative(REPO, file);
const walk = (directory) =>
  readdirSync(directory, { recursive: true })
    .map((entry) => join(directory, String(entry)))
    .filter((path) => statSync(path).isFile() && /\.tsx?$/.test(path) && !/\.test\.tsx?$/.test(path))
    .sort();
const parse = (file) => ts.createSourceFile(file, readFileSync(file, "utf8"), ts.ScriptTarget.Latest, true, file.endsWith("x") ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
const lineOf = (node) => node.getSourceFile().getLineAndCharacterOfPosition(node.getStart()).line + 1;
const where = (node) => `${rel(node.getSourceFile().fileName)}:${lineOf(node)}`;

// The fixed text in an expression: string literals, and the head of each template literal.
function texts(node) {
  const found = [];
  const visit = (n) => {
    if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) found.push(n.text);
    else if (ts.isTemplateExpression(n)) found.push(n.head.text);
    ts.forEachChild(n, visit);
  };
  if (node) visit(node);
  return found;
}
const clean = (list) =>
  [...new Set(list.map((text) => text.replace(/[…]|\.\.\.$/g, "").replace(/\s+/g, " ").trim()).filter((text) => text.length >= 3))];
const propName = (p) => (p.name && (ts.isIdentifier(p.name) || ts.isStringLiteral(p.name)) ? p.name.text : null);
const prop = (object, name) => object.properties.find((p) => ts.isPropertyAssignment(p) && propName(p) === name);

const files = walk(SRC);

// --- routes ---------------------------------------------------------------------------------------
const routes = { kinds: [], pages: [], tabs: [], navigation: [] };
{
  const file = join(SRC, "types", "ui.ts");
  const source = parse(file);
  const literals = (type) => (type ? (ts.isLiteralTypeNode(type) && ts.isStringLiteral(type.literal) ? [type.literal.text] : ts.isUnionTypeNode(type) ? type.types.flatMap(literals) : []) : []);
  const visit = (n) => {
    if (ts.isPropertySignature(n) && n.name && ts.isIdentifier(n.name)) {
      const owner = (() => {
        for (let up = n.parent; up; up = up.parent) if ((ts.isTypeAliasDeclaration(up) || ts.isInterfaceDeclaration(up)) && up.name) return up.name.text;
        return "";
      })();
      if (!["RouteState", "HomeRoute", "NotificationsRoute", "ChangesRoute", "SettingsRoute"].includes(owner)) return ts.forEachChild(n, visit);
      if (n.name.text === "kind") for (const value of literals(n.type)) routes.kinds.push({ value, source: where(n) });
      if (n.name.text === "page") for (const value of literals(n.type)) routes.pages.push({ value, source: where(n) });
    }
    if (ts.isTypeAliasDeclaration(n) && ["ModelTab", "WorkspaceTab", "ConsumerApiTab"].includes(n.name.text)) {
      for (const value of literals(n.type)) routes.tabs.push({ owner: n.name.text, value, source: where(n) });
    }
    ts.forEachChild(n, visit);
  };
  visit(source);
  const navigation = parse(join(SRC, "features", "settings", "navigation.ts"));
  const walkNav = (n) => {
    if (ts.isObjectLiteralExpression(n)) {
      const page = prop(n, "page");
      const label = prop(n, "label");
      if (page && label && ts.isStringLiteral(page.initializer) && ts.isStringLiteral(label.initializer)) {
        routes.navigation.push({ page: page.initializer.text, label: label.initializer.text, source: where(n) });
      }
    }
    ts.forEachChild(n, walkNav);
  };
  walkNav(navigation);
}

// --- the model editor's operations ---------------------------------------------------------------
const operations = [];
const evidence = {};
const EDITOR = join(SRC, "features", "model-editor");
for (const file of files.filter((f) => f.startsWith(EDITOR))) {
  const source = parse(file);
  const names = new Set();
  const strings = new Set();
  const visit = (n) => {
    if (ts.isPropertyAssignment(n) || ts.isShorthandPropertyAssignment(n) || ts.isPropertySignature(n)) {
      const name = n.name && (ts.isIdentifier(n.name) || ts.isStringLiteral(n.name)) ? n.name.text : null;
      if (name) names.add(name);
    }
    if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) strings.add(n.text);
    if (ts.isTemplateExpression(n)) strings.add(n.head.text);
    if (ts.isTemplateMiddle(n) || ts.isTemplateTail(n)) strings.add(n.text);
    // An operation spec: an object with `id`, `on` and `build`.
    if (ts.isObjectLiteralExpression(n) && prop(n, "id") && prop(n, "on") && prop(n, "build") && ts.isStringLiteral(prop(n, "id").initializer)) {
      const id = prop(n, "id").initializer.text;
      const fields = [];
      const fieldsProp = prop(n, "fields");
      if (fieldsProp) {
        const seek = (m) => {
          if (ts.isObjectLiteralExpression(m)) {
            const name = prop(m, "name");
            const label = prop(m, "label");
            if (name && ts.isStringLiteral(name.initializer)) {
              fields.push({ name: name.initializer.text, label: label ? texts(label.initializer)[0] ?? null : null, type: prop(m, "type") && ts.isStringLiteral(prop(m, "type").initializer) ? prop(m, "type").initializer.text : null });
            }
          }
          ts.forEachChild(m, seek);
        };
        seek(fieldsProp.initializer);
      }
      const build = prop(n, "build");
      const buildKinds = new Set();
      const buildKeys = new Set();
      const seekBuild = (m) => {
        if (ts.isPropertyAssignment(m)) {
          const name = propName(m);
          if (name === "kind" && ts.isStringLiteral(m.initializer)) buildKinds.add(m.initializer.text);
          else if (name) buildKeys.add(name);
        }
        if (ts.isShorthandPropertyAssignment(m)) buildKeys.add(m.name.text);
        ts.forEachChild(m, seekBuild);
      };
      seekBuild(build.initializer);
      operations.push({
        id,
        on: ts.isStringLiteral(prop(n, "on").initializer) ? prop(n, "on").initializer.text : null,
        labels: clean(texts(prop(n, "label")?.initializer)),
        titles: clean(texts(prop(n, "title")?.initializer)),
        confirms: clean(texts(prop(n, "confirm")?.initializer)),
        draftOnly: Boolean(prop(n, "draftOnly")),
        fields,
        buildKinds: [...buildKinds],
        buildKeys: [...buildKeys],
        source: where(n),
      });
    }
    ts.forEachChild(n, visit);
  };
  visit(source);
  evidence[rel(file)] = { names: [...names].sort(), strings: [...strings].sort() };
}

// --- action menus and confirmation dialogs -------------------------------------------------------
const menus = [];
const confirms = [];
for (const file of files) {
  if (file.endsWith("ActionMenu.tsx")) continue;
  const source = parse(file);
  const visit = (n) => {
    if (ts.isObjectLiteralExpression(n) && prop(n, "label") && prop(n, "onAction")) {
      const id = prop(n, "id");
      menus.push({
        id: id && ts.isStringLiteral(id.initializer) ? id.initializer.text : null,
        labels: clean(texts(prop(n, "label").initializer)),
        description: clean(texts(prop(n, "description")?.initializer)),
        source: where(n),
      });
    }
    if ((ts.isJsxOpeningElement(n) || ts.isJsxSelfClosingElement(n)) && n.tagName.getText() === "ConfirmDialog") {
      const get = (name) => {
        const attribute = n.attributes.properties.find((a) => ts.isJsxAttribute(a) && a.name.text === name);
        return attribute?.initializer ? clean(texts(attribute.initializer)) : [];
      };
      confirms.push({ titles: get("title"), confirmLabels: get("confirmLabel"), dismissLabels: get("dismissLabel"), source: where(n) });
    }
    ts.forEachChild(n, visit);
  };
  visit(source);
}

process.stdout.write(JSON.stringify({ routes, operations, menus, confirms, evidence }, null, 1));
