from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text
from sqlalchemy.sql import func
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from shared.database import Base

#SQLAlchemy ORM Models

class ProductDB(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class PurchaseDB(Base):
    __tablename__ = 'purchases'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    purchase_date = Column(DateTime, server_default=func.now())

#Pydantic Models для API

class PurchaseRequest(BaseModel):
    quantity: int = Field(1, ge=1, le=100)

class PurchaseResponse(BaseModel):
    product_id: int
    product_title: str
    quantity: int
    total_amount: float
    purchase_date: datetime
    remaining_stock: int
    message: str

class ProductResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    price: float
    stock: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class StatisticsResponse(BaseModel):
    total_purchases: int
    total_revenue: float
    total_items_sold: int
    popular_products: list