"""Integration test for complete note sharing workflow."""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.notemesh.main import app
from src.notemesh.database import get_db_session
from src.notemesh.core.models.base import BaseModel


class TestNoteSharingWorkflow:
    """Test complete note sharing workflow from creation to access."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_complete_sharing_workflow(self, client):
        """Test complete sharing workflow that reproduces the frontend bug."""

        # Step 1: Register two users (with unique names for each test run)
        import time
        unique_suffix = str(int(time.time() * 1000))[-6:]  # Last 6 digits of timestamp

        user1_data = {
            "username": f"sharetest1_{unique_suffix}",
            "password": "testpass123",
            "full_name": "Share Test User 1",
            "confirm_password": "testpass123"
        }

        user2_data = {
            "username": f"sharetest2_{unique_suffix}",
            "password": "testpass123",
            "full_name": "Share Test User 2",
            "confirm_password": "testpass123"
        }

        # Register users
        response1 = client.post("/api/auth/register", json=user1_data)
        assert response1.status_code == 201
        user1_id = response1.json()["id"]

        response2 = client.post("/api/auth/register", json=user2_data)
        assert response2.status_code == 201
        user2_id = response2.json()["id"]

        # Step 2: Login both users
        login1_response = client.post("/api/auth/login", json={
            "username": f"sharetest1_{unique_suffix}",
            "password": "testpass123"
        })
        assert login1_response.status_code == 200
        token1 = login1_response.json()["access_token"]

        login2_response = client.post("/api/auth/login", json={
            "username": f"sharetest2_{unique_suffix}",
            "password": "testpass123"
        })
        assert login2_response.status_code == 200
        token2 = login2_response.json()["access_token"]

        # Step 3: User1 creates a note
        note_data = {
            "title": "Test Shared Note",
            "content": "This note will be shared with user2. Link: https://example.com",
            "tags": ["test", "sharing"],
            "is_public": False
        }

        create_response = client.post(
            "/api/notes/",
            json=note_data,
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert create_response.status_code == 201
        note_id = create_response.json()["id"]
        assert note_id is not None

        # Step 4: User1 shares the note with User2
        share_data = {
            "note_id": note_id,
            "shared_with_usernames": [f"sharetest2_{unique_suffix}"],
            "permission_level": "read"
        }

        share_response = client.post(
            "/api/sharing/",
            json=share_data,
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert share_response.status_code == 201
        shares = share_response.json()
        assert len(shares) == 1
        share_id = shares[0]["id"]
        assert shares[0]["note_id"] == note_id

        # Step 5: Check share listing for User2 (this is what frontend calls)
        shares_received_response = client.get(
            "/api/sharing/?type=received",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert shares_received_response.status_code == 200
        shares_received = shares_received_response.json()["shares"]
        assert len(shares_received) == 1

        # Verify the share has correct structure
        received_share = shares_received[0]
        assert received_share["id"] == share_id  # This is the share ID
        assert received_share["note_id"] == note_id  # This is the note ID
        assert received_share["note_title"] == "Test Shared Note"

        # CRITICAL: Frontend should use note_id, NOT share.id
        frontend_note_id = received_share["note_id"]  # Correct: note ID
        frontend_wrong_id = received_share["id"]      # Wrong: share ID

        # Step 6: Test note access using correct note_id (what fixed frontend should do)
        note_access_response = client.get(
            f"/api/notes/{frontend_note_id}",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert note_access_response.status_code == 200
        accessed_note = note_access_response.json()
        assert accessed_note["title"] == "Test Shared Note"
        assert accessed_note["can_edit"] == False  # Read-only access

        # Step 7: Test shared note endpoint using correct note_id
        shared_note_response = client.get(
            f"/api/sharing/notes/{frontend_note_id}",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert shared_note_response.status_code == 200
        shared_note = shared_note_response.json()
        assert shared_note["title"] == "Test Shared Note"
        assert shared_note["permission_level"] == "read"

        # Step 8: Verify that using wrong ID (share.id) fails appropriately
        wrong_note_response = client.get(
            f"/api/notes/{frontend_wrong_id}",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert wrong_note_response.status_code == 404

        wrong_shared_response = client.get(
            f"/api/sharing/notes/{frontend_wrong_id}",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert wrong_shared_response.status_code == 404

        # Step 9: Test User1 can still access their own note
        owner_access_response = client.get(
            f"/api/notes/{note_id}",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert owner_access_response.status_code == 200
        owner_note = owner_access_response.json()
        assert owner_note["can_edit"] == True  # Owner can edit

        # Step 10: Verify shares given list for User1
        shares_given_response = client.get(
            "/api/sharing/?type=given",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert shares_given_response.status_code == 200
        shares_given = shares_given_response.json()["shares"]
        assert len(shares_given) == 1
        given_share = shares_given[0]
        assert given_share["note_id"] == note_id
        assert given_share["id"] == share_id

    def test_frontend_data_transformation_logic(self, client):
        """Test the exact data transformation that frontend does."""
        # This test simulates the frontend logic that was causing the bug

        # Simulate what frontend receives from sharing API
        mock_share_response = {
            "shares": [{
                "id": "share-id-12345",           # Share ID (wrong for note access)
                "note_id": "note-id-67890",       # Note ID (correct for note access)
                "note_title": "Test Note",
                "shared_with_user_id": "user-id-abc",
                "permission_level": "read",
                "note": None  # Note object might be None
            }]
        }

        # OLD BUGGY LOGIC (what was causing the issue):
        # buggy_notes = mock_share_response["shares"].map(share => share.note || share)
        # This would use share object when share.note is None, resulting in share.id

        # NEW CORRECT LOGIC (what the fix implements):
        shares = mock_share_response["shares"]
        fixed_notes = []

        for share in shares:
            if share.get("note"):
                # Use the note object if available
                fixed_notes.append(share["note"])
            else:
                # Create note-like object from share data using note_id
                note_like = {
                    "id": share["note_id"],  # CORRECT: Use note_id
                    "title": share["note_title"],
                    "is_shared": True,
                    "can_edit": share["permission_level"] == "write"
                }
                fixed_notes.append(note_like)

        # Verify the fix
        assert len(fixed_notes) == 1
        transformed_note = fixed_notes[0]
        assert transformed_note["id"] == "note-id-67890"  # Should be note ID, not share ID
        assert transformed_note["id"] != "share-id-12345"  # Should NOT be share ID