"""Sign-in providers and local sign-in, as a Security administrator sets them (Product 0.12 I3).

A provider's client secret is sealed with ``SECRETS_ENCRYPTION_KEY`` and never answered (D253,
D366). Saving an enabled provider reads its discovery document and keys first, so a mistyped issuer
is refused when saved (``SIGN_IN_PROVIDER_UNREACHABLE``). A provider somebody signed in with is
disabled rather than deleted (``SIGN_IN_PROVIDER_IN_USE``); disabling or deleting it ends the
sessions it started (D367). Local sign-in is turned off only once an enabled provider has signed
someone in (``NO_WORKING_PROVIDER``); while off, only people who keep it sign in with a password
(D365).
"""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...common.sealing import seal, unseal
from ...errors import ApiError, api_error
from ...models.commands import LocalSignInUpdate, SignInProviderCreate, SignInProviderUpdate
from ...models.database import LocalSignIn, SignInProvider, User, UserIdentity, UserSession
from . import provider_client, security_events
from .settings import IdentitySettings

LOCAL = "local"
# A session's signed_in_with is a provider's key, or one of these ways in.
RESERVED_KEYS = (LOCAL, "password", "passkey")
_KEYS = (integer_key("sequenceId", SignInProvider.id, "id"),)


def _context(key: str) -> bytes:
    return b"sign-in-provider:" + key.encode()


def client_secret(settings: IdentitySettings, provider: SignInProvider) -> str:
    return unseal(settings.encryption_key, provider.client_secret, _context(provider.key)).decode()


def redirect_uri(settings: IdentitySettings, key: str) -> str:
    """The address to register with the provider: where it returns the browser (D366)."""
    return f"{settings.issuer}/oauth/providers/{key}/callback"


def signed_out_uri(settings: IdentitySettings, key: str) -> str:
    """The address to register for signing out of the provider: where it returns the browser
    (I4a, D379)."""
    return f"{settings.issuer}/oauth/providers/{key}/signed-out"


def id_token_context(session_key: str) -> bytes:
    return b"provider-id-token:" + session_key.encode()


def _changing[T](session: Session, change: Callable[[], T]) -> T:
    try:
        result = change()
        session.commit()
    except ApiError:
        session.rollback()
        raise
    except IntegrityError:
        session.rollback()
        raise _key_taken() from None
    return result


def _key_taken() -> ApiError:
    return api_error(409, "SIGN_IN_PROVIDER_KEY_TAKEN", "Another sign-in provider has this key")


def _stale(what: str, current: int) -> ApiError:
    return api_error(
        409, "VERSION_CONFLICT", f"{what} version has changed", {"currentVersion": current}
    )


def load_provider(session: Session, key: str, *, for_update: bool = False) -> SignInProvider:
    statement = select(SignInProvider).where(SignInProvider.key == key)
    provider = session.scalar(statement.with_for_update() if for_update else statement)
    if provider is None:
        raise api_error(404, "SIGN_IN_PROVIDER_NOT_FOUND", f"Sign-in provider '{key}' not found")
    return provider


def provider_page(session: Session, *, page: PageRequest, page_size: int) -> Page[SignInProvider]:
    return paginate_statement(
        session,
        select(SignInProvider),
        keys=_KEYS,
        scope="sign-in-providers",
        filters={},
        page=page,
        page_size=page_size,
        message="Sign-in provider list cursor is invalid",
    )


def enabled_providers(session: Session) -> list[SignInProvider]:
    """The providers the sign-in page offers, as created."""
    return list(
        session.scalars(
            select(SignInProvider)
            .where(SignInProvider.enabled.is_(True))
            .order_by(SignInProvider.id)
        )
    )


def people(session: Session, provider_ids: list[int]) -> dict[int, int]:
    """How many people have signed in with each provider."""
    if not provider_ids:
        return {}
    rows = session.execute(
        select(UserIdentity.provider_id, func.count())
        .where(UserIdentity.provider_id.in_(provider_ids))
        .group_by(UserIdentity.provider_id)
    )
    return {provider_id: count for provider_id, count in rows}


def _check(issuer: str) -> None:
    try:
        provider_client.check(issuer)
    except provider_client.ProviderError as error:
        raise api_error(
            422,
            "SIGN_IN_PROVIDER_UNREACHABLE",
            f"The provider at {issuer!r} cannot be used: {error}",
            {"reason": str(error), "kind": error.kind},
        ) from None


def _check_sign_out(issuer: str) -> None:
    try:
        provider_client.check_sign_out(issuer)
    except provider_client.ProviderError as error:
        raise api_error(
            422,
            "SIGN_IN_PROVIDER_UNREACHABLE",
            f"The provider at {issuer!r} cannot sign people out: {error}",
            {"reason": str(error), "kind": error.kind},
        ) from None


def _groups_claim(value: str | None) -> str | None:
    return (value or "").strip() or None


def create_provider(
    session: Session, settings: IdentitySettings, payload: SignInProviderCreate
) -> SignInProvider:
    if payload.key in RESERVED_KEYS:
        raise _key_taken()
    issuer = payload.issuer.strip()
    if payload.enabled:
        _check(issuer)
    if payload.signOutOfProvider:
        _check_sign_out(issuer)

    def change() -> SignInProvider:
        if session.scalar(select(SignInProvider.id).where(SignInProvider.key == payload.key)):
            raise _key_taken()
        provider = SignInProvider(
            key=payload.key,
            name=payload.name,
            issuer=issuer,
            client_id=payload.clientId,
            client_secret=seal(
                settings.encryption_key, payload.clientSecret.encode(), _context(payload.key)
            ),
            groups_claim=_groups_claim(payload.groupsClaim),
            enabled=payload.enabled,
            sign_out_of_provider=payload.signOutOfProvider,
        )
        session.add(provider)
        session.flush()
        security_events.record(
            session, "sign-in-provider", provider.key, "created",
            details={"name": provider.name, "issuer": provider.issuer,
                     "groupsClaim": provider.groups_claim, "enabled": provider.enabled,
                     "signOutOfProvider": provider.sign_out_of_provider},
        )  # fmt: skip
        return provider

    return _changing(session, change)


def _end_sessions(session: Session, key: str, now: datetime) -> None:
    """End the open sessions a provider started (D367)."""
    session.execute(
        update(UserSession)
        .where(UserSession.signed_in_with == key, UserSession.ended_at.is_(None))
        .values(ended_at=now, ended_reason="providerDisabled", provider_id_token=None),
        execution_options={"synchronize_session": "fetch"},
    )


def update_provider(
    session: Session, settings: IdentitySettings, key: str, payload: SignInProviderUpdate
) -> SignInProvider:
    fields = payload.model_fields_set - {"expectedVersion"}
    current = load_provider(session, key)
    issuer = payload.issuer.strip() if payload.issuer is not None else current.issuer
    enabled = payload.enabled if payload.enabled is not None else current.enabled
    if enabled and ({"issuer", "enabled"} & fields):
        _check(issuer)
    sign_out = (
        payload.signOutOfProvider
        if payload.signOutOfProvider is not None
        else current.sign_out_of_provider
    )
    if sign_out and ({"issuer", "signOutOfProvider"} & fields):
        _check_sign_out(issuer)

    def change() -> SignInProvider:
        provider = load_provider(session, key, for_update=True)
        if provider.version != payload.expectedVersion:
            raise _stale("Sign-in provider", provider.version)
        now = datetime.now(UTC)
        if payload.name is not None:
            provider.name = payload.name
        provider.issuer = issuer
        if payload.clientId is not None:
            provider.client_id = payload.clientId
        if payload.clientSecret is not None:
            provider.client_secret = seal(
                settings.encryption_key, payload.clientSecret.encode(), _context(provider.key)
            )
        if "groupsClaim" in fields:
            provider.groups_claim = _groups_claim(payload.groupsClaim)
        if provider.enabled and not enabled:
            _end_sessions(session, provider.key, now)
        provider.enabled = enabled
        provider.sign_out_of_provider = sign_out
        provider.version += 1
        provider.updated_at = now
        security_events.record(
            session, "sign-in-provider", provider.key, "updated", version=provider.version,
            details=security_events.changed(
                sorted(fields), name=provider.name, issuer=provider.issuer,
                groupsClaim=provider.groups_claim, enabled=provider.enabled,
                signOutOfProvider=provider.sign_out_of_provider,
            ),
        )  # fmt: skip
        return provider

    return _changing(session, change)


def delete_provider(session: Session, key: str) -> None:
    """A provider nobody signed in with, with the groups made for it (D366)."""

    def change() -> None:
        provider = load_provider(session, key, for_update=True)
        used = session.scalar(select(exists().where(UserIdentity.provider_id == provider.id)))
        if used:
            raise api_error(
                409,
                "SIGN_IN_PROVIDER_IN_USE",
                f"People have signed in with '{provider.name}'; disable it instead",
            )
        _end_sessions(session, provider.key, datetime.now(UTC))
        session.execute(delete(SignInProvider).where(SignInProvider.id == provider.id))
        security_events.record(
            session, "sign-in-provider", provider.key, "deleted", details={"name": provider.name}
        )

    _changing(session, change)


# --- local sign-in --------------------------------------------------------------------------------


def local_state(session: Session, *, for_update: bool = False) -> LocalSignIn:
    statement = select(LocalSignIn).where(LocalSignIn.id == 1)
    state = session.scalar(statement.with_for_update() if for_update else statement)
    if state is None:
        state = LocalSignIn(id=1, enabled=True, version=1, updated_at=datetime.now(UTC))
        session.add(state)
        session.flush()
    return state


def local_enabled(session: Session) -> bool:
    return session.scalar(select(LocalSignIn.enabled).where(LocalSignIn.id == 1)) is not False


def kept_people(session: Session) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.local_kept.is_(True), User.active.is_(True))
        )
        or 0
    )


def set_local(session: Session, payload: LocalSignInUpdate) -> LocalSignIn:
    def change() -> LocalSignIn:
        state = local_state(session, for_update=True)
        if state.version != payload.expectedVersion:
            raise _stale("Local sign-in", state.version)
        changed: list[str] = []
        if payload.enabled is not None and state.enabled and not payload.enabled:
            working = session.scalar(
                select(
                    exists().where(
                        SignInProvider.enabled.is_(True),
                        SignInProvider.last_sign_in_at.is_not(None),
                    )
                )
            )
            if not working:
                raise api_error(
                    409,
                    "NO_WORKING_PROVIDER",
                    "Local sign-in stays on until an enabled sign-in provider has signed someone "
                    "in, so nobody is locked out",
                )
        if payload.enabled is not None and state.enabled != payload.enabled:
            state.enabled = payload.enabled
            changed.append("enabled")
        required = payload.secondFactorRequired
        if required is not None and state.second_factor_required != required:
            state.second_factor_required = required
            changed.append("secondFactorRequired")
        if changed:
            state.version += 1
            state.updated_at = datetime.now(UTC)
            security_events.record(
                session, "sign-in-provider", LOCAL, "updated", version=state.version,
                details=security_events.changed(
                    changed, enabled=state.enabled,
                    secondFactorRequired=state.second_factor_required,
                ),
            )  # fmt: skip
        return state

    return _changing(session, change)


def refuse_last_kept(session: Session, user: User) -> None:
    """While local sign-in is off, the last active person who keeps it is the way back (I4a,
    D381): they neither lose it nor are deactivated."""
    if user.local_kept and user.active and not local_enabled(session) and kept_people(session) <= 1:
        raise api_error(
            409,
            "LAST_LOCAL_ADMINISTRATOR",
            "Local sign-in is off and this is the last person who keeps it; turn local sign-in "
            "on, or let someone else keep it first",
        )


def refuse_while_off(session: Session, user: User) -> None:
    """A password is of no use to someone who cannot sign in with it (D365)."""
    if not user.local_kept and not local_enabled(session):
        raise api_error(
            409,
            "LOCAL_SIGN_IN_OFF",
            "Local sign-in is off: only administrators made on the server sign in with a password",
        )


# --- reads ----------------------------------------------------------------------------------------


def names(
    session: Session, *, ids: Sequence[int] = (), keys: Sequence[str] = ()
) -> dict[int | str, tuple[str, str]]:
    """Providers' keys and names, by ID and by key."""
    if not ids and not keys:
        return {}
    rows = session.execute(
        select(SignInProvider.id, SignInProvider.key, SignInProvider.name).where(
            SignInProvider.id.in_(list(ids)) | SignInProvider.key.in_(list(keys))
        )
    )
    found: dict[int | str, tuple[str, str]] = {}
    for provider_id, key, name in rows:
        found[provider_id] = found[key] = (key, name)
    return found


def identities(session: Session, user_ids: list[int]) -> dict[int, list[tuple[str, str, str]]]:
    """Each person's provider identities, as (provider key, provider name, subject), in one
    statement for a page."""
    if not user_ids:
        return {}
    rows = session.execute(
        select(UserIdentity.user_id, SignInProvider.key, SignInProvider.name, UserIdentity.subject)
        .join(SignInProvider, SignInProvider.id == UserIdentity.provider_id)
        .where(UserIdentity.user_id.in_(user_ids))
        .order_by(UserIdentity.id)
    )
    found: dict[int, list[tuple[str, str, str]]] = {}
    for user_id, key, name, subject in rows:
        found.setdefault(user_id, []).append((key, name, subject))
    return found
