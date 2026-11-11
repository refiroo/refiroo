// Rewrites the guide's own absolute links and images in the built pages (`/docs/...`, `/docs/screens/x.png`,
// written by hand in page bodies, raw HTML included) to the base the build is served under, so a version built for
// /docs/0.13 links to its own pages and screens and not to the latest. Pages always write `/docs/...`; Astro's own
// links already carry the base and are left alone. With the default base nothing changes.
import { readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const OWN = /(\s(?:href|src)=)(["'])\/docs(?=[/?#"'])/g;

export function rewriteBase(html, base) {
  const target = base.replace(/\/$/, "");
  return html.replace(OWN, (match, attribute, quote, offset) => {
    // Already under the base (Astro's own links): the text after /docs is the base's own continuation.
    const rest = html.slice(offset + match.length);
    const own = target.slice("/docs".length);
    return own && rest.startsWith(own) && /^[/?#"']/.test(rest.slice(own.length)) ? match : `${attribute}${quote}${target}`;
  });
}

export default function rewriteBaseLinks(base) {
  return {
    name: "refiroo-rewrite-base",
    hooks: {
      "astro:build:done": ({ dir }) => {
        if (base.replace(/\/$/, "") === "/docs") return;
        const walk = (folder) => {
          for (const name of readdirSync(folder)) {
            const path = join(folder, name);
            if (statSync(path).isDirectory()) walk(path);
            else if (name.endsWith(".html")) {
              const html = readFileSync(path, "utf8");
              const changed = rewriteBase(html, base);
              if (changed !== html) writeFileSync(path, changed);
            }
          }
        };
        walk(fileURLToPath(dir));
      },
    },
  };
}
