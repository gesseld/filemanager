from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from search_service import SearchService
from celery import Celery
from .celery import app as celery_app

app = FastAPI(
    title="File Manager API",
    description="A modern file management API with AI-powered search",
    version="0.1.0"
)

# Initialize services
search_service = SearchService()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "File Manager API is running"}


@app.get("/health")
async def health_check():
    # Check Celery worker status
    insp = celery_app.control.inspect()
    workers = insp.ping() or {}
    return {
        "status": "healthy",
        "celery_workers": len(workers),
        "celery_tasks": sum(len(tasks) for tasks in insp.active().values()) if insp.active() else 0
    }


@app.get("/api/v1/search")
async def hybrid_search(
    query: str,
    mode: str = "hybrid",
    limit: int = 10
):
    """
    Perform hybrid search combining keyword and vector results
    
    Parameters:
    - query: Search query string
    - mode: Search mode (hybrid/keyword/vector)
    - limit: Maximum number of results to return
    """
    if mode not in ["hybrid", "keyword", "vector"]:
        return {"error": "Invalid search mode"}
        
    results = await search_service.hybrid_search(query, limit)
    return {"results": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)