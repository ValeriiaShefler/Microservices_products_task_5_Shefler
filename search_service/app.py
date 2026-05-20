import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from datetime import datetime
from elastic_client import ElasticsearchClient
from search_logic import SearchLogic
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST', 'elasticsearch')
ELASTICSEARCH_PORT = int(os.getenv('ELASTICSEARCH_PORT', '9200'))

es_client = ElasticsearchClient(ELASTICSEARCH_HOST, ELASTICSEARCH_PORT)
search_logic = SearchLogic(es_client)

templates = Jinja2Templates(directory="templates")

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting Search Service...")
    
    max_retries = 10
    for attempt in range(max_retries):
        if es_client.connect():
            break
        logger.warning(f"Retry {attempt + 1}/{max_retries}...")
        import time
        time.sleep(3)
    else:
        logger.error("Failed to connect to Elasticsearch after retries")
        raise RuntimeError("Elasticsearch connection failed")
    
    es_client.create_index()
    
    logger.info("Search Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Search Service shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Products Search Service",
    description="Поисковик с использованием Elasticsearch",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/api/health")
async def api_health_check():
    return {
        "status": "healthy",
        "elasticsearch": es_client.is_connected(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/search")
async def api_search_products(
    q: str = Query("", description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    try:
        result = await search_logic.search(q, limit, offset)
        return result.dict()
    except Exception as e:
        raise HTTPException(503, str(e))

@app.get("/api/search/suggest")
async def api_get_suggestions(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(5, ge=1, le=20)
):
    try:
        suggestions = await search_logic.suggest(q, limit)
        return {"query": q, "suggestions": suggestions}
    except Exception as e:
        raise HTTPException(500, str(e))
    
@app.get("/api/product/{product_id}")
async def api_get_product_by_id(product_id: int):
    """Получить товар по ID (для Purchase Service)"""
    try:
        from elasticsearch import Elasticsearch
        es = Elasticsearch([f"http://{ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}"])
        
        response = es.get(index="products", id=product_id, ignore=[404])
        if response.get('found'):
            source = response['_source']
            return {
                "id": source['id'],
                "title": source['title'],
                "description": source.get('description'),
                "price": source['price'],
                "stock": source['stock'],
                "created_at": source['created_at'],
                "updated_at": source['updated_at']
            }
        raise HTTPException(404, f"Product {product_id} not found")
    except Exception as e:
        logger.error(f"Error getting product by ID: {e}")
        raise HTTPException(500, str(e))

@app.get("/", response_class=HTMLResponse)
async def web_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/search", response_class=HTMLResponse)
async def web_search(
    request: Request,
    q: str = "",
    limit: int = 20,
    offset: int = 0
):
    if not q:
        return templates.TemplateResponse("search.html", {
            "request": request,
            "query": "",
            "products": [],
            "total": 0,
            "limit": limit,
            "offset": offset
        })
    
    try:
        result = await search_logic.search(q, limit, offset)
        
        suggestions = []
        if len(q) >= 2:
            suggestions = await search_logic.suggest(q, 5)
        
        return templates.TemplateResponse("search.html", {
            "request": request,
            "query": q,
            "products": result.products,
            "total": result.total,
            "limit": limit,
            "offset": offset,
            "suggestions": suggestions
        })
    except Exception as e:
        logger.error(f"Search error: {e}")
        return templates.TemplateResponse("search.html", {
            "request": request,
            "query": q,
            "products": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "error": str(e)
        })

@app.get("/api/products")
async def api_get_all_products(limit: int = 100, offset: int = 0):
    #для получения всех товаров без поискового запроса
    try:
        from elasticsearch import Elasticsearch
        es = Elasticsearch([f"http://{ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}"])
        
        body = {
            "query": {"match_all": {}},
            "from": offset,
            "size": limit,
            "sort": [{"id": {"order": "asc"}}]
        }
        
        response = es.search(index="products", body=body)
        
        products = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            products.append({
                "id": source['id'],
                "title": source['title'],
                "description": source.get('description'),
                "price": source['price'],
                "stock": source['stock'],
                "created_at": source['created_at'],
                "updated_at": source['updated_at']
            })
        
        return {
            "total": response['hits']['total']['value'],
            "offset": offset,
            "limit": limit,
            "products": products
        }
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/suggest", response_class=HTMLResponse)
async def web_suggestions(
    request: Request,
    q: str = "",
    limit: int = 10
):
    if not q or len(q) < 2:
        return templates.TemplateResponse("suggestions.html", {
            "request": request,
            "query": q,
            "suggestions": []
        })
    
    try:
        suggestions = await search_logic.suggest(q, limit)
        return templates.TemplateResponse("suggestions.html", {
            "request": request,
            "query": q,
            "suggestions": suggestions
        })
    except Exception as e:
        return templates.TemplateResponse("suggestions.html", {
            "request": request,
            "query": q,
            "suggestions": [],
            "error": str(e)
        })

@app.get("/about", response_class=HTMLResponse)
async def web_about(request: Request):
    return templates.TemplateResponse("about.html", {
        "request": request,
        "elasticsearch_connected": es_client.is_connected()
    })

class StockUpdateRequest(BaseModel):
    stock: int

@app.put("/api/product/{product_id}/stock")
async def api_update_product_stock(product_id: int, request: StockUpdateRequest):
    #обновление остатка товара в Elasticsearch (для Purchase Service)"""
    try:
        from elasticsearch import Elasticsearch
        from datetime import datetime
        import os
        
        ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST', 'elasticsearch')
        ELASTICSEARCH_PORT = int(os.getenv('ELASTICSEARCH_PORT', '9200'))
        es = Elasticsearch([f"http://{ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}"])
        
        doc = es.get(index="products", id=product_id)
        source = doc['_source']
        
        source['stock'] = request.stock
        source['updated_at'] = datetime.now().isoformat()
        
        es.index(index="products", id=product_id, body=source)
        
        logger.info(f"Stock for product {product_id} updated to {request.stock}")
        return {"success": True, "stock": request.stock}
    except Exception as e:
        logger.error(f"Error updating stock: {e}")
        raise HTTPException(500, str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )