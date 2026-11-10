# MS-MI guide: managed identity for Microsoft 365 mail, and the "Sign in with" menu

Read `guide/AGENTS.md`. Readers: the access administrator (`administer/mail.md`) and the operator
(`run/sign-in-and-mail-setup.md`), as each page names. The pages already describe Microsoft 365 with a client secret or
a certificate (wave MS); this wave adds the managed identity and describes the form as it is now.

## Why

Package MS-D5 (`docs/BASE_0_13_IMPLEMENTATION_PLAN.md`, "MS", point 7) added a managed identity as a third way for refiroo
to sign in to Microsoft 365, for refiroo running on Azure. The Settings › Mail form for Microsoft 365 was reorganised. The
code wins: `frontend/src/features/settings/MailPage.tsx` and `mailText.ts` (`SIGN_IN`), `backend/app/engine/mail/graph.py`,
`settings.py`, `backend/app/models/commands.py` (`MailSettingsUpdate`), `docs/API.md` ("Mail"), `docs/OPERATIONS.md`
("Managed identity (refiroo runs in Azure)"), `../CHANGELOG.md` (Unreleased, 0.13 MS).

## What the product does now (check each point in the code)

- **The form, Microsoft 365 side.** **Send mail through** (SMTP server or Microsoft 365) is the first choice. With
  Microsoft 365, **Sign in with** follows it, with four entries: **Client secret**, **Certificate**, **Managed identity –
  this tenant**, **Managed identity – hosted in another tenant**. One plain line under the menu describes the chosen entry
  (secret: the simplest, it expires and must be renewed; certificate: no shared secret is sent, renewed when it expires;
  this tenant: no secret is stored, refiroo runs in Azure in the same tenant as Microsoft 365 and Azure gives it its
  token; another tenant: refiroo is hosted in another tenant than Microsoft 365 and a multitenant app in the hosting
  tenant trusts the identity). Only the chosen entry's fields are shown.
  - Client secret: **Tenant ID**, **Application (client) ID**, **Client secret**.
  - Certificate: **Tenant ID**, **Application (client) ID**, **Certificate** (PEM: the private key, not
    password-protected, RSA, and the certificate), with a saved certificate's thumbprint and expiry.
  - Managed identity – this tenant: **Identity client ID**, optional (empty: the host's own, system-assigned identity).
    No tenant ID and no application ID are asked for or accepted.
  - Managed identity – hosted in another tenant: **Tenant ID** (the customer's), **Application (client) ID** (the
    multitenant app registration that trusts the identity) and **Identity client ID** (required: only a user-assigned
    identity can be a federated credential).
  - Both managed identity entries carry the note that a managed identity works only when refiroo runs in Azure (App
    Service, Container Apps or a virtual machine) and that no secret is stored.
- **Below the fields:** **Sending mailbox**, then two folded sections, **What to set up in Microsoft Entra** (the steps of
  the chosen entry only) and **Other Microsoft clouds (token and Graph addresses)** (the two addresses; it opens by itself
  when a saved address is not the global default), then **Application address**.
- **No secret is stored for a managed identity.** Saving one clears a saved secret or certificate, and saving a secret or
  certificate clears the identity settings. A managed identity is sent whole in every save; nothing is "kept".
- **Managed identity – this tenant.** The engine asks the Azure host (not Microsoft's token endpoint) for a token for
  Microsoft Graph and sends with it. The host's token endpoint is `IDENTITY_ENDPOINT` with `IDENTITY_HEADER` (set by App
  Service and Container Apps), else the instance metadata service of a virtual machine. Entra setup (operator page; code
  in `docs/OPERATIONS.md`): give the identity's service principal the Microsoft Graph `Mail.Send` app role with the
  PowerShell commands shown there (there is no portal button, and no admin-consent screen for a managed identity), then
  limit it to the sending mailbox with an application access policy that names the identity's client ID.
- **Managed identity – hosted in another tenant.** The engine takes an identity token for the audience
  `api://AzureADTokenExchange` (`api://AzureADTokenExchangeUSGov`, `…China` by the cloud of the token address) from the host
  and sends it as the client assertion of the client-credentials grant at the customer's tenant, as a certificate's signed
  assertion would be. Setup: a multitenant app registration in the hosting tenant with a federated credential (issuer
  `https://login.microsoftonline.com/<hosting tenant ID>/v2.0`, subject the user-assigned identity's principal ID,
  audience `api://AzureADTokenExchange`; the JSON and the `az ad app federated-credential create` command are in
  `docs/OPERATIONS.md`), the customer's administrator grants admin consent to the app in their tenant, and in the customer's
  tenant the app has `Mail.Send` and the application access policy. Microsoft does not support another cloud than the
  identity's.
- **Failures.** Where no Azure host answers (refiroo does not run on Azure with a managed identity), the test message and
  queued mail fail as **the login was refused** with the sentence "refiroo is not running with a managed identity on an
  Azure host…", the same for every waiting message. The host refusing the identity's client ID is also a refused login
  naming the identity. A federated app without a matching federated credential, or not consented in the customer's tenant,
  is a refused token (AADSTS 70025 or 700213). The other Microsoft 365 failures are as the pages already say.
- **API.** `PUT /mail-settings` takes `identityMode` (`direct` or `federated`) and `identityClientId`; the response has
  `credential` (`secret`, `certificate` or `managedIdentity`), `identityMode`, `identityClientId`. A secret or certificate
  with an identity mode is refused at its field; `tenantId` and `clientId` are refused with `direct`. Link to `/docs/api`,
  do not repeat the reference.

## What to do

- `src/content/docs/administer/mail.md`: in **Send through Microsoft 365**, describe the form as it is now: the **Sign in
  with** menu with its four entries and what each asks for (the table that lists the fields may be reshaped to follow the
  entries), the two folded sections, and the managed identity entries, with one sentence each on when to choose them and the
  note that they need refiroo to run in Azure. Keep the existing text on Sent Items, bounces, the retry rules, the failure
  table (extend it for the managed identity failures) and removal. Do not change the existing screenshot or its caption;
  list the missing pictures.
- `src/content/docs/run/sign-in-and-mail-setup.md`: in **Prepare Microsoft 365 delivery**, add the two managed identity
  setups for the operator in full (the commands and the federated credential JSON from `docs/OPERATIONS.md`, copied, with
  placeholders as written there), how the host's token endpoint is found, that nothing is stored and nothing renews, and
  that AKS workload identity is not supported. Extend "Read mail refusals" with the managed identity failures. Do not alter
  an existing example.
- No new pages. Keep "SMTP" where a sentence is about SMTP only.

## Files you may edit

- `src/content/docs/administer/mail.md`
- `src/content/docs/run/sign-in-and-mail-setup.md`
- `_waves/progress/MS-MI.md`

## Report

Per page: what changed and why (one line each), the passages you checked and left as they are, the pictures that are
missing or no longer match, and anything in the points above that you could not support from the code.
