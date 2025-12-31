"""
Modul layanan SearXNG untuk aplikasi OriensSpace AI
"""
import asyncio
from typing import List, Dict, Any, Optional
from searxng_wrapper import SearxngWrapper
from app.core.config import config

class SearXNGService:
    def __init__(self):
        self.base_url = config.SEARXNG_BASE_URL
        self.client = SearxngWrapper(base_url=self.base_url)
        self._test_connection()

    def _test_connection(self):
        """Test koneksi ke SearXNG"""
        try:
            # Coba akses SearXNG untuk memastikan berjalan
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Jika loop sedang berjalan, buat task baru
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._async_test_connection())
                    result = future.result()
            else:
                result = asyncio.run(self._async_test_connection())

            if result:
                print("✓ Koneksi SearXNG berhasil")
            else:
                print("⚠ SearXNG merespons tetapi tidak ada hasil pencarian, pastikan konfigurasi sudah benar")
        except Exception as e:
            print(f"⚠ SearXNG tidak merespons. Pastikan instance SearXNG berjalan. Error: {e}")

    async def _async_test_connection(self):
        """Test koneksi async ke SearXNG"""
        try:
            result = await self.client.asearch(q="test", lang="id", limit=1)
            # Cek apakah result adalah None sebelum mengakses atributnya
            if result is None:
                return False
            # Akses atribut 'results' dari objek SearchResponse
            search_results = getattr(result, 'results', [])
            return len(search_results) > 0
        except Exception:
            return False

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Lakukan pencarian sync menggunakan SearXNG
        """
        try:
            result = self.client.search(
                q=query,
                language="id",
                max_results=max_results
            )

            # Cek apakah result adalah None sebelum mengakses atributnya
            if result is None:
                print("Peringatan: Hasil pencarian SearXNG adalah None (kemungkinan karena rate limiting)")
                return []

            # Ekstrak hasil pencarian - objek result adalah SearchResponse bukan dictionary
            results = []
            # Akses atribut 'results' dari objek SearchResponse
            search_results = getattr(result, 'results', [])

            for result_item in search_results:
                processed_result = {
                    "title": result_item.get("title", "") if isinstance(result_item, dict) else str(result_item),
                    "url": result_item.get("url", "") if isinstance(result_item, dict) else "",
                    "content": result_item.get("content", "") if isinstance(result_item, dict) else "",
                    "engine": result_item.get("engine", "") if isinstance(result_item, dict) else "",
                    "score": result_item.get("score", 0.0) if isinstance(result_item, dict) else 0.0
                }
                results.append(processed_result)

            return results

        except Exception as e:
            print(f"Error saat melakukan pencarian SearXNG: {e}")
            return []

    async def asearch(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Lakukan pencarian async menggunakan SearXNG
        """
        try:
            result = await self.client.asearch(
                q=query,
                language="id",
                max_results=max_results
            )

            # Cek apakah result adalah None sebelum mengakses atributnya
            if result is None:
                print("Peringatan: Hasil pencarian SearXNG adalah None (kemungkinan karena rate limiting)")
                return []

            # Ekstrak hasil pencarian - objek result adalah SearchResponse bukan dictionary
            results = []
            # Akses atribut 'results' dari objek SearchResponse
            search_results = getattr(result, 'results', [])

            for result_item in search_results:
                processed_result = {
                    "title": result_item.get("title", "") if isinstance(result_item, dict) else str(result_item),
                    "url": result_item.get("url", "") if isinstance(result_item, dict) else "",
                    "content": result_item.get("content", "") if isinstance(result_item, dict) else "",
                    "engine": result_item.get("engine", "") if isinstance(result_item, dict) else "",
                    "score": result_item.get("score", 0.0) if isinstance(result_item, dict) else 0.0
                }
                results.append(processed_result)

            return results

        except Exception as e:
            print(f"Error saat melakukan pencarian async SearXNG: {e}")
            return []

    def search_compliance_info(self, query: str) -> List[Dict[str, Any]]:
        """
        Lakukan pencarian informasi menggunakan SearXNG tanpa filter spesifik
        """
        try:
            # Lakukan pencarian langsung dengan query asli
            results = self.search(query, max_results=10)

            if results:
                print(f"Ditemukan {len(results)} hasil untuk query '{query}'")
                return results
            else:
                print(f"Tidak ada hasil ditemukan untuk query '{query}'")
                return []

        except Exception as e:
            print(f"Error saat melakukan pencarian informasi: {e}")
            return []


# Buat instance global
searxng_service = SearXNGService()