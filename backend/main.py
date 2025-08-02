from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from search_service import SearchService
from celery import Celery
from .celery import app as celery_app
from utils.validate import validate_search_mode

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
    limit: int = 10,
    filters: Optional[str] = None,
    facets: Optional[str] = None,
    natural: bool = False
):
    """
    Perform hybrid search combining keyword and vector results
    
    Parameters:
    - query: Search query string
    - mode: Search mode (hybrid/keyword/vector)
    - limit: Maximum number of results to return
    """
    if not validate_search_mode(mode):
        raise HTTPException(
            status_code=400,
            detail="Invalid search mode. Must be one of: hybrid, keyword, vector"
        )
        
    # Process natural language query if requested
    if natural:
        query = search_service.process_natural_language_query(query)
    
    # Parse filters and facets
    filter_dict = json.loads(filters) if filters else None
    facet_list = facets.split(',') if facets else None
    
    results = await search_service.hybrid_search(
        query=query,
        limit=limit,
        filters=filter_dict,
        facets=facet_list
    )
    
    return {
        "results": results.get('hits', []),
        "facets": results.get('facets', {}),
        "query_suggestions": results.get('query_suggestions', []),
        "processed_query": query if natural else None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
