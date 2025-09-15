"""TDD tests for sharing service dashboard functionality."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone
from src.notemesh.core.services.sharing_service import SharingService
from src.notemesh.core.schemas.sharing import ShareListRequest
from src.notemesh.core.models.share import Share
from src.notemesh.core.models.note import Note
from src.notemesh.core.models.user import User
from src.notemesh.core.models.tag import Tag


class TestSharingServiceDashboard:
    """Test sharing service dashboard functionality with proper note data."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def sharing_service(self, mock_session):
        """Create sharing service with mocked dependencies."""
        service = SharingService(mock_session)
        service.share_repo = AsyncMock()
        service.user_repo = AsyncMock()
        service.note_repo = AsyncMock()
        return service

    @pytest.fixture
    def owner_user_id(self):
        """Owner user ID."""
        return uuid.UUID("4614b1df-9cd8-4eaf-a814-4c08e4e8554f")

    @pytest.fixture
    def recipient_user_id(self):
        """Recipient user ID."""
        return uuid.UUID("70005fe1-df3b-48e8-bb94-d22a39cfdd16")

    @pytest.fixture
    def note_id(self):
        """Sample note ID."""
        return uuid.UUID("35064035-1ebc-4fad-b391-761387d486ce")

    @pytest.fixture
    def mock_owner(self, owner_user_id):
        """Mock owner user."""
        owner = Mock(spec=User)
        owner.id = owner_user_id
        owner.username = "frontenduser01"
        owner.full_name = "frontend user 01"
        return owner

    @pytest.fixture
    def mock_recipient(self, recipient_user_id):
        """Mock recipient user."""
        recipient = Mock(spec=User)
        recipient.id = recipient_user_id
        recipient.username = "recipient01"
        recipient.full_name = "Recipient User"
        return recipient

    @pytest.fixture
    def mock_tag(self):
        """Mock tag."""
        tag = Mock(spec=Tag)
        tag.name = "important"
        return tag

    @pytest.fixture
    def mock_note_with_tags(self, note_id, owner_user_id, mock_tag, mock_owner):
        """Mock note with tags."""
        note = Mock(spec=Note)
        note.id = note_id
        note.title = "Test Note with Tags"
        note.content = "This note has tags and should display properly"
        note.owner_id = owner_user_id
        note.owner = mock_owner  # Add owner object
        note.tags = [mock_tag]
        note.hyperlinks = ["https://example.com"]
        note.is_public = False
        note.created_at = datetime.now(timezone.utc)
        note.updated_at = datetime.now(timezone.utc)
        note.view_count = 5
        return note

    @pytest.fixture
    def mock_share(self, owner_user_id, recipient_user_id, note_id, mock_note_with_tags, mock_recipient):
        """Mock share with complete note data."""
        now = datetime.now(timezone.utc)
        share = Mock(spec=Share)
        share.id = uuid.uuid4()
        share.note_id = note_id
        share.note = mock_note_with_tags  # Include the full note object
        share.shared_by_user_id = owner_user_id
        share.shared_with_user_id = recipient_user_id
        share.shared_with_user = mock_recipient
        share.permission = "read"
        share.created_at = now  # Use created_at instead of shared_at
        share.shared_at = now
        share.expires_at = None
        share.is_active = True
        share.access_count = 0
        share.share_message = None
        return share

    @pytest.mark.asyncio
    async def test_list_received_shares_includes_complete_note_data(
        self, sharing_service, recipient_user_id, mock_share, mock_note_with_tags
    ):
        """Test that received shares include complete note data with tags and owner info."""
        # Arrange
        sharing_service.share_repo.list_shares_received.return_value = ([mock_share], 1)

        request = ShareListRequest(type="received", page=1, per_page=20)

        # Act
        response = await sharing_service.list_shares(recipient_user_id, request)

        # Assert: Response should include complete note data
        assert len(response.shares) == 1
        share_response = response.shares[0]

        # Basic share info
        assert share_response.note_id == mock_note_with_tags.id
        assert share_response.note_title == "Test Note with Tags"

        # CRITICAL: Should include complete note object with tags
        assert hasattr(share_response, 'note'), "ShareResponse should include complete note object"
        assert share_response.note is not None, "Note object should not be None"
        assert share_response.note.id == mock_note_with_tags.id
        assert share_response.note.title == "Test Note with Tags"
        assert share_response.note.content_preview.startswith("This note has tags and should display properly")

        # Tags should be included
        assert hasattr(share_response.note, 'tags'), "Note should include tags"
        assert len(share_response.note.tags) == 1
        assert "important" in [tag.name if hasattr(tag, 'name') else tag for tag in share_response.note.tags]

        # Owner info should be included
        assert hasattr(share_response.note, 'owner_username'), "Note should include owner_username"
        assert hasattr(share_response.note, 'owner_display_name'), "Note should include owner_display_name"

    @pytest.mark.asyncio
    async def test_list_given_shares_includes_complete_note_data(
        self, sharing_service, owner_user_id, mock_share, mock_note_with_tags
    ):
        """Test that given shares include complete note data with tags and owner info."""
        # Arrange
        sharing_service.share_repo.list_shares_given.return_value = ([mock_share], 1)

        request = ShareListRequest(type="given", page=1, per_page=20)

        # Act
        response = await sharing_service.list_shares(owner_user_id, request)

        # Assert: Response should include complete note data
        assert len(response.shares) == 1
        share_response = response.shares[0]

        # CRITICAL: Should include complete note object with tags
        assert hasattr(share_response, 'note'), "ShareResponse should include complete note object"
        assert share_response.note is not None, "Note object should not be None"
        assert share_response.note.tags is not None, "Note tags should not be None"
        assert len(share_response.note.tags) == 1

    @pytest.mark.asyncio
    async def test_share_response_has_complete_note_schema(
        self, sharing_service, recipient_user_id, mock_share
    ):
        """Test that ShareResponse schema includes all necessary note fields for dashboard."""
        # Arrange
        sharing_service.share_repo.list_shares_received.return_value = ([mock_share], 1)

        request = ShareListRequest(type="received")

        # Act
        response = await sharing_service.list_shares(recipient_user_id, request)

        # Assert: ShareResponse should have note field with all required attributes
        share_response = response.shares[0]

        # Required fields for dashboard display
        required_note_fields = [
            'id', 'title', 'content_preview', 'tags', 'owner_id',
            'owner_username', 'owner_display_name', 'created_at', 'updated_at'
        ]

        for field in required_note_fields:
            assert hasattr(share_response.note, field), f"Note should have {field} field"

    @pytest.mark.asyncio
    async def test_share_response_handles_missing_note_gracefully(
        self, sharing_service, recipient_user_id, mock_share
    ):
        """Test that ShareResponse handles missing note data gracefully."""
        # Arrange: Share without note object
        mock_share.note = None
        sharing_service.share_repo.list_shares_received.return_value = ([mock_share], 1)

        request = ShareListRequest(type="received")

        # Act
        response = await sharing_service.list_shares(recipient_user_id, request)

        # Assert: Should not crash and should provide fallback data
        assert len(response.shares) == 1
        share_response = response.shares[0]
        assert share_response.note_title is not None  # Should have at least title