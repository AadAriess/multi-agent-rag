"""
Modul layanan Milvus untuk aplikasi OriensSpace AI
"""
import logging
from typing import List, Dict, Any, Optional
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from app.core.config import settings
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MilvusConfig:
    host: str
    port: int
    user: str
    password: str
    secure: bool
    collection_name: str

class MilvusService:
    def __init__(self):
        self.config = MilvusConfig(
            host=settings.milvus_host,
            port=settings.milvus_port,
            user=settings.milvus_user,
            password=settings.milvus_password,
            secure=settings.milvus_secure,
            collection_name=settings.milvus_collection_name
        )
        self.collection_name = self.config.collection_name
        self.client = None
        self.collection = None
        self._connect()
        self._create_collection_if_not_exists()
        self._test_connection()

    def _connect(self):
        """Membuat koneksi ke Milvus"""
        try:
            connections.connect(
                alias="default",
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                secure=self.config.secure
            )
            logger.info("✓ Koneksi Milvus berhasil")
        except Exception as e:
            logger.error(f"✗ Gagal menghubungkan ke Milvus: {e}")
            raise

    def _test_connection(self):
        """Menguji koneksi ke Milvus"""
        try:
            # Mencoba mengakses koleksi untuk memastikan koneksi aktif
            if utility.has_collection(self.collection_name):
                logger.info(f"✓ Koleksi {self.collection_name} ditemukan")
            else:
                logger.warning(f"⚠ Koleksi {self.collection_name} tidak ditemukan")
        except Exception as e:
            logger.error(f"✗ Error saat menguji koneksi: {e}")

    def _create_collection_if_not_exists(self):
        """Membuat koleksi Milvus jika belum ada"""
        try:
            if not utility.has_collection(self.collection_name):
                # Definisikan skema koleksi yang kompatibel dengan LlamaIndex
                fields = [
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=768),  # Sesuaikan dimensi embedding
                    FieldSchema(name="metadata", dtype=DataType.JSON)
                ]

                schema = CollectionSchema(fields=fields, description="Koleksi dokumen kepatuhan")

                # Buat koleksi
                self.collection = Collection(name=self.collection_name, schema=schema)

                # Buat indeks untuk vektor embedding
                index_params = {
                    "index_type": "IVF_FLAT",
                    "metric_type": "COSINE",
                    "params": {"nlist": 128}
                }
                self.collection.create_index(field_name="vector", index_params=index_params)

                logger.info(f"✓ Koleksi {self.collection_name} berhasil dibuat")
            else:
                self.collection = Collection(name=self.collection_name)
                self.collection.load()  # Load koleksi ke memori

                logger.info(f"✓ Koleksi {self.collection_name} sudah ada dan telah dimuat")
        except Exception as e:
            logger.error(f"✗ Error saat membuat koleksi: {e}")
            raise

    def insert_documents(self, texts: List[str], embeddings: List[List[float]], metadatas: Optional[List[Dict]] = None):
        """Menyimpan dokumen ke dalam koleksi Milvus"""
        try:
            # Siapkan data untuk disisipkan - mengikuti skema: text, vector, metadata
            # id akan diisi otomatis
            metadatas = metadatas or [{}] * len(texts)
            data = [texts, embeddings, metadatas]

            # Sisipkan data ke koleksi
            insert_result = self.collection.insert(data)

            # Bangun indeks setelah menyisipkan data
            self.collection.flush()
            self.collection.compact()

            logger.info(f"✓ {len(texts)} dokumen berhasil disimpan ke koleksi {self.collection_name}")
            return insert_result
        except Exception as e:
            logger.error(f"✗ Error saat menyisipkan dokumen: {e}")
            raise

    def search_similar(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Mencari dokumen yang mirip berdasarkan embedding
        """
        try:
            # Membuat skema pencarian
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }

            # Lakukan pencarian
            results = self.collection.search(
                data=[query_embedding],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                output_fields=["text", "metadata"]  # Pastikan field ini sesuai dengan skema koleksi
            )

            # Format hasil pencarian
            formatted_results = []
            for i, result in enumerate(results[0]):  # results[0] karena hanya satu query
                formatted_result = {
                    "id": result.id,
                    "text": result.entity.get('text'),
                    "metadata": result.entity.get('metadata'),
                    "distance": result.distance
                }
                formatted_results.append(formatted_result)

            logger.info(f"✓ Ditemukan {len(formatted_results)} dokumen mirip")
            return formatted_results

        except Exception as e:
            logger.error(f"✗ Error saat mencari dokumen mirip: {e}")
            raise

    def search_in_collection(self, collection_name: str, query_vector: List[float], top_k: int = 5):
        """Search in a specific collection"""
        try:
            # Connect to the specific collection
            collection = Collection(collection_name)

            # Determine the text field name based on collection
            text_field = "text" if collection_name == "compliance_docs" else "summary_text"

            # Prepare search parameters
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }

            # Perform the search
            results = collection.search(
                data=[query_vector],
                anns_field="vector",  # Assuming the vector field is named 'vector'
                param=search_params,
                limit=top_k,
                output_fields=[text_field, "metadata"]  # Return text and metadata
            )

            # Format results
            formatted_results = []
            for result in results[0]:  # Results are returned in batches
                formatted_result = {
                    "id": result.id,
                    text_field: result.entity.get(text_field),
                    "metadata": result.entity.get('metadata'),
                    "distance": result.distance
                }
                formatted_results.append(formatted_result)

            logger.info(f"✓ Ditemukan {len(formatted_results)} dokumen mirip di koleksi {collection_name}")
            return formatted_results
        except Exception as e:
            logger.error(f"✗ Error saat mencari di koleksi {collection_name}: {e}")
            return []


# Buat instance global
milvus_service = MilvusService()