import asyncio
from search_service import SearchService

async def test_search():
    # Initialize search service
    search = SearchService()
    
    # Sample documents to index
    documents = [
        {
            "id": "1",
            "title": "Introduction to AI",
            "content": "Artificial Intelligence is transforming industries",
            "tags": ["ai", "technology"]
        },
        {
            "id": "2", 
            "title": "Machine Learning Basics",
            "content": "Learn about supervised and unsupervised learning",
            "tags": ["ml", "education"]
        }
    ]
    
    # Upsert test documents
    await search.upsert_documents(documents)
    print("Documents indexed successfully")
    
    # Test hybrid search
    results = await search.hybrid_search("AI learning", limit=2)
    print("\nSearch results:")
    for idx, doc in enumerate(results):
        print(f"{idx+1}. {doc['title']} - {doc['content'][:50]}...")

if __name__ == "__main__":
    asyncio.run(test_search())