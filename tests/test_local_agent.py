#!/usr/bin/env python3
"""
File untuk menguji Local Specialist Agent secara individual
"""
import asyncio
import sys
import os

# Tambahkan path root proyek ke sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.llms.agents.chatbot.specialist_agents import create_local_specialist_agent


async def test_local_agent():
    """Fungsi untuk menguji Local Specialist Agent secara individual"""
    print("=== Testing Local Specialist Agent ===")
    
    # Buat instance dari local specialist agent
    local_agent = create_local_specialist_agent()
    
    # Test query yang relevan dengan dokumen yang tersedia
    test_queries = [
        "Apa itu Administrasi Umum di Lingkungan Kementerian Pertahanan?",
        "Sebutkan fungsi-fungsi dalam Administrasi Umum Kementerian Pertahanan",
        "Apa yang dimaksud dengan Naskah Dinas Arahan?",
        "Jelaskan tentang sistematis naskah dinas menurut PERMENHAN"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test Query {i}: {query} ---")
        try:
            result = await local_agent.run_query(query)
            print(f"Agent ID: {result.get('agent_id', 'N/A')}")
            print(f"Response: {result.get('response', 'N/A')}")
            print(f"Sources: {result.get('sources', 'N/A')}")
            print(f"Confidence: {result.get('confidence', 'N/A')}")
        except Exception as e:
            print(f"Error saat menjalankan query: {str(e)}")
        
        print("-" * 50)
    
    print("\n=== Testing Selesai ===")


if __name__ == "__main__":
    asyncio.run(test_local_agent())