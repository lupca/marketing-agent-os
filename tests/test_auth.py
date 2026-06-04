# tests/test_auth.py
import os
import sys
import uuid
import pytest
from fastapi import FastAPI, Depends, status, Request
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.auth import hash_password, verify_password, create_access_token, decode_access_token
from core.dependencies import get_current_user, get_current_admin_user, get_current_workspace, get_db
from core.models import User, Workspace
from app import fastapi_app

# ──────────────────────────────────────────────────────────
# Cryptographic and JWT Token Tests
# ──────────────────────────────────────────────────────────

def test_password_hashing():
    password = "supersecretpassword123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_jwt_token_flow():
    token_payload = {"sub": "user_id_test", "email": "test@example.com", "role": "member"}
    token = create_access_token(data=token_payload)
    assert isinstance(token, str)

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user_id_test"
    assert decoded["email"] == "test@example.com"
    assert decoded["role"] == "member"
    assert "exp" in decoded

def test_jwt_invalid_token():
    assert decode_access_token("invalid.token.value") is None
    assert decode_access_token("") is None

# ──────────────────────────────────────────────────────────
# API Endpoint Integration Tests
# ──────────────────────────────────────────────────────────

@pytest.fixture
def client(db_session):
    """
    TestClient fixture that automatically operates within the transactional
    db_session context created by conftest.py.
    """
    with TestClient(fastapi_app) as c:
        yield c

def test_register_user_success(client, db_session):
    register_payload = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "securepassword123"
    }
    response = client.post("/api/auth/register", json=register_payload)
    assert response.status_code == status.HTTP_201_CREATED
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["name"] == "Jane Doe"
    assert data["user"]["email"] == "jane@example.com"
    assert data["user"]["role"] == "member"
    
    # Assert database state
    user_id = uuid.UUID(data["user"]["id"])
    db_user = db_session.query(User).filter_by(id=user_id).first()
    assert db_user is not None
    assert db_user.name == "Jane Doe"
    assert verify_password("securepassword123", db_user.password_hash)

    # Assert default workspace is created and has native UUID inside members
    db_workspace = db_session.query(Workspace).filter_by(owner_id=user_id).first()
    assert db_workspace is not None
    assert db_workspace.name == "Jane Doe's Workspace"
    assert db_workspace.owner_id == user_id
    
    # Verify members contains the user ID
    # Since members is stored as array/list of UUIDs
    assert user_id in db_workspace.members or str(user_id) in [str(m) for m in db_workspace.members]
    # Check it specifically matches the type check in db/seed.py
    assert isinstance(db_workspace.members[0], uuid.UUID) or str(db_workspace.members[0]) == str(user_id)

def test_register_duplicate_email(client):
    register_payload = {
        "name": "Jane Doe",
        "email": "duplicate@example.com",
        "password": "securepassword123"
    }
    # Register once
    response = client.post("/api/auth/register", json=register_payload)
    assert response.status_code == status.HTTP_201_CREATED

    # Register again with duplicate email
    response2 = client.post("/api/auth/register", json=register_payload)
    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response2.json()["detail"]

def test_register_invalid_email(client):
    register_payload = {
        "name": "Invalid Email User",
        "email": "invalid-email-format",
        "password": "securepassword123"
    }
    response = client.post("/api/auth/register", json=register_payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_login_user_json_success(client):
    register_payload = {
        "name": "Login User JSON",
        "email": "login_json@example.com",
        "password": "mysecretpassword"
    }
    # Create user
    client.post("/api/auth/register", json=register_payload)

    # Login
    login_payload = {
        "email": "login_json@example.com",
        "password": "mysecretpassword"
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login_json@example.com"

def test_login_user_form_urlencoded_success(client):
    register_payload = {
        "name": "Login User Form",
        "email": "login_form@example.com",
        "password": "myformpassword"
    }
    # Create user
    client.post("/api/auth/register", json=register_payload)

    # Login using Form-urlencoded
    form_data = {
        "username": "login_form@example.com",
        "password": "myformpassword"
    }
    response = client.post(
        "/api/auth/login",
        data=form_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login_form@example.com"

def test_login_invalid_credentials(client):
    login_payload = {
        "email": "nonexistent@example.com",
        "password": "somepassword"
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect email or password" in response.json()["detail"]

def test_get_profile_me_success(client):
    register_payload = {
        "name": "Profile User",
        "email": "profile@example.com",
        "password": "profilepassword"
    }
    register_res = client.post("/api/auth/register", json=register_payload).json()
    token = register_res["access_token"]

    # Retrieve profile
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "profile@example.com"
    assert data["name"] == "Profile User"

def test_get_profile_me_unauthorized(client):
    response = client.get("/api/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

# ──────────────────────────────────────────────────────────
# Security Dependency Tests
# ──────────────────────────────────────────────────────────

# Setup dummy app to isolate dependency resolution testing
dummy_app = FastAPI()

@dummy_app.get("/test/workspace")
async def route_test_workspace(ws: Workspace = Depends(get_current_workspace)):
    return {"workspace_id": str(ws.id), "name": ws.name}

@dummy_app.get("/test/admin")
async def route_test_admin(user: User = Depends(get_current_admin_user)):
    return {"admin_id": str(user.id)}

@pytest.fixture
def dummy_client(db_session):
    with TestClient(dummy_app) as c:
        yield c

def test_get_current_admin_user_restricted(dummy_client, db_session):
    # Register non-admin user
    new_user = User(
        id=uuid.uuid4(),
        name="Regular User",
        email="regular@example.com",
        password_hash=hash_password("password"),
        role="member"
    )
    db_session.add(new_user)
    db_session.commit()
    db_session.refresh(new_user)

    token = create_access_token(data={"sub": str(new_user.id), "email": new_user.email, "role": new_user.role})
    
    # Try accessing admin-only endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = dummy_client.get("/test/admin", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_get_current_admin_user_allowed(dummy_client, db_session):
    # Register admin user
    admin_user = User(
        id=uuid.uuid4(),
        name="Admin User",
        email="admin_test@example.com",
        password_hash=hash_password("password"),
        role="admin"
    )
    db_session.add(admin_user)
    db_session.commit()
    db_session.refresh(admin_user)

    token = create_access_token(data={"sub": str(admin_user.id), "email": admin_user.email, "role": admin_user.role})
    
    # Access admin-only endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = dummy_client.get("/test/admin", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["admin_id"] == str(admin_user.id)

def test_get_current_workspace_ownership(dummy_client, db_session):
    # Create user
    user = User(
        id=uuid.uuid4(),
        name="Workspace Owner",
        email="owner@example.com",
        password_hash=hash_password("password"),
        role="member"
    )
    db_session.add(user)
    db_session.flush()

    # Create workspace owned by user
    ws = Workspace(
        id=uuid.uuid4(),
        name="Owner's Workspace",
        owner_id=user.id,
        members=[user.id],
        settings={}
    )
    db_session.add(ws)
    db_session.commit()

    token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
    
    # Request access with workspace_id parameter
    headers = {"Authorization": f"Bearer {token}"}
    response = dummy_client.get(f"/test/workspace?workspace_id={str(ws.id)}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["workspace_id"] == str(ws.id)

def test_get_current_workspace_forbidden(dummy_client, db_session):
    # Create user 1 (workspace owner)
    user1 = User(id=uuid.uuid4(), name="Owner", email="o@example.com", password_hash=hash_password("pw"))
    # Create user 2 (attacker/stranger)
    user2 = User(id=uuid.uuid4(), name="Stranger", email="s@example.com", password_hash=hash_password("pw"))
    db_session.add_all([user1, user2])
    db_session.flush()

    # Create workspace owned by user 1
    ws = Workspace(
        id=uuid.uuid4(),
        name="Private Workspace",
        owner_id=user1.id,
        members=[user1.id],
        settings={}
    )
    db_session.add(ws)
    db_session.commit()

    # User 2 tries to access User 1's workspace
    token2 = create_access_token(data={"sub": str(user2.id), "email": user2.email, "role": user2.role})
    headers = {"Authorization": f"Bearer {token2}"}
    response = dummy_client.get(f"/test/workspace?workspace_id={str(ws.id)}", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
