
- 2026-11-12T10:58:27+01:00 — `guide/src/content/docs/use/records.md`: Updated one-field saving, keyboard controls, notices and Undo, optional removal, required refusals and retry controls. Confirmed against the shared field and record editor; no steer file exists. Settings notices and immediate Yes/No controls need separate checks because their callers choose the notice.

- 2026-11-12T10:58:59+01:00 — `guide/src/content/docs/guide/use/correct-a-record.md`: Corrected the single-value steps, removal, first-value Undo and conflict retry; kept the several-field form instructions. No steer file exists. Existing stop-edit-field.png and save-conflict.png need retakes for the changed controls.

- 2026-11-12T10:59:57+01:00 — `guide/src/content/docs/use/relationship-tables.md`: Unified row and grid field-saving instructions, removal and refusal recovery; added relationship-value Undo. No steer file exists. Uncertainties: The grid’s direct Yes/No control bypasses the input save notice and Undo; reported separately.

- 2026-11-12T10:59:57+01:00 — `guide/src/content/docs/use/relation-matrices.md`: Applied the same saving and retry rules to record and relationship inputs in the cell table, with removal and Undo. No steer file exists. Uncertainties: The direct Yes/No controls retain different notices; existing matrix editor screenshots need retakes.

- 2026-11-12T10:59:57+01:00 — `guide/src/content/docs/guide/use/fill-in-a-relation-matrix.md`: Corrected the cell-editing steps and the old editor caption while preserving its image reference. No steer file exists. Uncertainties: Both existing cell-editor images need retakes for their earlier controls.

- 2026-11-12T10:59:57+01:00 — `guide/src/content/docs/use/appearance-and-devices.md`: Updated keyboard saving, multiline input, immediate choices and Escape behavior. No steer file exists. Uncertainties: None.

- 2026-11-12T10:59:57+01:00 — `guide/src/content/docs/about/accessibility.md`: Replaced the general editor statement with the current single-field keyboard behavior and retained the form distinction. No steer file exists. Uncertainties: None.

- 2026-11-12T11:01:01+01:00 — `guide/src/content/docs/use/account.md`: Corrected passkey rename saving and refusal controls; retained Undo and removal instructions. No steer file exists. Uncertainties: None.

- 2026-11-12T11:01:01+01:00 — `guide/src/content/docs/administer/people-and-groups.md`: Corrected group name and description saving and retry; retained group deletion behavior. No steer file exists. Uncertainties: None.

- 2026-11-12T11:01:01+01:00 — `guide/src/content/docs/guide/administer/manage-a-group.md`: Corrected the group rename task and refusal recovery; membership and grant steps stay unchanged. No steer file exists. Uncertainties: None.

- 2026-11-12T11:01:01+01:00 — `guide/src/content/docs/administer/clients.md`: Corrected client renaming and refusal recovery while preserving client creation instructions. No steer file exists. Uncertainties: None.

- 2026-11-12T11:01:01+01:00 — `guide/src/content/docs/model/managing-workspaces.md`: Corrected workspace renaming and refusal recovery without altering creation or model activation. No steer file exists. Uncertainties: None.

- 2026-11-12T11:01:01+01:00 — `guide/src/content/docs/model/the-model-editor.md`: Updated model cell and heading saving, refusal controls and immediate opening-view selection; kept operation popover Save. No steer file exists. Uncertainties: None.

- 2026-11-12T11:01:01+01:00 — `guide/src/content/docs/guide/model/add-a-record-type-and-fields.md`: Corrected editing setting cells and refusals; kept the add-field and effective-period forms. No steer file exists. Uncertainties: model-type-required-edit.png shows the former Save and Cancel controls and needs a retake.

- 2026-11-12T11:01:01+01:00 — `guide/src/content/docs/guide/model/reuse-and-change-attributes.md`: Corrected immediate Required, Read-only and Hidden choices and Help text saving; retained the bounds popover Save. No steer file exists. Uncertainties: None.

- 2026-11-12T11:01:01+01:00 — `guide/src/content/docs/guide/model/arrange-applications-and-views.md`: Corrected immediate Default view selection; kept view forms and menus. No steer file exists. Uncertainties: None.

- 2026-11-12T11:01:01+01:00 — `guide/src/content/docs/model/applications-and-views.md`: Corrected Opens on and Default view selection saving; retained other view configuration forms. No steer file exists. Uncertainties: None.

- 2026-11-12T11:01:01+01:00 — `guide/src/content/docs/guide/model/group-collections-in-navigation.md`: Corrected immediate Opens on selection and removed obsolete Save/Cancel instructions. No steer file exists. Uncertainties: None.

- 2026-11-12T11:01:01+01:00 — `guide/src/content/docs/model/consumer-apis.md`: Corrected single-date editing, emptying and refused-save recovery for earlier contract versions. No steer file exists. Uncertainties: None.

- 2026-11-12T11:01:01+01:00 — `guide/src/content/docs/guide/model/stop-serving-an-earlier-contract-version.md`: Corrected announcing and withdrawing a sunset date and recovering after an invalid date; retained stop-serving confirmation. No steer file exists. Uncertainties: None.

- 2026-11-12T11:01:48+01:00 — `guide/src/content/docs/guide/model/define-a-consumer-api.md`: Corrected Default cell saving and refusal recovery; retained the multi-field consumer forms. No steer file exists. Uncertainties: None.

- 2026-11-12T11:01:48+01:00 — `guide/src/content/docs/use/records.md`: Clarified that input notices differ from the unchanged direct Yes/No controls, and described empty text inputs precisely. No steer file exists. Uncertainties: The structured-value input still parses literal null; the changelog’s blanket statement about Cleared needs clarification.

- 2026-11-12T11:02:32+01:00 — `guide/src/content/docs/guide/use/fill-in-a-relation-matrix.md`: Checked the actual matrix image and corrected its caption: it shows a cell table with Close, not a Cancel form. No steer file exists. Uncertainties: The two matrix screenshots already have button-free inputs or no open input, and their Enter/Esc hint still matches the code; no UX2 retake needed for them.

- 2026-11-12T11:03:31+01:00 — `guide/src/content/docs/guide/model/rename-or-re-key-an-element.md`: Separated direct heading renaming from the Rename form so only the latter instructs Save. No steer file exists. Uncertainties: None.

- 2026-11-12T11:05:18+01:00 — Final validation and report (`guide/_coverage/notes/UX2-GUIDE/report.md`): 22 pages updated; final build passed (257 pages), writing/brand/sidebar and inventory freshness passed, and the separate link check passed (76,039 links/sources). `npm run verify` stops at 11 workbook-canvas coverage gaps; the starting-text comparison has the identical gaps. Three referenced screenshots need retakes. Code exceptions and unverified structured-null persistence are recorded in the report. No steer file exists.
