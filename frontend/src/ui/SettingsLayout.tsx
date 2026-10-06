import type { ReactNode, Ref } from "react";
import { PageHeader } from "@/ui/PageHeader";

/**
 * A settings page (Track U U3, ADR-039 `B-Settings`): the page header with its group or parent
 * page as the eyebrow, then the page's sections, as wide as the application pages.
 */
export function SettingsLayout({
  eyebrow,
  title,
  titleRef,
  description,
  actions,
  children,
}: {
  eyebrow: ReactNode;
  title: ReactNode;
  titleRef?: Ref<HTMLHeadingElement>;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="settings-page">
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
