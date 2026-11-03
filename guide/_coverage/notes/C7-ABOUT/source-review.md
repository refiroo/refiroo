# C7-ABOUT source review

Read guide/AGENTS.md first, then the wave and COMPLETE-COMMON. Read the About sidebar, OUTLINE section 1 and About coverage in full. Consulted BEHAVIOUR-RULES sections A–L and NOT-YET-COVERED section C for reader-visible limits. No steering file existed at the start of any authored page.

Sources consulted: PRODUCT, GLOSSARY, PRODUCT_GUIDE; CURRENT_FUNCTIONALITY F01/F02/F05–F19/F21–F27 and selected integration sections; USER_JOURNEYS J02/J05/J08/J39–J41; COMPATIBILITY, OPEN_SOURCE, CONTRIBUTING, SECURITY; targeted ARCHITECTURE overview/model/workspace/jobs/topology and OPERATIONS authentication/jobs/webhook/deployment sections; guide samples README/SOURCES. Some broad multi-file tool output was truncated; targeted later reads supplied the relevant passages. No full architecture/product decision review was performed or needed.

Code checks: AboutPage and SettingsMenu for licence/source labels, AppearancePage/ShellFrame/ResizeHandle/Modal for display and keyboard facilities; authorization catalogue and current behaviour inventory for role scopes and approvals; identity authentication/sign-in for immediate revocation and slowing; values/attributes/rules and change-set publish for type/range/required/unique and merge checks; guide_site, astro config and reference viewer for local assets and optional CDN script. Read existing accessibility gate source without running it. Existing list-phone.png visually inspected.

Source differences resolved:
- PRODUCT_GUIDE still says workspace-specific models and named attribution are future work. CURRENT_FUNCTIONALITY and registry/authentication code describe the current behavior, used in the pages.
- OPERATIONS topology's opening one-process phrasing is followed by explicit multi-instance support. The guide distinguishes standard single-process container from supported shared-database deployment.
- CONSUMER_API carries superseded statements about grants to people/groups and authentication of contract documents. Current F27 and behaviour F5 restrict consumer grants to clients; current design notes identify public contract-document exceptions. No endpoint details are repeated on About pages.
- Nine general predefined roles are listed. The additional Agent role is in the deferred agent feature and is not documented here.
- C0040 combines current security and deferred AI. Its existing deferred marker is preserved; completion notes map the current security portion to the finished page.

Known limits: this wave validates documentation, not application behavior. No new screen-reader, browser acceptance, security assessment or compatibility experiment was run. No product defect established from this source review. The glossary link vocabulary is explained without exposing model JSON or API paths to evaluator readers.

Visual review: Chrome could not launch under the session sandbox (SIGABRT), so no browser page review was completed. Rendered the SVG with the existing sharp dependency into this notes folder and inspected it: labels fit, arrows and snapshot relationship are legible. This is diagram review, not browser acceptance. Existing phone screenshot was inspected directly. Final check results and outside-wave link failures are in validation.md.
