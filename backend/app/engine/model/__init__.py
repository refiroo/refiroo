"""Model lifecycle: parsing, validation, canonical compilation, diffing, releases and drafts.

These modules own the versioned JSON model as a first-class artefact. The rest of the engine
(records, change sets, reads, operations) sits beside this package and consumes a resolved model
snapshot.
"""
