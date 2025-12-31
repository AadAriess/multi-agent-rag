from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime

# Koneksi ke database MySQL
DATABASE_URL = "mysql+pymysql://root:root@localhost:3306/oriensspace"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_mysql_data():
    db = SessionLocal()
    
    try:
        # Cek tabel contexts
        print("=== Tabel Contexts ===")
        result = db.execute(text("SELECT * FROM contexts ORDER BY created_at DESC LIMIT 10"))
        contexts = result.fetchall()
        
        print(f"Jumlah entri di contexts: {len(contexts)}")
        for context in contexts:
            print(f"ID: {context[0]}")
            print(f"Session ID: {context[1]}")
            print(f"Created At: {context[3]}")
            print(f"Data: {str(context[2])[:100]}...")
            print("-" * 50)
        
        # Cek tabel search_history
        print("\n=== Tabel Search History ===")
        result = db.execute(text("SELECT * FROM search_history ORDER BY created_at DESC LIMIT 10"))
        search_history = result.fetchall()
        
        print(f"Jumlah entri di search_history: {len(search_history)}")
        for history in search_history:
            print(f"ID: {history[0]}")
            print(f"Session ID: {history[4]}")
            print(f"Query: {history[1]}")
            print(f"Created At: {history[6]}")
            print(f"Results Summary: {str(history[2])[:100]}...")
            print(f"Source URLs: {history[3]}")
            print("-" * 50)
        
        # Cek tabel documents
        print("\n=== Tabel Documents ===")
        result = db.execute(text("SELECT * FROM documents ORDER BY created_at DESC LIMIT 5"))
        documents = result.fetchall()
        
        print(f"Jumlah entri di documents: {len(documents)}")
        for doc in documents:
            print(f"ID: {doc[0]}")
            print(f"Name: {doc[1]}")
            print(f"Created At: {doc[7]}")
            print(f"Content Hash: {doc[5]}")
            print("-" * 50)

    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_mysql_data()