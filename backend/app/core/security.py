import hashlib
import hmac
import base64
import json
import time
import os
import warnings
from typing import Dict, Any, Optional

_env_secret = os.getenv("JWT_SECRET_KEY", "")
if not _env_secret:
    raise ValueError("FATAL CONFIGURATION ERROR: JWT_SECRET_KEY environment variable is missing. It MUST be set in all environments.")
SECRET_KEY = _env_secret

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 # 24 hours

def hash_password(password: str, salt: Optional[str] = None) -> str:
    if not salt:
        salt = base64.b64encode(os.urandom(16)).decode("utf-8")
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    )
    return f"{salt}${base64.b64encode(key).decode('utf-8')}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt, key_b64 = hashed_password.split("$", 1)
        expected_key = base64.b64decode(key_b64)
        actual_key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            100000
        )
        return hmac.compare_digest(expected_key, actual_key)
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[int] = None) -> str:
    to_encode = data.copy()
    expire = int(time.time()) + (expires_delta or ACCESS_TOKEN_EXPIRE_SECONDS)
    to_encode.update({"exp": expire})
    
    header = {"alg": ALGORITHM, "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(to_encode).encode()).decode().rstrip("=")
    
    signature = hmac.new(
        SECRET_KEY.encode(),
        f"{header_b64}.{payload_b64}".encode(),
        hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        
        expected_sig = hmac.new(
            SECRET_KEY.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()
        
        # Add padding back if necessary
        sig_padding = len(sig_b64) % 4
        padded_sig = sig_b64 + ("=" * (4 - sig_padding) if sig_padding else "")
        actual_sig = base64.urlsafe_b64decode(padded_sig)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
            
        payload_padding = len(payload_b64) % 4
        padded_payload = payload_b64 + ("=" * (4 - payload_padding) if payload_padding else "")
        payload_json = base64.urlsafe_b64decode(padded_payload).decode("utf-8")
        payload = json.loads(payload_json)
        
        if payload.get("exp", 0) < time.time():
            return None
            
        return payload
    except Exception:
        return None
