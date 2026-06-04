# api/auth_routes.py
import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, field_validator

from core.dependencies import get_db, get_current_user
from core.models import User, Workspace
from core.auth import hash_password, verify_password, create_access_token

auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])

# Regex for email validation (used because email-validator package may not be installed in current env)
EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

# ──────────────────────────────────────────────────────────
# Pydantic Schemas
# ──────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class UserRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Full name of the user")
    email: str = Field(..., min_length=3, max_length=255, description="Email address")
    password: str = Field(..., min_length=6, max_length=100, description="Password (min 6 characters)")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(EMAIL_REGEX, v):
            raise ValueError("Invalid email format")
        return v.lower().strip()

# ──────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────

@auth_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: Session = Depends(get_db)):
    """
    Registers a new user, automatically provisions a default workspace for them,
    and returns a JWT token.
    """
    # 1. Check if user already exists
    existing_user = db.query(User).filter(func.lower(User.email) == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists"
        )

    try:
        # 2. Create the user
        new_user = User(
            id=uuid.uuid4(),
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role="member"  # default role for registered users
        )
        db.add(new_user)
        db.flush()  # Acquire the new user's ID without committing yet

        # 3. Create a default workspace for the user
        # (Settings default to standard local configuration as defined in seed.py)
        default_settings = {
            "currency": "VND",
            "timezone": "Asia/Ho_Chi_Minh",
            "ai_api_url": "https://api.siliconflow.com/v1",
            "ai_model": "Qwen/Qwen3.6-35B-A3B",
            "embed_model": "Qwen/Qwen3-Embedding-0.6B",
            "rerank_model": "Qwen/Qwen3-Reranker-0.6B"
        }

        default_workspace = Workspace(
            id=uuid.uuid4(),
            name=f"{new_user.name}'s Workspace",
            owner_id=new_user.id,
            members=[new_user.id],  # Use native UUID object
            settings=default_settings
        )
        db.add(default_workspace)

        # 4. Commit both operations atomically
        db.commit()
        db.refresh(new_user)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during registration: {str(e)}"
        )

    # 5. Generate and return access token
    token_data = {"sub": str(new_user.id), "email": new_user.email, "role": new_user.role}
    access_token = create_access_token(data=token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": new_user
    }


@auth_router.post("/login", response_model=TokenResponse)
async def login(request: Request, db: Session = Depends(get_db)):
    """
    Authenticate a user and return a JWT.
    Supports both OAuth2 password request form (form data) and custom JSON payload.
    """
    content_type = request.headers.get("content-type", "")
    email = None
    password = None

    # Handle standard form data login (used by Swagger UI OAuth2 password bearer)
    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        email = form_data.get("username")
        password = form_data.get("password")
    # Handle JSON login (used by custom API clients/frontend)
    else:
        try:
            body = await request.json()
            email = body.get("email") or body.get("username")
            password = body.get("password")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request payload format"
            )

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email/username and password are required"
        )

    # Clean the email to check case-insensitive match
    clean_email = email.lower().strip()

    # Query the user
    user = db.query(User).filter(func.lower(User.email) == clean_email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate token
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role}
    access_token = create_access_token(data=token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@auth_router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Retrieves the currently authenticated user's profile details.
    Protected by the JWT security dependency.
    """
    return current_user
