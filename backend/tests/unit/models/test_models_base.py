"""
Unit tests for base model functionality.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

from src.notemesh.core.models.base import BaseModel


class ConcreteModel(BaseModel):
    """Concrete implementation of BaseModel for testing."""
    __tablename__ = "test_model"


class TestBaseModel:
    """Test BaseModel functionality."""
    
    def test_base_model_abstract(self):
        """Test that BaseModel is abstract and cannot be instantiated directly."""
        # BaseModel should have __abstract__ = True
        assert hasattr(BaseModel, "__abstract__")
        assert BaseModel.__abstract__ is True
    
    def test_id_field(self):
        """Test that id field is configured correctly."""
        model = ConcreteModel()
        
        # ID should be None before saving to database
        assert hasattr(model, "id")
        
        # When assigned, should accept UUID
        test_id = uuid.uuid4()
        model.id = test_id
        assert model.id == test_id
    
    def test_timestamp_fields(self):
        """Test that timestamp fields exist."""
        model = ConcreteModel()
        
        # Should have created_at and updated_at
        assert hasattr(model, "created_at")
        assert hasattr(model, "updated_at")
    
    def test_repr_method(self):
        """Test string representation."""
        model = ConcreteModel()
        test_id = uuid.uuid4()
        model.id = test_id
        
        expected = f"<ConcreteModel(id={test_id})>"
        assert repr(model) == expected
    
    def test_to_dict_basic(self):
        """Test to_dict method with basic fields."""
        model = ConcreteModel()
        test_id = uuid.uuid4()
        test_time = datetime.now(timezone.utc)
        
        # Mock the table columns
        mock_column_id = Mock()
        mock_column_id.name = "id"
        
        mock_column_created = Mock()
        mock_column_created.name = "created_at"
        
        mock_column_updated = Mock()
        mock_column_updated.name = "updated_at"
        
        mock_table = Mock()
        mock_table.columns = [mock_column_id, mock_column_created, mock_column_updated]
        
        # Set up the model
        model.id = test_id
        model.created_at = test_time
        model.updated_at = test_time
        model.__table__ = mock_table
        
        result = model.to_dict()
        
        # Check results
        assert isinstance(result, dict)
        assert result["id"] == str(test_id)  # UUID should be converted to string
        assert result["created_at"] == test_time.isoformat()  # datetime should be ISO format
        assert result["updated_at"] == test_time.isoformat()
    
    def test_to_dict_with_none_values(self):
        """Test to_dict method with None values."""
        model = ConcreteModel()
        
        # Mock the table columns
        mock_column = Mock()
        mock_column.name = "nullable_field"
        
        mock_table = Mock()
        mock_table.columns = [mock_column]
        
        model.nullable_field = None
        model.__table__ = mock_table
        
        result = model.to_dict()
        
        assert result["nullable_field"] is None
    
    def test_to_dict_with_various_types(self):
        """Test to_dict method with various field types."""
        model = ConcreteModel()
        
        # Mock columns for different types
        columns = []
        for field_name in ["string_field", "int_field", "bool_field", "float_field"]:
            mock_column = Mock()
            mock_column.name = field_name
            columns.append(mock_column)
        
        mock_table = Mock()
        mock_table.columns = columns
        
        # Set values
        model.string_field = "test string"
        model.int_field = 42
        model.bool_field = True
        model.float_field = 3.14
        model.__table__ = mock_table
        
        result = model.to_dict()
        
        assert result["string_field"] == "test string"
        assert result["int_field"] == 42
        assert result["bool_field"] is True
        assert result["float_field"] == 3.14
    
    def test_to_dict_with_list_field(self):
        """Test to_dict method with list fields."""
        model = ConcreteModel()
        
        mock_column = Mock()
        mock_column.name = "list_field"
        
        mock_table = Mock()
        mock_table.columns = [mock_column]
        
        model.list_field = ["item1", "item2", "item3"]
        model.__table__ = mock_table
        
        result = model.to_dict()
        
        assert result["list_field"] == ["item1", "item2", "item3"]
    
    def test_inheritance(self):
        """Test that models can inherit from BaseModel."""
        # ConcreteModel should inherit all BaseModel attributes
        assert hasattr(ConcreteModel, "id")
        assert hasattr(ConcreteModel, "created_at")
        assert hasattr(ConcreteModel, "updated_at")
        assert hasattr(ConcreteModel, "__repr__")
        assert hasattr(ConcreteModel, "to_dict")