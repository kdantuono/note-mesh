"""
Shared response schemas - pagination, errors etc
"""

from typing import Generic, TypeVar, Optional, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar('T')


class PaginationResponse(BaseModel, Generic[T]):
    """Pagination wrapper for API responses"""
    
    items: List[T]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        per_page: int
    ) -> "PaginationResponse[T]":
        # calculate page info
        pages = (total + per_page - 1) // per_page
        
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    
    error: str = Field(description="Error type")
    message: str = Field(description="Human-readable error message")
    details: Optional[dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Username too short",
                "details": {
                    "field": "username",
                    "issue": "Minimum 3 characters required"
                },
                "timestamp": "2025-09-13T17:23:45Z"
            }
        }


class SuccessResponse(BaseModel):
    """Standard success response schema."""
    
    success: bool = Field(default=True, description="Operation success status")
    message: str = Field(description="Success message")
    data: Optional[dict[str, Any]] = Field(default=None, description="Additional response data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"id": "123e4567-e89b-12d3-a456-426614174000"}
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response schema."""
    
    status: str = Field(description="Overall health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(description="Application version")
    checks: dict[str, dict[str, Any]] = Field(description="Individual component health checks")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-09-13T10:30:00Z",
                "version": "1.0.0",
                "checks": {
                    "database": {
                        "status": "healthy",
                        "response_time_ms": 15
                    },
                    "redis": {
                        "status": "healthy", 
                        "response_time_ms": 5
                    }
                }
            }
        }