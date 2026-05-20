#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."

until python -c "
import psycopg2
import time
try:
    conn = psycopg2.connect(
        host='postgres_purchase',
        port=5432,
        user='purchase_user',
        password='purchase123',
        database='products_purchase',
        connect_timeout=2
    )
    conn.close()
    exit(0)
except Exception as e:
    exit(1)
" 2>/dev/null; do
  echo "PostgreSQL is not ready yet. Waiting..."
  sleep 2
done

echo "PostgreSQL is ready!"

# создаём таблицы (через SQLAlchemy models)
echo "Creating tables..."
python -c "from app import db_manager; from models import Base; db_manager.connect(); Base.metadata.create_all(db_manager.engine)"

# синхронизируем товары из source БД в purchase БД
echo "Syncing products from source database to purchase database..."
python -c "
import psycopg2
from app import db_manager
from models import ProductDB
from sqlalchemy.orm import sessionmaker

#подключаемся к purchase БД
db_manager.connect()
Session = sessionmaker(bind=db_manager.engine)
session = Session()

# подключаемся к source БД
source_conn = psycopg2.connect(
    host='postgres_source',
    port=5432,
    user='admin',
    password='admin123',
    database='products_source'
)
cursor = source_conn.cursor()
cursor.execute('SELECT id, title, description, price, stock FROM products')
rows = cursor.fetchall()

for row in rows:
    product = session.query(ProductDB).filter(ProductDB.id == row[0]).first()
    if product:
        product.title = row[1]
        product.description = row[2]
        product.price = row[3]
        product.stock = row[4]
    else:
        new_product = ProductDB(
            id=row[0],
            title=row[1],
            description=row[2],
            price=row[3],
            stock=row[4]
        )
        session.add(new_product)
    print(f'Synced product {row[0]}: {row[1]}')

session.commit()
cursor.close()
source_conn.close()
print('Products sync completed!')
"

#запускаем приложение
exec python app.py