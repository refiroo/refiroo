import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Tab, TabList, TabPanel, Tabs as AriaTabs } from "react-aria-components";
import { holdTallest, restoreTabBar } from "@/lib/keepTabBarInPlace";

export type TabDefinition = { id: string; label: string; content: ReactNode; disabled?: boolean };

/**
 * Tabs: the tab list, then the selected panel. A `header` goes between them, for a page whose tabs
 * sit above its title (a webhook's Configuration and Deliveries, U5a).
 *
 * `keepVisited` is for tabs whose panels read their own data: a panel mounts when first chosen and
 * then stays mounted, hidden, so choosing it again shows it as it was without reading again, and
 * the page is scrolled so the tab list stays where it was when the panels differ in height.
 */
export function Tabs({
  label,
  tabs,
  selected,
  onChange,
  header,
  keepVisited = false,
}: {
  label: string;
  tabs: readonly TabDefinition[];
  selected?: string;
  onChange?: (id: string) => void;
  header?: ReactNode;
  keepVisited?: boolean;
}) {
  const [visited, setVisited] = useState<ReadonlySet<string>>(() => new Set(selected ? [selected] : []));
  if (keepVisited && selected && !visited.has(selected)) setVisited(new Set([...visited, selected]));
  const listRef = useRef<HTMLDivElement>(null);
  const barBefore = useRef<number | undefined>(undefined);
  useLayoutEffect(() => {
    if (barBefore.current !== undefined && listRef.current) restoreTabBar(listRef.current, barBefore.current);
    barBefore.current = undefined;
  }, [selected]);
  // With `keepVisited` the area never gets shorter than it has been, so a short panel does not
  // shorten the page and send the scroll position to the top.
  const panelsRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!keepVisited || !panelsRef.current) return;
    return holdTallest(panelsRef.current);
  }, [keepVisited]);
  const panels = tabs.map((tab) =>
    keepVisited ? (
      (visited.has(tab.id) || tab.id === selected) && (
        <TabPanel key={tab.id} id={tab.id} shouldForceMount hidden={tab.id !== selected}>
          {tab.content}
        </TabPanel>
      )
    ) : (
      <TabPanel key={tab.id} id={tab.id}>
        {tab.content}
      </TabPanel>
    ),
  );
  return (
    <AriaTabs
      selectedKey={selected}
      onSelectionChange={(key) => {
        if (keepVisited) barBefore.current = listRef.current?.getBoundingClientRect().top;
        onChange?.(String(key));
      }}
    >
      <TabList ref={listRef} aria-label={label} className="tab-list" items={tabs}>
        {(tab) => (
          <Tab id={tab.id} isDisabled={tab.disabled}>
            {tab.label}
          </Tab>
        )}
      </TabList>
      {header}
      {keepVisited ? <div ref={panelsRef}>{panels}</div> : panels}
    </AriaTabs>
  );
}
