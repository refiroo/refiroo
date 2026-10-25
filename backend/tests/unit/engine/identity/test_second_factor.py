"""The authenticator app's arithmetic (Product 0.12 I4b, D384): RFC 6238's own test vectors, the
window a code is accepted in, and each step accepted once."""

from datetime import UTC, datetime

import pytest

from app.engine.identity.second_factor import accepted_step, hotp, qr_svg

KEY = b"12345678901234567890"  # RFC 6238 Appendix B, SHA-1


def _at(seconds: int) -> datetime:
    return datetime.fromtimestamp(seconds, UTC)


@pytest.mark.parametrize(
    ("seconds", "code"),
    [
        (59, "94287082"),
        (1111111109, "07081804"),
        (1111111111, "14050471"),
        (1234567890, "89005924"),
        (2000000000, "69279037"),
        (20000000000, "65353130"),
    ],
)
def test_the_codes_of_rfc_6238(seconds, code):
    assert hotp(KEY, seconds // 30, digits=8) == code


def test_a_code_is_accepted_one_step_either_side_and_once():
    now = _at(1111111111)  # step 37037037
    step = 1111111111 // 30
    for ahead in (-1, 0, 1):
        assert accepted_step(KEY, hotp(KEY, step + ahead), now, None) == step + ahead
    assert accepted_step(KEY, hotp(KEY, step + 2), now, None) is None
    assert accepted_step(KEY, hotp(KEY, step - 2), now, None) is None
    # A step already used, and any before it, are refused; a later one in the window is not.
    assert accepted_step(KEY, hotp(KEY, step), now, step) is None
    assert accepted_step(KEY, hotp(KEY, step - 1), now, step) is None
    assert accepted_step(KEY, hotp(KEY, step + 1), now, step) == step + 1


def test_what_a_person_types_is_read_as_the_app_shows_it():
    now = _at(59)
    code = hotp(KEY, 1)
    assert accepted_step(KEY, f"{code[:3]} {code[3:]}", now, None) == 1
    for typed in ("", "12345", f"{code}0", "abcdef", "١٢٣٤٥٦"):
        assert accepted_step(KEY, typed, now, None) is None


def test_the_qr_code_is_an_svg_that_scales_with_a_quiet_zone():
    svg = qr_svg("otpauth://totp/Example:ana?secret=JBSWY3DPEHPK3PXP&issuer=Example")
    assert svg.startswith("<svg ") and 'viewBox="0 0 ' in svg and 'role="img"' in svg
    assert 'fill="#fff"' in svg and "width=" not in svg.split(">")[0]
    box = int(svg.split('viewBox="0 0 ')[1].split(" ")[0])
    # The first dark module sits inside the four-module quiet zone on every side.
    assert 'd="M4 4h7' in svg and box > 8


def test_recovery_codes_are_stored_keyed():
    """A leaked table is not a list of unkeyed hashes of 60-bit codes: the same code under another
    key, or plain SHA-256, gives a different value."""
    import hashlib
    from types import SimpleNamespace

    from app.engine.identity.second_factor import _recovery_hash

    first = SimpleNamespace(encryption_key=b"a" * 32)
    other = SimpleNamespace(encryption_key=b"b" * 32)
    code = "abcd-efgh-jkmn"
    assert _recovery_hash(first, code) == _recovery_hash(first, "ABCD EFGH-jkmn".replace(" ", "-"))
    assert _recovery_hash(first, code) != _recovery_hash(other, code)
    assert _recovery_hash(first, code) != hashlib.sha256(b"abcdefghjkmn").hexdigest()
