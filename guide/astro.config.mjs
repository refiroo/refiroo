// The refiroo guide: a static site the engine serves at /docs and a public site is built from.
// Nothing here reaches the internet at view time: Starlight's own styles use the system fonts, the
// search is Pagefind's static index, and no analytics or hosted script is configured.
import { existsSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import about from "./sidebar/about.mjs";
import journeys from "./sidebar/journeys.mjs";
import use from "./sidebar/use.mjs";
import model from "./sidebar/model.mjs";
import administer from "./sidebar/administer.mjs";
import run from "./sidebar/run.mjs";
import integrate from "./sidebar/integrate.mjs";
import examples from "./sidebar/examples.mjs";
import { satteri } from "@astrojs/markdown-satteri";
import rehypeBrand from "./tools/rehype-brand.mjs";

// The sections, in reading order, named by the reader's goal. A section appears in the sidebar once it
// holds a page; its directory under src/content/docs is the key.
const SECTIONS = [
  ["about", "About refiroo"],
  ["journeys", "User journeys"],
  ["use", "Use refiroo"],
  ["examples", "Example applications"],
  ["model", "Model your data"],
  ["administer", "Administer access"],
  ["run", "Run refiroo"],
  ["integrate", "Integrate"],
];

const docs = fileURLToPath(new URL("./src/content/docs/", import.meta.url));
const hasPages = (directory) => {
  const path = docs + directory;
  return (
    existsSync(path) &&
    readdirSync(path, { recursive: true }).some((file) =>
      /\.mdx?$/.test(String(file)),
    )
  );
};
// A section may list its pages by capability: the documentation page first, then the guides for its
// tasks (guides live under guide/<section>/). A slug whose page does not exist yet is skipped, so a
// group can be declared ahead of its pages. A page a section does not list here is not shown; sections
// without a list are generated. The outline of every page is guide/_waves/OUTLINE.md.
const GROUPS = {
  about,
  journeys,
  use,
  model,
  administer,
  run,
  integrate,
  examples,
};
const exists = (slug) =>
  existsSync(`${docs}${slug}.md`) || existsSync(`${docs}${slug}.mdx`);
// Guides sit under the documentation page before them: indented in the sidebar (see guide.css).
const entry = (item) => {
  const [slug, label] = Array.isArray(item) ? item : [item];
  const link = label ? { slug, label } : { slug };
  return slug.startsWith("guide/")
    ? { ...link, attrs: { class: "guide-entry" } }
    : link;
};
const listed = (items) =>
  items
    .filter((item) => exists(Array.isArray(item) ? item[0] : item))
    .map(entry);

const sidebar = SECTIONS.filter(([directory]) => hasPages(directory)).map(
  ([directory, label]) => ({
    label,
    items: GROUPS[directory]
      ? GROUPS[directory].flatMap(([group, items]) => {
          const pages = listed(items);
          if (!pages.length) return [];
          return group ? [{ label: group, items: pages }] : pages;
        })
      : [{ autogenerate: { directory } }],
  }),
);

// GUIDE_OUT builds elsewhere than dist/ (the engine serves dist/), so parallel Codex runs do not clash.
const out = process.env.GUIDE_OUT;

export default defineConfig({
  ...(out ? { outDir: out, cacheDir: `${out}-cache` } : {}),
  // The engine serves the built files at /docs (the API reference is /docs/api, outside this site).
  base: "/docs",
  trailingSlash: "always",
  build: { format: "directory" },
  // Every standalone "refiroo" in prose is marked as the brand name (see tools/rehype-brand.mjs).
  markdown: { processor: satteri({ hastPlugins: [rehypeBrand] }) },
  integrations: [
    // Starlight adds the sitemap unless an integration of this name is present; it has no use until the
    // public host is decided (DOC12), so it is disabled here with a stand-in of the same name.
    { name: "@astrojs/sitemap", hooks: {} },
    starlight({
      title: "refiroo documentation",
      description: "How to use, model, integrate, run and secure refiroo.",
      favicon: "/favicon.png",
      logo: { src: "./public/refiroo-mascot.png", alt: "" },
      // The header is the one of the application and the API reference (HD): its stylesheet is shared, in
      // frontend/public/brand/ (the engine serves it at /brand/). Header, ThemeProvider and ThemeSelect
      // are overridden for the logo, the Documentation | API reference switch and the application's theme
      // choice (rdm:theme:v1). The logo goes to the application's home ("/"); a public site build, which has
      // no application, sets PUBLIC_GUIDE_SITE=1 (for example `PUBLIC_GUIDE_SITE=1 npm run build`) and the
      // logo goes to the guide's home instead.
      customCss: [
        "../frontend/public/brand/refiroo-header.css",
        "./src/styles/guide.css",
      ],
      components: {
        Header: "./src/components/Header.astro",
        ThemeProvider: "./src/components/ThemeProvider.astro",
        ThemeSelect: "./src/components/ThemeSelect.astro",
      },
      // Pagefind's search box is labelled by its title alone, which assistive technology may skip
      // (axe: label-title-only). Give it a name of its own as soon as the search dialog builds it.
      head: [
        {
          tag: "script",
          content:
            "new MutationObserver(function(){document.querySelectorAll('.pagefind-ui__search-input:not([aria-label])').forEach(function(i){i.setAttribute('aria-label','Search the documentation')})}).observe(document.documentElement,{childList:true,subtree:true});",
        },
      ],
      sidebar,
      // The engine's own repository link and edit links are not offered: the guide is read from the
      // instance it describes.
      pagination: true,
      lastUpdated: false,
    }),
  ],
});
