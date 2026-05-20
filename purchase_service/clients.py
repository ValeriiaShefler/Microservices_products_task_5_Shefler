import httpx
import logging

logger = logging.getLogger(__name__)

class SearchClient:
    def __init__(self):
        self.base_url = "http://search_api:8002"
    
    async def search_products(self, query: str = "", limit: int = 20, offset: int = 0):
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Если query пустая, отправляем пустую строку (Search API обработает как match_all)
            params = {"q": query or "", "limit": limit, "offset": offset}
            response = await client.get(
                f"{self.base_url}/api/search",
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def get_product_by_id(self, product_id: int):
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/api/product/{product_id}",  # ← измени URL
                params={"limit": 1, "offset": 0}
            )
            response.raise_for_status()
            return response.json()
        
    async def get_all_products(self, limit: int = 20, offset: int = 0):
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/api/products",
                params={"limit": limit, "offset": offset}
            )
            response.raise_for_status()
            return response.json()

search_client = SearchClient()