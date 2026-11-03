import { defineCollection } from "astro:content";
import { docsLoader, i18nLoader } from "@astrojs/starlight/loaders";
import { docsSchema, i18nSchema } from "@astrojs/starlight/schema";
import { z } from "astro/zod";
import { READERS } from "../tools/schema.mjs";

// The front matter every page carries besides Starlight's own: who the page is for.
export const guideFields = z.object({
  reader: z.enum(READERS).optional(),
});

export const collections = {
  docs: defineCollection({ loader: docsLoader(), schema: docsSchema({ extend: guideFields }) }),
  i18n: defineCollection({ loader: i18nLoader(), schema: i18nSchema() }),
};
