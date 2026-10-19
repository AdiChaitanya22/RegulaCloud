import os
import tempfile
import hashlib
from contextlib import contextmanager
from typing import Generator, Tuple, Dict, Any

# Ensure JWT_SECRET_KEY is present before backend imports
if not os.environ.get("JWT_SECRET_KEY"):
    os.environ["JWT_SECRET_KEY"] = "benchmark-security-key-phase6a5"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.app.core.database import Base, get_db
import backend.app.core.database as db_core
from backend.app.core.security import create_access_token, hash_password
from backend.app.db.models import User
from backend.app.main import app

NORMAL_DB_PATH = "regulacloud.db"
EXPECTED_NORMAL_DB_HASH = "fc199433c9ba866b1c654ec4ae32345dabc6a35a82864d868ce68097801fd2ef"

@contextmanager
def isolated_test_db() -> Generator[Tuple[Any, sessionmaker, str], None, None]:
    """
    Creates an isolated temporary SQLite database for security and gate benchmarks.
    Redirects both FastAPI app dependency_overrides[get_db] and db_core.SessionLocal
    so that background models and API calls use the isolated database.
    Guarantees zero mutation to the user's normal database.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    db_url = f"sqlite:///{db_path}"
    test_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    orig_bind = db_core.SessionLocal.kw.get("bind")
    db_core.SessionLocal.configure(bind=test_engine)

    def override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield test_engine, TestSessionLocal, db_path
    finally:
        app.dependency_overrides.clear()
        db_core.SessionLocal.configure(bind=orig_bind)
        test_engine.dispose()
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except OSError:
                pass

def get_auth_header(username: str = "admin", role: str = "ADMIN") -> Dict[str, str]:
    """Generates an Authorization header containing a valid signed JWT."""
    token = create_access_token({"sub": username, "role": role, "id": f"usr-{username}"})
    return {"Authorization": f"Bearer {token}"}

def create_test_user(db: Session, username: str, role: str, password: str = "Password123!") -> User:
    """Creates a user record inside the specified session."""
    user = User(
        id=f"usr-{username}-bench",
        username=username,
        email=f"{username}@benchmark.local",
        hashed_password=hash_password(password),
        role=role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def verify_normal_db_untouched() -> Tuple[bool, str]:
    """Computes SHA-256 of normal regulacloud.db and verifies zero modification."""
    if not os.path.exists(NORMAL_DB_PATH):
        return True, "NOT_FOUND"
    with open(NORMAL_DB_PATH, "rb") as f:
        current_hash = hashlib.sha256(f.read()).hexdigest()
    is_untouched = (current_hash == EXPECTED_NORMAL_DB_HASH)
    return is_untouched, current_hash
