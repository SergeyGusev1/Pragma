from datetime import UTC, datetime, timedelta
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(
    subject: str, token_type: str, expire_delta: timedelta
) -> tuple[str, str]:
    """Create a JWT token. Returns (encoded_token, jti)."""
    jti = str(uuid4())
    expire = datetime.now(UTC) + expire_delta
    payload = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    encoded = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return encoded, jti


def create_access_token(user_id: str) -> tuple[str, str]:
    """Returns (access_token, jti)."""
    return _create_token(
        subject=user_id,
        token_type="access",
        expire_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """Returns (refresh_token, jti)."""
    return _create_token(
        subject=user_id,
        token_type="refresh",
        expire_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise JWTError(str(e)) from e
