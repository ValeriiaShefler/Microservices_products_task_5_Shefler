from sqlalchemy.orm import Session
from typing import List, Optional
from models import Product
from shared.config import settings

class ProductService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_products(self) -> List[Product]:
        return self.db.query(Product).all()
    
    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        return self.db.query(Product).filter(Product.id == product_id).first()
    
    def create_product(self, title: str, description: str, price: float, stock: int) -> Product:
        if len(title) < settings.min_product_title_length:
            raise ValueError(f"Наименование должно быть хотя бы {settings.min_product_title_length} символов")
        product = Product(title=title, description=description, price=price, stock=stock)
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product
    
    def update_product(self, product_id: int, **kwargs) -> Optional[Product]:
        product = self.get_product_by_id(product_id)
        if not product:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(product, key):
                setattr(product, key, value)
        self.db.commit()
        self.db.refresh(product)
        return product