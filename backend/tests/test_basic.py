# Basic tests
import pytest
from fastapi.testclient import TestClient

from src.notemesh.main import app

client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "NoteMesh API"}

def test_health_endpoint():
    """Test health check."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_models_import():
    """Test that models can be imported."""
    from src.notemesh.core.models.user import User
    from src.notemesh.core.models.note import Note
    from src.notemesh.core.models.tag import Tag
    from src.notemesh.core.models.share import Share
    from src.notemesh.core.models.refresh_token import RefreshToken

    # basic instantiation test
    assert User is not None
    assert Note is not None