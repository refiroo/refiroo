import type { ReactNode, Ref } from "react";
import { PageHeader } from "@/ui/PageHeader";

/**
 * A settings page (Track U U3, ADR-039 `B-Settings`): the page header with its group as the
 * eyebrow, then the page's sections, as wide as the application pages. A page under another
 * (a job, an import profile) shows its `trail` of breadcrumbs above the header instead.
 */
export function SettingsLayout({
  eyebrow,
  trail,
  title,
  titleRef,
  description,
  actions,
  children,
}: {
  eyebrow?: ReactNode;
  /** `ui/Breadcrumbs`: the group, the list the page belongs to, the page (0.10 A5c). */
  trail?: ReactNode;
  title: ReactNode;
  titleRef?: Ref<HTMLHeadingElement>;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="settings-page">
      {trail}
      <PageHeader
        variant="detail"
        eyebrow={eyebrow}
        title={title}
        titleRef={titleRef}
        description={description}
        actions={actions}
      />
      {children}
    </div>
  );
}
