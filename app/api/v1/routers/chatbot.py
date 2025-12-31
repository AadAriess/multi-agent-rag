"""
Router FastAPI untuk chatbot Multi Agent RAG
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import uuid4
import asyncio

from app.llms.agents.chatbot.aggregator_agent import create_aggregator_agent
from app.llms.agents.chatbot.ingestion_pipeline import ingest_directory
from app.llms.agents.chatbot.memory_manager import memory_manager
from app.database.mysql_config import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

# Model untuk request dan response
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None

class QueryResponse(BaseModel):
    response: str
    session_id: str

class IngestionRequest(BaseModel):
    directory_path: str

class IngestionResponse(BaseModel):
    success: bool
    message: str
    processed_files: int


@router.post("/query", response_model=QueryResponse)
async def query_chatbot(request: QueryRequest, db: Session = Depends(get_db)):
    """
    Endpoint untuk mengirimkan query ke chatbot Multi Agent RAG
    """
    try:
        # Buat session_id jika tidak ada
        session_id = request.session_id or str(uuid4())

        # Cek apakah ada state sebelumnya di Redis
        previous_state = memory_manager.load_graph_state(session_id)

        # Buat aggregator agent
        aggregator_agent = create_aggregator_agent()

        # Jalankan query melalui aggregator agent
        result = await aggregator_agent.ainvoke(request.query, session_id)

        # Gunakan aggregator agent untuk update konteks percakapan ke MySQL
        # dengan struktur data yang sesuai (array untuk <=10 percakapan, objek summary+history untuk >10)
        aggregator_agent = create_aggregator_agent()
        agent_responses = [
            {"agent_id": "local_specialist", "response": result.get("local_response", "N/A")},
            {"agent_id": "search_specialist", "response": result.get("search_response", "N/A")}
        ]

        aggregator_agent._update_context_for_session(
            session_id=session_id,
            query=request.query,
            response=result["final_response"],
            agent_responses=agent_responses
        )

        # Simpan state graph ke Redis untuk sesi berikutnya
        state_to_save = {
            "last_query": request.query,
            "last_response": result["final_response"],
            "session_id": session_id
        }
        memory_manager.save_graph_state(session_id, state_to_save)

        return QueryResponse(
            response=result["final_response"],
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.post("/ingest", response_model=IngestionResponse)
def ingest_documents(request: IngestionRequest, db: Session = Depends(get_db)):
    """
    Endpoint untuk menginjeksi dokumen ke dalam sistem RAG
    """
    try:
        success = ingest_directory(request.directory_path, db)
        
        if success:
            return IngestionResponse(
                success=True,
                message=f"Successfully ingested documents from {request.directory_path}",
                processed_files=0  # Jumlah file yang diproses akan ditentukan dalam fungsi sebenarnya
            )
        else:
            return IngestionResponse(
                success=False,
                message=f"Failed to ingest documents from {request.directory_path}",
                processed_files=0
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during ingestion: {str(e)}")


@router.get("/session/{session_id}")
def get_session_context(session_id: str, db: Session = Depends(get_db)):
    """
    Endpoint untuk mendapatkan konteks percakapan berdasarkan session_id
    """
    try:
        context = memory_manager.get_conversation_context(session_id)
        
        if context:
            return {"session_id": session_id, "context": context}
        else:
            raise HTTPException(status_code=404, detail="Session context not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving session context: {str(e)}")


@router.get("/health")
def health_check():
    """
    Endpoint untuk mengecek kesehatan layanan
    """
    return {"status": "healthy", "service": "Multi Agent RAG Chatbot"}


# Tambahkan endpoint lain sesuai kebutuhan