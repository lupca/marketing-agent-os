# core/dependencies.py
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy.orm import Session
from db.connection import SessionLocal
import logging
import uuid
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from core.models import User, Workspace

logger = logging.getLogger(__name__)

def get_db_base() -> Generator[Session, None, None]:
    """
    Base generator for database sessions.
    Used by FastAPI dependencies and the context manager.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions (for manual use).
    Usage:
        with get_session() as db:
            # do work
            db.commit()
    """
    # Simply wrap the base generator
    yield from get_db_base()

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.
    Usage:
        @app.get("/")
        def index(db: Session = Depends(get_db)):
            ...
    """
    yield from get_db_base()

# OAuth2PasswordBearer defines where FastAPI looks for the Bearer token in the request.
# auto_error is False so that we can handle custom error messaging.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

async def get_current_user(db: Session = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme)) -> User:
    """
    FastAPI dependency to retrieve the authenticated user from the JWT token.
    Raises 401 Unauthorized if verification or lookup fails.
    """
    from core.auth import decode_access_token  # Deferred import to prevent potential circular imports
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise credentials_exception
    
    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        raise credentials_exception
        
    return user

async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to restrict endpoint access to users with the 'admin' role.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted to administrators",
        )
    return current_user

async def get_current_workspace(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Workspace:
    """
    Dependency to verify if the authenticated user has access to the requested workspace.
    Checks if the user is owner or member of the active workspace.
    """
    ws_id_str = request.query_params.get("workspace_id") or request.headers.get("x-workspace-id")
    if not ws_id_str:
        # Retrieve default workspace or first workspace user owns/members in
        ws = db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
        if ws and (ws.owner_id == current_user.id or str(current_user.id) in [str(m) for m in ws.members]):
            return ws
        
        ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
        if ws:
            return ws
            
        # Fallback to check members arrays on all workspaces
        workspaces = db.query(Workspace).all()
        for w in workspaces:
            if str(current_user.id) in [str(m) for m in w.members]:
                return w
                
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No accessible workspace found for user",
        )

    try:
        ws_uuid = uuid.UUID(ws_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format",
        )

    ws = db.query(Workspace).filter(Workspace.id == ws_uuid).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Authorization check
    is_owner = ws.owner_id == current_user.id
    is_member = str(current_user.id) in [str(m) for m in ws.members]
    
    if not (is_owner or is_member):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this workspace is forbidden",
        )
        
    return ws



