# Микросервисная система управления продуктами  

## О проекте  

Микросервисная система для управления каталогом продуктов электронной коммерции (во всяком случае подразумевалась под нее).  

### Технологии  

| Компонент | Технология |
|-----------|------------|
| API | FastAPI |
| Admin Panel | Flask |
| Базы данных | PostgreSQL 15 |
| Поисковый движок | Elasticsearch 8.11 |
| ORM | SQLAlchemy 2.0 |
| Контейнеризация | Docker, Docker Compose |
| Конфигурация | Pydantic BaseSettings |

## Переменные окружения:  

    # PostgreSQL Source  
    SOURCE_DB_HOST=postgres_source  
    SOURCE_DB_PORT=5432  
    SOURCE_DB_NAME=products_source  
    SOURCE_DB_USER=admin  
    SOURCE_DB_PASSWORD=admin123  

    # PostgreSQL Purchase  
    PURCHASE_DB_HOST=postgres_purchase  
    PURCHASE_DB_PORT=5432  
    PURCHASE_DB_NAME=products_purchase  
    PURCHASE_DB_USER=purchase_user  
    PURCHASE_DB_PASSWORD=purchase123  

    # Elasticsearch  
    ELASTICSEARCH_HOST=elasticsearch  
    ELASTICSEARCH_PORT=9200  

    # URLs  
    SEARCH_SERVICE_URL=http://search_api:8002  

    # ETL  
    ETL_INTERVAL_SECONDS=5  
    ETL_BATCH_SIZE=100  

    # Validation  
    MIN_PASSWORD_LENGTH=8  
    MAX_PASSWORD_LENGTH=128  
    MIN_PRODUCT_TITLE_LENGTH=3  
    MAX_PRODUCT_TITLE_LENGTH=255  
    MAX_PURCHASE_QUANTITY=100  
    DEFAULT_PAGE_SIZE=20  
    MAX_PAGE_SIZE=100  

## Полное дерево проекта:  

    microservices_products/  
    │  
    ├── docker-compose.yml                 # Оркестрация всех сервисов  
    ├── .env.example                       # Шаблон переменных окружения  
    ├── .gitignore                         # Игнорируемые файлы  
    ├── README.md                          # Документация  
    │  
    ├── shared/                            # Общие модули (Pydantic BaseSettings)  
    │   ├── __init__.py  
    │   ├── config.py                      # Конфигурация через BaseSettings  
    │   └── database.py                    # Базовый класс для работы с БД  
    │  
    ├── admin_panel/                       # Flask Admin Panel (порт 8000)  
    │   ├── Dockerfile  
    │   ├── requirements.txt  
    │   ├── app.py                         # Основное приложение  
    │   ├── models.py                      # SQLAlchemy модели  
    │   ├── services.py                    # Бизнес-логика  
    │   └── templates/  
    │       ├── base.html                  # Базовый шаблон  
    │       ├── index.html                 # Список товаров  
    │       └── product_form.html          # Форма создания/редактирования  
    │
    ├── purchase_service/                  # FastAPI Purchase Service (порт 8001)  
    │   ├── Dockerfile  
    │   ├── requirements.txt  
    │   ├── app.py                         # API + веб-интерфейс  
    │   ├── models.py                      # SQLAlchemy + Pydantic модели  
    │   ├── services.py                    # Бизнес-логика  
    │   ├── database.py                    # Подключение к БД  
    │   ├── clients.py                     # HTTP клиент для Search Service  
    |   └── templates/  
    │       ├── base.html                  # Базовый шаблон  
    │       ├── index.html                 # Главная страница  
    │       ├── products_list.html         # Список товаров  
    │       ├── product_detail.html        # Детали товара  
    │       ├── search_page.html           # Страница поиска  
    │       └── stats.html                 # Статистика продаж  
    │  
    ├── search_service/                    # FastAPI Search Service (порт 8002)  
    │   ├── Dockerfile  
    │   ├── requirements.txt  
    │   ├── app.py                         # API + веб-интерфейс  
    │   ├── models.py                      # Pydantic модели  
    │   ├── elastic_client.py              # Клиент Elasticsearch  
    │   ├── search_logic.py                # Логика поиска  
    |   └── templates/  
    │       ├── base.html                  # Базовый шаблон  
    │       ├── index.html                 # Главная страница  
    │       ├── search.html                # Поиск с результатами  
    │       ├── suggestions.html           # Автокомплит  
    │       └── about.html                 # О сервисе  
    │  
    └── etl_service/                       # ETL Service (синхронизация)  
        ├── Dockerfile  
        ├── requirements.txt  
        ├── etl.py                         # Основной вход  
        ├── models.py                      # SQLAlchemy модели  
        ├── scheduler.py                   # Планировщик задач  
        └── sync_service.py                # Логика синхронизации   

Shared - централизованное хранение конфигурации и общих утилит, переиспользуемых всеми сервисами  

Admin Panel (порт 8000) - веб-интерфейс для администратора — управление каталогом товаров  

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/` | Главная страница (список товаров) |
| GET | `/products/new` | Форма создания товара |
| POST | `/products` | Создание товара |
| GET | `/products/{id}/edit` | Форма редактирования товара |
| POST | `/products/{id}` | Обновление товара |

Purchase Service (порт 8001) - основной API и веб-интерфейс для работы с товарами и покупками  

| Метод | Эндпоинт | Описание | Формат |
|-------|----------|----------|--------|
| GET | `/products` | Список всех продуктов | JSON + HTML |
| GET | `/products/{id}` | Продукт по ID | JSON + HTML |
| POST | `/products/{id}/purchase` | Купить продукт | JSON |
| GET | `/products/search?q=` | Поиск (через Search Service) | JSON |
| GET | `/purchase/{id}` | Форма покупки | HTML |
| POST | `/purchase/{id}` | Обработка покупки | HTML |
| GET | `/search` | Страница поиска | HTML |
| GET | `/stats` | Статистика продаж | HTML |
| GET | `/health` | Проверка здоровья сервиса | JSON |
| GET | `/docs` | Swagger UI | HTML |


Search Service (порт 8002) - полнотекстовый поиск товаров с поддержкой русского языка  

| Метод | Эндпоинт | Описание | Формат |
|-------|----------|----------|--------|
| GET | `/api/search?q=` | Полнотекстовый поиск | JSON |
| GET | `/api/search/suggest?q=` | Поисковые подсказки | JSON |
| GET | `/api/products` | Получить все товары (без запроса) | JSON |
| GET | `/api/product/{id}` | Получить товар по ID | JSON |
| PUT | `/api/product/{id}/stock` | Обновить остаток | JSON |
| GET | `/` | Главная страница | HTML |
| GET | `/search` | Страница поиска с результатами | HTML |
| GET | `/suggest` | Страница автокомплита | HTML |
| GET | `/about` | О сервисе | HTML |
| GET | `/docs` | Swagger UI | HTML |

ETL Service - автоматическая синхронизация данных из PostgreSQL в Elasticsearch  

Базы данных:  

| База данных | Порт | Назначение | Таблицы |
|-------------|------|------------|---------|
| PostgreSQL (source) | 5434 | Исходные данные для админ-панели и ETL | `products`, `etl_state` |
| PostgreSQL (purchase) | 5435 | Данные для сервиса покупок | `products`, `purchases` |
| Elasticsearch | 9200 | Поисковый движок | индекс `products` |

### Установка и запуск

# 1. Клонирование репозитория
git clone https://github.com/yourusername/Microservices_products_task_5_Shefler.git
cd Microservices_products_task_5_Shefler

# 2. Настройка окружения
cp .env.example .env

# 3. Запуск всех сервисов
docker-compose up --build

# Health check всех сервисов
curl http://localhost:8000/          # Admin Panel
curl http://localhost:8001/health    # Purchase Service
curl http://localhost:8002/health    # Search Service

# Методы пользования  

## Способ 1  

Пользоваться можно через Swagger UI (http://localhost:8001/docs и http://localhost:8002/docs)  

# Способ 2  

Через curl-запросы:  

    Получить список всех продуктов:  
        curl http://localhost:8001/products  
    
    С пагинацией:   
        curl "http://localhost:8001/products?skip=0&limit=10"  

    Получить продукт по id:  
        curl http://localhost:8001/products/1  

    Приобрести продукт:  
        curl -X POST http://localhost:8001/products/1/purchase \  
            -H "Content-Type: application/json" \  
            -d '{"quantity": 2}'  
    
    Поиск продуктов:  
        curl "http://localhost:8001/products/search?q=ноутбук"  

Панель администратора достпуна по адресу http://localhost:8000

# Способ 3 (рекомендуется)  

Работа через веб-клиент по адресам:  

    http://localhost:8000 - панель администратора  
    http://localhost:8001 - сервис покупок  
    http://localhost:8002 - сервис поиска  

# Просмотр логов
docker-compose logs -f

# Статус контейнеров
docker-compose ps