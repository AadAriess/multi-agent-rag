"""
Modul layanan Redis untuk aplikasi OriensSpace AI
"""
import redis
import json
from typing import Optional, Dict, Any
from app.core.config import settings

class RedisService:
    def __init__(self):
        self.client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
        self._test_connection()

    def _test_connection(self):
        """Test koneksi ke Redis"""
        try:
            self.client.ping()
            print("✓ Koneksi Redis berhasil")
        except redis.ConnectionError:
            raise ConnectionError("Gagal menghubungkan ke Redis. Pastikan Redis berjalan.")

    def get_cache(self, key: str) -> Optional[str]:
        """Dapatkan data dari cache"""
        try:
            return self.client.get(key)
        except Exception as e:
            print(f"Error saat mengambil dari cache: {e}")
            return None

    def set_cache(self, key: str, value: str, expire: int = 3600) -> bool:
        """Simpan data ke cache dengan expiry time"""
        try:
            self.client.setex(key, expire, value)
            return True
        except Exception as e:
            print(f"Error saat menyimpan ke cache: {e}")
            return False

    def delete_cache(self, key: str) -> bool:
        """Hapus data dari cache"""
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"Error saat menghapus dari cache: {e}")
            return False

    def store_session(self, session_id: str, data: Dict[str, Any], expire: int = 7200) -> bool:
        """Simpan data session ke Redis"""
        try:
            serialized_data = json.dumps(data)
            self.client.setex(f"session:{session_id}", expire, serialized_data)
            return True
        except Exception as e:
            print(f"Error saat menyimpan session: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Ambil data session dari Redis"""
        try:
            serialized_data = self.client.get(f"session:{session_id}")
            if serialized_data:
                return json.loads(serialized_data)
            return None
        except Exception as e:
            print(f"Error saat mengambil session: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """Hapus session dari Redis"""
        try:
            self.client.delete(f"session:{session_id}")
            return True
        except Exception as e:
            print(f"Error saat menghapus session: {e}")
            return False

# Buat instance global
redis_service = RedisService()