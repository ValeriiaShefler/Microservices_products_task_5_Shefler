from shared.database import DatabaseManager
from shared.config import settings

db_manager = DatabaseManager(settings.purchase_database_url)

def get_db():
    return next(db_manager.get_session())

def init_db():
    db_manager.connect()
    db_manager.create_tables()