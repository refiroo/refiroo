# Sunset action discrepancy

The wave says to replace inline editing with the Set sunset day… row action and Sunset of version N dialog.
Code wins under guide/AGENTS.md rule 4. Current code contradicts that assumption:

- frontend/src/features/model-editor/operations.ts defines consumer-version-sunset with the requested dialog and hint.
- frontend/src/features/model-editor/ConsumerApis.tsx, Earlier versions EditorTable (around 345–390), supplies an editable Sunset day column and a Stop serving OperationButton, but no menu prop or sunset OperationButton.
- frontend/src/features/model-editor/EditorTable.tsx only renders an actions menu when passed a menu prop.
- frontend/src/features/model-editor/EditableCell.tsx shows Not saved on refusal and retains the input.
- backend/app/engine/model/authoring/consumer.py set_consumer_api_sunset restores the saved value after refusal.

The two pages therefore retain the reachable inline flow and clarify format, empty value, refusal and announcement semantics. No user-facing steps for the unreachable dialog were invented. This screen inventory entry remains unverified/uncovered; the registry alone is not evidence of a usable screen. Report this as a product wiring issue, without editing application code.
