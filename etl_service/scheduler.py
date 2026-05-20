import schedule
import time
import threading
import logging
from typing import Callable

logger = logging.getLogger(__name__)

class ETLScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def add_interval_job(self, job_func: Callable, interval_seconds: int):
        schedule.every(interval_seconds).seconds.do(job_func)
        logger.info(f"Scheduled ETL every {interval_seconds} seconds")
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def _run(self):
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)