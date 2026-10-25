"""J39.8, J40.13 — a provider identity moved onto the person who already had a local account,
signing out of the provider, and the last person who keeps local sign-in (USER_JOURNEYS.md §
Security, 0.12 I4a).

A provider sign-in made a new, empty person; an administrator moves the identity and the provider
groups onto the person the sign-in belongs to and the new person is deactivated. A provider may be
set to sign people out of it too: signing out of the engine then sends the browser to the
provider's sign-out address with the ID token and back. Every case runs on two configurations
through the public API, with the harness provider and a plain HTTP client keeping the cookies.
"""

from urllib.parse import parse_qs, urlsplit

import jwt
import pytest
from oidc_provider import OidcProvider
from scenario import W1, ok, refused
from test_j39_provider_sign_in import (
    PAT,
    _back,
    _create_admin,
    _group_by_claim,
    _members,
    _provider,
    _signed_in,
    _through,
)
from test_j39_sign_in import (
    PASSWORD,
    _bearer,
    _browser,
    _code,
    _exchange,
    _person,
    _pkce,
    _post_form,
    _renew,
    _revoked,
)

APP = "http://localhost:5173/"


@pytest.fixture
def idp():
    with OidcProvider() as provider:
        yield provider


def _link(world, target: dict, source: dict):
    return world.api.post(
        f"/users/{target['id']}/identities",
        {"fromUserId": source["id"], "expectedVersion": target["version"]},
    )


def _user(world, user_id: str) -> dict:
    return ok(world.api.get(f"/users/{user_id}"))


def _me(world, token: str) -> dict:
    return ok(world.api.client.get("/api/v1/me", headers=_bearer(token)))


def _actions(world, aggregate_id: str) -> list[str]:
    events = ok(world.api.get("/security-events", aggregateType="user", pageSize=500))["items"]
    return [e["action"] for e in events if e["aggregateId"] == aggregate_id]


@pytest.mark.journey("J40")
@pytest.mark.structures("R")
def test_a_provider_identity_is_moved_onto_an_existing_person(world, idp):
    """Given Ann with a password and Reader in the workspace, and a provider group `staff`. When Ann
    signs in through the provider the first time she becomes a new person; linking Ann (who has a
    password and a grant) into that person, or a provider person holding a direct grant into Ann,
    answers `409 PERSON_HAS_ACCESS`. With the grant removed, linking the new person's identity to
    Ann answers Ann with the identity, deactivates the new person and ends their session; linking
    another person of the same provider into Ann answers `409 IDENTITY_PROVIDER_TAKEN`, and into the deactivated new person `409 LINK_TARGET_DEACTIVATED`. Her next
    provider sign-in is Ann, with her role and the group `staff` moved onto her. Unlinking removes
    the identity and the memberships (`404 IDENTITY_NOT_FOUND` for none); the next sign-in makes a
    new person again. The security events name the link and the unlink."""
    _provider(world, idp)
    staff = ok(world.api.post("/groups", {
        "name": "Staff", "source": {"provider": "harness", "claimValue": "staff"}}, ), 201)  # fmt: skip
    ann = _person(world, "ann")
    direct = {"principal": {"kind": "user", "id": ann["id"]}, "role": "reader"}
    ok(world.api.post("/grants", {**direct, "scope": {"workspaceKey": W1}}), 201)
    ann = _user(world, ann["id"])

    _, first_token = _sign_in_keeping(world, idp, sub="a-1", name="Ann Provider",
                                      preferred_username="ann.p", groups=["staff"])  # fmt: skip
    first = _me(world, first_token)
    new = _user(world, first["id"])
    assert new["id"] != ann["id"] and new["hasPassword"] is False
    assert [i["subject"] for i in new["identities"]] == ["a-1"] and ann["identities"] == []

    refused(_link(world, new, ann), 409, "PERSON_HAS_ACCESS")
    bob_token = _signed_in(world, idp, sub="b-1", name="Bob Provider", groups=[])
    bob = _user(world, _me(world, bob_token)["id"])
    # A person with no password has no use for a second factor or a passkey of their own.
    refused(world.api.client.post("/api/v1/me/second-factor", headers=_bearer(bob_token)),
            409, "PASSWORD_REQUIRED")  # fmt: skip
    bob_grant = ok(world.api.post("/grants", {
        "principal": {"kind": "user", "id": bob["id"]}, "role": "reader",
        "scope": {"workspaceKey": W1}}), 201)  # fmt: skip
    refused(_link(world, ann, bob), 409, "PERSON_HAS_ACCESS")
    ok(world.api.delete(f"/grants/{bob_grant['id']}"), 204)

    linked = ok(_link(world, ann, new), 200)
    assert linked["id"] == ann["id"] and linked["version"] == ann["version"] + 1
    assert [i["subject"] for i in linked["identities"]] == ["a-1"]
    assert [r["key"] for r in linked["roles"]] == ["reader"]
    gone = _user(world, new["id"])
    assert gone["active"] is False and gone["identities"] == []
    _revoked(world.api.client.get("/api/v1/me", headers=_bearer(first_token)))
    bob = _user(world, bob["id"])
    refused(_link(world, linked, bob), 409, "IDENTITY_PROVIDER_TAKEN")
    refused(_link(world, gone, bob), 409, "LINK_TARGET_DEACTIVATED")
    refused(world.api.post(f"/users/{ann['id']}/identities",
                           {"fromUserId": ann["id"], "expectedVersion": linked["version"]}),
            422, "LINK_SAME_PERSON")  # fmt: skip
    refused(_link(world, ann, bob), 409, "VERSION_CONFLICT")

    token = _signed_in(world, idp, sub="a-1", name="Ann Provider", preferred_username="ann.p",
                       groups=["staff"])  # fmt: skip
    me = _me(world, token)
    assert me["id"] == ann["id"] and me["signedInWith"] == "harness"
    assert _members(world, _group_by_claim(world, "staff")) == ["Ann Provider"]
    assert staff["id"] == _group_by_claim(world, "staff")["id"]

    ok(world.api.delete(f"/users/{ann['id']}/identities/harness"), 204)
    refused(world.api.delete(f"/users/{ann['id']}/identities/harness"), 404, "IDENTITY_NOT_FOUND")
    assert _user(world, ann["id"])["identities"] == []
    assert _members(world, _group_by_claim(world, "staff")) == []
    _revoked(world.api.client.get("/api/v1/me", headers=_bearer(token)))
    again = _me(world, _signed_in(world, idp, sub="a-1", name="Ann Provider",
                                  preferred_username="ann.p", groups=["staff"]))  # fmt: skip
    assert again["id"] not in (ann["id"], new["id"])
    assert "identity-linked" in _actions(world, ann["id"])
    assert "identity-unlinked" in _actions(world, ann["id"])


def _sign_in_keeping(world, idp: OidcProvider, **person):
    """A new browser signed in through the provider: the browser and its access token."""
    browser = _browser(world)
    answer, verifier = _through(browser, idp, **person)
    token = ok(_exchange(browser, _code(answer), verifier))["access_token"]
    return browser, token


@pytest.mark.journey("J39")
def test_signing_out_of_the_provider_too(world, idp):
    """Given a provider that signs people out of it too. When a person signs in through it and
    signs out by opening `/oauth/sign-out`, then the session has ended and the browser is sent to
    the provider's sign-out address with the ID token for that person and the engine's
    `signed-out` address; the provider sends it back through `signed-out` to the application's
    address; the refresh cookie is cleared. A return address of another site is not followed. With
    the setting off, or for a person who signed in with a password, the browser goes straight to the
    application. Turning it on for a provider whose discovery names no sign-out address answers
    `422 SIGN_IN_PROVIDER_UNREACHABLE`."""
    idp.end_session = False
    body = {"signOutOfProvider": True}
    refused(world.api.post("/sign-in-providers", {
        "key": "harness", "name": "Harness ID", "issuer": idp.issuer, "clientId": idp.client_id,
        "clientSecret": idp.client_secret, "enabled": True, **body}),
        422, "SIGN_IN_PROVIDER_UNREACHABLE")  # fmt: skip
    provider = _provider(world, idp)
    assert provider["signOutOfProvider"] is False
    refused(
        world.api.patch(
            "/sign-in-providers/harness", {"expectedVersion": provider["version"], **body}
        ),
        422,
        "SIGN_IN_PROVIDER_UNREACHABLE",
    )
    idp.end_session = True
    provider = ok(
        world.api.patch(
            "/sign-in-providers/harness", {"expectedVersion": provider["version"], **body}
        )
    )
    assert provider["signOutOfProvider"] is True
    assert provider["signedOutUri"].endswith("/oauth/providers/harness/signed-out")

    browser, token = _sign_in_keeping(world, idp, **PAT)
    ok(world.api.client.get("/api/v1/me", headers=_bearer(token)))
    out = browser.get("/oauth/sign-out", params={"return": APP}, follow_redirects=False)
    assert out.status_code == 303, out.text
    target = urlsplit(out.headers["location"])
    assert f"{target.scheme}://{target.netloc}{target.path}" == f"{idp.issuer}/logout"
    query = {k: v[0] for k, v in parse_qs(target.query).items()}
    hint = jwt.decode(query["id_token_hint"], options={"verify_signature": False})
    assert hint["sub"] == "p-1" and query["post_logout_redirect_uri"] == provider["signedOutUri"]
    _revoked(world.api.client.get("/api/v1/me", headers=_bearer(token)))
    assert _renew(browser).status_code == 400

    home = _back(browser, idp.sign_out(out.headers["location"]))
    assert home.status_code == 303 and home.headers["location"] == APP

    browser, token = _sign_in_keeping(world, idp, **PAT)
    out = browser.get("/oauth/sign-out", params={"return": "https://evil.example/"},
                      follow_redirects=False)  # fmt: skip
    assert out.status_code == 303 and "evil.example" not in out.headers["location"]
    followed = _back(browser, idp.sign_out(out.headers["location"]))
    assert "evil.example" not in followed.headers["location"]
    assert followed.headers["location"].startswith("http://localhost:5173")

    ok(
        world.api.patch(
            "/sign-in-providers/harness",
            {"expectedVersion": provider["version"], "signOutOfProvider": False},
        )
    )
    browser, token = _sign_in_keeping(world, idp, **PAT)
    out = browser.get("/oauth/sign-out", params={"return": APP}, follow_redirects=False)
    assert out.status_code == 303 and out.headers["location"] == APP
    _revoked(world.api.client.get("/api/v1/me", headers=_bearer(token)))

    ok(
        world.api.patch(
            "/sign-in-providers/harness",
            {"expectedVersion": provider["version"] + 1, "signOutOfProvider": True},
        )
    )
    _person(world, "lou")
    local = _browser(world)
    verifier, challenge = _pkce()
    code = _code(_post_form(local, "lou", PASSWORD, challenge))
    local_token = ok(_exchange(local, code, verifier))["access_token"]
    out = local.get("/oauth/sign-out", params={"return": APP}, follow_redirects=False)
    assert out.status_code == 303 and out.headers["location"] == APP
    _revoked(world.api.client.get("/api/v1/me", headers=_bearer(local_token)))
    assert len(idp.logouts) == 2


@pytest.mark.journey("J40")
def test_the_last_person_who_keeps_local_sign_in(world, idp):
    """Given local sign-in turned off and one person who keeps it. Turning their `localKept` off, or
    deactivating them, answers `409 LAST_LOCAL_ADMINISTRATOR`; with a second person keeping it the
    first can be changed; with local sign-in on again nothing is refused."""
    _create_admin(world, "kept")
    kept = ok(world.api.get("/users", q="kept"))["items"][0]
    _provider(world, idp)
    _signed_in(world, idp, **PAT)
    local = ok(world.api.get("/sign-in-providers/local"))
    ok(world.api.patch("/sign-in-providers/local", {"expectedVersion": local["version"],
                                                    "enabled": False}))  # fmt: skip
    keepers = [u for u in ok(world.api.get("/users", pageSize=500))["items"] if u["localKept"]]
    assert kept["id"] in [u["id"] for u in keepers]
    others = [u for u in keepers if u["id"] != kept["id"]]
    for other in others:
        ok(world.api.patch(f"/users/{other['id']}", {"expectedVersion": other["version"],
                                                    "localKept": False}))  # fmt: skip
    kept = _user(world, kept["id"])
    refused(world.api.patch(f"/users/{kept['id']}", {"expectedVersion": kept["version"],
                                                    "localKept": False}),
            409, "LAST_LOCAL_ADMINISTRATOR")  # fmt: skip
    refused(world.api.patch(f"/users/{kept['id']}", {"expectedVersion": kept["version"],
                                                    "active": False}),
            409, "LAST_LOCAL_ADMINISTRATOR")  # fmt: skip

    _create_admin(world, "second")
    kept = _user(world, kept["id"])
    ok(world.api.patch(f"/users/{kept['id']}", {"expectedVersion": kept["version"],
                                               "localKept": False}))  # fmt: skip
    second = ok(world.api.get("/users", q="second"))["items"][0]
    refused(world.api.patch(f"/users/{second['id']}", {"expectedVersion": second["version"],
                                                      "localKept": False}),
            409, "LAST_LOCAL_ADMINISTRATOR")  # fmt: skip
    local = ok(world.api.get("/sign-in-providers/local"))
    ok(world.api.patch("/sign-in-providers/local", {"expectedVersion": local["version"],
                                                    "enabled": True}))  # fmt: skip
    second = _user(world, second["id"])
    ok(world.api.patch(f"/users/{second['id']}", {"expectedVersion": second["version"],
                                                  "localKept": False}))  # fmt: skip
