from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional, Dict, Any
from datetime import datetime
from models import PurchaseDB, PurchaseResponse, ProductDB
from clients import search_client
import httpx
import logging

logger = logging.getLogger(__name__)


class PurchaseService:
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_product_from_search(self, product_id: int) -> Optional[Dict[str, Any]]:
        return await search_client.get_product_by_id(product_id)
    
    async def update_product_stock(self, product_id: int, new_stock: int):
        logger.info(f"Updating stock for product {product_id} to {new_stock}")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.put(
                    f"http://search_api:8002/api/product/{product_id}/stock",
                    json={"stock": new_stock}
                )
                response.raise_for_status()
                logger.info(f"Stock updated successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to update stock in Elasticsearch: {e}")
            return False

    async def purchase_product(self, product_id: int, quantity: int) -> Optional[PurchaseResponse]:
        MAX_QUANTITY = 100
        
        if quantity > MAX_QUANTITY:
            raise ValueError(f"Максимальное количество {MAX_QUANTITY}")
        
        if quantity <= 0:
            raise ValueError("Чисто должно быть больше нуля")
        
        product = await self.get_product_from_search(product_id)
        if not product:
            raise ValueError(f"Продукт с id {product_id} не найден")
        
        stock = product.get("stock", 0)
        if stock < quantity:
            raise ValueError(f"Вы столько не купите( Доступно: {stock}, Пытаетесь купить: {quantity}")
        
        new_stock = stock - quantity
        total_amount = float(product.get("price", 0)) * quantity
        
        purchase = PurchaseDB(
            product_id=product_id,
            quantity=quantity,
            total_amount=total_amount
        )
        self.db.add(purchase)
        self.db.commit()
        self.db.refresh(purchase)
        
        # Обновляем остаток в Elasticsearch
        await self.update_product_stock(product_id, new_stock)
        
        return PurchaseResponse(
            product_id=product_id,
            product_title=product.get("title", "Unknown"),
            quantity=quantity,
            total_amount=total_amount,
            purchase_date=purchase.purchase_date,
            remaining_stock=new_stock,
            message=f"Успешно приобретено {quantity} x '{product.get('title', 'Unknown')}'"
        )
    
    def get_purchase_history(self, product_id: Optional[int] = None, limit: int = 50) -> List[dict]:
        query = self.db.query(PurchaseDB).order_by(desc(PurchaseDB.purchase_date))
        
        if product_id:
            query = query.filter(PurchaseDB.product_id == product_id)
        
        purchases = query.limit(min(limit, 500)).all()
        
        result = []
        for p in purchases:
            result.append({
                "id": p.id,
                "product_id": p.product_id,
                "quantity": p.quantity,
                "total_amount": float(p.total_amount),
                "purchase_date": p.purchase_date
            })
        
        return result
    
    def get_statistics(self) -> dict:
        total_purchases = self.db.query(func.count(PurchaseDB.id)).scalar() or 0
        total_revenue = self.db.query(func.sum(PurchaseDB.total_amount)).scalar() or 0
        total_items = self.db.query(func.sum(PurchaseDB.quantity)).scalar() or 0
        
        popular = self.db.query(
            PurchaseDB.product_id,
            func.sum(PurchaseDB.quantity).label('total_quantity'),
            func.count(PurchaseDB.id).label('purchase_count')
        ).group_by(PurchaseDB.product_id).order_by(
            desc('total_quantity')
        ).limit(10).all()
        
        popular_products = []
        for item in popular:
            product = self.db.query(ProductDB).filter(ProductDB.id == item.product_id).first()
            popular_products.append({
                "product_id": item.product_id,
                "product_title": product.title if product else f"Товар {item.product_id}",
                "total_purchased": item.total_quantity,
                "purchase_count": item.purchase_count,
                "current_stock": product.stock if product else 0
            })
        
        return {
            "total_purchases": total_purchases,
            "total_revenue": float(total_revenue),
            "total_items_sold": total_items,
            "popular_products": popular_products
        }