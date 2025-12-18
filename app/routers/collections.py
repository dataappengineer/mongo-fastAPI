"""
Collections router with endpoints for MongoDB collection operations.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.database import get_database
from app.models import (
    CollectionListResponse,
    CollectionMetadata,
    FieldMetadata,
    CollectionDataResponse
)

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get("/", response_model=CollectionListResponse)
async def list_collections():
    """
    Endpoint 1: List all collections in the database.
    
    Returns:
        CollectionListResponse: List of collection names and count
    """
    try:
        db: Database = get_database()
        collections = db.list_collection_names()
        
        return CollectionListResponse(
            collections=collections,
            count=len(collections)
        )
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{collection_name}/metadata", response_model=CollectionMetadata)
async def get_collection_metadata(collection_name: str):
    """
    Endpoint 2: Get metadata for a specific collection.
    
    Returns collection name, document count, field metadata (data types, columns),
    and other collection information.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        CollectionMetadata: Detailed metadata about the collection
    """
    try:
        db: Database = get_database()
        
        # Check if collection exists
        if collection_name not in db.list_collection_names():
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
        
        collection = db[collection_name]
        
        # Get document count
        document_count = collection.count_documents({})
        
        # Get collection stats
        stats = db.command("collStats", collection_name)
        size_bytes = stats.get("size", 0)
        
        # Get indexes
        indexes = [idx["name"] for idx in collection.list_indexes()]
        
        # Analyze fields by sampling documents (limit to 100 for performance)
        sample_size = min(100, document_count)
        documents = list(collection.find().limit(sample_size))
        
        # Build field metadata
        field_analysis = {}
        
        for doc in documents:
            for field, value in doc.items():
                if field not in field_analysis:
                    field_analysis[field] = {
                        "types": set(),
                        "null_count": 0,
                        "samples": []
                    }
                
                if value is None:
                    field_analysis[field]["null_count"] += 1
                else:
                    field_analysis[field]["types"].add(type(value).__name__)
                    if len(field_analysis[field]["samples"]) < 3:
                        field_analysis[field]["samples"].append(value)
        
        # Convert to FieldMetadata objects
        fields = []
        for field_name, analysis in field_analysis.items():
            fields.append(FieldMetadata(
                field_name=field_name,
                data_types=sorted(list(analysis["types"])),
                null_count=analysis["null_count"],
                sample_values=analysis["samples"]
            ))
        
        return CollectionMetadata(
            collection_name=collection_name,
            document_count=document_count,
            fields=fields,
            size_bytes=size_bytes,
            indexes=indexes
        )
    except HTTPException:
        raise
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{collection_name}/data", response_model=CollectionDataResponse)
async def get_collection_data(
    collection_name: str,
    max_righe: Optional[int] = Query(None, description="Numero massimo di righe da restituire", ge=1)
):
    """
    Endpoint 3: Get data from a specific collection.
    
    Returns all documents or limited by max_righe parameter.
    
    Args:
        collection_name: Name of the collection
        max_righe: Maximum number of rows to return (optional, in Italian as requested)
        
    Returns:
        CollectionDataResponse: Collection data with documents
    """
    try:
        db: Database = get_database()
        
        # Check if collection exists
        if collection_name not in db.list_collection_names():
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
        
        collection = db[collection_name]
        
        # Get total count
        total_count = collection.count_documents({})
        
        # Fetch data with optional limit
        if max_righe is not None:
            documents = list(collection.find().limit(max_righe))
        else:
            documents = list(collection.find())
        
        # Convert ObjectId to string for JSON serialization
        for doc in documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
        
        return CollectionDataResponse(
            collection_name=collection_name,
            data=documents,
            total_count=total_count,
            returned_count=len(documents),
            max_righe=max_righe
        )
    except HTTPException:
        raise
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
