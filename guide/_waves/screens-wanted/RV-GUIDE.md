# RV-GUIDE screens wanted

These files are referenced by pages but are not yet captured. Use the guide reference world only.
The reference model currently has no carried relationship attributes or relationships-table view.
To show those states, prepare a clearly documented illustrative extension in the reference instance;
this writing wave has not changed the model or data. Do not use development-model screenshots.

| File under public/screens | Pages | Screen, state and required content |
| --- | --- | --- |
| `record-relationship-attribute-columns.png` | `use/relationships.md` | A record's Relationships panel with related-record fields followed by two carried attributes. Open Display so the “Attributes of the relationship” group and its selected columns are visible. |
| `matrix-cell-relationship-table-editor.png` | `use/relation-matrices.md`, `guide/use/fill-in-a-relation-matrix.md` | A populated matrix cell dialog, preferably with several linked records. Show record fields, the tinted “Attributes of the relationship” column group, a Yes or no checkbox, another carried value's editor open over its cell, Filter, Open and Unlink. Choose a view where these actions are permitted. |
| `relationships-table-rows.png` | `use/relationship-tables.md` | Relationships table in rows layout. Both endpoint fields, relationship values, a group heading with its count, search/filter/sort/Display and tickboxes must be visible. |
| `relationships-grid-two-headers.png` | `use/relationship-tables.md` | Relationships table in grid layout. Show both header rows, at least two column groups with “n of m linked”, carried values including a checkbox, one hatched Not linked group with + Link, row toolbar, column-record menu and Display. |
| `relationships-grid-change-preview.png` | `guide/use/change-relationship-values-in-bulk.md` | Change relationship values dialog with selected-row context, Attribute of the relationship, At … scope, Set to/Clear and a valid typed value. Preview must show Would change, Already … and Not linked counts, the Also link them checkbox, total writes and Apply. Prefer nonzero counts in all three categories. |
| `model-add-relationships-table-layout.png` | `guide/model/add-a-relationships-table.md` | Add a view dialog with the relationships-table kind, selected directed pair, both endpoint column choices, relationship attributes, Layout choices, Head the rows by and Name. Include the grid option in the open Layout menu. |
| `model-consumer-relationship-field-picker.png` | `model/consumer-apis.md`, `guide/model/define-a-consumer-api.md` | Consumer editor Add related or Fields… picker with “Attributes of the relationship”, a text attribute and a Yes or no attribute, public output names and the selected Via relation. Use the illustrative stops extension, not a main object field picker. |

Existing matrix screenshots and their captions are preserved as required. In particular,
`matrix-cell-editor.png` shows the earlier form presentation. Capture the new table above before
reviewing the matrix task as a complete visual walkthrough. No appearance has been verified by this wave.
