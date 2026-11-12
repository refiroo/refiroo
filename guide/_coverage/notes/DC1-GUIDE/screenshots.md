# Screenshot inspection

Visually inspected these seven existing files. All show a form at the desktop window’s right edge rather than centred. No image, filename, reference or caption was changed. This is a bounded inspection, not an audit of all screenshots.

- `new-record-required-connections.png`: New Name translation, with required parent and Translates choices.
- `stop-edit-record.png`: Chur Wiesental whole-record editing form.
- `relationship-picker-mode.png`: Add Mode connection form for Chur Wiesental.
- `relationship-picker-operator.png`: Replace Operator connection form with relationship attributes.
- `model-field-dialog.png`: New attribute on Stop, with value type and feature choices.
- `use-wb-dialog.png`: New from a workbook model proposal form.
- `workspaces-new-dialog.png`: New workspace from a workbook, before selecting a file.

No difference found between the current dialog code and the changelog’s centred-dialog entry. Desktop placement, scrolling and footer behaviour were checked against Modal.tsx, components.css and interactions.css; the unchanged phone layout was checked in responsive.css. No live browser check was performed.
