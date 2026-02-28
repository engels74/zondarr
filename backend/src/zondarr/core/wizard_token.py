"""Signed wizard completion tokens for server-side enforcement.

Provides HMAC-based token signing and verification for wizard completion.
Tokens encode the wizard_id and completion timestamp, signed with the
app's SECRET_KEY. Used to prove wizard completion during invitation
redemption — prevents bypassing configured pre-wizard requirements.

Also provides progress tokens that chain validated step IDs, ensuring
all steps must be completed sequentially before a completion token is
issued.

Token format: base64(json_payload).hmac_signature
"""

import base64
import hashlib
import hmac
import time
from uuid import UUID

import msgspec


class _WizardTokenPayload(msgspec.Struct, frozen=True):
    """Internal payload for wizard completion tokens."""

    wizard_id: str
    completed_at: float


class _WizardProgressPayload(msgspec.Struct, frozen=True):
    """Internal payload for wizard progress tokens.

    Tracks which steps have been validated so far. Each step validation
    extends this chain, and the final step verification checks that all
    prior steps are present.
    """

    wizard_id: str
    validated_step_ids: list[str]
    updated_at: float


def _sign_payload(payload_bytes: bytes, secret_key: str) -> str:
    """Sign a payload and return base64_payload.signature format."""
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode()
    signature = hmac.new(
        secret_key.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def _verify_signature(token: str, secret_key: str) -> tuple[bytes, bool]:
    """Verify HMAC signature and return (payload_bytes, is_valid)."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return b"", False

        payload_b64, signature = parts
        payload_bytes = base64.urlsafe_b64decode(payload_b64)

        expected_sig = hmac.new(
            secret_key.encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return b"", False

        return payload_bytes, True
    except Exception:
        return b"", False


def sign_wizard_completion(wizard_id: UUID, secret_key: str, /) -> str:
    """Create a signed wizard completion token.

    Args:
        wizard_id: The UUID of the completed wizard (positional-only).
        secret_key: The app secret key for HMAC signing (positional-only).

    Returns:
        A signed token string in the format ``base64_payload.signature``.
    """
    payload = _WizardTokenPayload(
        wizard_id=str(wizard_id),
        completed_at=time.time(),
    )
    return _sign_payload(msgspec.json.encode(payload), secret_key)


def verify_wizard_completion(
    token: str,
    expected_wizard_id: UUID,
    secret_key: str,
    /,
    *,
    max_age_seconds: int = 3600,
) -> bool:
    """Verify a signed wizard completion token.

    Checks HMAC signature validity, wizard_id match, and token age.

    Args:
        token: The signed token string (positional-only).
        expected_wizard_id: The wizard ID that must match (positional-only).
        secret_key: The app secret key for HMAC verification (positional-only).
        max_age_seconds: Maximum token age in seconds (keyword-only, default 3600).

    Returns:
        True if the token is valid, False otherwise.
    """
    try:
        payload_bytes, valid = _verify_signature(token, secret_key)
        if not valid:
            return False

        payload = msgspec.json.decode(payload_bytes, type=_WizardTokenPayload)

        if payload.wizard_id != str(expected_wizard_id):
            return False

        age = time.time() - payload.completed_at
        if age < 0 or age > max_age_seconds:
            return False

    except Exception:
        return False

    return True


def sign_wizard_progress(
    wizard_id: UUID,
    validated_step_ids: list[UUID],
    secret_key: str,
    /,
) -> str:
    """Create a signed wizard progress token.

    Encodes the set of validated step IDs so far, proving sequential
    completion. Each step validation extends this chain.

    Args:
        wizard_id: The UUID of the wizard (positional-only).
        validated_step_ids: Ordered list of validated step UUIDs (positional-only).
        secret_key: The app secret key for HMAC signing (positional-only).

    Returns:
        A signed progress token string.
    """
    payload = _WizardProgressPayload(
        wizard_id=str(wizard_id),
        validated_step_ids=[str(sid) for sid in validated_step_ids],
        updated_at=time.time(),
    )
    return _sign_payload(msgspec.json.encode(payload), secret_key)


def verify_wizard_progress(
    token: str,
    expected_wizard_id: UUID,
    secret_key: str,
    /,
    *,
    max_age_seconds: int = 3600,
) -> list[str] | None:
    """Verify a signed wizard progress token and return validated step IDs.

    Checks HMAC signature validity, wizard_id match, and token age.

    Args:
        token: The signed progress token string (positional-only).
        expected_wizard_id: The wizard ID that must match (positional-only).
        secret_key: The app secret key for HMAC verification (positional-only).
        max_age_seconds: Maximum token age in seconds (keyword-only, default 3600).

    Returns:
        List of validated step ID strings if valid, None otherwise.
    """
    try:
        payload_bytes, valid = _verify_signature(token, secret_key)
        if not valid:
            return None

        payload = msgspec.json.decode(payload_bytes, type=_WizardProgressPayload)

        if payload.wizard_id != str(expected_wizard_id):
            return None

        age = time.time() - payload.updated_at
        if age < 0 or age > max_age_seconds:
            return None

    except Exception:
        return None

    return payload.validated_step_ids
