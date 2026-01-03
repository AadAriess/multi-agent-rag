"""
Aggregator Agent untuk Multi Agent RAG
Menggunakan LangGraph untuk koordinasi antar agen
"""
import asyncio
from typing import Dict, List, Any, Optional
from langchain_core.agents import AgentFinish
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, END
from pydantic import BaseModel
from app.core.config import settings
from app.llms.agents.chatbot.specialist_agents import create_local_specialist_agent, create_search_specialist_agent
from app.llms.agents.tools.mcp_tool import call_sequential_thinking_tool
from langchain_openai import ChatOpenAI
import logging

logger = logging.getLogger(__name__)


class AgentState(BaseModel):
    """State untuk LangGraph"""
    query: str
    local_response: Optional[Dict[str, Any]] = None
    search_response: Optional[Dict[str, Any]] = None
    final_response: Optional[str] = None
    reasoning: Optional[str] = None
    session_id: Optional[str] = None
    conflict_resolved: bool = False


class AggregatorAgent:
    """
    Aggregator Agent (CoT & Supervisor Logic)
    - CoT Analysis: Saat Query masuk, Aggregator harus membedah:
      "Apakah ini butuh data internal, eksternal, atau keduanya?"
    - LangGraph Routing: Gunakan Graph untuk memicu Agent 1 & 2 secara paralel.
    - Conflict Resolution: Jika ada perbedaan antara data lokal (Agent 1) dan internet (Agent 2),
      Aggregator harus memberikan penalaran (Reasoning) mana yang lebih relevan.
    """

    def __init__(self):
        # Inisialisasi LLM
        self.llm = ChatOpenAI(
            model=settings.llm_model_name,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            temperature=0.1
        )

        # Buat agen spesialis
        self.local_agent = create_local_specialist_agent()
        self.search_agent = create_search_specialist_agent()

        # Bangun graph
        self.graph = self._build_graph()

        # Inisialisasi Redis service untuk state management
        from app.services.redis_service import redis_service
        self.redis_service = redis_service

    def _get_context_from_session(self, session_id: str) -> Dict[str, Any]:
        """Ambil konteks dari session sebelumnya dari tabel contexts"""
        from app.llms.agents.chatbot.memory_manager import memory_manager
        if session_id:
            context = memory_manager.get_conversation_context(session_id)
            if context:
                # Cek apakah context adalah list atau dict
                import json
                if isinstance(context, str):
                    try:
                        parsed_context = json.loads(context)
                        return parsed_context
                    except json.JSONDecodeError:
                        return {}
                return context
            return {}
        return {}

    def _update_context_for_session(self, session_id: str, query: str, response: str, agent_responses: List[Dict]) -> bool:
        """Update konteks untuk session dengan menambahkan query dan response baru"""
        from app.llms.agents.chatbot.memory_manager import memory_manager
        from app.database.mysql_config import get_db
        from app.models.database_schema import Context
        import json
        from datetime import datetime

        if not session_id:
            return False

        # Ambil konteks sebelumnya
        existing_context = self._get_context_from_session(session_id)

        # Buat entri baru TANPA agent_responses
        new_entry = {
            "query": query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }

        # Cek apakah existing_context adalah list (masih <= 10 percakapan) atau dict (sudah > 10 percakapan)
        if isinstance(existing_context, list):
            # Cek apakah entri baru sudah ada di dalam existing_context untuk mencegah duplikasi
            is_duplicate = any(
                item['query'] == new_entry['query'] and item['response'] == new_entry['response']
                for item in existing_context
            )

            if not is_duplicate:
                # Masih dalam mode list (<= 10 percakapan)
                updated_context = existing_context + [new_entry]

                # Cek apakah sudah lebih dari 10, jika ya ubah ke format summary + history
                if len(updated_context) > 10:
                    # Buat ringkasan dari 10 percakapan pertama
                    history_to_summarize = updated_context[:-1]  # Ambil 10 percakapan pertama
                    history_text = "\n".join([
                        f"Pertanyaan: {item['query']}\nJawaban: {item['response']}"
                        for item in history_to_summarize
                    ])

                    summarize_prompt = f"""
                    Kamu adalah Senior Knowledge Engineer yang bertugas mengelola ingatan jangka panjang AI.

                    Tugas: Ringkas riwayat percakapan antara User dan AI menjadi satu paragraf ringkasan konteks (Summary) yang padat dan informatif.

                    Input:
                    1. Current Summary (Ringkasan sebelumnya jika ada):
                    2. Last 10 Conversations (Daftar 10 tanya-jawab terakhir yang akan diringkas):
                    {history_text}

                    Instruksi Ketat:
                    1. Pertahankan Identitas: Jangan pernah menghapus nomor peraturan (misal: PERMENHAN No. 30 Tahun 2019), nama lembaga, atau tanggal-tanggal penting.
                    2. Gabungkan Informasi: Ringkasan baru harus menggabungkan poin-poin penting dari Last 10 Conversations ke dalam Current Summary secara koheren.
                    3. Hapus Redundansi: Buang basa-basi seperti "User bertanya tentang..." atau "AI menjelaskan bahwa...". Langsung tuliskan faktanya.
                    4. Fokus pada Fakta Terakhir: Jika ada perubahan aturan yang ditemukan oleh Agent Search, pastikan ringkasan mencatat status terbaru tersebut.
                    5. Output: Hanya berikan teks ringkasannya saja dalam satu atau dua paragraf.

                    Contoh Output Bagus: "Diskusi berfokus pada PERMENHAN No. 30 Tahun 2019 tentang Administrasi Umum Kemenhan. Poin utama meliputi struktur penomoran dokumen resmi, jenis surat perintah, dan prosedur paraf hierarkis. Ditemukan tambahan informasi bahwa untuk tahun 2025, terdapat digitalisasi tanda tangan yang harus divalidasi oleh Biro TU."

                    Ringkasan:
                    """

                    summary_response = self.llm.invoke(summarize_prompt).content

                    # Ubah ke format summary + history
                    converted_context = {
                        "summary": summary_response,
                        "history": [updated_context[-1]]  # Hanya entri ke-11
                    }

                    # Simpan ke database
                    context_json = json.dumps(converted_context)
                else:
                    # Masih dalam format list, simpan langsung
                    context_json = json.dumps(updated_context)
            else:
                # Jika entri duplikat, gunakan konteks yang sudah ada
                context_json = json.dumps(existing_context)
        elif isinstance(existing_context, dict):
            # Sudah dalam format summary + history (> 10 percakapan)
            # Cek apakah entri baru sudah ada di dalam history untuk mencegah duplikasi
            history = existing_context.get("history", [])
            is_duplicate = any(
                item['query'] == new_entry['query'] and item['response'] == new_entry['response']
                for item in history
            )

            if not is_duplicate:
                # Tambahkan entri baru ke history
                updated_history = history + [new_entry]

                # Cek apakah history sudah lebih dari 10, jika ya lakukan summarization lagi
                if len(updated_history) > 10:
                    # Buat ringkasan dari 10 percakapan dalam history
                    history_to_summarize = updated_history[:-1]  # Ambil 10 percakapan pertama
                    history_text = "\n".join([
                        f"Pertanyaan: {item['query']}\nJawaban: {item['response']}"
                        for item in history_to_summarize
                    ])

                    summarize_prompt = f"""
                    Kamu adalah Senior Knowledge Engineer yang bertugas mengelola ingatan jangka panjang AI.

                    Tugas: Ringkas riwayat percakapan antara User dan AI menjadi satu paragraf ringkasan konteks (Summary) yang padat dan informatif.

                    Input:
                    1. Current Summary (Ringkasan sebelumnya jika ada): {existing_context.get("summary", "")}
                    2. Last 10 Conversations (Daftar 10 tanya-jawab terakhir yang akan diringkas):
                    {history_text}

                    Instruksi Ketat:
                    1. Pertahankan Identitas: Jangan pernah menghapus nomor peraturan (misal: PERMENHAN No. 30 Tahun 2019), nama lembaga, atau tanggal-tanggal penting.
                    2. Gabungkan Informasi: Ringkasan baru harus menggabungkan poin-poin penting dari Last 10 Conversations ke dalam Current Summary secara koheren.
                    3. Hapus Redundansi: Buang basa-basi seperti "User bertanya tentang..." atau "AI menjelaskan bahwa...". Langsung tuliskan faktanya.
                    4. Fokus pada Fakta Terakhir: Jika ada perubahan aturan yang ditemukan oleh Agent Search, pastikan ringkasan mencatat status terbaru tersebut.
                    5. Output: Hanya berikan teks ringkasannya saja dalam satu atau dua paragraf.

                    Contoh Output Bagus: "Diskusi berfokus pada PERMENHAN No. 30 Tahun 2019 tentang Administrasi Umum Kemenhan. Poin utama meliputi struktur penomoran dokumen resmi, jenis surat perintah, dan prosedur paraf hierarkis. Ditemukan tambahan informasi bahwa untuk tahun 2025, terdapat digitalisasi tanda tangan yang harus divalidasi oleh Biro TU."

                    Ringkasan:
                    """

                    new_summary = self.llm.invoke(summarize_prompt).content

                    # Gunakan summary yang sudah digabungkan oleh LLM
                    # Reset history hanya menyisakan entri ke-11
                    updated_history = [updated_history[-1]]

                    updated_context = {
                        "summary": new_summary,
                        "history": updated_history
                    }
                else:
                    # Update history saja
                    updated_context = {
                        "summary": existing_context.get("summary", ""),
                        "history": updated_history
                    }

                # Simpan ke database
                context_json = json.dumps(updated_context)
            else:
                # Jika entri duplikat, gunakan konteks yang sudah ada
                context_json = json.dumps(existing_context)
        else:
            # Jika tidak ada konteks sebelumnya, buat dalam format list
            context_json = json.dumps([new_entry])

        # Simpan konteks yang telah diperbarui ke database
        try:
            # Dapatkan session database
            db = next(get_db())

            # Cek apakah sudah ada konteks untuk session ini
            existing_record = db.query(Context).filter(Context.session_id == session_id).first()

            if existing_record:
                # Update konteks yang sudah ada
                existing_record.data = context_json
                existing_record.updated_at = datetime.now()  # Update waktu terakhir diubah
            else:
                # Buat konteks baru
                new_context = Context(
                    session_id=session_id,
                    data=context_json
                )
                db.add(new_context)

            db.commit()
            db.close()

            logger.info(f"Successfully saved conversation context for session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving conversation context: {str(e)}")
            return False

    async def _analyze_query_type(self, query: str) -> str:
        """Analisis jenis query: internal, external, atau keduanya"""
        # Gunakan server sequential-thinking melalui MCP untuk menganalisis jenis query secara dinamis
        try:
            logger.info(f"[ANALYZE_QUERY_TYPE] Mengirim query ke sequential thinking: {query}")

            # Gunakan MCP untuk memanggil fungsi sequential thinking
            result = await call_sequential_thinking_tool(
                "sequentialthinking", 
                {
                    "thought": f"Analisis kebutuhan data untuk query: {query}. Tentukan 'internal', 'external', atau 'both'.",
                    "thoughtNumber": 1,
                    "totalThoughts": 1
                }
            )

            logger.info(f"[ANALYZE_QUERY_TYPE] Hasil dari sequential thinking: {result}")

            if result and "result" in result:
                # MCP Sequential Thinking mengembalikan string yang seringkali berisi JSON
                analysis_text = result["result"].lower()
            
                # Cek kata kunci di dalam teks hasil reasoning
                if "internal" in analysis_text and "external" in analysis_text:
                    return "both"
                elif "both" in analysis_text:
                    return "both"
                elif "internal" in analysis_text:
                    return "internal"
                elif "external" in analysis_text:
                    return "external"
                
                logger.warning(f"Keputusan tidak eksplisit di hasil MCP, menggunakan default 'both'")
                return "both"
            
            return "both"
        except Exception as e:
            logger.error(f"Error saat menganalisis jenis query dengan sequential thinking: {e}, menggunakan default 'both'")
            # Jika MCP gagal, kembali ke metode LLM biasa
            return await self._analyze_query_type_fallback(query)

    def _analyze_query_type_fallback(self, query: str) -> str:
        """Fallback untuk analisis jenis query jika MCP tidak tersedia"""
        # Gunakan LLM untuk menganalisis jenis query secara dinamis
        analysis_prompt = f"""
        Analisis pertanyaan berikut dan tentukan apakah membutuhkan:
        1. Informasi dari sumber internal (seperti kebijakan perusahaan, prosedur, dokumen internal)
        2. Informasi dari sumber eksternal (seperti berita terkini, informasi publik, data terbaru)
        3. Kombinasi keduanya

        Pertanyaan: {query}

        Jawab dengan salah satu: "internal", "external", atau "both"
        """

        try:
            response = self.llm.invoke(analysis_prompt)
            analysis_result = response.content.strip().lower()

            # Validasi hasil analisis
            if analysis_result in ["internal", "external", "both"]:
                return analysis_result
            else:
                # Jika LLM memberikan jawaban tak terduga, kembalikan default
                logger.warning(f"LLM memberikan jawaban tak terduga: {analysis_result}, menggunakan default 'both'")
                return "both"
        except Exception as e:
            logger.error(f"Error saat menganalisis jenis query: {e}, menggunakan default 'both'")
            return "both"

    async def _run_local_agent(self, state: AgentState) -> Dict[str, Any]:
        """Jalankan local specialist agent"""
        logger.info("Running local specialist agent")

        # Simpan state ke Redis sebelum eksekusi
        if state.session_id:
            state_key = f"graph_state:{state.session_id}"
            state_data = {
                "current_task": "running_local_agent",
                "query": state.query,
                "session_id": state.session_id
            }
            self.redis_service.set_cache(state_key, str(state_data), expire=3600)  # 1 jam expiry

        response = await self.local_agent.run_query(state.query)

        # Update state di Redis setelah eksekusi
        if state.session_id:
            state_key = f"graph_state:{state.session_id}"
            state_data = {
                "current_task": "local_agent_completed",
                "query": state.query,
                "response": response,
                "session_id": state.session_id
            }
            self.redis_service.set_cache(state_key, str(state_data), expire=3600)

        return {"local_response": response}

    async def _run_search_agent(self, state: AgentState) -> Dict[str, Any]:
        """Jalankan search specialist agent"""
        logger.info("Running search specialist agent")

        # Simpan state ke Redis sebelum eksekusi
        if state.session_id:
            state_key = f"graph_state:{state.session_id}"
            state_data = {
                "current_task": "running_search_agent",
                "query": state.query,
                "session_id": state.session_id
            }
            self.redis_service.set_cache(state_key, str(state_data), expire=3600)  # 1 jam expiry

        response = await self.search_agent.run_query(state.query, state.session_id)

        # Update state di Redis setelah eksekusi
        if state.session_id:
            state_key = f"graph_state:{state.session_id}"
            state_data = {
                "current_task": "search_agent_completed",
                "query": state.query,
                "response": response,
                "session_id": state.session_id
            }
            self.redis_service.set_cache(state_key, str(state_data), expire=3600)

        return {"search_response": response}

    async def _aggregate_responses(self, state: AgentState) -> Dict[str, Any]:
        """Aggregasi dan resolusi konflik antara respon agen"""
        logger.info(f"[AGGREGATOR] Aggregating responses for query: '{state.query}'")

        local_response = state.local_response
        search_response = state.search_response

        # Log informasi dari kedua agen
        if local_response:
            logger.info(f"[AGGREGATOR] Local agent response: {local_response['response'][:200]}...")
        else:
            logger.info("[AGGREGATOR] No response from local agent")

        if search_response:
            logger.info(f"[AGGREGATOR] Search agent response: {search_response['response'][:200]}...")
        else:
            logger.info("[AGGREGATOR] No response from search agent")

        # Ambil konteks dari session sebelumnya jika ada
        context = {}
        if state.session_id:
            context = self._get_context_from_session(state.session_id)

        # Gunakan analisis query type yang telah diperbarui
        query_type = await self._analyze_query_type(state.query)

        # Penjelasan penalaran (reasoning) menggunakan pendekatan CoT
        reasoning = f"Query analysis: Determined that this query requires {'both internal and external' if query_type == 'both' else query_type} sources.\n"

        # Gabungkan respon dari kedua agen
        combined_response = ""
        sources = []

        if local_response:
            combined_response += f"Internal Knowledge Base Response:\n{local_response['response']}\n\n"
            sources.extend(local_response.get('sources', []))

        if search_response:
            combined_response += f"External Search Response:\n{search_response['response']}\n\n"
            sources.extend(search_response.get('sources', []))

        # Deteksi dan tangani konflik menggunakan pendekatan CoT
        conflict_resolved = False
        if local_response and search_response:
            # Gunakan pendekatan CoT untuk menyelesaikan konflik
            try:
                # Gunakan MCP untuk memanggil fungsi sequential thinking untuk resolusi konflik
                conflict_resolution = await call_sequential_thinking_tool(
                    "sequentialthinking",
                    {
                        "thought": (
                            f"User bertanya: {state.query}. Data internal mengatakan X, internet mengatakan Y. "
                            "Selesaikan kontradiksi ini dan simpulkan mana yang lebih akurat untuk User. "
                            "Berikan ringkasan solusi konflik Anda."
                        ),
                        "thoughtNumber": 1,
                        "totalThoughts": 1
                    }
                )

                if conflict_resolution and "result" in conflict_resolution:
                    # Simpan hasil reasoning agar bisa dibaca oleh LLM final
                    reasoning += f"Conflict Resolution Insight: {conflict_resolution['result']}\n"
                    conflict_resolved = True
                else:
                    # Jika sequential thinking tidak memberikan hasil, gunakan logika sederhana
                    if "tidak ditemukan" in local_response['response'].lower() and "tidak ditemukan" not in search_response['response'].lower():
                        reasoning += "Internal knowledge base did not contain relevant information, prioritizing external search results.\n"
                        conflict_resolved = True
                    elif "baru" in state.query.lower() or "terkini" in state.query.lower():
                        reasoning += "Query indicates need for latest information, prioritizing external search results.\n"
                        conflict_resolved = True
                    else:
                        reasoning += "Both sources provide relevant information, combining insights.\n"
                        conflict_resolved = True
            except Exception as e:
                logger.error(f"Error saat menggunakan sequential thinking untuk resolusi konflik: {e}")
                # Jika MCP gagal, gunakan logika sederhana
                if "tidak ditemukan" in local_response['response'].lower() and "tidak ditemukan" not in search_response['response'].lower():
                    reasoning += "Internal knowledge base did not contain relevant information, prioritizing external search results.\n"
                    conflict_resolved = True
                elif "baru" in state.query.lower() or "terkini" in state.query.lower():
                    reasoning += "Query indicates need for latest information, prioritizing external search results.\n"
                    conflict_resolved = True
                else:
                    reasoning += "Both sources provide relevant information, combining insights.\n"
                    conflict_resolved = True

        # Gunakan LLM untuk menghasilkan respons akhir yang koheren
        # Tambahkan konteks dari percakapan sebelumnya ke dalam prompt
        context_info = ""

        # Cek apakah context adalah list (masih <= 10 percakapan) atau dict (sudah > 10 percakapan)
        if isinstance(context, list):
            # Context masih dalam format list, ambil 3 percakapan terakhir
            recent_history = context[-3:] if len(context) >= 3 else context
            for item in recent_history:
                context_info += f"Pertanyaan sebelumnya: {item.get('query', '')}\n"
                context_info += f"Jawaban sebelumnya: {item.get('response', '')}\n"
        elif isinstance(context, dict):
            # Context dalam format summary + history
            if "summary" in context and context["summary"]:
                context_info += f"Latar belakang percakapan sebelumnya: {context['summary']}\n"
            if "history" in context and context["history"]:
                recent_history = context["history"][-3:]  # Ambil 3 percakapan terakhir
                for item in recent_history:
                    context_info += f"Pertanyaan sebelumnya: {item.get('query', '')}\n"
                    context_info += f"Jawaban sebelumnya: {item.get('response', '')}\n"

        final_prompt = f"""
        Kamu adalah Senior Aggregator Agent yang bertugas menyusun jawaban komprehensif. 
        Tugasmu adalah menjawab pertanyaan pengguna: "{state.query}" 
        
        Gunakan data berikut sebagai referensi:
        ---
        KONTEKS PERCAKAPAN SEBELUMNYA:
        {context_info if context_info else "Tidak ada konteks sebelumnya."}
        
        HASIL TEMUAN AGEN SPESIALIS:
        {combined_response}
        ---

        INSTRUKSI KETAT PENYUSUNAN JAWABAN:
        1. VALIDASI RELEVANSI: Periksa setiap temuan agen. Jika ada dokumen (misal: peraturan pemerintah/Permenhan) yang sama sekali tidak relevan dengan topik pertanyaan (misal: fisika kuantum), ABAIKAN dokumen tersebut. Jangan memaksakan menghubungkan informasi yang tidak berhubungan.
        2. PRIORITAS SUMBER: Jika pertanyaan bersifat umum/ilmiah, prioritaskan temuan dari 'External Search'. Jika pertanyaan bersifat prosedural/aturan internal, prioritaskan 'Internal Knowledge Base'.
        3. GAYA BAHASA: Berikan jawaban yang mudah dipahami dan alami seperti percakapan sehari-hari. Gunakan Bahasa Indonesia yang santun namun tidak kaku.
        4. PENANGANAN KONFLIK: Jika ada perbedaan data antara sumber internal dan eksternal, jelaskan perbedaannya secara transparan dan berikan rekomendasi mana yang lebih akurat untuk situasi pengguna.
        5. FORMAT: Jawab dalam paragraf naratif yang mengalir. Hindari penggunaan markdown berlebihan seperti banyak simbol **, #, atau list peluru (-) kecuali sangat diperlukan untuk kejelasan poin.
        6. KONTEKS: Gunakan riwayat percakapan sebelumnya untuk memberikan jawaban yang lebih personal dan nyambung dengan diskusi sebelumnya.

        Jawaban:
        """

        final_response = self.llm.invoke(final_prompt).content

        logger.info(f"[AGGREGATOR] Final response generated: {final_response[:200]}...")

        return {
            "final_response": final_response,
            "reasoning": reasoning,
            "sources": sources,
            "conflict_resolved": conflict_resolved,
            "local_response": local_response,
            "search_response": search_response
        }

    def _build_graph(self) -> StateGraph:
        """Bangun graf dengan LangGraph"""
        from langgraph.graph import START, END

        graph = StateGraph(AgentState)

        # Tambahkan nodes
        graph.add_node("local_agent", self._run_local_agent)
        graph.add_node("search_agent", self._run_search_agent)
        graph.add_node("aggregator", self._aggregate_responses)

        # Jalankan kedua agen secara paralel dari START
        graph.add_edge(START, "local_agent")
        graph.add_edge(START, "search_agent")

        # Gunakan mekanisme sinkronisasi sederhana:
        # Aggregator akan menunggu kedua agen selesai sebelum dijalankan
        # Kita akan menggabungkan hasil dari kedua agen ke aggregator
        graph.add_edge(["local_agent", "search_agent"], "aggregator")

        # Tambahkan edge dari aggregator ke END
        graph.add_edge("aggregator", END)

        return graph.compile()

    async def ainvoke(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """Jalankan aggregator agent secara async"""
        logger.info(f"Starting aggregation for query: {query}")

        # Ambil konteks dari session sebelumnya jika ada
        context = self._get_context_from_session(session_id) if session_id else {}

        # Tambahkan konteks ke state jika ada
        initial_state = AgentState(
            query=query,
            session_id=session_id
        )

        # Jalankan graph
        result = await self.graph.ainvoke(initial_state)

        # Jika result adalah dictionary (karena LangGraph mengembalikan dictionary)
        if isinstance(result, dict):
            # Update konteks session dengan hasil baru
            if session_id:
                # Tidak menyertakan agent_responses dalam konteks
                self._update_context_for_session(
                    session_id=session_id,
                    query=query,
                    response=result.get("final_response", ""),
                    agent_responses=[]  # Kosongkan karena tidak disimpan
                )

            return {
                "final_response": result.get("final_response", ""),
                "reasoning": result.get("reasoning", ""),
                "sources": result.get("sources", []),
                "conflict_resolved": result.get("conflict_resolved", False),
                "local_response": result.get("local_response", None),
                "search_response": result.get("search_response", None)
            }
        else:
            # Jika result adalah objek AgentState
            # Update konteks session dengan hasil baru
            if session_id:
                # Tidak menyertakan agent_responses dalam konteks
                self._update_context_for_session(
                    session_id=session_id,
                    query=query,
                    response=result.final_response,
                    agent_responses=[]  # Kosongkan karena tidak disimpan
                )

            return {
                "final_response": result.final_response,
                "reasoning": result.reasoning,
                "sources": self._extract_sources(result),
                "conflict_resolved": result.conflict_resolved,
                "local_response": result.local_response,
                "search_response": result.search_response
            }

    def invoke(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """Jalankan aggregator agent secara sync"""
        # Karena graph hanya memiliki metode async, kita jalankan dalam event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Jika tidak ada event loop, buat baru
            return asyncio.run(self.ainvoke(query, session_id))
        else:
            # Jika sudah ada event loop, gunakan thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.ainvoke(query, session_id))
                return future.result()

    def _extract_sources(self, result: AgentState) -> List[str]:
        """Ekstrak sumber dari hasil agen"""
        sources = []

        if result.local_response and result.local_response.get('sources'):
            sources.extend(result.local_response['sources'])

        if result.search_response and result.search_response.get('sources'):
            sources.extend(result.search_response['sources'])

        return list(set(sources))  # Hapus duplikat


# Fungsi untuk membuat instance aggregator agent
def create_aggregator_agent() -> AggregatorAgent:
    """Create and return an Aggregator Agent instance"""
    return AggregatorAgent()