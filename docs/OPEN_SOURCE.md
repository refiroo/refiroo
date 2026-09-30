# Open-source preparation

The project has intentionally independent source code, model terminology and interface design. The
supplied vendor package is discovery material and is not included in the repository.

## Licence decision

No licence has been selected yet. Publishing a repository without a licence does not grant normal
open-source reuse rights, so a licence must be chosen before the first public release.

Apache License 2.0 is the practical default for a permissive infrastructure product because it includes
an explicit patent grant. AGPL-3.0 is the alternative if hosted modifications should also remain open.
The choice should reflect the intended adoption and commercial model.

## Third-party code shipped with the engine

| Component | Version | Licence | Where | Used for |
| --- | --- | --- | --- | --- |
| [Scalar API Reference](https://github.com/scalar/scalar) (`@scalar/api-reference`, `dist/browser/standalone.js`) | 1.72.2 | MIT, © 2023-present Scalar | `backend/app/management/reference/scalar/` with its `LICENSE` | The API reference page at `/docs` (0.9 V1) |

The script is the npm package's file unchanged, so its SHA-384 matches the copy jsDelivr serves for the
same version (the CDN setting relies on it). To upgrade: replace the file from the new version's
package, update `SCALAR_VERSION` and `SCALAR_INTEGRITY` in `backend/app/management/reference/`, and run
the `contract` group and `test:browser:v1`.

## Before the first public release

- Choose and add the licence.
- Replace STOPS-oriented seed terminology if the repository should be entirely generic.
- Add contribution guidelines, a code of conduct and security reporting instructions.
- Run dependency and secret scanning.
- Confirm that all committed examples are synthetic.
- Establish semantic versioning and a public compatibility policy for the model language and API.

