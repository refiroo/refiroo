/** The application a type's preview, record page and table views belong to (0.13 DF5). */
interface ApplicationOfType {
  key: string;
  objectTypeKeys: string[];
  details: { objectTypeKey: string }[];
  views: { type: string; objectTypeKey?: string }[];
}

/**
 * The application a type is shown in: the one named, when it holds the type; otherwise the one that owns the
 * workspace's records of the type (a record is shown in its own application's page); otherwise the first with
 * a detail page or a table view for the type, else the first that lists it. The one place this is decided,
 * so a type in several applications opens in the one the reader came from.
 */
export function applicationForType<A extends ApplicationOfType>(
  applications: readonly A[],
  typeKey: string,
  applicationKey?: string,
  recordsApplicationKey?: string,
): A | undefined {
  const holding = applications.filter((item) => item.objectTypeKeys.includes(typeKey));
  const named = applicationKey ? holding.find((item) => item.key === applicationKey) : undefined;
  if (named) return named;
  const owner = recordsApplicationKey ? holding.find((item) => item.key === recordsApplicationKey) : undefined;
  if (owner) return owner;
  const designed = holding.find(
    (item) =>
      item.details.some((detail) => detail.objectTypeKey === typeKey) ||
      item.views.some((view) => view.type === "table" && view.objectTypeKey === typeKey),
  );
  return designed ?? holding[0];
}

/** The applications that list the type: the ones a reader can choose between. */
export function applicationsHolding<A extends ApplicationOfType>(applications: readonly A[], typeKey: string): A[] {
  return applications.filter((item) => item.objectTypeKeys.includes(typeKey));
}
