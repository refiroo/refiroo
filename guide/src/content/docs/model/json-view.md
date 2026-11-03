---
title: The JSON view
description: Use the specialist document workbench for definitions beyond the visual editor.
reader: model-admin
---

Most modelling tasks use the visual editor. The **JSON** view is the specialist workbench for
the complete model document, including settings without visual forms. Ask a specialist model
author to maintain those settings if you do not work with model documents. Both views edit the
same draft; neither directly changes the active workspace.

Open **JSON** in the editor header, or **Open as JSON** in its menu. The workbench has **Draft
name**, **JSON model**, **Authoritative validation**, a summary and **Compile and compare**.
You need **Model authoring** to save. See [Edit a draft as JSON](/docs/guide/model/edit-a-draft-as-json/)
for the workbench controls, without needing to learn document syntax here.

![Document workbench with draft name, validation and compile actions](/docs/screens/model-draft-json.png)

## Saving and checking

A syntax error prevents saving the text. Valid syntax does not prove that referenced definitions
exist or that the model is usable. **Authoritative validation** checks those rules and lets you
select a diagnostic to reach the affected text. Saving keeps the draft, including work still
needing model corrections. **Compile and compare** uses the saved version and shows **Canonical
model**, **Ready for review** or **Invalid**, a model hash and the semantic differences.

**Export JSON** downloads the current document. It does not install or activate it. **Install
immutable release…** separately confirms creation of an inactive release; activation still
requires a workspace compatibility check. The visual editor's **Install and activate…** combines
those stages. See [Releases](/docs/model/releases/).

## Other editors and unsupported visual settings

Unsaved text is local to this workbench until **Save draft**. If another author saves first,
**A newer draft version exists** preserves your text. **Copy local JSON** keeps it for review;
**Reload saved version** reads the saved draft without merging. Saved document edits appear
as **JSON edit** in History.

The document covers application descriptions and presentation settings; type display, placement
and effective periods; shared and relationship attributes; validation and uniqueness rules;
full view and panel declarations; consumer contracts; and import-profile instructions where
applicable. Visual controls cover only the options described on their pages. Do not infer that
an absent form means the model cannot declare a feature. Integrators use
[Integrate](/docs/integrate/overview/) for the model contract details rather than browser steps.
