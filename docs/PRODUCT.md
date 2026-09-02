# Product definition

## Purpose

RDM Engine lets teams define and operate reference-data applications without developing a separate
application for every domain. A JSON model defines the concepts and the interface; the engine supplies
validated storage, APIs, search, history and reusable UI components.

## Product statement

An open-source, model-driven engine for building reference-data applications, mappings and integration
APIs without writing application-specific code.

## Intended users

- Data owners maintaining canonical codes and names
- Integration teams translating values between systems
- Local data stewards maintaining translations and availability
- Developers consuming reliable, scalable reference-data APIs
- Product administrators defining new RDM applications through configuration

## Core capabilities

1. Define applications, object types, reusable attribute types and typed relationships.
2. Organize values into codelists, hierarchies and other model-defined structures.
3. Map canonical values to representations in external systems.
4. Attach language-specific translations to governed values.
5. Generate effective tables, forms, mapping grids, selectors and trees from configuration.
6. Provide integration-grade query, bulk, import/export, webhook and change-feed APIs.
7. Record provenance, versions and changes.

## Boundaries

The product is focused on reference data. It is not intended to become a general data catalogue,
business glossary, lineage scanner or enterprise governance suite. Generic applications are supported
where the same object/attribute/relation/view model is genuinely useful, but RDM integration remains the design
centre.

## Initial success condition

An administrator can define a new application in JSON, restart the engine, and obtain navigation,
tables, forms, validated CRUD APIs and relationships without modifying Python or TypeScript. A model
release is installed as an immutable metadata snapshot so the running behavior is reproducible.
