"""Simplified tests for sharing service focusing on business logic."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from fastapi import HTTPException

from src.notemesh.core.services.sharing_service import SharingService
from src.notemesh.core.schemas.sharing import ShareRequest


class TestSharingServiceSimple:
    """Simplified tests focusing on business logic without complex schema conversion."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def sharing_service(self, mock_session):
        """Create sharing service with mocked dependencies."""
        service = SharingService(mock_session)
        service.share_repo = AsyncMock()
        service.note_repo = AsyncMock()
        service.user_repo = AsyncMock()
        return service

    @pytest.fixture
    def user_id(self):
        """Sample user ID."""
        return uuid.uuid4()

    @pytest.fixture
    def note_id(self):
        """Sample note ID."""
        return uuid.uuid4()

    @pytest.mark.asyncio
    async def test_share_note_success_calls_repo_methods(self, sharing_service, user_id, note_id):
        """Test that successful share calls appropriate repository methods."""
        shared_with_user_id = uuid.uuid4()
        request = ShareRequest(
            note_id=note_id,
            shared_with_usernames=["testuser"],
            permission_level="read"
        )

        # Mock note exists and is owned by user
        mock_note = Mock()
        mock_note.id = note_id
        mock_note.owner_id = user_id
        sharing_service.note_repo.get_by_id_and_user.return_value = mock_note

        # Mock user exists
        mock_user = Mock()
        mock_user.id = shared_with_user_id
        mock_user.username = "testuser"
        sharing_service.user_repo.get_by_username.return_value = mock_user

        # Mock no existing share
        sharing_service.share_repo.get_existing_share.return_value = None

        # Mock share creation
        mock_share = Mock()
        mock_share.id = uuid.uuid4()
        sharing_service.share_repo.create_share.return_value = mock_share

        # Stub out complex response conversion to focus on repo interactions
        sharing_service._share_to_response = Mock(return_value={"id": mock_share.id})

        # Execute
        result = await sharing_service.share_note(user_id, request)
        assert isinstance(result, list) and len(result) == 1

        # Verify repository calls were made correctly
        sharing_service.note_repo.get_by_id_and_user.assert_called_once_with(note_id, user_id)
        sharing_service.user_repo.get_by_username.assert_called_once_with("testuser")
        sharing_service.share_repo.get_existing_share.assert_called_once_with(note_id, shared_with_user_id)
        sharing_service.share_repo.create_share.assert_called_once()

    @pytest.mark.asyncio
    async def test_share_note_fails_when_note_not_found(self, sharing_service, user_id):
        """Test share creation fails when note not found."""
        request = ShareRequest(
            note_id=uuid.uuid4(),
            shared_with_usernames=["testuser"],
            permission_level="read"
        )

        # Mock note not found
        sharing_service.note_repo.get_by_id_and_user.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await sharing_service.share_note(user_id, request)

        assert exc_info.value.status_code == 404
        assert "Note not found or not owned by user" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_share_note_fails_when_user_not_found(self, sharing_service, user_id, note_id):
        """Test share creation fails when target user not found."""
        request = ShareRequest(
            note_id=note_id,
            shared_with_usernames=["nonexistent"],
            permission_level="read"
        )

        # Mock note exists
        mock_note = Mock()
        mock_note.id = note_id
        mock_note.owner_id = user_id
        sharing_service.note_repo.get_by_id_and_user.return_value = mock_note

        # Mock user not found
        sharing_service.user_repo.get_by_username.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await sharing_service.share_note(user_id, request)

        assert exc_info.value.status_code == 404
        assert "User 'nonexistent' not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_share_note_fails_when_sharing_with_self(self, sharing_service, user_id, note_id):
        """Test share creation fails when trying to share with self."""
        request = ShareRequest(
            note_id=note_id,
            shared_with_usernames=["self_user"],
            permission_level="read"
        )

        # Mock note exists
        mock_note = Mock()
        mock_note.id = note_id
        mock_note.owner_id = user_id
        sharing_service.note_repo.get_by_id_and_user.return_value = mock_note

        # Mock user exists but is the same as requesting user
        mock_user = Mock()
        mock_user.id = user_id  # Same as user_id
        mock_user.username = "self_user"
        sharing_service.user_repo.get_by_username.return_value = mock_user

        with pytest.raises(HTTPException) as exc_info:
            await sharing_service.share_note(user_id, request)

        assert exc_info.value.status_code == 400
        assert "Cannot share note with yourself" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_revoke_share_calls_repository(self, sharing_service, user_id):
        """Test share revocation calls repository method."""
        share_id = uuid.uuid4()

        sharing_service.share_repo.delete_share.return_value = True

        result = await sharing_service.revoke_share(user_id, share_id)

        assert result is True
        sharing_service.share_repo.delete_share.assert_called_once_with(share_id, user_id)

    @pytest.mark.asyncio
    async def test_get_shared_note_fails_when_no_access(self, sharing_service, user_id):
        """Test getting shared note fails when user has no access."""
        note_id = uuid.uuid4()

        # Mock no access
        sharing_service.share_repo.check_note_access.return_value = {"can_read": False}

        with pytest.raises(HTTPException) as exc_info:
            await sharing_service.get_shared_note(note_id, user_id)

        assert exc_info.value.status_code == 404
        assert "Note not found" in str(exc_info.value.detail)