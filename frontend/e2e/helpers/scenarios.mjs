// The scenario filter of the accessibility and visual gates (TS1): `--scenario a,b` runs only the scenarios
// whose group (e2e/manifest.mjs) is named, and every scenario a gate visits must have a group, filtered or not.
import { SCENARIOS } from "../manifest.mjs";

/** A scenario's name without its theme: a leading `dark-` (accessibility gate) or a trailing `-light` / `-dark`. */
export function plainName(name) {
  return name.replace(/^dark-/, "").replace(/-(light|dark)$/, "");
}

/** Does `name` match a group's pattern, where `*` stands for any text? */
export function matches(pattern, name) {
  const source = pattern.replace(/[.+?^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*");
  return new RegExp(`^${source}$`).test(plainName(name));
}

/** The group a scenario belongs to, or undefined. */
export function groupOf(name, scenarios = SCENARIOS) {
  return scenarios.find((entry) => entry.names.some((pattern) => matches(pattern, name)));
}

/**
 * The gate's filter. `argv` may hold `--scenario group,group` (group names of the manifest). The returned
 * function says whether a scenario runs, and throws for a scenario no group names, so a new scenario cannot
 * be left out of the mapping.
 */
export function scenarioFilter(argv = process.argv, scenarios = SCENARIOS) {
  const at = argv.indexOf("--scenario");
  const wanted = at < 0 ? undefined : new Set(argv[at + 1].split(",").filter(Boolean));
  if (wanted) {
    const unknown = [...wanted].filter((name) => !scenarios.some((entry) => entry.group === name));
    if (unknown.length) throw new Error(`Unknown scenario group: ${unknown.join(", ")}.`);
  }
  return {
    filtered: Boolean(wanted),
    selected(name) {
      const group = groupOf(name, scenarios);
      if (!group)
        throw new Error(`Scenario ${name} has no group in e2e/manifest.mjs: add it to the group of its screen.`);
      return !wanted || wanted.has(group.group);
    },
  };
}
