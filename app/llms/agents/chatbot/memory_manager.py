"""
Memory Management untuk Multi Agent RAG
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.database_schema import Context, SearchHistory
from app.database.milvus_config import search_memory_collection
from app.database.mysql_config import get_db
from llama_index.embeddings.ollama import OllamaEmbedding
from app.services.redis_service import redis_service
import logging

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Kelas untuk mengelola memory dalam sistem Multi Agent RAG:
    - Simpan ringkasan hasil search baru ke Milvus search_memory
    - Simpan seluruh log percakapan ke MySQL contexts sebagai memori jangka pendek
    - Gunakan Redis untuk menyimpan state LangGraph
    """
    
    def __init__(self):
        # Inisialisasi embedding
        self.embed_model = OllamaEmbedding(
            model_name=settings.embedding_model_name,
            base_url=settings.llm_base_url
        )
    
    def save_search_memory(self, summary: str, search_id: str, session_id: str, source_urls: List[str]) -> bool:
        """Simpan ringkasan hasil search baru ke Milvus search_memory"""
        try:
            # Validasi bahwa summary tidak kosong
            if not summary or len(summary.strip()) < 5:
                summary = "Ringkasan hasil pencarian dari internet"

            # Buat embedding dari summary
            summary_embedding = self.embed_model.get_text_embedding(summary)

            # Pastikan embedding tidak kosong
            if not summary_embedding or len(summary_embedding) == 0:
                logger.error("Embedding result is empty")
                return False

            # Siapkan metadata
            metadata = {
                "search_id": search_id,
                "session_id": session_id,
                "source_urls": source_urls,
                "timestamp": datetime.now().isoformat()
            }

            # Simpan ke search_memory collection
            insert_result = search_memory_collection.insert([
                [summary],  # summary_text
                [summary_embedding],  # vector
                [metadata]  # metadata
            ])

            # Commit perubahan
            search_memory_collection.flush()

            logger.info(f"Successfully stored search result in memory with ID: {search_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing search memory: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    def save_conversation_context(self, session_id: str, query: str, response: str, agent_responses: List[Dict]) -> bool:
        """Simpan log percakapan ke MySQL contexts"""
        try:
            # Buat konteks percakapan
            context_data = {
                "query": query,
                "response": response,
                "agent_responses": agent_responses,
                "timestamp": datetime.now().isoformat()
            }

            # Dapatkan session database
            db = next(get_db())

            # Cek apakah sudah ada konteks untuk session ini
            existing_context = db.query(Context).filter(Context.session_id == session_id).first()

            if existing_context:
                # Update konteks yang sudah ada
                existing_context.data = json.dumps(context_data)
                existing_context.created_at = datetime.now()
            else:
                # Buat konteks baru
                new_context = Context(
                    session_id=session_id,
                    data=json.dumps(context_data)
                )
                db.add(new_context)

            db.commit()
            db.close()

            logger.info(f"Successfully saved conversation context for session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving conversation context: {str(e)}")
            return False
    
    def save_search_history(self, query: str, results_summary: str, source_urls: List[str], session_id: str) -> str:
        """Simpan histori pencarian ke MySQL"""
        try:
            from uuid import uuid4
            search_id = str(uuid4())
            
            # Dapatkan session database
            db = next(get_db())
            
            # Buat record histori pencarian
            search_history = SearchHistory(
                id=search_id,
                query=query,
                results_summary=results_summary,
                source_urls=json.dumps(source_urls),
                session_id=session_id
            )
            
            db.add(search_history)
            db.commit()
            db.close()
            
            logger.info(f"Successfully saved search history with ID: {search_id}")
            return search_id
        except Exception as e:
            logger.error(f"Error saving search history: {str(e)}")
            return ""
    
    def save_graph_state(self, session_id: str, state: Dict[str, Any], expiry: int = None) -> bool:
        """Simpan state LangGraph ke Redis"""
        try:
            if expiry is None:
                expiry = settings.session_expiry
            
            # Serialisasi state
            state_str = json.dumps(state, default=str)
            
            # Simpan ke Redis
            redis_service.set_cache(f"graph_state:{session_id}", state_str, expiry)
            
            logger.info(f"Successfully saved graph state for session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving graph state: {str(e)}")
            return False
    
    def load_graph_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Muat state LangGraph dari Redis"""
        try:
            # Ambil dari Redis
            state_str = redis_service.get_cache(f"graph_state:{session_id}")
            
            if state_str:
                # Deserialisasi state
                state = json.loads(state_str)
                logger.info(f"Successfully loaded graph state for session: {session_id}")
                return state
            else:
                logger.info(f"No graph state found for session: {session_id}")
                return None
        except Exception as e:
            logger.error(f"Error loading graph state: {str(e)}")
            return None
    
    def get_relevant_search_memory(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Dapatkan hasil pencarian yang relevan dari search_memory di Milvus"""
        try:
            # Buat embedding dari query
            query_embedding = self.embed_model.get_text_embedding(query)
            
            # Cari di search_memory collection
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            results = search_memory_collection.search(
                data=[query_embedding],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                output_fields=["summary_text", "metadata"]
            )
            
            relevant_results = []
            for result in results[0]:  # Ambil hasil dari batch pertama
                relevant_results.append({
                    "summary_text": result.entity.get('summary_text'),
                    "metadata": result.entity.get('metadata')
                })
            
            logger.info(f"Retrieved {len(relevant_results)} relevant search memories")
            return relevant_results
        except Exception as e:
            logger.error(f"Error retrieving search memory: {str(e)}")
            return []
    
    def get_conversation_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Dapatkan konteks percakapan dari MySQL"""
        try:
            # Dapatkan session database
            db = next(get_db())
            
            # Ambil konteks untuk session ini
            context = db.query(Context).filter(Context.session_id == session_id).first()
            db.close()
            
            if context:
                context_data = json.loads(context.data)
                logger.info(f"Retrieved conversation context for session: {session_id}")
                return context_data
            else:
                logger.info(f"No conversation context found for session: {session_id}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving conversation context: {str(e)}")
            return None


# Fungsi helper untuk membuat instance memory manager
def create_memory_manager() -> MemoryManager:
    """Create and return a Memory Manager instance"""
    return MemoryManager()


# Instance global untuk digunakan di seluruh aplikasi
memory_manager = create_memory_manager()