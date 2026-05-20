from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime, func
from shared.database import Base

Base = declarative_base()

class ProductSource(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class ETLState(Base):
    __tablename__ = 'etl_state'
    
    id = Column(Integer, primary_key=True, default=1)
    last_sync_time = Column(DateTime, nullable=False, default=func.now())
    last_sync_id = Column(Integer, default=0)
    total_synced = Column(Integer, default=0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())