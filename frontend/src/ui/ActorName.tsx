import type { Actor, Principal } from "@/types";

/** A person by their name, a client by its name and "(client)" (0.12 Z4, D320). */
export function principalName(principal: Principal) {
  return principal.kind === "client" ? `${principal.name} (client)` : principal.name;
}

/** Who made a change, as it reads after its time: "by Ana Varga", "by Catalogue sync (client)",
 * "by the engine", or "Before sign-in" for a change recorded before 0.12 (D320). */
export function actorText(actor: Actor | null) {
  if (actor === null) return "Before sign-in";
  return actor.kind === "engine" ? "by the engine" : `by ${principalName(actor)}`;
}

/** The one place a change's actor is rendered: a record's history, the editors' histories, a
 * release's activations and a person's recent activity. */
export function ActorName({ actor }: { actor: Actor | null }) {
  return <span className="actor-name">{actorText(actor)}</span>;
}
