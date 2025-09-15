"""Tests to increase share repository coverage."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.notemesh.core.repositories.share_repository import ShareRepository
from src.notemesh.core.models.share import ShareStatus


class TestShareRepositoryCoverage:
    """Tests to increase coverage of share repository."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def share_repository(self, mock_session):
        """Create share repository with mocked session."""
        return ShareRepository(mock_session)

    @pytest.fixture
    def user_id(self):
        """Sample user ID."""
        return uuid.uuid4()

    @pytest.fixture
    def note_id(self):
        """Sample note ID."""
        return uuid.uuid4()

    @pytest.mark.asyncio
    async def test_create_share(self, share_repository, user_id, note_id):
        """Test share creation."""
        shared_with_user_id = uuid.uuid4()
        share_data = {
            "note_id": note_id,
            "shared_by_user_id": user_id,
            "shared_with_user_id": shared_with_user_id,
            "permission": "read",
            "status": ShareStatus.ACTIVE
        }

        # Mock the session operations
        mock_share = Mock()
        mock_share.id = uuid.uuid4()

        share_repository.session.add = Mock()
        share_repository.session.commit = AsyncMock()
        share_repository.session.refresh = AsyncMock()

        # Override the Share constructor
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("src.notemesh.core.repositories.share_repository.Share", lambda **kwargs: mock_share)

            result = await share_repository.create_share(share_data)

        assert result == mock_share
        share_repository.session.add.assert_called_once()
        share_repository.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_share_by_id(self, share_repository):
        """Test get share by ID."""
        share_id = uuid.uuid4()
        mock_share = Mock()
        mock_share.id = share_id

        # Mock the query result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_share
        share_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await share_repository.get_share_by_id(share_id)

        assert result == mock_share
        share_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_share_by_id_not_found(self, share_repository):
        """Test get share by ID when not found."""
        share_id = uuid.uuid4()

        # Mock the query result returning None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        share_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await share_repository.get_share_by_id(share_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_share_status(self, share_repository):
        """Test update share status."""
        share_id = uuid.uuid4()
        new_status = "revoked"

        mock_share = Mock()
        mock_share.id = share_id
        mock_share.status = "active"

        # Mock the full chain: get_by_id, setattr, commit, refresh
        share_repository.get_by_id = AsyncMock(return_value=mock_share)
        share_repository.session.commit = AsyncMock()
        share_repository.session.refresh = AsyncMock()

        result = await share_repository.update_share_status(share_id, new_status)

        assert result == mock_share
        assert mock_share.status == new_status
        share_repository.session.commit.assert_called_once()
        share_repository.session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_share_status_not_found(self, share_repository):
        """Test update share status when share not found."""
        share_id = uuid.uuid4()
        new_status = "revoked"

        # Mock get_by_id to return None (which will raise ValueError in update_share)
        share_repository.get_by_id = AsyncMock(return_value=None)

        result = await share_repository.update_share_status(share_id, new_status)

        assert result is None

    @pytest.mark.asyncio
    async def test_list_shares_given(self, share_repository, user_id):
        """Test list shares given by user."""
        mock_shares = [Mock(), Mock()]
        mock_total = 5

        # Mock count query result
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = mock_total

        # Mock shares query result - scalars() should return an iterable
        mock_shares_result = Mock()
        mock_shares_result.scalars.return_value = iter(mock_shares)

        # Session execute returns different results for different calls
        share_repository.session.execute = AsyncMock(side_effect=[mock_count_result, mock_shares_result])

        result_shares, result_total = await share_repository.list_shares_given(
            user_id, page=1, per_page=20
        )

        assert result_shares == mock_shares
        assert result_total == mock_total
        assert share_repository.session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_list_shares_received(self, share_repository, user_id):
        """Test list shares received by user."""
        mock_shares = [Mock()]
        mock_total = 1

        # Mock count query result
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = mock_total

        # Mock shares query result - scalars() should return an iterable
        mock_shares_result = Mock()
        mock_shares_result.scalars.return_value = iter(mock_shares)

        share_repository.session.execute = AsyncMock(side_effect=[mock_count_result, mock_shares_result])

        result_shares, result_total = await share_repository.list_shares_received(
            user_id, page=1, per_page=10
        )

        assert result_shares == mock_shares
        assert result_total == mock_total

    @pytest.mark.asyncio
    async def test_get_note_shares(self, share_repository, note_id):
        """Test get all shares for a note."""
        mock_shares = [Mock(), Mock(), Mock()]

        # Mock query result - scalars() should return an iterable
        mock_result = Mock()
        mock_result.scalars.return_value = iter(mock_shares)
        share_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await share_repository.get_note_shares(note_id)

        assert result == mock_shares
        share_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_share(self, share_repository, user_id):
        """Test delete share."""
        share_id = uuid.uuid4()

        mock_share = Mock()
        mock_share.id = share_id

        # Mock the operations - delete_share uses get_user_share
        share_repository.get_user_share = AsyncMock(return_value=mock_share)
        share_repository.session.delete = AsyncMock()
        share_repository.session.commit = AsyncMock()

        result = await share_repository.delete_share(share_id, user_id)

        assert result is True
        share_repository.session.delete.assert_called_once_with(mock_share)
        share_repository.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_share_not_found(self, share_repository, user_id):
        """Test delete share when not found."""
        share_id = uuid.uuid4()

        # Mock get_user_share to return None
        share_repository.get_user_share = AsyncMock(return_value=None)

        result = await share_repository.delete_share(share_id, user_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_existing_share(self, share_repository, user_id, note_id):
        """Test check if share already exists."""
        shared_with_user_id = uuid.uuid4()
        mock_share = Mock()

        # Mock query result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_share
        share_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await share_repository.check_existing_share(note_id, shared_with_user_id)

        assert result == mock_share
        share_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_existing_share_not_found(self, share_repository, user_id, note_id):
        """Test check existing share when none found."""
        shared_with_user_id = uuid.uuid4()

        # Mock query result returning None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        share_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await share_repository.check_existing_share(note_id, shared_with_user_id)

        assert result is None