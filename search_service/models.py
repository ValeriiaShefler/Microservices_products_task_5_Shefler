from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProductDocument(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    price: float
    stock: int
    created_at: datetime
    updated_at: datetime

class SearchResponse(BaseModel):
    query: str
    total: int
    offset: int
    limit: int
    products: List[ProductDocument]