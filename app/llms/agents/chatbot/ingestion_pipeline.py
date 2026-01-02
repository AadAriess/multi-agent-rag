"""
Ingestion Pipeline untuk Multi Agent RAG
"""
import hashlib
import os
from typing import List, Optional
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from llama_index.core import SimpleDirectoryReader
from llama_index.embeddings.ollama import OllamaEmbedding
from app.database.milvus_config import milvus_collection
from app.models import DocumentChunk, DocumentMetadata
from app.core.config import settings
from sqlalchemy.orm import Session
from app.models.database_schema import Document
from sqlalchemy.sql import func
import logging

logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read the file in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_existing_document(db: Session, material_id: str) -> Optional[Document]:
    """Get existing document from MySQL by material_id"""
    return db.query(Document).filter(Document.id == material_id).first()


def delete_vectors_from_milvus(material_id: str):
    """Delete existing vectors from Milvus by material_id"""
    # Search for entities with the material_id in metadata
    search_expr = f'metadata["material_id"] == "{material_id}"'
    results = milvus_collection.query(
        expr=search_expr,
        output_fields=["id"]
    )
    
    # Extract IDs to delete
    ids_to_delete = [result["id"] for result in results]
    
    if ids_to_delete:
        # Delete the vectors
        milvus_collection.delete(expr=f"id in {ids_to_delete}")
        logger.info(f"Deleted {len(ids_to_delete)} vectors for material_id: {material_id}")


def chunk_markdown_document(file_path: str) -> List[DocumentChunk]:
    """Chunk markdown document using RecursiveCharacterTextSplitter with markdown-specific separators"""
    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Initialize the text splitter with markdown-specific separators
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n#{1,6} ", "\n##{1,5} ", "\n###{1,4} ", "\n####{1,3} ", "\n#####{1,2} ", "\n###### ", "\n\n", "\n", " ", ""]
    )
    
    chunks = text_splitter.split_text(content)
    
    # Create document chunks with metadata
    document_chunks = []
    for idx, chunk in enumerate(chunks):
        # For this function, we'll temporarily use placeholder metadata
        # The actual metadata will be added during ingestion
        metadata = DocumentMetadata(
            material_id="",
            doc_name=os.path.basename(file_path),
            page_number=1,  # Placeholder, will be updated based on actual document structure
            chunk_index=idx,
            hash=hashlib.sha256(chunk.encode()).hexdigest()
        )
        
        document_chunk = DocumentChunk(
            text=chunk,
            metadata=metadata
        )
        
        document_chunks.append(document_chunk)
    
    return document_chunks


def embed_chunks(chunks: List[DocumentChunk]) -> List:
    """Generate embeddings for document chunks"""
    # Initialize Ollama embedding model
    embed_model = OllamaEmbedding(
        model_name=settings.embedding_model_name,
        base_url=settings.llm_embedding
    )
    
    embedded_chunks = []
    for chunk in chunks:
        # Generate embedding for the text
        embedding = embed_model.get_text_embedding(chunk.text)
        embedded_chunks.append({
            'text': chunk.text,
            'embedding': embedding,
            'metadata': chunk.metadata.dict()
        })
    
    return embedded_chunks


def store_in_milvus(embedded_chunks: List) -> bool:
    """Store embedded chunks in Milvus"""
    try:
        # Prepare data for insertion
        texts = [chunk['text'] for chunk in embedded_chunks]
        embeddings = [chunk['embedding'] for chunk in embedded_chunks]
        metadatas = [chunk['metadata'] for chunk in embedded_chunks]
        
        # Insert into Milvus
        insert_result = milvus_collection.insert([
            texts,
            embeddings,
            metadatas
        ])
        
        # Commit the changes
        milvus_collection.flush()
        
        logger.info(f"Successfully stored {len(texts)} chunks in Milvus")
        return True
    except Exception as e:
        logger.error(f"Error storing chunks in Milvus: {str(e)}")
        return False


def update_document_metadata(db: Session, material_id: str, file_path: str, content_hash: str, content: str = None, pages: int = None):
    """Update document metadata in MySQL"""
    doc = get_existing_document(db, material_id)

    if doc:
        # Update existing document
        doc.content_hash = content_hash
        doc.last_synced = func.now()
        # Update content dan pages jika disediakan
        if content is not None:
            doc.content = content
        if pages is not None:
            doc.pages = pages
    else:
        # Create new document record
        new_doc = Document(
            id=material_id,
            name=os.path.basename(file_path),
            file_path=file_path,
            content=content,  # Simpan ringkasan dokumen
            pages=pages,  # Simpan jumlah halaman
            content_hash=content_hash,
            last_synced=func.now()
        )
        db.add(new_doc)

    db.commit()


def ingest_document(file_path: str, material_id: str, doc_name: str, db: Session) -> bool:
    """
    Main ingestion function that follows the pipeline:
    1. Calculate file hash
    2. Compare with existing hash in MySQL
    3. If different, delete old vectors from Milvus
    4. Chunk the document
    5. Generate embeddings
    6. Store in Milvus
    7. Update MySQL metadata (only after successful Milvus storage)
    """
    try:
        # Step 1: Calculate file hash
        current_hash = calculate_file_hash(file_path)
        logger.info(f"Calculated hash for {file_path}: {current_hash}")

        # Step 2: Get existing document from MySQL
        existing_doc = get_existing_document(db, material_id)
        logger.info(f"Existing document for material_id {material_id}: {existing_doc}")

        # Step 3: Check if content has changed
        should_ingest = False
        if existing_doc:
            # Jika dokumen ditemukan
            if existing_doc.content_hash and existing_doc.content_hash == current_hash:
                # Jika hash sama, lewati
                logger.info(f"Document {material_id} has not changed, skipping ingestion")
                return True
            else:
                # Jika hash berbeda atau tidak ada hash, lanjutkan proses
                logger.info(f"Document {material_id} has changed or has no hash, proceeding with ingestion")
                if existing_doc.content_hash:
                    logger.info(f"Old hash: {existing_doc.content_hash}, New hash: {current_hash}")
                # Hapus vektor lama dari Milvus
                delete_vectors_from_milvus(material_id)
                should_ingest = True
        else:
            # Jika dokumen tidak ditemukan, ini adalah dokumen baru
            logger.info(f"New document {material_id}, proceeding with ingestion")
            should_ingest = True

        if should_ingest:
            # Step 4: Chunk the document
            logger.info(f"Chunking document {file_path}")
            chunks = chunk_markdown_document(file_path)

            # Update metadata with actual material_id
            for i, chunk in enumerate(chunks):
                chunk.metadata.material_id = material_id
                chunk.metadata.doc_name = doc_name
                chunk.metadata.page_number = i + 1  # Simplified page numbering

            # Step 5: Generate embeddings
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            embedded_chunks = embed_chunks(chunks)

            # Step 6: Store in Milvus
            logger.info("Storing chunks in Milvus")
            success = store_in_milvus(embedded_chunks)

            if not success:
                logger.error("Failed to store chunks in Milvus")
                return False

            # Step 7: Update MySQL metadata (only after successful Milvus storage)
            logger.info("Updating MySQL metadata")

            # Baca konten file untuk disimpan sebagai ringkasan
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()

            # Ambil ringkasan dari awal dokumen (misalnya 500 karakter pertama)
            summary_content = file_content[:500] + "..." if len(file_content) > 500 else file_content

            # Hitung jumlah halaman (dalam kasus file markdown, kita bisa menghitung jumlah heading utama atau jumlah paragraf)
            # Untuk sederhananya, kita gunakan jumlah paragraf sebagai jumlah 'halaman'
            paragraphs = [p.strip() for p in file_content.split('\n\n') if p.strip()]
            num_pages = len(paragraphs)

            update_document_metadata(db, material_id, file_path, current_hash, content=summary_content, pages=num_pages)

        logger.info(f"Successfully processed document {material_id}")
        return True

    except Exception as e:
        logger.error(f"Error during ingestion of {file_path}: {str(e)}")
        return False


def ingest_directory(directory_path: str = "data/knowledge_base/", db: Session = None) -> bool:
    """Ingest all markdown files in a directory"""
    try:
        markdown_files = Path(directory_path).glob("**/*.md")
        success_count = 0

        # Konversi ke list agar bisa dihitung jumlahnya
        markdown_files_list = list(markdown_files)
        logger.info(f"Found {len(markdown_files_list)} markdown files in {directory_path}")

        for file_path in markdown_files_list:
            file_path_str = str(file_path)
            material_id = str(hashlib.md5(file_path_str.encode()).hexdigest())
            doc_name = file_path.name

            logger.info(f"Processing file: {file_path_str}")

            if ingest_document(file_path_str, material_id, doc_name, db):
                success_count += 1
            else:
                logger.error(f"Failed to ingest document: {file_path_str}")

        logger.info(f"Successfully ingested {success_count} out of {len(markdown_files_list)} documents")
        return True

    except Exception as e:
        logger.error(f"Error during directory ingestion: {str(e)}")
        return False


def ingest_default_knowledge_base(db: Session = None) -> bool:
    """Ingest the default knowledge base from data/knowledge_base/ directory"""
    knowledge_base_path = "data/knowledge_base/"
    logger.info(f"Starting ingestion of default knowledge base from {knowledge_base_path}")
    return ingest_directory(knowledge_base_path, db)