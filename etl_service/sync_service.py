import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from elasticsearch import Elasticsearch
from models import Base, ProductSource

logger = logging.getLogger(__name__)

class ETLSyncService:
    def __init__(self):
        self.engine = None
        self.session = None
        self.es_client = None
        self.batch_size = 100
    
    def connect_source_db(self) -> bool:
        try:
            database_url = os.getenv("DATABASE_URL", "postgresql://admin:admin123@postgres_source:5432/products_source")
            self.engine = create_engine(database_url, pool_pre_ping=True)
            SessionLocal = sessionmaker(bind=self.engine)
            self.session = SessionLocal()
            
            # Создаём ВСЕ таблицы через SQLAlchemy (включая etl_state)
            from models import Base, ETLState, ProductSource
            Base.metadata.create_all(self.engine)
            
            # Проверяем, есть ли начальные данные в etl_state
            from sqlalchemy import text
            result = self.session.execute(text("SELECT COUNT(*) FROM etl_state"))
            count = result.scalar()
            
            if count == 0:
                # Вставляем начальное состояние
                from datetime import datetime, timedelta
                initial_state = ETLState(
                    id=1,
                    last_sync_time=datetime.now() - timedelta(days=7),
                    last_sync_id=0,
                    total_synced=0
                )
                self.session.add(initial_state)
                self.session.commit()
                logger.info("Initial ETL state created")
            
            logger.info("Connected to source PostgreSQL")
            return True
        except Exception as e:
            logger.error(f"Source DB connection failed: {e}")
            return False
    
    def connect_elasticsearch(self) -> bool:
        try:
            host = os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
            port = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
            self.es_client = Elasticsearch([f"http://{host}:{port}"])
            if self.es_client.ping():
                logger.info("Connected to Elasticsearch")
                return True
        except Exception as e:
            logger.error(f"Elasticsearch connection failed: {e}")
        return False
    
    def ensure_index(self):
        index_name = "products"
        if not self.es_client.indices.exists(index=index_name):
            mapping = {
                "mappings": {
                    "properties": {
                        "id": {"type": "integer"},
                        "title": {"type": "text", "analyzer": "russian"},
                        "description": {"type": "text", "analyzer": "russian"},
                        "price": {"type": "float"},
                        "stock": {"type": "integer"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"}
                    }
                }
            }
            self.es_client.indices.create(index=index_name, body=mapping)
            logger.info(f"Created index '{index_name}'")
    
    def get_last_sync_time(self) -> datetime:
        try:
            result = self.session.execute(text("SELECT last_sync_time FROM etl_state LIMIT 1"))
            row = result.fetchone()
            if row:
                return row[0]
        except:
            pass
        return datetime.now() - timedelta(days=7)
    
    def update_sync_state(self, sync_time: datetime, synced_count: int):
        self.session.execute(text("""
            INSERT INTO etl_state (id, last_sync_time, last_sync_id, total_synced)
            VALUES (1, :sync_time, :synced_count, :synced_count)
            ON CONFLICT (id) DO UPDATE SET
                last_sync_time = EXCLUDED.last_sync_time,
                last_sync_id = etl_state.last_sync_id + EXCLUDED.last_sync_id,
                total_synced = etl_state.total_synced + EXCLUDED.total_synced
        """), {"sync_time": sync_time, "synced_count": synced_count})
        self.session.commit()
    
    def get_updated_products(self, since_time: datetime) -> List[ProductSource]:
        try:
            from sqlalchemy import text
            result = self.session.execute(text("""
                SELECT id, title, description, price, stock, created_at, updated_at 
                FROM products
                WHERE updated_at > :since_time
                ORDER BY updated_at ASC
                LIMIT :limit
            """), {"since_time": since_time, "limit": self.batch_size})
            
            products = result.fetchall()
            logger.info(f"Found {len(products)} updated products since {since_time}")
            return products
        except Exception as e:
            logger.error(f"Failed to fetch updated products: {e}")
            return []
    
    def index_to_elasticsearch(self, products: List[ProductSource]) -> int:
        if not products:
            return 0
        
        actions = []
        for product in products:
            actions.append({
                '_index': 'products',
                '_id': product.id,
                '_source': {
                    'id': product.id,
                    'title': product.title,
                    'description': product.description,
                    'price': float(product.price),
                    'stock': product.stock,
                    'created_at': product.created_at.isoformat(),
                    'updated_at': product.updated_at.isoformat()
                }
            })
        
        from elasticsearch.helpers import bulk
        success, _ = bulk(self.es_client, actions, stats_only=True, raise_on_error=False)
        return success
    
    def run_sync(self):
        logger.info("Running ETL sync...")
        try:
            last_sync = self.get_last_sync_time()
            products = self.get_updated_products(last_sync)
            
            if products:
                indexed = self.index_to_elasticsearch(products)
                if indexed > 0:
                    self.update_sync_state(products[-1].updated_at, indexed)
                logger.info(f"Synced {indexed} products")
            else:
                logger.info("No new products to sync")
        except Exception as e:
            logger.error(f"Sync failed: {e}")

    def full_reindex(self) -> dict:
        logger.info("Starting FULL REINDEX...")
        
        result = {
            "success": False,
            "products_total": 0,
            "products_indexed": 0,
            "error": None
        }
        
        try:
            from sqlalchemy import text
            result_proxy = self.session.execute(text("""
                SELECT id, title, description, price, stock, created_at, updated_at 
                FROM products
            """))
            
            products = result_proxy.fetchall()
            result["products_total"] = len(products)
            logger.info(f"Found {len(products)} products in database")
            
            if products:
                actions = []
                for p in products:
                    doc = {
                        'id': p[0],
                        'title': p[1],
                        'description': p[2] if p[2] else '',
                        'price': float(p[3]),
                        'stock': p[4],
                        'created_at': p[5].isoformat() if p[5] else None,
                        'updated_at': p[6].isoformat() if p[6] else None
                    }
                    actions.append({'_index': 'products', '_id': p[0], '_source': doc})
                
                from elasticsearch.helpers import bulk
                success, failed = bulk(self.es_client, actions, stats_only=True, raise_on_error=False)
                result["products_indexed"] = success
                logger.info(f"Indexed {success} products, failed: {failed}")
                
                #обновляем состояние ETL
                if products:
                    latest = max(products, key=lambda p: p[5] if p[5] else p[6])
                    self.session.execute(text("""
                        INSERT INTO etl_state (id, last_sync_time, last_sync_id, total_synced)
                        VALUES (1, :sync_time, :sync_id, :synced)
                        ON CONFLICT (id) DO UPDATE SET
                            last_sync_time = EXCLUDED.last_sync_time,
                            last_sync_id = EXCLUDED.last_sync_id,
                            total_synced = etl_state.total_synced + EXCLUDED.total_synced
                    """), {"sync_time": latest[5] or latest[6], "sync_id": p[0], "synced": success})
                    self.session.commit()
            
            result["success"] = True
            logger.info(f"Full reindex completed: {result['products_indexed']}/{result['products_total']} products")
            
        except Exception as e:
            logger.error(f"Full reindex failed: {e}")
            result["error"] = str(e)
            import traceback
            traceback.print_exc()
        
        return result
    
    def close(self):
        if self.session:
            self.session.close()
        if self.engine:
            self.engine.dispose()
        if self.es_client:
            self.es_client.close()