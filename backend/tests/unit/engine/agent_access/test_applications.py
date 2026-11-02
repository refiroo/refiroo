"""The addresses an assistant may return to, checked again on every use (``applications.accepts``)."""

from types import SimpleNamespace

import pytest

from app.engine.agent_access import applications


def _application(source, *uris):
    return SimpleNamespace(source=source, redirect_uris=list(uris))


def test_a_self_registered_address_is_checked_against_the_hosts_listed_now():
    held = _application(
        "registered", "https://assistant.example.com/cb", "http://localhost:4000/cb"
    )
    uri = "https://assistant.example.com/cb"
    assert applications.accepts(held, uri, ("assistant.example.com",))
    # The operator removed the host after the registration: the address no longer counts.
    assert not applications.accepts(held, uri, ())
    assert not applications.accepts(held, uri, ("other.example.com",))
    # This computer is never a host to list, and any port is taken.
    assert applications.accepts(held, "http://localhost:4000/cb", ())
    assert applications.accepts(held, "http://localhost:51234/cb", ())


def test_an_administrators_address_is_not_held_to_the_list():
    held = _application("administrator", "https://assistant.example.com/cb")
    assert applications.accepts(held, "https://assistant.example.com/cb", ())


@pytest.mark.parametrize(
    "uris",
    [
        [f"http://localhost:{port}/cb" for port in range(applications.MOST_REDIRECT_URIS + 1)],
        ["http://localhost:1/" + "a" * applications.LONGEST_REDIRECT_URI],
    ],
)
def test_a_registration_carries_at_most_ten_addresses_of_two_thousand_characters(uris):
    with pytest.raises(applications.RegistrationRefused):
        applications._checked("x", uris, None)
