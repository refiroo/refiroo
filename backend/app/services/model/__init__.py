"""Model lifecycle: parsing, validation, canonical compilation, diffing, releases and drafts.

These modules own the versioned JSON model as a first-class artefact. Runtime domain services
(objects, relations, attributes) sit beside this package and consume a resolved model snapshot.
"""
