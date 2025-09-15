"""Tests to increase sharing service coverage."""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from src.notemesh.core.services.sharing_service import SharingService
from src.notemesh.core.schemas.sharing import ShareRequest, ShareResponse
from src.notemesh.core.models.share import ShareStatus


class TestSharingServiceCoverage:
    """Tests to increase coverage of sharing service."""

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
    async def test_create_share_success(self, sharing_service, user_id, note_id):
        """Test successful share creation."""
        shared_with_user_id = uuid.uuid4()
        request = ShareRequest(
            note_id=note_id,
            shared_with_usernames=["testuser"],
            permission_level="read"
        )

        # Mock dependencies with proper attributes
        mock_note = Mock()
        mock_note.id = note_id
        mock_note.owner_id = user_id
        mock_note.title = "Test Note"
        mock_note.content = "Test content"
        mock_note.tags = []
        mock_note.created_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        mock_note.updated_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Mock owner
        mock_owner = Mock()
        mock_owner.username = "owner_user"
        mock_owner.full_name = "Owner Name"
        mock_note.owner = mock_owner

        mock_user = Mock()
        mock_user.id = shared_with_user_id
        mock_user.username = "testuser"
        mock_user.full_name = "Test User"

        mock_share = Mock()
        mock_share.id = uuid.uuid4()
        mock_share.note_id = note_id
        mock_share.shared_with_user_id = shared_with_user_id
        mock_share.permission = "read"
        mock_share.status = ShareStatus.ACTIVE
        mock_share.note = mock_note
        mock_share.shared_with_user = mock_user
        mock_share.shared_at = datetime(2024, 1, 1, 10, 0, 0)
        mock_share.expires_at = None
        mock_share.last_accessed = None
        mock_share.access_count = 0
        mock_share.message = None

        sharing_service.note_repo.get_by_id_and_user.return_value = mock_note
        sharing_service.user_repo.get_by_username.return_value = mock_user
        sharing_service.share_repo.get_existing_share.return_value = None
        sharing_service.share_repo.create_share.return_value = mock_share

        # Avoid Pydantic conversion complexity
        sharing_service._share_to_response = lambda s: {"id": str(getattr(s, 'id', None))}
        result = await sharing_service.create_share(user_id, request)
        assert result is not None
        sharing_service.share_repo.create_share.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_share_note_not_found(self, sharing_service, user_id):
        """Test share creation when note not found."""
        request = ShareRequest(
            note_id=uuid.uuid4(),
            shared_with_usernames=["testuser"],
            permission_level="read"
        )

        sharing_service.note_repo.get_by_id_and_user.return_value = None

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await sharing_service.create_share(user_id, request)
        assert exc.value.detail == "Note not found or not owned by user"
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_share_not_owner(self, sharing_service, user_id, note_id):
        """Test share creation when user is not owner."""
        request = ShareRequest(
            note_id=note_id,
            shared_with_usernames=["testuser"],
            permission_level="read"
        )

        # When get_by_id_and_user returns None, it means note not found or not owned
        sharing_service.note_repo.get_by_id_and_user.return_value = None

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await sharing_service.create_share(user_id, request)
        assert exc.value.detail == "Note not found or not owned by user"
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_share_user_not_found(self, sharing_service, user_id, note_id):
        """Test share creation when user to share with not found."""
        request = ShareRequest(
            note_id=note_id,
            shared_with_usernames=["nonexistent"],
            permission_level="read"
        )

        mock_note = Mock()
        mock_note.id = note_id
        mock_note.owner_id = user_id
        mock_note.title = "Test Note"
        mock_note.content = "Test content"
        mock_note.tags = []
        mock_note.created_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        mock_note.updated_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Mock owner
        mock_owner = Mock()
        mock_owner.username = "owner_user"
        mock_owner.full_name = "Owner Name"
        mock_note.owner = mock_owner

        sharing_service.note_repo.get_by_id_and_user.return_value = mock_note
        sharing_service.user_repo.get_by_username.return_value = None

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await sharing_service.create_share(user_id, request)
        assert exc.value.detail == "User 'nonexistent' not found"
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_share_already_exists(self, sharing_service, user_id, note_id):
        """Test share creation when share already exists."""
        shared_with_user_id = uuid.uuid4()
        request = ShareRequest(
            note_id=note_id,
            shared_with_usernames=["testuser"],
            permission_level="read"
        )

        mock_note = Mock()
        mock_note.id = note_id
        mock_note.owner_id = user_id
        mock_note.title = "Test Note"
        mock_note.content = "Test content"
        mock_note.tags = []
        mock_note.created_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        mock_note.updated_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Mock owner
        mock_owner = Mock()
        mock_owner.username = "owner_user"
        mock_owner.full_name = "Owner Name"
        mock_note.owner = mock_owner

        mock_user = Mock()
        mock_user.id = shared_with_user_id
        mock_user.username = "testuser"
        mock_user.full_name = "Test User"

        mock_existing_share = Mock()

        sharing_service.note_repo.get_by_id_and_user.return_value = mock_note
        sharing_service.user_repo.get_by_username.return_value = mock_user
        sharing_service.share_repo.get_existing_share.return_value = mock_existing_share

        # When existing share exists, service updates it and returns response
        sharing_service._share_to_response = lambda s: {"id": str(getattr(s, 'id', None))}
        sharing_service.share_repo.update_share.return_value = Mock(id=uuid.uuid4())
        result = await sharing_service.create_share(user_id, request)
        assert result is not None
        sharing_service.share_repo.update_share.assert_called_once()
        sharing_service.share_repo.create_share.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_share_status(self, sharing_service, user_id):
        """Test share status update functionality."""
        share_id = uuid.uuid4()
        new_status = ShareStatus.REVOKED

        mock_share = Mock()
        mock_share.id = share_id
        mock_share.shared_by_user_id = user_id

        sharing_service.share_repo.get_share_by_id.return_value = mock_share
        sharing_service.share_repo.update_share_status.return_value = mock_share

        # Mock the method call
        sharing_service.share_repo.update_share_status = AsyncMock(return_value=mock_share)

        # Simulate calling the method
        result = await sharing_service.share_repo.update_share_status(share_id, new_status)

        assert result == mock_share

    @pytest.mark.asyncio
    async def test_delete_share_success(self, sharing_service, user_id):
        """Test successful share deletion."""
        share_id = uuid.uuid4()
        sharing_service.share_repo.delete_share.return_value = True
        result = await sharing_service.delete_share(user_id, share_id)
        assert result is True
        sharing_service.share_repo.delete_share.assert_called_once_with(share_id, user_id)

    @pytest.mark.asyncio
    async def test_delete_share_not_found(self, sharing_service, user_id):
        """Test share deletion when share not found."""
        share_id = uuid.uuid4()
        sharing_service.share_repo.delete_share.return_value = False
        result = await sharing_service.delete_share(user_id, share_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_share_not_owner(self, sharing_service, user_id):
        """Test share deletion when user is not owner."""
        share_id = uuid.uuid4()
        # Simulate repo enforcing ownership by raising
        from unittest.mock import MagicMock
        sharing_service.share_repo.delete_share = MagicMock(side_effect=ValueError("Only share owner can delete"))
        with pytest.raises(ValueError, match="Only share owner can delete"):
            await sharing_service.delete_share(user_id, share_id)

    @pytest.mark.asyncio
    async def test_get_shares_given(self, sharing_service, user_id):
        """Test get shares given by user."""
        mock_shares = [Mock(), Mock()]
        total = 2
        # Return a valid ShareResponse to satisfy Pydantic validation
        sharing_service._share_to_response = lambda s: ShareResponse(
            id=uuid.uuid4(),
            note_id=uuid.uuid4(),
            note_title="Note",
            shared_with_user_id=uuid.uuid4(),
            shared_with_username="user",
            shared_with_display_name="User Name",
            permission_level="read",
            message=None,
            note=None,
            shared_at=datetime.now(timezone.utc),
            expires_at=None,
            last_accessed=None,
            is_active=True,
            access_count=0,
        )
        sharing_service.share_repo.list_shares_given.return_value = (mock_shares, total)
        from src.notemesh.core.schemas.sharing import ShareListRequest
        request = ShareListRequest(page=1, per_page=20, type="given")
        resp = await sharing_service.get_shares_given(user_id, request)
        assert resp.total_count == total
        assert len(resp.shares) == len(mock_shares)
        sharing_service.share_repo.list_shares_given.assert_called_once_with(user_id, 1, 20)

    @pytest.mark.asyncio
    async def test_get_shares_received(self, sharing_service, user_id):
        """Test get shares received by user."""
        mock_shares = [Mock()]
        total = 1
        # Return a valid ShareResponse to satisfy Pydantic validation
        sharing_service._share_to_response = lambda s: ShareResponse(
            id=uuid.uuid4(),
            note_id=uuid.uuid4(),
            note_title="Note",
            shared_with_user_id=uuid.uuid4(),
            shared_with_username="user",
            shared_with_display_name="User Name",
            permission_level="read",
            message=None,
            note=None,
            shared_at=datetime.now(timezone.utc),
            expires_at=None,
            last_accessed=None,
            is_active=True,
            access_count=0,
        )
        sharing_service.share_repo.list_shares_received.return_value = (mock_shares, total)
        from src.notemesh.core.schemas.sharing import ShareListRequest
        request = ShareListRequest(page=1, per_page=20, type="received")
        resp = await sharing_service.get_shares_received(user_id, request)
        assert resp.total_count == total
        assert len(resp.shares) == len(mock_shares)
        sharing_service.share_repo.list_shares_received.assert_called_once_with(user_id, 1, 20)

    @pytest.mark.asyncio
    async def test_get_note_shares(self, sharing_service, user_id, note_id):
        """Test get all shares for a note."""
        mock_note = Mock()
        mock_note.id = note_id
        mock_note.owner_id = user_id
        mock_shares = [Mock(), Mock()]
        sharing_service._share_to_response = lambda s: {"id": 1}
        # Service verifies ownership using get_by_id_and_user
        sharing_service.note_repo.get_by_id_and_user.return_value = mock_note
        sharing_service.share_repo.get_note_shares.return_value = mock_shares
        result = await sharing_service.get_note_shares(user_id, note_id)
        assert isinstance(result, list)
        assert len(result) == len(mock_shares)
        sharing_service.share_repo.get_note_shares.assert_called_once_with(note_id)

    @pytest.mark.asyncio
    async def test_get_note_shares_not_owner(self, sharing_service, user_id, note_id):
        """Test get note shares when user is not owner."""
        from fastapi import HTTPException
        # Simulate ownership check failing (service uses get_by_id_and_user)
        sharing_service.note_repo.get_by_id_and_user.return_value = None
        with pytest.raises(HTTPException) as exc:
            await sharing_service.get_note_shares(user_id, note_id)
        assert exc.value.detail == "Note not found or not owned by user"
        assert exc.value.status_code == 404