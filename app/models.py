"""
Pydantic models for API request/response schemas.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class CollectionInfo(BaseModel):
    """Information about a single collection."""
    name: str = Field(..., description="Name of the collection")
    type: str = Field(..., description="Type: collection, view, timeseries")
    
    
class CollectionListResponse(BaseModel):
    """Response model for listing collections."""
    collections: List[CollectionInfo] = Field(..., description="List of collections with their types")
    count: int = Field(..., description="Total number of collections")


class FieldMetadata(BaseModel):
    """Metadata for a single field in a collection."""
    field_name: str = Field(..., description="Name of the field")
    data_types: List[str] = Field(..., description="Data types found for this field (can be multiple)")
    null_count: int = Field(..., description="Number of documents where this field is null or missing")
    sample_values: List[Any] = Field(..., description="Sample values from this field")


class CollectionMetadata(BaseModel):
    """Response model for collection metadata."""
    collection_name: str = Field(..., description="Name of the collection")
    document_count: int = Field(..., description="Total number of documents")
    fields: List[FieldMetadata] = Field(..., description="Metadata for each field")
    size_bytes: Optional[int] = Field(None, description="Collection size in bytes")
    indexes: List[str] = Field(..., description="List of indexes on the collection")


class CollectionDataResponse(BaseModel):
    """Response model for collection data."""
    collection_name: str = Field(..., description="Name of the collection")
    data: List[Dict[str, Any]] = Field(..., description="List of documents")
    total_count: int = Field(..., description="Total documents in collection")
    returned_count: int = Field(..., description="Number of documents returned")
    max_righe: Optional[int] = Field(None, description="Maximum rows requested")


class SQLValidationRequest(BaseModel):
    """Request model for SQL query validation."""
    query: str = Field(..., description="SQL query to validate", min_length=1)


class SQLValidationResponse(BaseModel):
    """Response model for SQL query validation."""
    valid: bool = Field(..., description="Whether the query is valid")
    query: str = Field(..., description="The query that was validated")
    formatted_query: Optional[str] = Field(None, description="Formatted/prettified version of the query")
    error_message: Optional[str] = Field(None, description="Error message if query is invalid")
    query_type: Optional[str] = Field(None, description="Type of SQL query (SELECT, INSERT, UPDATE, etc.)")
