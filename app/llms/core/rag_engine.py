"""
Modul utama RAG engine untuk aplikasi OriensSpace AI
Menggabungkan fungsi RAG tradisional dan Multi Agent RAG
"""
import os
import sys
import json
import traceback
from typing import Dict, Any, Literal, List
from dotenv import load_dotenv
from llama_index.core import StorageContext, Settings, VectorStoreIndex
from llama_index.core.prompts.prompts import SimpleInputPrompt
from llama_index.core.retrievers import VectorIndexRetriever, QueryFusionRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.llms.openai_like import OpenAILike
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# ==============================================================================
# 0. KONFIGURASI DAN VALIDASI
# ==============================================================================

def setup_config() -> Dict[str, Any]:
    """
    Memuat variabel lingkungan dan memvalidasi konfigurasi.
    """
    load_dotenv()

    config_dict = {
        "VECTOR_STORE_DIR": "vector_store",  # For backward compatibility, but not used with Milvus
        "BASE_URL": settings.llm_base_url,
        "LLM_MODEL_NAME": settings.llm_model_name,
        # Mengambil nama model embedding dari .env (Contoh: nomic-embed-text:latest)
        "EMBEDDING_MODEL_NAME": settings.embedding_model_name,
        # Milvus Configuration
        "MILVUS_HOST": settings.milvus_host,
        "MILVUS_PORT": settings.milvus_port,
        "MILVUS_USER": settings.milvus_user,
        "MILVUS_PASSWORD": settings.milvus_password,
        "MILVUS_SECURE": settings.milvus_secure,
        # Configuration RAG
        "SIMILARITY_TOP_K": settings.similarity_top_k,
        "QUERY_FUSION_TOP_K": settings.query_fusion_top_k,
        "QUERY_FUSION_NUM_QUERIES": settings.query_fusion_num_queries,
        "CHUNK_SIZE": settings.chunk_size,
        "TIMEOUT": settings.timeout # Request timeout
    }

    required_vars = ["BASE_URL", "LLM_MODEL_NAME", "EMBEDDING_MODEL_NAME"]
    missing_vars = [var for var in required_vars if not config_dict.get(var)]

    if missing_vars:
        raise ValueError(
            f"!!! Konfigurasi Gagal !!! Pastikan semua variabel berikut disetel di .env: {', '.join(missing_vars)}"
        )

    return config_dict

# ==============================================================================
# 1. DEFINISI PROMPT TERPUSAT
# ==============================================================================

def define_prompts():
    """Mendefinisikan dan mengembalikan semua SimpleInputPrompt yang digunakan."""

    # Prompt untuk menjawab pertanyaan berdasarkan konteks
    QA_PROMPT_TEMPLATE = (
        """
        Anda adalah asisten AI yang membantu menjawab pertanyaan berdasarkan dokumen kepatuhan yang tersedia.

        Pertanyaan: {query_str}
        Konteks dari dokumen: {context_str}

        Berikan jawaban yang akurat dan informatif berdasarkan konteks yang tersedia. Jika informasi tidak ditemukan dalam konteks, berikan jawaban berdasarkan pengetahuan umum Anda. Gunakan Bahasa Indonesia yang baku dan formal.

        """
    )

    # Prompt untuk menghasilkan query pencarian jika tidak ada konteks yang ditemukan
    QUERY_GEN_PROMPT_TEMPLATE = (
        """
        Anda adalah asisten yang membantu menghasilkan pertanyaan pencarian berdasarkan pertanyaan pengguna.

        Pertanyaan pengguna: {query_str}

        Buat {num_queries} pertanyaan pencarian yang relevan untuk mencari informasi terkait di mesin pencarian. Fokus pada istilah kunci dan konsep utama dalam pertanyaan pengguna.

        Hasilkan pertanyaan-pertanyaan tersebut dalam format daftar, masing-masing pada baris baru:
        """
    )

    return {
        "qa": SimpleInputPrompt(QA_PROMPT_TEMPLATE),
        "query_gen": SimpleInputPrompt(QUERY_GEN_PROMPT_TEMPLATE)
    }


# ==============================================================================
# 2. FUNGSI INISIALISASI QUERY ENGINES
# ==============================================================================

def initialize_query_engines(config_dict: Dict[str, Any], prompts: Dict[str, SimpleInputPrompt]):
    """Inisialisasi model dan menyiapkan Query Engines sederhana untuk Q&A."""

    # 2.1 Inisialisasi Model LlamaIndex
    try:
        llm = OpenAILike(
                model=os.getenv("LLM_MODEL_NAME"),
                api_base=f"{config_dict['BASE_URL']}/v1",
                api_key=os.getenv("LLM_API_KEY"),
                is_chat_model=True
            )

        # Menggunakan OllamaEmbedding
        embed_model = OllamaEmbedding(
            model_name=config_dict["EMBEDDING_MODEL_NAME"],
            base_url=config_dict["BASE_URL"]
        )

        Settings.llm = llm
        Settings.embed_model = embed_model
        Settings.chunk_size = config_dict["CHUNK_SIZE"]
    except Exception as e:
        raise ConnectionError(f"Gagal inisialisasi LLM/Embedding (Ollama). Cek BASE_URL dan nama model: {e}")

    # Impor milvus_service
    from app.services.milvus_service import milvus_service

    # Simpan reference ke milvus_service untuk digunakan dalam enhanced_rag_chain
    global milvus_service_instance
    milvus_service_instance = milvus_service

    # Karena kita tidak menggunakan engine klasifikasi/validation/discussion,
    # kita hanya menyimpan reference ke milvus_service
    return {
        # Kita tetap kembalikan dict kosong karena fungsi lain mungkin mengharapkan struktur ini
    }


# ==============================================================================
# 3. LAYANAN TAMBAHAN (Redis dan SearXNG)
# ==============================================================================

from app.services.redis_service import redis_service
from app.services.searxng_service import searxng_service


def is_response_sufficient(response: str, min_length: int = 50) -> bool:
    """
    Evaluasi apakah respons dari RAG cukup informatif
    """
    # Cek panjang respons dan kata kunci umum yang menunjukkan ketidakpastian
    if len(response.strip()) < min_length:
        return False

    uncertain_keywords = [
        "tidak ditemukan", "tidak ada informasi",
        "saya tidak tahu", "saya tidak yakin",
        "tidak dapat menemukan", "belum tersedia"
    ]

    response_lower = response.lower()
    for keyword in uncertain_keywords:
        if keyword in response_lower:
            return False

    return True


def combine_rag_and_search(rag_response: str, search_results: List[Dict[str, Any]]) -> str:
    """
    Gabungkan respons RAG dengan hasil pencarian web
    """
    if not search_results:
        return rag_response

    # Format hasil pencarian
    search_summary = "\n\nInformasi tambahan dari pencarian web:\n"
    for i, result in enumerate(search_results[:3]):  # Ambil 3 hasil teratas
        search_summary += f"\n{i+1}. {result['title']}\n"
        search_summary += f"   Sumber: {result['url']}\n"
        search_summary += f"   Ringkasan: {result['content'][:200]}...\n"

    # Gabungkan respons
    combined_response = f"{rag_response}{search_summary}\n\nCatatan: Informasi di atas didapat dari hasil pencarian web dan mungkin memerlukan verifikasi lebih lanjut."

    return combined_response


def enhanced_rag_chain(draft_text: str, use_cache: bool = True) -> str:
    """
    Versi sederhana dari RAG chain dalam format Q&A, tetapi tetap menggunakan konteks dari Milvus dan SearXNG jika diperlukan
    """
    global milvus_service_instance

    # Gunakan cache jika diaktifkan
    cache_key = f"query:{hash(draft_text)}"
    if use_cache:
        cached_response = redis_service.get_cache(cache_key)
        if cached_response:
            print("-> Menggunakan respons dari cache")
            return cached_response

    print(f"-> Menganalisis pertanyaan: {draft_text[:50]}...")

    # 1. Coba cari konteks dari Milvus terlebih dahulu
    print("-> Mencari konteks dari Milvus...")
    try:
        # Ambil embedding untuk query
        from llama_index.core import Settings
        query_embedding = Settings.embed_model.get_text_embedding(draft_text)

        # Cari dokumen serupa dari Milvus
        search_results = milvus_service_instance.search_similar(query_embedding, top_k=10)  # Tambah jumlah hasil

        if search_results:
            print(f"-> Ditemukan {len(search_results)} dokumen dari Milvus")

            # Ambil hasil dengan skor tertinggi tanpa filter keywords
            # Urutkan berdasarkan skor kemiripan (distance terendah = kemiripan tertinggi)
            sorted_results = sorted(search_results, key=lambda x: x['distance'])

            # Ambil 5 hasil terbaik berdasarkan skor
            top_results = sorted_results[:5]

            # Gabungkan konteks dari hasil pencarian terbaik
            context_str = "\n".join([result['text'] for result in top_results])

            # Filter konteks untuk menghapus konten yang tidak relevan atau tidak bermakna
            # Hapus konten yang hanya berisi karakter berulang atau karakter acak
            import re
            # Hapus baris yang hanya berisi karakter X atau karakter acak
            context_str = re.sub(r'[Xx]{10,}', '', context_str)
            # Hapus baris yang hanya berisi karakter berulang
            context_str = re.sub(r'([^\w\s])\1{10,}', '', context_str)
            # Hapus baris yang hanya berisi karakter non-teks
            context_str = re.sub(r'^\s*[^\w\s]+\s*$', '', context_str, flags=re.MULTILINE)

            # Bersihkan whitespace berlebihan
            context_str = re.sub(r'\n\s*\n', '\n\n', context_str)

            print(f"-> Konteks telah difilter dan siap digunakan")
        else:
            print("-> Tidak ditemukan dokumen relevan dari Milvus")
            context_str = ""
    except Exception as e:
        print(f"-> Gagal mencari konteks dari Milvus: {e}")
        context_str = ""

    # 2. Siapkan LLM
    from llama_index.llms.openai_like import OpenAILike
    from llama_index.core import PromptTemplate

    llm = OpenAILike(
        model=os.getenv("LLM_MODEL_NAME"),
        api_base=f"{settings.llm_base_url}/v1",
        api_key=os.getenv("LLM_API_KEY"),
        is_chat_model=True
    )

    # 3. Evaluasi kualitas konteks dari Milvus
    print("-> Mengevaluasi kualitas konteks dari Milvus...")

    # Jika konteks kosong atau tidak relevan, langsung cari ke SearXNG
    if not context_str or len(context_str.strip()) < 50:  # Jika konteks kosong atau terlalu pendek
        print("-> Konteks dari Milvus tidak memadai, mencari informasi dari web...")

        search_results = searxng_service.search_compliance_info(draft_text)

        if search_results:
            print(f"-> Ditemukan {len(search_results)} hasil dari pencarian web")
            # Buat konteks dari hasil pencarian web
            web_context = "\n".join([
                f"Judul: {result['title']}\n"
                f"URL: {result['url']}\n"
                f"Ringkasan: {result['content'][:300]}..."
                for result in search_results[:3]  # Ambil 3 hasil teratas
            ])

            # Gunakan konteks dari web untuk menjawab pertanyaan
            web_qa_template = PromptTemplate(
                "Anda adalah asisten AI yang membantu menjawab pertanyaan berdasarkan informasi dari hasil pencarian web.\n\n"
                "Pertanyaan: {query_str}\n"
                "Informasi dari web: {web_context}\n\n"
                "Berikan jawaban berdasarkan informasi dari hasil pencarian web. "
                "Gunakan Bahasa Indonesia yang baku dan formal.\n\n"
                "Jawaban:"
            )

            formatted_template = web_qa_template.format(query_str=draft_text, web_context=web_context)
            response = llm.complete(formatted_template)
            rag_response = str(response.text)
        else:
            print("-> Tidak ditemukan hasil dari pencarian web")
            # Jika tidak ada konteks dari Milvus maupun web, beri respons umum
            general_template = PromptTemplate(
                "Anda adalah asisten AI yang membantu menjawab pertanyaan.\n\n"
                "Pertanyaan: {query_str}\n\n"
                "Berikan jawaban yang informatif dan akurat berdasarkan pengetahuan umum Anda. "
                "Gunakan Bahasa Indonesia yang baku dan formal.\n\n"
            )

            formatted_template = general_template.format(query_str=draft_text)
            response = llm.complete(formatted_template)
            rag_response = str(response.text)
    else:
        print("-> Menggunakan konteks dari Milvus untuk menjawab pertanyaan...")

        # Gunakan prompt QA yang lebih fokus untuk menjawab berdasarkan konteks
        qa_template = PromptTemplate(
            "Anda adalah asisten AI yang membantu menjawab pertanyaan berdasarkan dokumen kepatuhan resmi yang tersedia.\n\n"
            "Pertanyaan spesifik pengguna: {query_str}\n\n"
            "Konteks dari dokumen resmi: {context_str}\n\n"
            "Berikan jawaban yang akurat dan spesifik sesuai dengan pertanyaan pengguna berdasarkan konteks yang tersedia. "
            "Fokuslah pada informasi yang langsung menjawab pertanyaan dan hindari informasi yang tidak terkait. "
            "Jika konteks menyediakan informasi yang relevan, gunakan informasi tersebut untuk menjawab pertanyaan. "
            "Jika konteks tidak menyediakan informasi yang relevan untuk menjawab pertanyaan secara spesifik, berikan jawaban bahwa informasi tersebut tidak ditemukan dalam dokumen yang telah diindeks. "
            "Gunakan Bahasa Indonesia yang baku dan formal. Jawaban HARUS dalam bentuk narasi teks murni. JANGAN GUNAKAN format markdown seperti **, -, #, atau bentuk format lainnya. "
            "Hanya gunakan kalimat biasa yang runtut dan mudah dibaca.\n\n"
        )

        # Format template dan dapatkan respons
        formatted_template = qa_template.format(query_str=draft_text, context_str=context_str)
        response = llm.complete(formatted_template)
        rag_response = str(response.text)

        # Jika jawaban menyatakan bahwa informasi tidak ditemukan, coba cari ke SearXNG
        if "tidak ditemukan" in rag_response.lower() or "informasi tersebut tidak ditemukan" in rag_response.lower():
            print("-> Jawaban dari Milvus menyatakan informasi tidak ditemukan, mencari informasi dari web...")

            search_results = searxng_service.search_compliance_info(draft_text)

            if search_results:
                print(f"-> Ditemukan {len(search_results)} hasil dari pencarian web")
                # Buat konteks dari hasil pencarian web
                web_context = "\n".join([
                    f"Judul: {result['title']}\n"
                    f"URL: {result['url']}\n"
                    f"Ringkasan: {result['content'][:300]}..."
                    for result in search_results[:3]  # Ambil 3 hasil teratas
                ])

                # Gunakan konteks dari web untuk menjawab pertanyaan
                web_qa_template = PromptTemplate(
                    "Anda adalah asisten AI yang membantu menjawab pertanyaan berdasarkan informasi dari hasil pencarian web.\n\n"
                    "Pertanyaan: {query_str}\n"
                    "Informasi dari web: {web_context}\n\n"
                    "Berikan jawaban berdasarkan informasi dari hasil pencarian web. "
                    "Gunakan Bahasa Indonesia yang baku dan formal.\n\n"
                )

                formatted_template = web_qa_template.format(query_str=draft_text, web_context=web_context)
                response = llm.complete(formatted_template)
                rag_response = str(response.text)
            else:
                print("-> Tidak ditemukan hasil dari pencarian web")

    # Fungsi untuk membersihkan output dari format markdown
    def clean_markdown_format(text: str) -> str:
        import re
        # Hapus bold format **text**
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        # Hapus bullet points dengan -
        text = re.sub(r'^\s*-\s+', '', text, flags=re.MULTILINE)
        # Hapus bullet points dengan angka
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        # Hapus header markdown #
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        # Hapus format list lainnya
        text = re.sub(r'^\s*\*\s+', '', text, flags=re.MULTILINE)
        # Hapus baris kosong berlebihan
        text = re.sub(r'\n\s*\n', '\n\n', text)
        # Hilangkan spasi berlebihan di awal dan akhir paragraf
        text = re.sub(r'\n\s+', '\n', text)
        return text.strip()

    # Bersihkan respons dari format markdown
    rag_response = clean_markdown_format(rag_response)

    # Simpan ke cache jika diaktifkan
    if use_cache:
        redis_service.set_cache(cache_key, rag_response, expire=3600)  # Cache selama 1 jam

    # Mengembalikan response teks dari LLM
    return rag_response


# ==============================================================================
# 4. GLOBAL VARIABLE DAN ROUTING FUNCTION
# ==============================================================================

# Lakukan inisialisasi di luar fungsi agar hanya dipanggil sekali
try:
    print("--- [STARTING: LLM CHAIN INITIALIZATION] ---")
    APP_CONFIG = setup_config()
    PROMPTS = define_prompts()
    QUERY_ENGINES = initialize_query_engines(APP_CONFIG, PROMPTS)
    print("--- [SUCCESS: LLM CHAIN READY FOR API] ---")
except (ValueError, FileNotFoundError, ConnectionError, IOError) as e:
    # Menangkap error spesifik selama inisialisasi dan menghentikan proses
    print(f"!!! KRITIS: GAGAL MEMUAT QUERY ENGINE !!!")
    print(f"ERROR DETAIL: {e}")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"!!! KRITIS: GAGAL TOTAL SELAMA INISIALISASI !!!")
    print(f"ERROR DETAIL: {e}")
    traceback.print_exc()
    sys.exit(1)


def run_rag_chain(draft_text: str) -> str:
    """
    Fungsi utama untuk menjalankan RAG chain dalam format Q&A sederhana.
    """
    return enhanced_rag_chain(draft_text)


# ==============================================================================
# 5. INTEGRASI DENGAN MULTI AGENT RAG
# ==============================================================================

def run_multi_agent_rag(query: str, session_id: str = None) -> Dict[str, Any]:
    """
    Fungsi untuk menjalankan sistem Multi Agent RAG
    """
    from app.llms.agents.chatbot.aggregator_agent import create_aggregator_agent
    from app.llms.agents.chatbot.memory_manager import memory_manager

    # Buat aggregator agent
    aggregator_agent = create_aggregator_agent()

    # Jalankan query melalui aggregator agent
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        # Jika sudah ada event loop, gunakan thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, aggregator_agent.ainvoke(query, session_id))
            result = future.result()
    except RuntimeError:
        # Jika tidak ada event loop, buat baru
        result = asyncio.run(aggregator_agent.ainvoke(query, session_id))

    # Simpan konteks percakapan
    # Ambil respons dari state akhir dari LangGraph
    local_response = result.get("local_response", {})
    search_response = result.get("search_response", {})

    agent_responses = [
        {"agent_id": "local_specialist", "response": local_response.get("response", "N/A") if local_response else "N/A"},
        {"agent_id": "search_specialist", "response": search_response.get("response", "N/A") if search_response else "N/A"}
    ]

    # Hapus penyimpanan konteks dari sini karena sudah disimpan di endpoint
    # agar tidak terjadi duplikasi data
    return result