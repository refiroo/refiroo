import type { ReactNode } from "react";
import { Tab, TabList, TabPanel, Tabs as AriaTabs } from "react-aria-components";

export type TabDefinition = { id: string; label: string; content: ReactNode; disabled?: boolean };

export function Tabs({
  label,
  tabs,
  selected,
  onChange,
}: {
  label: string;
  tabs: readonly TabDefinition[];
  selected?: string;
  onChange?: (id: string) => void;
}) {
  return (
    <AriaTabs selectedKey={selected} onSelectionChange={(key) => onChange?.(String(key))}>
      <TabList aria-label={label} className="tab-list" items={tabs}>
        {(tab) => (
          <Tab id={tab.id} isDisabled={tab.disabled}>
            {tab.label}
          </Tab>
        )}
      </TabList>
      {tabs.map((tab) => (
        <TabPanel key={tab.id} id={tab.id}>
          {tab.content}
        </TabPanel>
      ))}
    </AriaTabs>
  );
}
