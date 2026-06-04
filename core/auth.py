# core/auth.py
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt

# Monkeypatch bcrypt and passlib to avoid ValueError with bcrypt >= 4.0.0
try:
    import bcrypt
    orig_hashpw = bcrypt.hashpw
    def patched_hashpw(password, salt):
        if password and len(password) > 72:
            password = password[:72]
        return orig_hashpw(password, salt)
    bcrypt.hashpw = patched_hashpw
except Exception:
    pass

try:
    import passlib.handlers.bcrypt
    orig_detect_wrap_bug = passlib.handlers.bcrypt.detect_wrap_bug
    def patched_detect_wrap_bug(ident):
        try:
            return orig_detect_wrap_bug(ident)
        except ValueError:
            # Newer bcrypt raises ValueError on >72 bytes, so it doesn't have the wrap bug.
            return False
    passlib.handlers.bcrypt.detect_wrap_bug = patched_detect_wrap_bug
except Exception:
    pass

from passlib.context import CryptContext

# CryptContext configuration for password hashing.
# Standardizes on bcrypt. passlib handles automatic salting.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration variables loaded from the environment with sensible defaults for development.
# Security warning: Ensure high entropy keys are set in production via env.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super_secret_jwt_key_marketing_agent_os_2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # Default: 24 hours (1440 minutes)

def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a JSON Web Token (JWT) with the specified payload and expiration.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Standardize the 'exp' claim with UTC timezone-aware timestamp
    to_encode.update({"exp": int(expire.timestamp())})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT.
    Returns the payload dict if valid, or None if expired/invalid.
    """
    try:
        # Security measure: Specifying the exact algorithm in decode to prevent algorithm confusion attacks.
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        # Token has expired
        return None
    except jwt.InvalidTokenError:
        # Token is invalid (signature failure, malformed, etc.)
        return None
