"""
Database connection module for MongoDB.
Provides connection configuration that can work with both Docker and external MongoDB.
"""
import os
from pymongo import MongoClient
from pymongo.database import Database
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection settings
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_DB = os.getenv("MONGO_DB", "testdb")
MONGO_USER = os.getenv("MONGO_USER", "")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")

# Global MongoDB client
_client = None


def get_mongo_client() -> MongoClient:
    """
    Get or create MongoDB client instance.
    
    Returns:
        MongoClient: MongoDB client connection
    """
    global _client
    
    if _client is None:
        # Build connection string
        if MONGO_USER and MONGO_PASSWORD:
            # With authentication
            connection_string = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/"
        else:
            # Without authentication (for local Docker development)
            connection_string = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/"
        
        _client = MongoClient(connection_string)
        
    return _client


def get_database() -> Database:
    """
    Get the MongoDB database instance.
    
    Returns:
        Database: MongoDB database object
    """
    client = get_mongo_client()
    return client[MONGO_DB]


def close_connection():
    """
    Close MongoDB connection.
    Call this on application shutdown.
    """
    global _client
    if _client is not None:
        _client.close()
        _client = None
