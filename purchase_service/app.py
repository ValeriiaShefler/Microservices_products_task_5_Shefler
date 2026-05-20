import os
import logging
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from shared.database import DatabaseManager
from models import ProductResponse, PurchaseRequest, PurchaseResponse
from services import PurchaseService
from clients import search_client
from shared.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(title="Purchase Service")

# настройка шаблонов
templates = Jinja2Templates(directory="templates")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://purchase_user:purchase123@postgres_purchase:5432/products_purchase")
db_manager = DatabaseManager(DATABASE_URL)

def get_db():
    return next(db_manager.get_session())

@app.on_event("startup")
def startup():
    db_manager.connect()
    db_manager.create_tables()


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/products")
async def get_products_api(limit: int = 20, offset: int = 0):
    try:
        result = await search_client.get_all_products(limit, offset)
        return result
    except Exception as e:
        logger.error(f"API products error: {e}")
        raise HTTPException(503, str(e))

@app.get("/api/products/{product_id}")
async def get_product_api(product_id: int):
    try:
        product = await search_client.get_product_by_id(product_id)
        if not product:
            raise HTTPException(404, f"Product {product_id} not found")
        return product
    except Exception as e:
        logger.error(f"API product error: {e}")
        raise HTTPException(503, str(e))

@app.post("/api/products/{product_id}/purchase", response_model=PurchaseResponse)
async def purchase_api(product_id: int, request: PurchaseRequest, db: Session = Depends(get_db)):
    service = PurchaseService(db)
    try:
        result = await service.purchase_product(product_id, request.quantity)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.get("/api/stats")
def get_stats_api(db: Session = Depends(get_db)):
    service = PurchaseService(db)
    return service.get_statistics()

# веб интерфейс

@app.get("/", response_class=HTMLResponse)
async def web_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/products", response_class=HTMLResponse)
async def web_products_list(request: Request, skip: int = 0, limit: int = 20):
    try:
        result = await search_client.get_all_products(limit, skip)
        products = result.get("products", [])
        total = result.get("total", 0)
        
        return templates.TemplateResponse("products_list.html", {
            "request": request,
            "products": products,
            "skip": skip,
            "limit": limit,
            "total": total
        })
    except Exception as e:
        logger.error(f"Web products error: {e}")
        return templates.TemplateResponse("products_list.html", {
            "request": request,
            "products": [],
            "skip": skip,
            "limit": limit,
            "total": 0,
            "error": str(e)
        })

@app.get("/products/{product_id}", response_class=HTMLResponse)
async def web_product_detail(request: Request, product_id: int):
    try:
        product = await search_client.get_product_by_id(product_id)
        if not product:
            return templates.TemplateResponse("product_detail.html", {
                "request": request,
                "product": None,
                "error": "Товар не найден"
            })
        return templates.TemplateResponse("product_detail.html", {
            "request": request,
            "product": product
        })
    except Exception as e:
        return templates.TemplateResponse("product_detail.html", {
            "request": request,
            "product": None,
            "error": str(e)
        })

@app.get("/search", response_class=HTMLResponse)
async def web_search(request: Request, q: str = "", limit: int = 20):
    """Страница поиска"""
    if not q:
        return templates.TemplateResponse("search_page.html", {
            "request": request,
            "query": "",
            "products": [],
            "total": 0
        })
    
    try:
        result = await search_client.search_products(q, limit, 0)
        products = result.get("products", [])
        total = result.get("total", 0)
        
        return templates.TemplateResponse("search_page.html", {
            "request": request,
            "query": q,
            "products": products,
            "total": total
        })
    except Exception as e:
        return templates.TemplateResponse("search_page.html", {
            "request": request,
            "query": q,
            "products": [],
            "total": 0,
            "error": str(e)
        })

@app.get("/purchase/{product_id}", response_class=HTMLResponse)
async def web_purchase_form(request: Request, product_id: int):
    """Форма покупки"""
    try:
        product = await search_client.get_product_by_id(product_id)
        if not product:
            return templates.TemplateResponse("purchase_form.html", {
                "request": request,
                "product": None,
                "error": "Товар не найден"
            })
        return templates.TemplateResponse("purchase_form.html", {
            "request": request,
            "product": product
        })
    except Exception as e:
        return templates.TemplateResponse("purchase_form.html", {
            "request": request,
            "product": None,
            "error": str(e)
        })

@app.post("/purchase/{product_id}", response_class=HTMLResponse)
async def web_purchase(request: Request, product_id: int, db: Session = Depends(get_db)):
    form_data = await request.form()
    quantity = int(form_data.get('quantity', 1))
    
    service = PurchaseService(db)
    try:
        result = await service.purchase_product(product_id, quantity)
        return templates.TemplateResponse("purchase_result.html", {
            "request": request,
            "success": True,
            "product_id": result.product_id,
            "product_title": result.product_title,
            "quantity": result.quantity,
            "total_amount": result.total_amount,
            "purchase_date": result.purchase_date,
            "remaining_stock": result.remaining_stock
        })
    except ValueError as e:
        return templates.TemplateResponse("purchase_result.html", {
            "request": request,
            "success": False,
            "error": str(e),
            "product_id": product_id
        })

@app.get("/stats", response_class=HTMLResponse)
async def web_stats(request: Request, db: Session = Depends(get_db)):
    service = PurchaseService(db)
    stats = service.get_statistics()
    return templates.TemplateResponse("stats.html", {
        "request": request,
        "stats": stats
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)