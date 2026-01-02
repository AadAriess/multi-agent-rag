"""
Modul untuk menyimpan dokumen yang telah diproses ke Milvus dengan preprocessing
"""
import sys
import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Tambahkan path proyek ke sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Settings
from llama_index.embeddings.ollama import OllamaEmbedding
from app.services.milvus_service import milvus_service

def clean_text(text):
    """
    Membersihkan teks dari karakter-karakter yang tidak bermakna sebelum disimpan ke Milvus
    """
    if not text or not isinstance(text, str):
        return text

    # Hapus baris yang hanya berisi karakter X atau karakter acak
    text = re.sub(r'[Xx]{10,}', '', text)
    # Hapus baris yang hanya berisi karakter berulang
    text = re.sub(r'([^\w\s])\1{10,}', '', text)
    # Hapus baris yang hanya berisi karakter non-teks
    text = re.sub(r'^\s*[^\w\s]+\s*$', '', text, flags=re.MULTILINE)
    # Hapus karakter gambar atau placeholder gambar
    text = re.sub(r'\[Figure\].*?\]', '', text)
    # Hapus HTML tags jika ada
    text = re.sub(r'<[^>]+>', '', text)
    # Bersihkan whitespace berlebihan
    text = re.sub(r'\n\s*\n', '\n\n', text)

    return text.strip()

def save_documents_to_milvus_with_cleaning():
    load_dotenv()

    # Muat konfigurasi
    config = {
        "DATA_DIR": Path("data/knowledge_base"),
        "LLM_BASE_URL": os.getenv("LLM_BASE_URL"),
        "LLM_EMBEDDING": os.getenv("LLM_EMBEDDING"),
        "LLM_MODEL_NAME": os.getenv("LLM_MODEL_NAME"),
        "API_KEY": os.getenv("LLM_API_KEY", "oriensagentapi"),
        "EMBEDDING_MODEL_NAME": os.getenv("EMBEDDING_MODEL_NAME"),
        "MILVUS_COLLECTION_NAME": os.getenv("MILVUS_COLLECTION_NAME"),
        "CHUNK_SIZE": 1024,
        "CHUNK_OVERLAP": 256
    }

    # Inisialisasi model
    embed_model = OllamaEmbedding(
        model_name=config["EMBEDDING_MODEL_NAME"],
        base_url=config["LLM_EMBEDDING"],
    )

    Settings.embed_model = embed_model

    # Muat dokumen
    loader = SimpleDirectoryReader(
        input_dir=config['DATA_DIR'],
        recursive=True
    )
    documents = loader.load_data()

    # Split dokumen
    splitter = SentenceSplitter(
        chunk_size=config['CHUNK_SIZE'],
        chunk_overlap=config['CHUNK_OVERLAP']
    )
    nodes = splitter.get_nodes_from_documents(documents)

    print(f"Memproses {len(nodes)} nodes untuk disimpan ke Milvus...")

    # Ekstrak teks dan embedding
    texts = []
    embeddings = []

    for i, node in enumerate(nodes):
        text_content = node.get_content()

        # Bersihkan teks sebelum disimpan
        cleaned_text = clean_text(text_content)

        # Hanya simpan jika teks tidak kosong setelah dibersihkan
        if cleaned_text and len(cleaned_text.strip()) > 10:  # Hanya simpan teks dengan panjang lebih dari 10 karakter
            texts.append(cleaned_text)

            # Dapatkan embedding
            embedding = embed_model.get_text_embedding(cleaned_text)
            embeddings.append(embedding)

        if (i + 1) % 50 == 0:
            print(f"Memproses node {i + 1}/{len(nodes)} - {len(texts)} teks valid ditemukan")

    # Simpan ke Milvus
    if texts and embeddings:
        print(f"Menyimpan {len(texts)} teks ke Milvus...")
        milvus_service.insert_documents(texts, embeddings)
        print("Selesai menyimpan ke Milvus!")
    else:
        print("Tidak ada teks valid untuk disimpan ke Milvus.")


if __name__ == "__main__":
    save_documents_to_milvus_with_cleaning()