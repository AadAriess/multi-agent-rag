"""
Definisi Agen Spesialis untuk Multi Agent RAG
"""
import asyncio
from typing import Dict, List, Any, Optional
from langchain_core.tools import BaseTool
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from app.core.config import settings
from app.services.searxng_service import searxng_service
from app.services.milvus_service import milvus_service
from app.database.milvus_config import search_memory_collection
from app.llms.agents.tools.mcp_tool import call_sequential_thinking_tool
from app.llms.agents.chatbot.memory_manager import memory_manager
from langchain_openai import ChatOpenAI
import logging

logger = logging.getLogger(__name__)


class LocalSpecialistTool(BaseTool):
    name: str = "milvus_search"
    description: str = "Search for information in local compliance documents stored in Milvus"

    def _run(self, query: str) -> str:
        """Search for relevant documents in Milvus"""
        try:
            # Ambil konteks dari Milvus
            from app.services.milvus_service import milvus_service
            from llama_index.core import Settings

            embed_model = OllamaEmbedding(
                model_name=settings.embedding_model_name,
                base_url=settings.llm_embedding
            )

            query_embedding = embed_model.get_text_embedding(query)
            search_results = milvus_service.search_similar(query_embedding, top_k=settings.similarity_top_k)

            if search_results:
                # Format hasil pencarian
                formatted_results = []
                for result in search_results:
                    formatted_result = f"Document: {result.get('metadata', {}).get('doc_name', 'Unknown')}\n"
                    formatted_result += f"Content: {result.get('text', '')[:500]}...\n"
                    formatted_result += f"Relevance Score: {result.get('distance', 'N/A')}\n\n"
                    formatted_results.append(formatted_result)

                return "\n".join(formatted_results)
            else:
                return "No relevant documents found in local compliance database."
        except Exception as e:
            logger.error(f"Error searching local documents: {str(e)}")
            return f"Error searching local documents: {str(e)}"

    async def _arun(self, query: str) -> str:
        """Asynchronous version of _run"""
        return self._run(query)


class LocalSpecialistAgent:
    """
    Agent 1 (Local Specialist): Bertugas mencari di Milvus.
    Gunakan ReAct: Berpikir apakah butuh data tambahan dari MySQL documents (seperti ringkasan)
    atau langsung mengambil teks dari chunk Milvus.
    """

    def __init__(self):
        # Inisialisasi LLM
        self.llm = ChatOpenAI(
            model=settings.llm_model_name,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            temperature=0.1
        )

        # Inisialisasi embedding
        self.embed_model = OllamaEmbedding(
            model_name=settings.embedding_model_name,
            base_url=settings.llm_embedding
        )

        # Gunakan milvus_service yang sudah kita buat sebelumnya
        # Kita tidak perlu membuat index baru karena milvus_service sudah menanganinya
        from app.services.milvus_service import milvus_service
        self.milvus_service = milvus_service

        # Buat tools untuk agen
        self.tools = [
            LocalSpecialistTool(),
            # Tool lain bisa ditambahkan di sini
        ]

    async def search_local_documents(self, query: str) -> str:
        """Search for relevant documents in Milvus"""
        try:
            
            logger.info(f"Proses pencarian lokal untuk: {query}")

            # Lakukan pencarian di Milvus
            query_embedding = self.embed_model.get_text_embedding(query)
            search_results = self.milvus_service.search_similar(query_embedding, top_k=settings.similarity_top_k)

            if search_results:
                formatted_results = []
                for result in search_results:
                    formatted_result = f"Document: {result.get('metadata', {}).get('doc_name', 'Unknown')}\n"
                    formatted_result += f"Content: {result.get('text', '')}\n"
                    formatted_result += f"Relevance Score: {result.get('distance', 'N/A')}\n\n"
                    formatted_results.append(formatted_result)
                
                return "\n".join(formatted_results)
            else:
                return "No relevant documents found in local compliance database."
        except Exception as e:
            logger.error(f"Error searching local documents: {str(e)}")
            return f"Error searching local documents: {str(e)}"

    def lookup_mysql_document(self, doc_id: str) -> str:
        """Look up document summary and metadata from MySQL"""
        try:
            # Ini akan diimplementasikan sesuai dengan struktur database Anda
            # Untuk saat ini, kita kembalikan pesan bahwa fungsionalitas ini belum selesai
            return f"Document summary lookup for ID: {doc_id} - Implementation pending"
        except Exception as e:
            logger.error(f"Error looking up document in MySQL: {str(e)}")
            return f"Error looking up document in MySQL: {str(e)}"

    async def run_query(self, query: str) -> Dict[str, Any]:
        """Run query through the local specialist agent"""
        try:
            # Jalankan pencarian langsung ke Milvus
            response = await self.search_local_documents(query)
            return {
                "agent_id": "local_specialist",
                "response": response,
                "sources": ["milvus_compliance_docs"],
                "confidence": 0.8  # Placeholder, seharusnya dihitung dari skor kemiripan
            }
        except Exception as e:
            logger.error(f"Error in local specialist agent: {str(e)}")
            return {
                "agent_id": "local_specialist",
                "response": f"Error processing query: {str(e)}",
                "sources": [],
                "confidence": 0.0
            }


class SearchSpecialistTool(BaseTool):
    name: str = "internet_search"
    description: str = "Search for information on the internet using Searxng"

    def _run(self, query: str) -> str:
        """Search for information on the internet"""
        try:
            # Cek dulu di search_memory
            search_results = searxng_service.search_compliance_info(query)

            if search_results:
                # Format hasil pencarian
                formatted_results = []
                for result in search_results[:3]:  # Ambil 3 hasil teratas
                    formatted_result = f"Title: {result.get('title', 'No title')}\n"
                    formatted_result += f"URL: {result.get('url', 'No URL')}\n"
                    formatted_result += f"Content: {result.get('content', '')[:300]}...\n\n"
                    formatted_results.append(formatted_result)

                return "\n".join(formatted_results)
            else:
                return "No relevant results found on the internet."
        except Exception as e:
            logger.error(f"Error searching internet: {str(e)}")
            return f"Error searching internet: {str(e)}"

    async def _arun(self, query: str) -> str:
        """Asynchronous version of _run"""
        return self._run(query)


class SearchSpecialistAgent:
    """
    Agent 2 (Search Specialist): Bertugas ke internet via Searxng.
    Wajib cek search_memory di Milvus terlebih dahulu sebelum melakukan crawling baru.
    """

    def __init__(self):
        # Inisialisasi LLM
        self.llm = ChatOpenAI(
            model=settings.llm_model_name,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            temperature=0.1
        )

        # Buat tools untuk agen
        self.tools = [
            SearchSpecialistTool(),
            # Tool lain bisa ditambahkan di sini
        ]

    def check_search_memory(self, query: str) -> str:
        """Check search_memory in Milvus for previous search results"""
        try:
            logger.info(f"\033[94m[CHECKING SEARCH MEMORY]\033[0m Checking search_memory in Milvus for query: {query}")
            # Ambil embedding dari query
            query_embedding = OllamaEmbedding(
                model_name=settings.embedding_model_name,
                base_url=settings.llm_embedding
            ).get_text_embedding(query)

            # Cari di search_memory collection
            search_results = milvus_service.search_in_collection(
                collection_name="search_memory",
                query_vector=query_embedding,
                top_k=settings.similarity_top_k
            )

            logger.info(f"\033[94m[SEARCH RESULTS]\033[0m Found {len(search_results)} results in search_memory for query: {query}")

            if search_results:
                # Ambil hasil dengan skor kemiripan tertinggi (jarak terendah)
                best_result = search_results[0]  # Hasil dengan jarak terendah (kemiripan tertinggi)
                best_similarity_score = best_result.get('distance', float('inf'))  # Gunakan jarak sebagai ukuran kemiripan

                # Gunakan threshold tetap berdasarkan skor kemiripan terbaik
                # Kita gunakan threshold tetap untuk konsistensi antar permintaan
                # Berdasarkan pengujian sebelumnya, nilai 0.65 masih terlalu tinggi
                # Kita turunkan threshold untuk mencegah sistem menganggap pertanyaan yang berbeda sebagai mirip
                similarity_threshold = 0.5  # Threshold tetap untuk menentukan kemiripan

                logger.info(f"\033[94m[BEST SCORE]\033[0m Best similarity score: {best_similarity_score}")
                logger.info(f"\033[94m[THRESHOLD]\033[0m Fixed similarity threshold: {similarity_threshold}")

                # Jika skor terbaik lebih kecil dari threshold, maka cukup mirip
                # Dalam konteks cosine similarity, jarak yang lebih rendah berarti kemiripan yang lebih tinggi
                if best_similarity_score < similarity_threshold:
                    # Ambil hanya hasil dengan skor kemiripan terbaik (jarak terendah)
                    # Gunakan field yang benar berdasarkan skema search_memory
                    summary_text = best_result.get('summary_text', best_result.get('text', ''))

                    # Format hasil pencarian dari memory
                    formatted_result = f"Previous Search Summary: {summary_text}\n"
                    formatted_result += f"Source URLs: {best_result.get('metadata', {}).get('source_urls', [])}\n"
                    formatted_result += f"Timestamp: {best_result.get('metadata', {}).get('timestamp', 'N/A')}\n\n"

                    logger.info(f"\033[92m[SUFFICIENT SIMILARITY]\033[0m Using cached results with similarity score: {best_similarity_score} (threshold: {similarity_threshold})")
                    return formatted_result
                else:
                    logger.info(f"\033[93m[LOW SIMILARITY]\033[0m Best similarity score {best_similarity_score} is above threshold {similarity_threshold}, need to search internet")
                    return "No previous search results found in memory for this query."
            else:
                logger.info(f"\033[91m[NO RESULTS FOUND]\033[0m No previous search results found in memory for query: {query}")
                return "No previous search results found in memory for this query."
        except Exception as e:
            logger.error(f"Error checking search memory: {str(e)}")
            return f"Error checking search memory: {str(e)}"

    async def search_internet(self, query: str) -> str:
        """Search for information on the internet using Searxng"""
        try:
            # Gunakan pendekatan ReAct (Reason + Act) dengan bantuan sequential thinking
            # Pertama, lakukan reasoning untuk memahami query
            reasoning_result = await call_sequential_thinking_tool(
                tool_name="sequentialThinking", 
                parameters={
                    "thought": f"Analisis query: {query}",
                    "thoughtNumber": 1,
                    "totalThoughts": 1,
                    "nextThoughtNeeded": False
                }
            )

            logger.info(f"[SEARCH AGENT] Query asli: {query}")
            logger.info(f"[SEARCH AGENT] Hasil reasoning: {reasoning_result}")

            # Ekstrak kata kunci dari hasil reasoning
            if reasoning_result and "result" in reasoning_result:
                reasoning_content = reasoning_result["result"]
                logger.info(f"[SEARCH AGENT] Isi reasoning: {reasoning_content}")

                # Coba ekstrak kata kunci dari reasoning
                import re
                # Cari pola kata kunci dalam reasoning
                keywords_match = re.search(r'kata kunci.*?:(.*?)(?:\n|$)', reasoning_content, re.IGNORECASE | re.DOTALL)
                if keywords_match:
                    keywords = keywords_match.group(1).strip()
                    logger.info(f"[SEARCH AGENT] Kata kunci diekstrak dari reasoning: {keywords}")
                else:
                    # Jika tidak ditemukan, gunakan query asli
                    keywords = query
                    logger.info(f"[SEARCH AGENT] Tidak menemukan kata kunci spesifik, menggunakan query asli: {keywords}")
            else:
                keywords = query
                logger.info(f"[SEARCH AGENT] Sequential thinking tidak memberikan hasil, menggunakan query asli: {keywords}")

            logger.info(f"[SEARCH AGENT] Kata kunci yang akan digunakan untuk pencarian: {keywords}")

            # Gunakan searxng_service untuk pencarian
            search_results = searxng_service.search_compliance_info(keywords)

            if search_results:
                logger.info(f"[SEARCH AGENT] Ditemukan {len(search_results)} hasil untuk kata kunci: {keywords}")

                # Format hasil pencarian
                formatted_results = []
                for result in search_results:
                    formatted_result = f"Title: {result.get('title', 'No title')}\n"
                    formatted_result += f"URL: {result.get('url', 'No URL')}\n"
                    formatted_result += f"Content: {result.get('content', '')[:300]}...\n\n"
                    formatted_results.append(formatted_result)

                # Gunakan pendekatan ReAct untuk mengevaluasi hasil
                evaluation_result = await call_sequential_thinking_tool(
                    "sequentialThinking",
                    {
                        "thought": f"Evaluasi apakah hasil pencarian internet untuk query: '{query}' ini relevan.", # <--- Gunakan key 'thought' bukan 'input'
                        "thoughtNumber": 2,
                        "totalThoughts": 2
                    }
                )

                if evaluation_result and "result" in evaluation_result:
                    return f"Evaluation: {evaluation_result['result']}\n\n" + "\n".join(formatted_results)
                else:
                    return "\n".join(formatted_results)
            else:
                logger.info(f"[SEARCH AGENT] Tidak ditemukan hasil untuk kata kunci: {keywords}")
                return "No results found from internet search."
        except Exception as e:
            logger.error(f"Error searching internet: {str(e)}")
            return f"Error searching internet: {str(e)}"

    async def run_query(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """Run query through the search specialist agent"""
        try:
            # Cek dulu apakah sudah ada hasil serupa di memory
            logger.info(f"\033[94m[CHECKING MEMORY]\033[0m Checking search memory for query: {query}")
            memory_check = self.check_search_memory(query)

            if "No previous search results found" in memory_check:
                logger.info("\033[93m[NO CACHED RESULT]\033[0m No similar query found in search memory, performing new internet search")
                # Lakukan pencarian baru
                response = await self.search_internet(query)

                # Simpan hasil pencarian ke memory jika session_id disediakan
                if session_id:
                    logger.info("\033[95m[SAVING RESULTS]\033[0m Saving new search results to MySQL and Milvus")
                    # Ekstrak informasi dari hasil pencarian untuk disimpan
                    results_summary = self._extract_summary_from_response(response)
                    source_urls = self._extract_urls_from_response(response)

                    # Simpan ke MySQL search_history
                    search_id = memory_manager.save_search_history(query, results_summary, source_urls, session_id)
                    logger.info(f"\033[95m[SAVED TO MYSQL]\033[0m Saved search history to MySQL with ID: {search_id}")

                    # Simpan ke Milvus search_memory
                    if search_id:
                        memory_manager.save_search_memory(results_summary, search_id, session_id, source_urls)
                        logger.info(f"\033[95m[SAVED TO MILVUS]\033[0m Saved search memory to Milvus with search_id: {search_id}")
            else:
                logger.info("\033[92m[USING CACHED RESULT]\033[0m Found similar query in search memory, using cached results")
                # Gunakan hasil dari memory
                response = memory_check

            return {
                "agent_id": "search_specialist",
                "response": response,
                "sources": ["searxng_internet", "search_memory"],
                "confidence": 0.7  # Placeholder
            }
        except Exception as e:
            logger.error(f"Error in search specialist agent: {str(e)}")
            return {
                "agent_id": "search_specialist",
                "response": f"Error processing query: {str(e)}",
                "sources": [],
                "confidence": 0.0
            }

    def _extract_summary_from_response(self, response: str) -> str:
        """Ekstrak ringkasan dari respons pencarian"""
        # Jika respons kosong, kembalikan string default
        if not response or len(response.strip()) < 10:
            return "Ringkasan hasil pencarian dari internet"

        # Hapus bagian evaluasi jika ada
        if "Evaluation:" in response:
            response = response.split("Evaluation:")[1]

        # Ambil bagian konten dari hasil pencarian
        lines = response.split("\n")
        content_lines = []
        for line in lines:
            if line.startswith("Content:") or line.startswith("Title:"):
                content_lines.append(line)

        # Jika tidak ada konten yang ditemukan, gunakan sebagian dari respons
        if not content_lines:
            # Ambil bagian awal dari respons sebagai ringkasan
            summary = response[:1000]
            # Pastikan tidak mengandung karakter yang tidak valid
            summary = summary.replace('\x00', '').strip()
            return summary if summary else "Ringkasan hasil pencarian dari internet"

        result = "\n".join(content_lines)[:1000]  # Batasi panjang ringkasan
        # Pastikan tidak mengandung karakter yang tidak valid
        result = result.replace('\x00', '').strip()
        return result if result else "Ringkasan hasil pencarian dari internet"

    def _extract_urls_from_response(self, response: str) -> List[str]:
        """Ekstrak URL dari respons pencarian"""
        import re

        # Cari URL dalam respons menggunakan pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, response)

        # Jika tidak ada URL yang ditemukan dari pattern, coba ekstrak dari format "URL: [actual_url]"
        if not urls:
            # Cari pola "URL: [url]" dalam respons
            url_lines = [line for line in response.split('\n') if line.strip().startswith('URL:')]
            for line in url_lines:
                # Ekstrak URL dari format "URL: [url]"
                found_urls = re.findall(url_pattern, line)
                urls.extend(found_urls)

        return list(set(urls))  # Hapus duplikat


# Fungsi untuk membuat instance agen
def create_local_specialist_agent() -> LocalSpecialistAgent:
    """Create and return a Local Specialist Agent instance"""
    return LocalSpecialistAgent()


def create_search_specialist_agent() -> SearchSpecialistAgent:
    """Create and return a Search Specialist Agent instance"""
    return SearchSpecialistAgent()