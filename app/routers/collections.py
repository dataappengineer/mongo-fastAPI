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
    Endpoint 1: List all collections in the database with their types.
    
    Returns collection name, type (collection, view, timeseries), and metadata.
    
    Returns:
        CollectionListResponse: List of collections with type information
    """
    try:
        db: Database = get_database()
        
        # Get detailed collection information using listCollections command
        collections_info = []
        collections_cursor = db.list_collections()
        
        for coll_info in collections_cursor:
            name = coll_info.get("name")
            
            # Skip system collections
            if name.startswith("system.") and name != "system.views":
                continue
            
            # Determine collection type
            # First check the 'type' field directly (MongoDB 3.4+)
            coll_type = coll_info.get("type")
            options = coll_info.get("options", {})
            
            if coll_type == "view":
                coll_type = "view"
            elif coll_type == "timeseries":
                coll_type = "timeseries"
            elif "viewOn" in options:
                # Fallback: check options for viewOn
                coll_type = "view"
            elif "timeseries" in options:
                # Fallback: check options for timeseries
                coll_type = "timeseries"
            elif options.get("capped", False):
                # Check for capped collections
                coll_type = "capped"
            else:
                coll_type = "collection"
            
            from app.models import CollectionInfo
            collections_info.append(CollectionInfo(
                name=name,
                type=coll_type
            ))
        
        return CollectionListResponse(
            collections=collections_info,
            count=len(collections_info)
        )
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{collection_name}/metadata", response_model=CollectionMetadata)
async def get_collection_metadata(collection_name: str):
    """
    Endpoint 2: Get metadata for a specific collection, view, or timeseries.
    
    Returns collection name, document count, field metadata (data types, columns),
    and other collection information. Works with regular collections, views,
    timeseries collections, and capped collections.
    
    Args:
        collection_name: Name of the collection/view
        
    Returns:
        CollectionMetadata: Detailed metadata about the collection
    """
    try:
        db: Database = get_database()
        
        # Check if collection exists
        if collection_name not in db.list_collection_names():
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
        
        # Determine collection type
        coll_info = db.list_collections(filter={"name": collection_name})
        coll_info_list = list(coll_info)
        if not coll_info_list:
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
        
        coll_data = coll_info_list[0]
        coll_type = coll_data.get("type")
        options = coll_data.get("options", {})
        is_view = coll_type == "view" or "viewOn" in options
        is_timeseries = coll_type == "timeseries" or "timeseries" in options
        
        collection = db[collection_name]
        
        # Get document count (works for all types)
        try:
            document_count = collection.count_documents({})
        except Exception:
            # Fallback for views that might have issues with count_documents
            document_count = len(list(collection.find().limit(1000)))
        
        # Get collection stats (might not work for views)
        size_bytes = 0
        try:
            stats = db.command("collStats", collection_name)
            size_bytes = stats.get("size", 0)
        except Exception:
            # Views don't have size stats, that's OK
            pass
        
        # Get indexes (views don't have their own indexes)
        indexes = []
        try:
            indexes = [idx["name"] for idx in collection.list_indexes()]
        except Exception:
            # Views don't have indexes, use empty list
            indexes = []
        
        # Analyze fields by sampling documents (works for all types)
        sample_size = min(100, document_count) if document_count > 0 else 100
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
                        # Convert ObjectId to string for serialization
                        if field == "_id":
                            field_analysis[field]["samples"].append(str(value))
                        else:
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
