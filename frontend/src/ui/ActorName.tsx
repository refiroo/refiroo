import { routePath } from "@/routing/routes";
import type { Actor, Principal, RouteState } from "@/types";
import { RouteLink } from "@/ui/RouteLink";

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
 * release's activations and a person's recent activity. With `onOpenChanges`, a person's or client's
 * name links to their changes across workspaces (0.12 Z6, D345); the engine and "Before sign-in"
 * stay text. */
export function ActorName({
  actor,
  onOpenChanges,
}: {
  actor: Actor | null;
  onOpenChanges?: (route: RouteState) => void;
}) {
  if (!actor || actor.kind === "engine" || !onOpenChanges)
    return <span className="actor-name">{actorText(actor)}</span>;
  const route: RouteState = { kind: "changes", actorId: actor.id, actorName: actor.name };
  return (
    <span className="actor-name">
      by{" "}
      <RouteLink
        href={routePath(route)}
        onNavigate={() => onOpenChanges(route)}
        aria-label={`${principalName(actor)}: their changes`}
      >
        {actor.name}
      </RouteLink>
      {actor.kind === "client" && " (client)"}
    </span>
  );
}
