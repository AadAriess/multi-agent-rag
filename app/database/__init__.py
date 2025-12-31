"""
Konfigurasi dan koneksi database untuk Multi Agent RAG
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings
import redis
import logging

# MySQL Configuration
mysql_url = f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
mysql_engine = create_engine(mysql_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=mysql_engine)

# Redis Configuration
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password,
    decode_responses=True
)

# Milvus Configuration
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

def connect_to_milvus():
    connections.connect(
        alias="default",
        host=settings.milvus_host,
        port=settings.milvus_port,
        user=settings.milvus_user,
        password=settings.milvus_password,
        secure=settings.milvus_secure
    )

def create_milvus_collections():
    # Define index parameters
    index_params = {
        "index_type": "HNSW",
        "metric_type": "COSINE",
        "params": {"M": 8, "efConstruction": 64}
    }

    # Create compliance_docs collection if it doesn't exist
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=768),
        FieldSchema(name="metadata", dtype=DataType.JSON)
    ]

    schema = CollectionSchema(fields=fields, description="Compliance documents collection")

    if not utility.has_collection("compliance_docs"):
        compliance_docs_collection = Collection(name="compliance_docs", schema=schema)
        # Create index
        compliance_docs_collection.create_index(field_name="vector", index_params=index_params)
        compliance_docs_collection.load()  # Load collection into memory
    else:
        compliance_docs_collection = Collection(name="compliance_docs")
        compliance_docs_collection.load()  # Load collection into memory

    # Create search_memory collection if it doesn't exist
    search_fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="summary_text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=768),
        FieldSchema(name="metadata", dtype=DataType.JSON)
    ]

    search_schema = CollectionSchema(fields=search_fields, description="Search memory collection")

    if not utility.has_collection("search_memory"):
        search_memory_collection = Collection(name="search_memory", schema=search_schema)
        # Create index
        search_memory_collection.create_index(field_name="vector", index_params=index_params)
        search_memory_collection.load()  # Load collection into memory
    else:
        search_memory_collection = Collection(name="search_memory")
        search_memory_collection.load()  # Load collection into memory

    return compliance_docs_collection, search_memory_collection

# Initialize connections
connect_to_milvus()
compliance_docs_collection, search_memory_collection = create_milvus_collections()

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)