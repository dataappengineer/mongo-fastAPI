"""
Collections router with endpoints for MongoDB collection operations.
Includes verbose logging and comprehensive error diagnostics.
"""
import logging
import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.database import (
    get_database,
    MONGO_HOST,
    MONGO_PORT,
    MONGO_DB,
    MONGO_USER,
)
from app.logging_config import diagnose_mongo_error
from app.models import (
    CollectionListResponse,
    CollectionMetadata,
    FieldMetadata,
    CollectionDataResponse,
    CollectionInfo,
)

logger = logging.getLogger("app.routers.collections")

router = APIRouter(prefix="/collections", tags=["collections"])


def _handle_mongo_exception(endpoint: str, exc: Exception):
    """Centralized exception helper that logs verbose diagnostic info and raises HTTP 500."""
    diag = diagnose_mongo_error(
        exc,
        host=MONGO_HOST,
        port=MONGO_PORT,
        database=MONGO_DB,
        user=MONGO_USER,
    )
    logger.error(
        "❌ [ENDPOINT ERROR: %s] Errore nell'operazione MongoDB:\n"
        "   Categoria: %s\n"
        "   Sommario: %s\n"
        "   Target: host=%s, port=%d, db=%s, user=%s\n"
        "   Dettaglio eccezione: %s\n"
        "   Azione consigliata: %s",
        endpoint,
        diag["error_category"],
        diag["summary"],
        MONGO_HOST,
        MONGO_PORT,
        MONGO_DB,
        MONGO_USER or "None",
        diag["details"],
        diag["actionable_hint"],
        exc_info=True,
    )
    raise HTTPException(status_code=500, detail=diag)


@router.get("", response_model=CollectionListResponse, include_in_schema=False)
@router.get("/", response_model=CollectionListResponse)
async def list_collections():
    """
    Endpoint 1: List all collections in the database with their types.
    
    Returns collection name, type (collection, view, timeseries), and metadata.
    """
    start_time = time.time()
    logger.info("📥 [GET /collections/] Richiesta elenco collezioni per database '%s'...", MONGO_DB)
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
            coll_type = coll_info.get("type")
            options = coll_info.get("options", {})
            
            if coll_type == "view":
                coll_type = "view"
            elif coll_type == "timeseries":
                coll_type = "timeseries"
            elif "viewOn" in options:
                coll_type = "view"
            elif "timeseries" in options:
                coll_type = "timeseries"
            elif options.get("capped", False):
                coll_type = "capped"
            else:
                coll_type = "collection"
            
            collections_info.append(CollectionInfo(
                name=name,
                type=coll_type
            ))
        
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info("📤 [GET /collections/] Restituite %d collezioni in %.2f ms", len(collections_info), duration_ms)
        
        return CollectionListResponse(
            collections=collections_info,
            count=len(collections_info)
        )
    except HTTPException:
        raise
    except Exception as e:
        _handle_mongo_exception("GET /collections/", e)


@router.get("/{collection_name}/metadata", response_model=CollectionMetadata)
async def get_collection_metadata(collection_name: str):
    """
    Endpoint 2: Get metadata for a specific collection, view, or timeseries.
    
    Returns collection name, document count, field metadata (data types, columns),
    and other collection information.
    """
    start_time = time.time()
    logger.info("📥 [GET /collections/%s/metadata] Richiesta metadati...", collection_name)
    try:
        db: Database = get_database()
        
        # Check if collection exists
        available_names = db.list_collection_names()
        if collection_name not in available_names:
            logger.warning(
                "⚠️ [METADATA 404] Collezione '%s' non trovata nel database '%s'. Collezioni disponibili: %s",
                collection_name,
                MONGO_DB,
                available_names,
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "error_category": "COLLECTION_NOT_FOUND",
                    "summary": f"La collezione '{collection_name}' non esiste nel database '{MONGO_DB}'",
                    "requested_collection": collection_name,
                    "database": MONGO_DB,
                    "available_collections": available_names,
                    "actionable_hint": "Verifica il nome della collezione specificato nell'URL.",
                },
            )
        
        # Determine collection type
        coll_info = db.list_collections(filter={"name": collection_name})
        coll_info_list = list(coll_info)
        if not coll_info_list:
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
        
        coll_data = coll_info_list[0]
        coll_type = coll_data.get("type")
        options = coll_data.get("options", {})
        
        collection = db[collection_name]
        
        # Get document count (works for all types)
        try:
            document_count = collection.count_documents({})
        except Exception as e:
            logger.debug("count_documents fallito su '%s', fallback su limit(1000): %s", collection_name, str(e))
            document_count = len(list(collection.find().limit(1000)))
        
        # Get collection stats (protected against authorization or mongo 8 issues)
        size_bytes = 0
        try:
            stats = db.command("collStats", collection_name)
            size_bytes = stats.get("size", 0)
        except Exception as e:
            logger.debug("collStats non disponibile per '%s': %s", collection_name, str(e))
            size_bytes = 0
        
        # Get indexes (views don't have indexes)
        indexes = []
        try:
            indexes = [idx["name"] for idx in collection.list_indexes()]
        except Exception as e:
            logger.debug("list_indexes non disponibile per '%s': %s", collection_name, str(e))
            indexes = []
        
        # Analyze fields by sampling documents
        sample_size = min(100, document_count) if document_count > 0 else 100
        documents = list(collection.find().limit(sample_size))
        
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
                        if field == "_id":
                            field_analysis[field]["samples"].append(str(value))
                        else:
                            # Safely cast non-primitive values to string for JSON serialization
                            try:
                                if isinstance(value, (str, int, float, bool, list, dict)):
                                    field_analysis[field]["samples"].append(value)
                                else:
                                    field_analysis[field]["samples"].append(str(value))
                            except Exception:
                                field_analysis[field]["samples"].append(str(value))
        
        # Convert to FieldMetadata objects
        fields = []
        for field_name, analysis in field_analysis.items():
            fields.append(FieldMetadata(
                field_name=field_name,
                data_types=sorted(list(analysis["types"])),
                null_count=analysis["null_count"],
                sample_values=analysis["samples"]
            ))
        
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(
            "📤 [GET /collections/%s/metadata] Metadati estratti con successo (%d campi, %d doc) in %.2f ms",
            collection_name,
            len(fields),
            document_count,
            duration_ms,
        )
        
        return CollectionMetadata(
            collection_name=collection_name,
            document_count=document_count,
            fields=fields,
            size_bytes=size_bytes,
            indexes=indexes
        )
    except HTTPException:
        raise
    except Exception as e:
        _handle_mongo_exception(f"GET /collections/{collection_name}/metadata", e)


@router.get("/{collection_name}/data", response_model=CollectionDataResponse)
async def get_collection_data(
    collection_name: str,
    max_righe: Optional[int] = Query(None, description="Numero massimo di righe da restituire (deprecato, usa page_size)", ge=1),
    page: Optional[int] = Query(None, description="Numero della pagina (1-based)", ge=1),
    page_size: Optional[int] = Query(None, description="Numero di documenti per pagina", ge=1, le=1000)
):
    """
    Endpoint 3: Get data from a specific collection with optional pagination.
    
    Returns all documents or limited by pagination parameters.
    """
    start_time = time.time()
    logger.info(
        "📥 [GET /collections/%s/data] Richiesta dati (page=%s, page_size=%s, max_righe=%s)...",
        collection_name,
        page,
        page_size,
        max_righe,
    )
    try:
        db: Database = get_database()
        
        # Check if collection exists
        available_names = db.list_collection_names()
        if collection_name not in available_names:
            logger.warning(
                "⚠️ [DATA 404] Collezione '%s' non trovata nel database '%s'. Collezioni disponibili: %s",
                collection_name,
                MONGO_DB,
                available_names,
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "error_category": "COLLECTION_NOT_FOUND",
                    "summary": f"La collezione '{collection_name}' non esiste nel database '{MONGO_DB}'",
                    "requested_collection": collection_name,
                    "database": MONGO_DB,
                    "available_collections": available_names,
                    "actionable_hint": "Verifica il nome della collezione specificato nell'URL.",
                },
            )
        
        collection = db[collection_name]
        total_count = collection.count_documents({})
        
        # Determine pagination mode
        use_pagination = page is not None and page_size is not None
        use_legacy = max_righe is not None and not use_pagination
        
        if use_pagination:
            skip = (page - 1) * page_size
            limit = page_size
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_previous = page > 1
            
            documents = list(collection.find().skip(skip).limit(limit))
            for doc in documents:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
            
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.info(
                "📤 [GET /collections/%s/data] Restituiti %d/%d documenti (pagina %d/%d) in %.2f ms",
                collection_name,
                len(documents),
                total_count,
                page,
                total_pages,
                duration_ms,
            )
            
            return CollectionDataResponse(
                collection_name=collection_name,
                data=documents,
                total_count=total_count,
                returned_count=len(documents),
                max_righe=None,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=has_next,
                has_previous=has_previous
            )
            
        elif use_legacy:
            documents = list(collection.find().limit(max_righe))
            for doc in documents:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
            
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.info("📤 [GET /collections/%s/data] Restituiti %d documenti (legacy) in %.2f ms", collection_name, len(documents), duration_ms)
            
            return CollectionDataResponse(
                collection_name=collection_name,
                data=documents,
                total_count=total_count,
                returned_count=len(documents),
                max_righe=max_righe,
                page=None,
                page_size=None,
                total_pages=None,
                has_next=None,
                has_previous=None
            )
            
        else:
            documents = list(collection.find())
            for doc in documents:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
            
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.info("📤 [GET /collections/%s/data] Restituiti tutti i %d documenti in %.2f ms", collection_name, len(documents), duration_ms)
            
            return CollectionDataResponse(
                collection_name=collection_name,
                data=documents,
                total_count=total_count,
                returned_count=len(documents),
                max_righe=None,
                page=None,
                page_size=None,
                total_pages=None,
                has_next=None,
                has_previous=None
            )
            
    except HTTPException:
        raise
    except Exception as e:
        _handle_mongo_exception(f"GET /collections/{collection_name}/data", e)
