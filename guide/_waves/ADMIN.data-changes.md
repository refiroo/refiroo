# ADMIN screens: changes to the reference instance

The ADMIN screens are view-only, but two clicks act at once without a confirmation dialog:

- Signing keys: the click on "Start a new key" (first attempt at the rotation-dialog screen) rotated the key. The reference instance now has a new current key (created 10:35 PM) and the earlier key `Fxgau0lLhxEDivKS` is "Verifying until 11:35 PM", then retired by itself. Sessions and clients moved on without action. The spec no longer clicks it; the dialog screen is `admin-signing-keys-retire` (Retire the current key now, cancelled).
- People: "Reset password" on Rita Approver (`admin-person-reset-password`) makes a one-time password link at once (audit entry "One-time password link made"). The link was not used, so her password is unchanged; it expires after 24 hours or when a newer link replaces it.
- Each run signs in as the administrator (and as nobody else): more entries under Account, "Where you're signed in".
