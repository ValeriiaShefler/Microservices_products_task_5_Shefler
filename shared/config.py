from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    source_db_host: str = Field("postgres_source", alias="SOURCE_DB_HOST")
    source_db_port: int = Field(5432, alias="SOURCE_DB_PORT")
    source_db_name: str = Field("products_source", alias="SOURCE_DB_NAME")
    source_db_user: str = Field("admin", alias="SOURCE_DB_USER")
    source_db_password: str = Field("admin123", alias="SOURCE_DB_PASSWORD")
    
    purchase_db_host: str = Field("postgres_purchase", alias="PURCHASE_DB_HOST")
    purchase_db_port: int = Field(5432, alias="PURCHASE_DB_PORT")
    purchase_db_name: str = Field("products_purchase", alias="PURCHASE_DB_NAME")
    purchase_db_user: str = Field("purchase_user", alias="PURCHASE_DB_USER")
    purchase_db_password: str = Field("purchase123", alias="PURCHASE_DB_PASSWORD")
    
    @property
    def source_database_url(self) -> str:
        return f"postgresql://{self.source_db_user}:{self.source_db_password}@{self.source_db_host}:{self.source_db_port}/{self.source_db_name}"
    
    @property
    def purchase_database_url(self) -> str:
        return f"postgresql://{self.purchase_db_user}:{self.purchase_db_password}@{self.purchase_db_host}:{self.purchase_db_port}/{self.purchase_db_name}"
    
    elasticsearch_host: str = Field("elasticsearch", alias="ELASTICSEARCH_HOST")
    elasticsearch_port: int = Field(9200, alias="ELASTICSEARCH_PORT")
    
    search_service_url: str = Field("http://search_api:8002", alias="SEARCH_SERVICE_URL")
    
    etl_interval_minutes: int = Field(5, alias="ETL_INTERVAL_MINUTES")
    etl_batch_size: int = Field(100, alias="ETL_BATCH_SIZE")
    
    min_product_title_length: int = Field(3, alias="MIN_PRODUCT_TITLE_LENGTH")
    max_product_title_length: int = Field(255, alias="MAX_PRODUCT_TITLE_LENGTH")
    max_purchase_quantity: int = Field(100, alias="MAX_PURCHASE_QUANTITY")
    default_page_size: int = Field(20, alias="DEFAULT_PAGE_SIZE")
    max_page_size: int = Field(100, alias="MAX_PAGE_SIZE")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

settings = Settings()