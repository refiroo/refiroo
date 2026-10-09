import { Button, Tag, TagGroup, TagList } from "react-aria-components";
import { Icon } from "@/ui/Icon";

export interface Chip {
  id: string;
  label: string;
}

/**
 * Chosen values as removable chips (U5a): a grid the keyboard moves through with the arrows, where
 * Delete or a chip's button removes it. `TokenField`, `MultiSelect` and `RecordListField` show their
 * choices with it.
 */
export function ChipList({
  label,
  chips,
  onRemove,
  emptyLabel,
  describedBy,
}: {
  label: string;
  chips: readonly Chip[];
  onRemove: (ids: Set<string>) => void;
  /** Shown in place of chips while nothing is chosen. */
  emptyLabel?: string;
  describedBy?: string;
}) {
  return (
    <TagGroup
      aria-label={label}
      aria-describedby={describedBy}
      onRemove={(keys) => onRemove(new Set([...keys].map(String)))}
    >
      <TagList
        className="chip-list"
        items={chips}
        renderEmptyState={emptyLabel ? () => <span className="chip-empty">{emptyLabel}</span> : undefined}
      >
        {(chip) => (
          <Tag id={chip.id} textValue={chip.label} className="chip">
            <span className="chip-label">{chip.label}</span>
            <Button slot="remove" className="chip-remove" aria-label={`Remove ${chip.label}`}>
              <Icon name="close" size={12} />
            </Button>
          </Tag>
        )}
      </TagList>
    </TagGroup>
  );
}
