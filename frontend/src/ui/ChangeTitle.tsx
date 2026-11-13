import { routePath } from "@/routing/routes";
import type { ChangeEntry, RouteState } from "@/types";
import { changeTarget, changeTitle } from "@/ui/changeText";
import { RouteLink } from "@/ui/RouteLink";

type Navigate = (route: RouteState) => void;

/** An entry's title, a link to what it changed while that can be opened. */
export function ChangeTitle({
  entry,
  application,
  onNavigate,
}: {
  entry: ChangeEntry;
  application: string | undefined;
  onNavigate: Navigate;
}) {
  const title = changeTitle(entry);
  const target = changeTarget(entry, application);
  if (!target) return <>{title}</>;
  return (
    <RouteLink className="changes-link" href={routePath(target)} onNavigate={() => onNavigate(target)}>
      {title}
    </RouteLink>
  );
}
