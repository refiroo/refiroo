# Licensing TODO

This checklist records the work required to publish and operate RDM Engine as an open-source
project with an optional commercial services and licensing business. It is intentionally separate
from the canonical license text and from the product roadmap.

## Current decision

- [x] Keep the root [`LICENSE`](../LICENSE) as the unmodified GNU Affero General Public License,
  version 3, with the project policy of `AGPL-3.0-or-later`.
- [x] Treat the AGPL as an open-source license: do not prohibit commercial use or add restrictions
  intended to prevent competing businesses from using the software.
- [ ] Obtain legal advice before accepting outside contributions or selling a separate commercial
  license. This checklist is operational guidance, not legal advice.

## Before the first public release

### P0 — Explain the license and source offer in `README.md`

- [x] State clearly that the project is licensed under `AGPL-3.0-or-later` and link to the root
  [`LICENSE`](../LICENSE). _Done in 0.12 L1._
- [x] Add a copyright holder and year that match the confirmed ownership record below. _Done (Krisztian Toth, 2026), pending the confirmation below._
- [x] Document where the corresponding source code for each released version can be obtained.
  Keep release tags or source archives available for as long as the applicable AGPL obligations
  require. _Done: the tag `v<version>` of github.com/refiroo/refiroo; the repository must exist and be public._
- [x] For an RDM Engine instance modified and made available over a network, provide users with a
  conspicuous, working link or other practical route to the corresponding source for that running
  version, including modifications and required scripts/configuration that are part of the covered
  work. _Done: `SOURCE_CODE_URL`, `GET /system`, About and the account menu (D219)._
- [x] Review the README wording against the final deployment and distribution process so the
  documented source offer is actually maintainable. _Done._

Acceptance criteria: a new user can identify the license, read the complete license text, find the
source for a tagged release, and understand how to obtain corresponding source from a networked
modified deployment.

### P0 — Confirm copyright and intellectual-property ownership

- [x] Record the legal copyright holder(s) for existing source, documentation, model examples,
  artwork, and other committed material. _Krisztian Toth (OPEN_SOURCE)._
- [ ] Confirm that no employer, former employer, client, contractor, or vendor retains rights that
  conflict with publication under AGPL or a future commercial license.
- [ ] Inventory externally supplied code, generated files, copied snippets, fonts, icons, logos,
  and example data; remove or replace anything without permission or an appropriate license.
- [x] Decide whether future copyright notices use a personal legal name, a company name, or both,
  and apply that convention consistently to new original files. _Personal name, no per-file headers (D216, D222)._

Acceptance criteria: there is a written ownership record, unresolved third-party ownership issues
are tracked to a named owner, and the README/license notices use the confirmed holder.

### P0 — Establish contribution policy and commercial-relicensing rights

- [x] Add `CONTRIBUTING.md` covering acceptable contributions, coding and review expectations,
  licensing under AGPL-3.0-or-later, copyright notices, and how to submit changes. _Done._
- [ ] Choose a contribution mechanism. If commercial relicensing of contributed code is intended,
  use a contributor license agreement (CLA) or equivalent written assignment/license that gives the
  project owner sufficient copyright and patent rights to offer those commercial terms.
- [ ] Have counsel review the CLA, its scope, patent language, treatment of existing contributions,
  and the process for accepting contributions before enabling external contributions.
- [ ] Do not assume a DCO sign-off alone provides the rights needed for commercial relicensing.
- [ ] Keep a durable record of accepted contributor agreements and identify the maintainer allowed
  to approve contributions.

Acceptance criteria: the contribution path, inbound license, and commercial-relicensing authority
are documented; counsel has reviewed the chosen agreement; and no external contribution is merged
before the required agreement is recorded.

### P1 — Publish a commercial licensing and support contact

- [x] Add a short `COMMERCIAL.md` (or an equivalent public page) stating that commercial licenses,
  implementation assistance, support, training, and optional hosting are available. _Done._
- [x] Publish one maintained business contact route and state what response/support level is and is
  not offered. Do not promise enterprise-grade availability that a solo maintainer cannot provide. _Done: krisztian.toth@refiroo.org._
- [ ] Prepare a per-customer commercial agreement covering license scope, permitted proprietary
  modifications, payment and renewal, support/maintenance boundaries, data responsibility,
  confidentiality, warranty disclaimers, and termination. Have counsel review the template.
- [ ] Define which services remain available under AGPL and which customer requests require a
  separate commercial agreement; keep the distinction clear in sales material.

Acceptance criteria: a prospective customer can find the contact route and understand that a
commercial license or service is negotiated per customer, while no commercial promise changes the
rights granted by the AGPL community license.

### P1 — Separate the project trademark policy from copyright licensing

- [x] Identify the names, logos, domain names, and other marks intended to represent official RDM
  Engine releases or services. _The name refiroo, the logo and the domains refiroo.com, .org and .dev (OPEN_SOURCE)._
- [x] Add `TRADEMARKS.md` describing permitted nominative/descriptive use, attribution, and how a
  modified or unofficial distribution must avoid implying endorsement. _Done._
- [ ] Confirm ownership and registration strategy for the marks before using them as a commercial
  source of trust.

Acceptance criteria: users may accurately refer to and redistribute the software under the AGPL,
but the project can distinguish official builds and services from modified distributions.

### P0 — Audit dependency licenses and publish required notices

- [x] Generate an inventory of backend and frontend dependencies, bundled assets, generated output,
  and build-time tools that are distributed with a release or required to reproduce it. _Done: `scripts/third_party_notices.py`._
- [x] Verify each dependency's license and compatibility with AGPL-3.0-or-later, including any
  attribution, notice, source-offer, patent, or redistribution requirements. _Done by the script's allow-list._
- [x] Resolve incompatible, missing, or unclear licenses before release; do not rely on package
  metadata alone when an asset is copied into the repository. _No incompatible licence found in 0.12 L1; the script refuses one._
- [x] Add `THIRD_PARTY_NOTICES.md` containing the notices and license texts required for the actual
  release contents, and regenerate it as part of release preparation. _Done._
- Recorded as they were added (to verify in the inventory): `openpyxl` (MIT), a backend runtime
  dependency since 0.9 J2 for reading imported workbooks (A-D10), and `python-multipart`
  (Apache-2.0), added in 0.9 J2 to read `multipart/form-data` uploads (D67). Both are permissive and
  compatible with AGPL-3.0-or-later; Apache-2.0's NOTICE requirement applies to the notices file.

Acceptance criteria: a named reviewer can reproduce the inventory for a release, every distributed
third-party item has a recorded license decision, and the shipped notices cover all required text.

### P1 — Add a security reporting policy

- [x] Add `SECURITY.md` with a private vulnerability-reporting route, supported release policy,
  expected acknowledgement timeline, and safe-disclosure guidance. _Done; the address security@refiroo.org must exist._
- [x] State what a solo maintainer can realistically support and how urgent production issues are
  handled; avoid an implied 24/7 SLA unless separately contracted. _Done._
- [x] Document how security fixes and advisories will be credited, released, and communicated,
  including any corresponding-source updates for AGPL network deployments. _Done._

Acceptance criteria: a researcher can report a vulnerability privately, knows what response to
expect, and can find the supported-version and disclosure process without exposing the issue
publicly first.

## Guardrails for future license changes

- [ ] Do not add a "no commercial use" clause, hosted-service restriction, competitor restriction,
  custom AGPL exception, or other additional condition to the AGPL text without a documented legal
  and product decision.
- [ ] Do not edit or append terms to the canonical root `LICENSE`. If a future dual-license or
  additional-permission strategy is chosen, document it in a separate, counsel-reviewed agreement
  and update the repository's notices consistently.
- [ ] Recheck contributor and third-party rights before offering any proprietary commercial license.

Acceptance criteria: the published community license remains recognizable and open-source
compatible, and any commercial terms are separate, explicit, and reviewed before use.

## Still open after 0.12 L1 (the maintainer's or counsel's)

- Confirm that no employer, former employer or client holds rights in the work, and that the example model
  and data are synthetic (the ownership record in [OPEN_SOURCE](OPEN_SOURCE.md)).
- Counsel: review the contributor agreement, then open contributions (CONTRIBUTING says none are merged
  before); the commercial agreement template; the trademark registration strategy.
- Create the mailbox security@refiroo.org and the public repository, and turn on GitHub private
  vulnerability reporting.
- Run the secret scan of the whole history once (`gitleaks`) before the first push.

## Suggested order

1. Confirm ownership and dependency rights.
2. Decide and review the contribution agreement before accepting outside code.
3. Add the README, commercial contact, trademark, security, and third-party notice documents.
4. Run a release-specific legal and notice review before the first public production release.
