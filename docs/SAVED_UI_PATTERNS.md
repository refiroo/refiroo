# Saved UI patterns

Solutions built and then taken out of a screen, kept here because the user wants them at hand for a
later surface (2026-10-12). Nothing here is in the product. Each entry says where it came from, how
it behaved, and the code as it stood, so it can be brought back as a shared component rather than
copied (U-D14: extract once into `ui/`, then use it).

## A folding side pane

**From:** 0.10 A4b, the model editor's first preview (2026-10-12), before the user moved the preview
into the centre and the layout editor to the whole editor. **The user's words:** "that sidebar … to
collapse and expand the preview … looks cool … it might come handy later."

**How it behaved:**

- A third column at the right of a pane grid (`model pane | centre | side pane`), its width a CSS
  variable on the grid (`--editor-preview`), resized by dragging its left edge or with the arrow keys
  through `ui/ResizeHandle` with `direction={-1}` (the handle counts from the right), the width
  remembered per browser (`useLocalNumberPreference`, 320–900px, 440 by default).
- A quiet icon button in the pane's top-right corner (**Fold**, `to-end` glyph) folds it to a 44px
  strip; the grid's variable becomes `44px`, so the centre takes the width at once. The strip shows a
  **Show** button (`to-start` glyph) and the pane's name written vertically. Open or folded is
  remembered per browser (`readLocalPreference` / `writeLocalPreference`).
- On a phone (below 760px) there is no fold: the pane is one of the editor's tabs.

**To bring it back:** extract `ui/SidePane` (the frame, the fold button, the folded strip and the
resize handle) with `name`, `storageKey`, `defaultWidth` and `children`, and give the host grid the
column variable. The pieces below are as they were in `ModelEditor.tsx`, `PreviewPane.tsx` and
`styles/model-editor.css`.

```tsx
// The host (ModelEditor): open or folded, and the width, remembered in this browser.
const PREVIEW_KEY = "rdm:model-editor:preview-open:v1";
const previewWidth = useLocalNumberPreference("rdm:model-editor:preview-width:v1", 440, 320, 900);
const [previewOpen, setPreviewOpen] = useState(() =>
  readLocalPreference(PREVIEW_KEY, true, (value): value is boolean => typeof value === "boolean"),
);
const togglePreview = (open: boolean) => {
  setPreviewOpen(open);
  writeLocalPreference(PREVIEW_KEY, open);
};

<div
  className="model-editor-panes"
  style={
    {
      "--editor-pane": `${paneWidth.value}px`,
      "--editor-preview": previewOpen ? `${previewWidth.value}px` : "44px",
    } as CSSProperties
  }
>
  {pane}
  <ResizeHandle className="editor-resizer" label="Resize the model pane" … />
  {centre}
  {previewOpen ? (
    <>
      <ResizeHandle
        className="editor-resizer preview-resizer"
        label="Resize the preview"
        value={previewWidth.value}
        min={320}
        max={900}
        direction={-1}
        onChange={previewWidth.change}
        onReset={previewWidth.reset}
      />
      {preview /* the pane, given onFold={phone ? undefined : () => togglePreview(false)} */}
    </>
  ) : (
    <div className="model-editor-preview-folded">
      <IconButton icon="to-start" label="Show the preview" tooltip="Preview" onClick={() => togglePreview(true)} />
      <span aria-hidden="true">Preview</span>
    </div>
  )}
</div>

// The pane's frame, with its fold button.
function PreviewFrame({ children, onFold }: { children: ReactNode; onFold?: () => void }) {
  return (
    <aside className="model-editor-preview" aria-label="Preview">
      {onFold && (
        <IconButton className="preview-fold" icon="to-end" label="Fold the preview" tooltip="Fold" quiet onClick={onFold} />
      )}
      {children}
    </aside>
  );
}
```

```css
.model-editor-panes {
  grid-template-columns: var(--editor-pane, 300px) minmax(0, 1fr) var(--editor-preview, 520px);
}
/* The handle counts from the right edge. */
.editor-resizer.preview-resizer {
  left: auto;
  right: calc(var(--editor-preview, 520px) - 5px);
}
.model-editor-preview {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: auto;
  border-left: 1px solid var(--border-subtle);
  background: var(--surface-sunken);
  display: flex;
  flex-direction: column;
}
.preview-fold {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  z-index: 2;
}
/* The pane's head leaves room for the fold button. */
.preview-head {
  padding-right: calc(var(--space-4) + 32px);
}
/* Folded, the pane is a strip the reader opens again. */
.model-editor-preview-folded {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding-top: var(--space-3);
  border-left: 1px solid var(--border-subtle);
  background: var(--surface-sunken);
  color: var(--text-secondary);
  font-size: var(--text-xs);
}
.model-editor-preview-folded > span {
  writing-mode: vertical-rl;
}
@media (max-width: 760px) {
  .editor-resizer {
    display: none;
  }
}
```
