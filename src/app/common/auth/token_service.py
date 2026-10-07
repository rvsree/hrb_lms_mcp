"""OAuth2 client-credentials token issuing/verification (2026-09-22).
Replaces the never-actually-enforced X-API-Key check on /mcp with a real
signed JWT, verified per request."""

import hashlib
from datetime import datetime, timedelta, timezone

import jwt

from src.app.common.config.app_logging import get_logger
from src.app.common.config.config import settings
from src.app.common.providers_client.db_client.postgres_db_client import get_postgres_connection

logger = get_logger("token_service")

JWT_ALGORITHM = "HS256"


def _hash_secret(client_secret: str) -> str:
    return hashlib.sha256(client_secret.encode()).hexdigest()


def verify_client_credentials(client_id: str, client_secret: str) -> list[str] | None:
    """Returns the client's scopes if client_id/client_secret are valid and
    the client is active, else None."""
    with get_postgres_connection() as conn:
        row = conn.execute(
            "SELECT client_secret_hash, scopes FROM hrb_lms_mcp_auth.oauth_clients "
            "WHERE client_id = %s AND is_active = true",
            (client_id,),
        ).fetchone()

    if row is None:
        return None

    stored_hash, scopes = row
    if _hash_secret(client_secret) != stored_hash:
        return None
    return scopes


def create_access_token(client_id: str, scopes: list[str]) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    expires_in = settings.jwt_access_token_expire_minutes * 60
    expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {"sub": client_id, "scopes": scopes, "exp": expiry}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError (ExpiredSignatureError/InvalidTokenError/...)
    on any invalid/expired token - caller decides how to respond."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
