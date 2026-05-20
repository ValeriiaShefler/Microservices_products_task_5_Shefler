from typing import List, Dict, Any
from elastic_client import ElasticsearchClient
from models import ProductDocument, SearchResponse

class SearchLogic:
    def __init__(self, es_client: ElasticsearchClient):
        self.es_client = es_client
    
    def build_query(self, query: str, offset: int, limit: int) -> Dict[str, Any]:
        return {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "description"],
                    "fuzziness": "AUTO"
                }
            },
            "from": offset,
            "size": limit,
            "sort": [{"_score": {"order": "desc"}}]
        }
    
    async def search(self, query: str, limit: int, offset: int) -> SearchResponse:
        if not self.es_client.is_connected():
            raise ConnectionError("Elasticsearch is not available")
        
        if not query or query.strip() == "" or query.strip() == "*":
            search_body = {
                "query": {"match_all": {}},
                "from": offset,
                "size": limit,
                "sort": [{"id": {"order": "asc"}}]
            }
        else:
            search_body = self.build_query(query, offset, limit)
        
        response = self.es_client.search(search_body)
        
        products = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            product = ProductDocument(
                id=source['id'],
                title=source['title'],
                description=source.get('description'),
                price=source['price'],
                stock=source['stock'],
                created_at=source['created_at'],
                updated_at=source['updated_at']
            )
            products.append(product)
        
        return SearchResponse(
            query=query,
            total=response['hits']['total']['value'],
            offset=offset,
            limit=limit,
            products=products
        )
    
    async def suggest(self, prefix: str, limit: int) -> List[str]:
        if not self.es_client.is_connected():
            raise ConnectionError("Elasticsearch is not available")
        
        query_body = {
            "query": {
                "wildcard": {
                    "title": {
                        "value": f"{prefix}*"
                    }
                }
            },
            "size": limit,
            "_source": ["title"]
        }
        
        response = self.es_client.search(query_body)
        suggestions = list(set([hit['_source']['title'] for hit in response['hits']['hits']]))
        return suggestions[:limit]