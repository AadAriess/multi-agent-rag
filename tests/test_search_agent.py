#!/usr/bin/env python3
"""
File untuk menguji Search Specialist Agent (Agent 2) secara individual
"""
import asyncio
import sys
import os

# Tambahkan path root proyek ke sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.llms.agents.chatbot.specialist_agents import create_search_specialist_agent


async def test_search_agent():
    """Fungsi untuk menguji Search Specialist Agent (Agent 2) secara individual"""
    print("=== Testing Search Specialist Agent (Agent 2) ===")

    # Buat instance dari search specialist agent
    search_agent = create_search_specialist_agent()

    # Test query yang relevan untuk pencarian eksternal
    test_queries = [
        "Aturan Administrasi Kemenhan 2025",
        "Kebijakan terbaru Kementerian Pertahanan",
        "Peraturan Menteri Pertahanan terbaru",
        "Dokumen kebijakan publik Kemenhan"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test Query {i}: {query} ---")
        try:
            # Agent 2 menerima session_id sebagai parameter tambahan
            result = await search_agent.run_query(query, session_id=f"test_session_{i}")
            print(f"Agent ID: {result.get('agent_id', 'N/A')}")
            print(f"Response: {result.get('response', 'N/A')}")
            print(f"Sources: {result.get('sources', 'N/A')}")
            print(f"Confidence: {result.get('confidence', 'N/A')}")
        except Exception as e:
            print(f"Error saat menjalankan query: {str(e)}")

        print("-" * 50)

    print("\n=== Testing Selesai ===")


if __name__ == "__main__":
    asyncio.run(test_search_agent())