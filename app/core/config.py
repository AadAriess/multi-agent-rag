"""
Konfigurasi untuk sistem Multi Agent RAG
Semua variabel konfigurasi dibaca dari file .env
"""
from pydantic_settings import BaseSettings
from typing import Optional


class MultiAgentRAGSettings(BaseSettings):
    # Konfigurasi LLM
    llm_base_url: str  # Dibaca dari LLM_BASE_URL di .env
    llm_model_name: str  # Dibaca dari LLM_MODEL_NAME di .env
    llm_api_key: str  # Dibaca dari LLM_API_KEY di .env
    llm_embedding: str # Dibaca dari LLM_EMBEDDING di .env

    # Konfigurasi Embedding
    embedding_model_name: str  # Dibaca dari EMBEDDING_MODEL_NAME di .env

    # Konfigurasi Milvus
    milvus_host: str  # Dibaca dari MILVUS_HOST di .env
    milvus_port: int  # Dibaca dari MILVUS_PORT di .env
    milvus_user: Optional[str]  # Dibaca dari MILVUS_USER di .env
    milvus_password: Optional[str]  # Dibaca dari MILVUS_PASSWORD di .env
    milvus_secure: bool  # Dibaca dari MILVUS_SECURE di .env
    milvus_collection_name: str  # Dibaca dari MILVUS_COLLECTION_NAME di .env

    # Konfigurasi Redis
    redis_host: str  # Dibaca dari REDIS_HOST di .env
    redis_port: int  # Dibaca dari REDIS_PORT di .env
    redis_db: int  # Dibaca dari REDIS_DB di .env
    redis_password: Optional[str]  # Dibaca dari REDIS_PASSWORD di .env
    default_cache_expiry: int  # Dibaca dari DEFAULT_CACHE_EXPIRY di .env
    session_expiry: int  # Dibaca dari SESSION_EXPIRY di .env

    # Konfigurasi MySQL
    mysql_host: str  # Dibaca dari MYSQL_HOST di .env
    mysql_port: int  # Dibaca dari MYSQL_PORT di .env
    mysql_user: str  # Dibaca dari MYSQL_USER di .env
    mysql_password: str  # Dibaca dari MYSQL_PASSWORD di .env
    mysql_database: str  # Dibaca dari MYSQL_DATABASE di .env

    # Konfigurasi SearXNG
    searxng_base_url: str  # Dibaca dari SEARXNG_BASE_URL di .env

    # Konfigurasi RAG
    chunk_size: int  # Dibaca dari CHUNK_SIZE di .env
    chunk_overlap: int  # Dibaca dari CHUNK_OVERLAP di .env
    timeout: int  # Dibaca dari TIMEOUT di .env
    similarity_top_k: int  # Dibaca dari SIMILARITY_TOP_K di .env
    query_fusion_top_k: int  # Dibaca dari QUERY_FUSION_TOP_K di .env
    query_fusion_num_queries: int  # Dibaca dari QUERY_FUSION_NUM_QUERIES di .env

    # Konfigurasi API
    api_host: str  # Dibaca dari API_HOST di .env
    api_port: int  # Dibaca dari API_PORT di .env
    cors_origins: str  # Dibaca dari CORS_ORIGINS di .env

    # Konfigurasi Proyek
    project_name: str  # Dibaca dari PROJECT_NAME di .env
    debug: bool  # Dibaca dari DEBUG di .env
    api_v1_str: str  # Dibaca dari API_V1_STR di .env

    # Konfigurasi MCP (Model Context Protocol)
    mcp_server_url: str  # Dibaca dari MCP_SERVER_URL di .env
    mcp_max_retries: int  # Dibaca dari MCP_MAX_RETRIES di .env
    mcp_retry_delay: float  # Dibaca dari MCP_RETRY_DELAY di .env

    # Server LLM tambahan (untuk kompatibilitas dengan .env yang ada)
    llm_api_server: Optional[str] = None  # Dibaca dari LLM_API_SERVER di .env
    llm_api_key_server: Optional[str] = None  # Dibaca dari LLM_API_KEY_SERVER di .env

    class Config:
        env_file = ".env"
        extra = "ignore"  # Tambahkan ini untuk mengabaikan variabel tambahan di .env


# Ganti nama variabel untuk menghindari konflik
settings = MultiAgentRAGSettings()


# Untuk kompatibilitas dengan kode lama, buat alias
class Config:
    def __getattr__(self, name):
        # Mapping nama lama ke nama baru
        mapping = {
            'LLM_BASE_URL': 'llm_base_url',
            'LLM_MODEL_NAME': 'llm_model_name',
            'LLM_API_KEY': 'llm_api_key',
            'LLM_EMBEDDING': 'llm_embedding',
            'EMBEDDING_MODEL_NAME': 'embedding_model_name',
            'MILVUS_HOST': 'milvus_host',
            'MILVUS_PORT': 'milvus_port',
            'MILVUS_USER': 'milvus_user',
            'MILVUS_PASSWORD': 'milvus_password',
            'MILVUS_SECURE': 'milvus_secure',
            'MILVUS_COLLECTION_NAME': 'milvus_collection_name',
            'SIMILARITY_TOP_K': 'similarity_top_k',
            'QUERY_FUSION_TOP_K': 'query_fusion_top_k',
            'QUERY_FUSION_NUM_QUERIES': 'query_fusion_num_queries',
            'CHUNK_SIZE': 'chunk_size',
            'TIMEOUT': 'timeout',
            'API_HOST': 'api_host',
            'API_PORT': 'api_port',
            'CORS_ORIGINS': 'cors_origins',
            'PROJECT_NAME': 'project_name',
            'DEBUG': 'debug',
            'API_V1_STR': 'api_v1_str',
            'MCP_SERVER_URL': 'mcp_server_url',
            'MCP_MAX_RETRIES': 'mcp_max_retries',
            'MCP_RETRY_DELAY': 'mcp_retry_delay'
        }

        mapped_name = mapping.get(name, name.lower())
        return getattr(settings, mapped_name)


# Buat instance untuk kompatibilitas
config = Config()