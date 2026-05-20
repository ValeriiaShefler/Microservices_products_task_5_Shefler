import logging
from typing import Dict, Any, List
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

logger = logging.getLogger(__name__)

class ElasticsearchClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.client = None
        self.index_name = "products"
    
    def connect(self) -> bool:
        try:
            self.client = Elasticsearch([f"http://{self.host}:{self.port}"])
            if self.client.ping():
                logger.info(f"Connected to Elasticsearch")
                return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
        return False
    
    def is_connected(self) -> bool:
        return self.client and self.client.ping()
    
    def create_index(self) -> bool:
        if self.client.indices.exists(index=self.index_name):
            return True
        
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
        
        try:
            self.client.indices.create(index=self.index_name, body=mapping)
            logger.info(f"Created index '{self.index_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            return False
    
    def search(self, query_body: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.search(index=self.index_name, body=query_body)
    
    def close(self):
        if self.client:
            self.client.close()