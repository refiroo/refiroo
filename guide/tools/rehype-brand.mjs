// Marks every standalone "refiroo" in rendered prose as the brand name, so page writers keep writing
// plain text. Tokens such as refiroo-guide-ref, refiroo.example, paths and URLs are left alone, as is
// anything inside code, pre, kbd, script, style or title.
//
// Astro 7 renders Markdown with Satteri, whose HTML-tree plugins (the counterpart of rehype plugins)
// ship with Astro; no extra package is needed. The tree is the same hast shape.
const SKIP = new Set(["code", "pre", "kbd", "script", "style", "title"]);
const NAME = /(?<![\w./@:-])refiroo(?![\w/@-]|\.[\w])/g;

const classes = (node) => {
  const value = node.properties?.className;
  return Array.isArray(value) ? value : String(value ?? "").split(/\s+/);
};

const skipped = (node, ctx) => {
  for (let up = ctx.parent(node); up; up = ctx.parent(up)) {
    if (up.type !== "element") continue;
    if (SKIP.has(up.tagName) || classes(up).includes("brand-name")) return true;
  }
  return false;
};

export const brandPlugin = {
  name: "refiroo-brand-name",
  text(node, ctx) {
    const text = node.value;
    const parts = [];
    let last = 0;
    for (const match of text.matchAll(NAME)) {
      if (match.index > last)
        parts.push({ type: "text", value: text.slice(last, match.index) });
      parts.push({
        type: "element",
        tagName: "span",
        properties: { className: ["brand-name"] },
        children: [{ type: "text", value: "refiroo" }],
      });
      last = match.index + match[0].length;
    }
    if (!parts.length || skipped(node, ctx)) return;
    if (last < text.length)
      parts.push({ type: "text", value: text.slice(last) });
    ctx.replaceNode(node, parts);
  },
};

export default brandPlugin;
