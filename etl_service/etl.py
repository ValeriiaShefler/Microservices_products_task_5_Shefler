#!/usr/bin/env python3
import os
import time
import logging
from sqlalchemy import text
from sync_service import ETLSyncService
from scheduler import ETLScheduler
from models import Base as SourceBase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ETLApplication:
    def __init__(self):
        self.sync_service = ETLSyncService()
        self.scheduler = ETLScheduler()
        self.interval = int(os.getenv("ETL_INTERVAL_SECONDS", "60"))
    
    def start(self):
        logger.info("Starting ETL Service...")
        logger.info(f"Sync interval: {self.interval} seconds")
        
        # ждем базы данных
        time.sleep(10)
        
        if not self.sync_service.connect_source_db():
            logger.error("Failed to connect to source DB")
            return
        
        # создаём таблицы в source БД, если их нет
        SourceBase.metadata.create_all(self.sync_service.engine)
        logger.info("Source database tables verified/created")

        if not self.sync_service.connect_elasticsearch():
            logger.error("Failed to connect to Elasticsearch")
            return
        
        self.sync_service.ensure_index()
        
        # проверяем, есть ли данные в source БД (ждём максимум 30 секунд)
        max_wait = 30
        waited = 0
        while waited < max_wait:
            result = self.sync_service.session.execute(text("SELECT COUNT(*) FROM products"))
            count = result.scalar()
            if count > 0:
                logger.info(f"Found {count} products in source database")
                break
            logger.info(f"No products yet. Waiting... ({waited}s/{max_wait}s)")
            time.sleep(5)
            waited += 5
        
        #запускаем полную индексацию
        logger.info("Running full reindex...")
        self.sync_service.full_reindex()
        
        self.scheduler.add_interval_job(self.sync_service.run_sync, self.interval)
        self.scheduler.start()
        
        self.sync_service.run_sync()
        
        logger.info("ETL Service running...")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.scheduler.stop()
            self.sync_service.close()
            logger.info("ETL Service stopped")

if __name__ == "__main__":
    app = ETLApplication()
    app.start()