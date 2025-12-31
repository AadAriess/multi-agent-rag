"""
Model dan skema data untuk Multi Agent RAG
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime


class DocumentMetadata(BaseModel):
    material_id: str
    doc_name: str
    page_number: int
    chunk_index: int
    hash: str


class SearchMetadata(BaseModel):
    search_id: str
    session_id: str
    source_urls: List[str]
    timestamp: str


class DocumentChunk(BaseModel):
    text: str
    metadata: DocumentMetadata


class SearchMemoryChunk(BaseModel):
    summary_text: str
    metadata: SearchMetadata


class AgentResponse(BaseModel):
    agent_id: str
    response: str
    sources: List[str]
    confidence: float


class AggregatedResponse(BaseModel):
    final_response: str
    reasoning: str
    sources: List[str]
    agent_responses: List[AgentResponse]
    conflict_resolved: bool


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class IngestionRequest(BaseModel):
    file_path: str
    material_id: str
    doc_name: str


# Placeholder untuk model-model yang diperlukan oleh services
class DocumentModel:
    """Placeholder untuk DocumentModel"""
    pass


class ChatSession:
    """Placeholder untuk ChatSession"""
    pass


# Ekspor semua kelas
__all__ = [
    "DocumentMetadata",
    "SearchMetadata",
    "DocumentChunk",
    "SearchMemoryChunk",
    "AgentResponse",
    "AggregatedResponse",
    "QueryRequest",
    "IngestionRequest",
    "DocumentModel",
    "ChatSession"
]