from pymilvus import connections, Collection
import json

# Koneksi ke Milvus
connections.connect(
    alias="default",
    host="localhost",
    port=19530
)

# Akses koleksi search_memory
try:
    search_memory_collection = Collection("search_memory")
    
    # Load koleksi untuk query
    search_memory_collection.load()
    
    # Query semua entri
    result = search_memory_collection.query(
        expr="id >= 0",
        output_fields=["id", "summary_text", "metadata"]
    )
    
    print(f"Jumlah entri di search_memory: {len(result)}")
    
    for entry in result:
        print(f"ID: {entry['id']}")
        print(f"Summary: {entry['summary_text'][:100]}...")
        print(f"Metadata: {json.dumps(entry['metadata'], indent=2)}")
        print("-" * 50)
        
except Exception as e:
    print(f"Error saat mengakses Milvus: {e}")