# tests/test_workspace_routes.py
import os
import sys
import uuid
import pytest
from fastapi import status
from fastapi.testclient import TestClient

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.auth import hash_password, create_access_token
from core.models import User, Workspace
from app import fastapi_app

@pytest.fixture
def client(db_session):
    with TestClient(fastapi_app) as c:
        yield c

def test_workspace_list_unauthenticated(client):
    response = client.get("/api/workspace/list")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_workspace_list_authenticated_scoping(client, db_session):
    # Create User A and User B
    user_a = User(
        id=uuid.uuid4(),
        name="User A",
        email="usera@example.com",
        password_hash=hash_password("password"),
        role="member"
    )
    user_b = User(
        id=uuid.uuid4(),
        name="User B",
        email="userb@example.com",
        password_hash=hash_password("password"),
        role="member"
    )
    db_session.add_all([user_a, user_b])
    db_session.flush()

    # Create workspaces
    ws_a = Workspace(
        id=uuid.uuid4(),
        name="Workspace A",
        owner_id=user_a.id,
        members=[user_a.id],
        settings={}
    )
    ws_b = Workspace(
        id=uuid.uuid4(),
        name="Workspace B",
        owner_id=user_b.id,
        members=[user_b.id],
        settings={}
    )
    db_session.add_all([ws_a, ws_b])
    db_session.commit()

    # User A token
    token_a = create_access_token(data={"sub": str(user_a.id), "email": user_a.email, "role": user_a.role})
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Fetch workspace list as User A
    response = client.get("/api/workspace/list", headers=headers_a)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    
    # User A should only see Workspace A, not Workspace B
    workspaces = data["data"]
    workspace_ids = [w["id"] for w in workspaces]
    assert str(ws_a.id) in workspace_ids
    assert str(ws_b.id) not in workspace_ids

def test_workspace_settings_unauthorized_forbidden(client, db_session):
    # Create User A and User B
    user_a = User(
        id=uuid.uuid4(),
        name="User A",
        email="usera_settings@example.com",
        password_hash=hash_password("password"),
        role="member"
    )
    user_b = User(
        id=uuid.uuid4(),
        name="User B",
        email="userb_settings@example.com",
        password_hash=hash_password("password"),
        role="member"
    )
    db_session.add_all([user_a, user_b])
    db_session.flush()

    # Create workspaces
    ws_a = Workspace(
        id=uuid.uuid4(),
        name="Workspace A",
        owner_id=user_a.id,
        members=[user_a.id],
        settings={"ai_model": "gpt-4"}
    )
    ws_b = Workspace(
        id=uuid.uuid4(),
        name="Workspace B",
        owner_id=user_b.id,
        members=[user_b.id],
        settings={"ai_model": "claude-3"}
    )
    db_session.add_all([ws_a, ws_b])
    db_session.commit()

    # User A token
    token_a = create_access_token(data={"sub": str(user_a.id), "email": user_a.email, "role": user_a.role})
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Access Workspace A settings as User A - should succeed
    response_a = client.get(f"/api/workspace/settings?workspace_id={str(ws_a.id)}", headers=headers_a)
    assert response_a.status_code == status.HTTP_200_OK

    # Access Workspace B settings as User A - should be forbidden (403)
    response_b = client.get(f"/api/workspace/settings?workspace_id={str(ws_b.id)}", headers=headers_a)
    assert response_b.status_code == status.HTTP_403_FORBIDDEN
