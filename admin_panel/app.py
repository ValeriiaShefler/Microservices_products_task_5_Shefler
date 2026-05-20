import os
from flask import Flask, render_template, request, redirect, url_for, flash
from shared.database import DatabaseManager
from models import Product
from services import ProductService

app = Flask(__name__)
app.secret_key = "dev-secret-key"

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin123@postgres_source:5432/products_source")
db_manager = DatabaseManager(DATABASE_URL)

def get_db():
    return next(db_manager.get_session())

@app.route('/')
def index():
    db = get_db()
    service = ProductService(db)
    products = service.get_all_products()
    return render_template('index.html', products=products)

@app.route('/products/new', methods=['GET'])
def new_product():
    return render_template('product_form.html', product=None)

@app.route('/products', methods=['POST'])
def create_product():
    print("=== CREATE PRODUCT CALLED ===")
    print("Form data:", request.form)
    db = get_db()
    service = ProductService(db)
    try:
        product = service.create_product(
            title=request.form['title'],
            description=request.form.get('description', ''),
            price=float(request.form['price']),
            stock=int(request.form.get('stock', 0))
        )
        flash(f'Продукт "{product.title}" добавлен', 'success')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
    return redirect(url_for('index'))

@app.route('/products/<int:id>/edit', methods=['GET'])
def edit_product(id):
    db = get_db()
    service = ProductService(db)
    product = service.get_product_by_id(id)
    return render_template('product_form.html', product=product)

@app.route('/products/<int:id>', methods=['POST'])
def update_product(id):
    db = get_db()
    service = ProductService(db)
    try:
        product = service.update_product(
            product_id=id,
            title=request.form.get('title'),
            description=request.form.get('description'),
            price=float(request.form['price']) if request.form.get('price') else None,
            stock=int(request.form['stock']) if request.form.get('stock') else None
        )
        flash(f'Продукт обновлен!', 'success')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    db_manager.connect()
    db_manager.create_tables()
    app.run(host='0.0.0.0', port=8000, debug=True)