# Security policy

## Reporting a vulnerability

Please report a vulnerability **privately**, not in a public issue or discussion:

- by e-mail to **security@refiroo.org**, or
- through GitHub's private vulnerability reporting on the repository (Security › Report a vulnerability).

Say what you found, the version (Settings › About shows it), and how to reproduce it. A proof of concept
helps; please do not touch data that is not yours.

refiroo is maintained by one person. You will get an acknowledgement **within 7 days** as a best effort;
there is no round-the-clock promise. We will work with you on a fix and agree a disclosure date before
anything is published (coordinated disclosure). You are credited in the advisory and the
[CHANGELOG](CHANGELOG.md) unless you prefer not to be.

## Supported versions

Before 1.0, only the **latest minor release** receives security fixes. A fix is a new tagged release; its
tag is the corresponding source (see the licence section of the [README](README.md)).

## What is in scope

The engine (`backend/`), the browser application (`frontend/`), the container images and the reference
installation in `compose.yml` and [docs/OPERATIONS.md](docs/OPERATIONS.md). How authentication and
authorization are meant to work is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#security-012); the
0.12 independent review and its findings are in [docs/SECURITY_REVIEW_0_12.md](docs/SECURITY_REVIEW_0_12.md).

Out of scope: findings that need an already-compromised host or administrator account, missing
hardening of a deployment that does not follow OPERATIONS, and denial of service by sheer volume.
