# C9 source checks

Instructions read in full: guide/AGENTS.md, _waves/C9-HOME.md, COMPLETE-COMMON.md, coverage/examples.md, steer/C6-INTEGRATE.md. No C9 steering or earlier progress file existed at start.

Existing pages read in full. Checked starter and sample model applications and complete consumer declarations using JSON parsing; docs/EXAMPLE_MODEL.md in full; _waves/OUTLINE.md section 7; relevant ownership/consumer rules in BEHAVIOUR-RULES.md; samples/README.md and SOURCES.md in full. One broad source command was truncated; do not count its missing output as read.

Starter declares no translation tree. Both models permit at most one active translation per owner/language. Starter values-changed watches code/name/isActive/validFrom/validTo, rather than every projected field. Sample Systems declares a system-code tree as well as mapping grids and a matrix; existing showcase omitted that hierarchy link.

No live instance checks have been performed. Examples must distinguish composed snapshot bodies from captured HTTP traffic, and identify instance-generated opaque values.
