# Open-source preparation

The project has intentionally independent source code, model terminology and interface design. The
supplied vendor package is discovery material and is not included in the repository.

## Licence and ownership record

The licence is the GNU Affero General Public License, version 3 or later (`AGPL-3.0-or-later`). The
root [`LICENSE`](../LICENSE) is the unmodified licence text. It was chosen so that modified versions run
as a network service stay open, and so that the owner can still offer separate commercial licences.

**Ownership record (0.12 L1, D216).** Copyright holder of the code, documentation, example model and
artwork: **Krisztian Toth** (personal name; the git history has one author). New files carry no
per-file header (D222). The maintainer must confirm, and the confirmation is theirs alone, that no employer,
former employer or client holds rights in the work and that the committed example model and data are
synthetic; until it is recorded here, [LICENSING_TODO](LICENSING_TODO.md) keeps it open.
**Confirmed by the maintainer (2026-10-28):** the work is a one-person project; Krisztian Toth is its only
author, working with AI assistants (Claude, ChatGPT) on their own accounts, and no employer, former employer or
client is involved. No counsel review is planned (the maintainer's decision). Still open: that the committed
example model and data are synthetic.

**Project identity.** Name: refiroo. Domains: refiroo.com (the website), refiroo.org, refiroo.dev.
Repository: <https://github.com/refiroo/refiroo> (the Python distribution and directories keep the name
`rdm-engine`, [BRANDING](BRANDING.md)). Contact: krisztian.toth@refiroo.org; security reports:
security@refiroo.org ([SECURITY.md](../SECURITY.md)).

**Policies.** [CONTRIBUTING](../CONTRIBUTING.md) (no outside code until a counsel-reviewed contributor
agreement exists, D217), [SECURITY](../SECURITY.md), [TRADEMARKS](../TRADEMARKS.md),
[COMMERCIAL](../COMMERCIAL.md), [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md). The remaining licensing
work is in [LICENSING_TODO](LICENSING_TODO.md).

## Third-party code shipped with the engine

| Component | Version | Licence | Where | Used for |
| --- | --- | --- | --- | --- |
| [Scalar API Reference](https://github.com/scalar/scalar) (`@scalar/api-reference`, `dist/browser/standalone.js`) | 1.72.2 | MIT, © 2023-present Scalar | `backend/app/management/reference/scalar/` with its `LICENSE` | The API reference page at `/docs` (0.9 V1) |
| [Instrument Sans](https://github.com/Instrument/instrument-sans) (`@fontsource-variable/instrument-sans`, variable weight) | 5.3.0 (package) | SIL Open Font Licence 1.1 | Bundled by Vite into the UI build (`dist/assets/*.woff2`); the licence is the package's `LICENSE` | The UI's text face (0.9 U2, ADR-039) |
| [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono) (`@fontsource-variable/jetbrains-mono`, variable weight) | 5.3.0 (package) | SIL Open Font Licence 1.1 | As above | Codes, keys and URLs in the UI (0.9 U2, ADR-039) |
| [Inter](https://github.com/rsms/inter) (`@fontsource-variable/inter`, variable weight) | 5.3.0 (package) | SIL Open Font Licence 1.1 | As above | The text face of the Instrument theme (0.17 UX1) |
| [Fraunces](https://github.com/undercasetype/Fraunces) (`@fontsource-variable/fraunces`, variable weight and optical size) | 5.3.0 (package) | SIL Open Font Licence 1.1 | As above | The title face of the Hearth theme (0.17 UX1) |
| [Bricolage Grotesque](https://fontsource.org/fonts/bricolage-grotesque) (`@fontsource-variable/bricolage-grotesque`, variable weight and optical size) | 5.3.0 (package) | SIL Open Font Licence 1.1 | As above | The title face of the Studio theme (0.17 UX1) |

The script is the npm package's file unchanged, so its SHA-384 matches the copy jsDelivr serves for the
same version (the CDN setting relies on it). To upgrade: replace the file from the new version's
package, update `SCALAR_VERSION` and `SCALAR_INTEGRITY` in `backend/app/management/reference/`, and run
the `contract` group and `test:browser:v1`.

The fonts are served from the engine with the UI, so it needs no internet access. The OFL allows
bundling them with software; the font files are not modified. To upgrade: change the versions in
`frontend/package.json` and re-record the visual baselines with each changed screenshot inspected.

## Before the first public release

- Finish the licensing work in [LICENSING_TODO](LICENSING_TODO.md).
- Add a code of conduct (with the contributor agreement). The code of conduct exists: [CODE_OF_CONDUCT](../CODE_OF_CONDUCT.md), the Contributor Covenant 2.1 (0.13).
- Run the secret scan over the whole history (`gitleaks`) once, before the first push.
- Confirm that all committed examples are synthetic.
- Establish semantic versioning and a public compatibility policy for the model language and API.

