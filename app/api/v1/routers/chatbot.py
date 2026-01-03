"""
Router FastAPI untuk chatbot Multi Agent RAG
"""
import json
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, AsyncGenerator
from uuid import uuid4
import asyncio
import time
from datetime import datetime

from app.llms.agents.chatbot.aggregator_agent import create_aggregator_agent
from app.llms.agents.chatbot.ingestion_pipeline import ingest_directory
from app.llms.agents.chatbot.memory_manager import memory_manager
from app.database.mysql_config import get_db
from sqlalchemy.orm import Session
from app.core.config import settings

router = APIRouter(prefix="", tags=["chatbot"])

# Model untuk request dan response
class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = settings.llm_model_name
    messages: List[Message]
    temperature: Optional[float] = 0.1
    max_tokens: Optional[int] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None

class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: str = "stop"

class Usage(BaseModel):
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage
    system_fingerprint: Optional[str] = None

class IngestionRequest(BaseModel):
    directory_path: str

class IngestionResponse(BaseModel):
    success: bool
    message: str
    processed_files: int


async def generate_streaming_response(request: ChatCompletionRequest, db: Session) -> AsyncGenerator[str, None]:
    """
    Fungsi generator untuk menghasilkan respons streaming dari chatbot Multi Agent RAG
    """
    try:
        # Ambil query dari pesan terakhir
        query = request.messages[-1].content if request.messages else ""

        # Buat session_id dan user_id jika tidak ada
        session_id = request.session_id or str(uuid4())
        user_id = request.user_id or str(uuid4())

        # Buat aggregator agent
        aggregator_agent = create_aggregator_agent()

        # Buat response dalam format OpenAI API streaming
        response_id = f"chatcmpl-{uuid4().hex}"
        current_timestamp = int(time.time())

        # Kirim chunk awal
        initial_chunk = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": current_timestamp,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                        "content": ""
                    },
                    "finish_reason": None
                }
            ]
        }

        yield f"data: {json.dumps(initial_chunk)}\n\n"

        # Gunakan fungsi astream untuk mendapatkan respons token per token
        token_count = 0
        async for token in aggregator_agent.astream(query, session_id):
            token_count += 1

            # Format chunk dalam format OpenAI API streaming
            chunk = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": current_timestamp,
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": token
                        },
                        "finish_reason": None
                    }
                ]
            }

            yield f"data: {json.dumps(chunk)}\n\n"

        # Kirim chunk terakhir dengan finish_reason
        final_chunk = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": current_timestamp,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "completion_tokens": token_count,
                "prompt_tokens": 0,
                "total_tokens": token_count
            }
        }

        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        error_chunk = {
            "error": {
                "type": "server_error",
                "message": f"Error processing query: {str(e)}"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"


@router.post("/chat/completions", response_class=StreamingResponse)
async def chat_completions(request: ChatCompletionRequest, db: Session = Depends(get_db)):
    """
    Endpoint untuk mengirimkan query ke chatbot Multi Agent RAG dengan format OpenAI API streaming
    """
    return StreamingResponse(
        generate_streaming_response(request, db),
        media_type="text/event-stream"
    )


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