"""Tests to increase user repository coverage."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock

from src.notemesh.core.repositories.user_repository import UserRepository


class TestUserRepositoryCoverage:
    """Tests to increase coverage of user repository."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def user_repository(self, mock_session):
        """Create user repository with mocked session."""
        return UserRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_user(self, user_repository):
        """Test user creation."""
        user_data = {
            "username": "testuser",
            "password_hash": "hashed_password",
            "full_name": "Test User"
        }

        # Mock the session operations
        mock_user = Mock()
        mock_user.id = uuid.uuid4()
        mock_user.username = "testuser"

        user_repository.session.add = Mock()
        user_repository.session.commit = AsyncMock()
        user_repository.session.refresh = AsyncMock()

        # Override the User constructor to return our mock
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("src.notemesh.core.repositories.user_repository.User", lambda **kwargs: mock_user)

            result = await user_repository.create_user(user_data)

        assert result == mock_user
        user_repository.session.add.assert_called_once_with(mock_user)
        user_repository.session.commit.assert_called_once()
        user_repository.session.refresh.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_get_by_id(self, user_repository):
        """Test get user by ID."""
        user_id = uuid.uuid4()
        mock_user = Mock()
        mock_user.id = user_id

        # Mock the query result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        user_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await user_repository.get_by_id(user_id)

        assert result == mock_user
        user_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, user_repository):
        """Test get user by ID when not found."""
        user_id = uuid.uuid4()

        # Mock the query result returning None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        user_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await user_repository.get_by_id(user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_username(self, user_repository):
        """Test get user by username."""
        username = "testuser"
        mock_user = Mock()
        mock_user.username = username

        # Mock the query result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        user_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await user_repository.get_by_username(username)

        assert result == mock_user
        user_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_username_not_found(self, user_repository):
        """Test get user by username when not found."""
        username = "nonexistent"

        # Mock the query result returning None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        user_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await user_repository.get_by_username(username)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_user(self, user_repository):
        """Test user update."""
        user_id = uuid.uuid4()
        update_data = {"full_name": "Updated Name"}

        mock_user = Mock()
        mock_user.id = user_id
        mock_user.full_name = "Original Name"

        # Mock get_by_id to return the user
        user_repository.get_by_id = AsyncMock(return_value=mock_user)
        user_repository.session.commit = AsyncMock()
        user_repository.session.refresh = AsyncMock()

        result = await user_repository.update_user(user_id, update_data)

        assert result == mock_user
        user_repository.session.commit.assert_called_once()
        user_repository.session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_repository):
        """Test update user when user not found."""
        user_id = uuid.uuid4()
        update_data = {"full_name": "Updated Name"}

        # Mock get_by_id to return None
        user_repository.get_by_id = AsyncMock(return_value=None)

        result = await user_repository.update_user(user_id, update_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_user(self, user_repository):
        """Test user deletion."""
        user_id = uuid.uuid4()

        mock_user = Mock()
        mock_user.id = user_id

        # Mock the operations
        user_repository.get_by_id = AsyncMock(return_value=mock_user)
        user_repository.session.delete = AsyncMock()
        user_repository.session.commit = AsyncMock()

        result = await user_repository.delete_user(user_id)

        assert result is True
        user_repository.session.delete.assert_called_once_with(mock_user)
        user_repository.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_repository):
        """Test delete user when user not found."""
        user_id = uuid.uuid4()

        # Mock get_by_id to return None
        user_repository.get_by_id = AsyncMock(return_value=None)

        result = await user_repository.delete_user(user_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_list_users(self, user_repository):
        """Test list users with pagination."""
        mock_users = [Mock(), Mock(), Mock()]
        mock_total = 10

        # Mock count query result
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = mock_total

        # Mock users query result - scalars() should return an iterable
        mock_users_result = Mock()
        mock_users_result.scalars.return_value = iter(mock_users)

        # Session execute returns different results for different calls
        user_repository.session.execute = AsyncMock(side_effect=[mock_count_result, mock_users_result])

        result_users, result_total = await user_repository.list_users(page=1, per_page=20)

        assert result_users == mock_users
        assert result_total == mock_total
        assert user_repository.session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_check_username_exists(self, user_repository):
        """Test check if username exists."""
        username = "existinguser"
        mock_user = Mock()

        # Mock the query result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        user_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await user_repository.check_username_exists(username)

        assert result is True
        user_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_username_not_exists(self, user_repository):
        """Test check username when it doesn't exist."""
        username = "newuser"

        # Mock the query result returning None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        user_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await user_repository.check_username_exists(username)

        assert result is False