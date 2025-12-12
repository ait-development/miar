# MIAR - Microservices Architecture Project

Проект микросервисной архитектуры с использованием FastAPI, RabbitMQ и развёртыванием в Яндекс.Облаке.

## Структура проекта

```
miar/
├── services/              # Микросервисы
│   ├── auth-service/      # Сервис аутентификации
│   ├── customers-service/ # Сервис управления клиентами
│   ├── accounts-service/  # Сервис управления счетами ✨ (с CI/CD)
│   ├── payments-service/  # Сервис платежей
│   ├── cards-service/     # Сервис управления картами
│   ├── loans-service/     # Сервис кредитов
│   ├── notifications-service/ # Сервис уведомлений
│   └── audit-service/     # Сервис аудита ✨ (с CI/CD)
├── common/                # Общие модули
├── tests/                 # Тесты
│   ├── component/         # Компонентные тесты
│   ├── integration/       # Интеграционные тесты
│   └── unit/              # Юнит-тесты
├── docker/                # Docker конфигурации
├── scripts/               # Скрипты для деплоя и тестирования
└── docs/                  # Документация
```

## Сервисы

### Accounts Service (с CI/CD) ✨

Сервис для управления счетами и создания платежных инструкций.

**Особенности:**
- Автоматическая CI/CD через GitHub Actions
- Развёртывание в Яндекс.Облако Serverless Containers
- Автоматическое масштабирование
- REST API для управления платежами
- Интеграция с RabbitMQ

**Endpoints:**
- `POST /accounts/{account_id}/payments` - Создание платежной инструкции

**Документация:**
- [Полное руководство по развёртыванию](./docs/ACCOUNTS_SERVICE_DEPLOYMENT.md)

### Audit Service (с CI/CD) ✨

Сервис для сбора и хранения событий аудита от других сервисов.

**Особенности:**
- Автоматическая CI/CD через GitHub Actions
- Развёртывание в Яндекс.Облако Serverless Containers
- Автоматическое масштабирование
- Сбор событий через RabbitMQ

**Документация:**
- [Полное руководство по развёртыванию](./docs/AUDIT_SERVICE_DEPLOYMENT.md)
- [Быстрый старт](./docs/QUICKSTART_DEPLOYMENT.md)

## Локальная разработка

### Предварительные требования

- Python 3.11+
- Docker и Docker Compose
- RabbitMQ (запускается через Docker Compose)

### Установка зависимостей

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/macOS
# или
.\venv\Scripts\activate   # Windows

# Установить зависимости
pip install -r requirements-test.txt
```

### Запуск всех сервисов

```bash
# Запустить все сервисы через Docker Compose
docker-compose up -d

# Проверить статус
docker-compose ps

# Просмотр логов
docker-compose logs -f audit-service
```

### Доступ к сервисам

- **RabbitMQ Management**: http://localhost:15672 (admin/admin)
- **Auth Service**: http://localhost:8001
- **Customers Service**: http://localhost:8002
- **Accounts Service**: http://localhost:8003
- **Payments Service**: http://localhost:8004
- **Cards Service**: http://localhost:8005
- **Loans Service**: http://localhost:8006
- **Notifications Service**: http://localhost:8007
- **Audit Service**: http://localhost:8008

## Тестирование

### Запуск всех тестов

```bash
# Компонентные тесты
pytest tests/component/ -v

# Интеграционные тесты
pytest tests/integration/ -v

# Юнит-тесты
pytest tests/unit/ -v

# Все тесты
pytest -v
```

### Тестирование Audit Service

```bash
# Только тесты audit-service
pytest tests/component/test_audit_service.py -v

# С покрытием кода
pytest tests/component/test_audit_service.py --cov=services/audit-service
```

### Smoke тест

```bash
# Проверка работоспособности всех сервисов
python scripts/smoke_test.py
```

## CI/CD

### GitHub Actions Workflows

Проект использует GitHub Actions для автоматизации CI/CD процессов.

#### Accounts Service Workflow

**Триггеры:**
- Push в `main` с изменениями в `services/accounts-service/` или `common/`
- Pull Request с изменениями в указанных директориях
- Ручной запуск через GitHub UI

**Этапы:**
1. **Test** - Запуск компонентных тестов
2. **Build** - Сборка Docker-образа
3. **Push** - Загрузка образа в Yandex Container Registry
4. **Deploy** - Развёртывание в Serverless Containers
5. **Health Check** - Проверка работоспособности

**Статус:** [![Accounts Service CI/CD](../../actions/workflows/accounts-service-deploy.yml/badge.svg)](../../actions/workflows/accounts-service-deploy.yml)

#### Audit Service Workflow

**Триггеры:**
- Push в `main` с изменениями в `services/audit-service/` или `common/`
- Pull Request с изменениями в указанных директориях
- Ручной запуск через GitHub UI

**Этапы:**
1. **Test** - Запуск компонентных тестов
2. **Build** - Сборка Docker-образа
3. **Push** - Загрузка образа в Yandex Container Registry
4. **Deploy** - Развёртывание в Serverless Containers
5. **Health Check** - Проверка работоспособности

**Статус:** [![Audit Service CI/CD](../../actions/workflows/audit-service-deploy.yml/badge.svg)](../../actions/workflows/audit-service-deploy.yml)

### Локальное развёртывание в Yandex Cloud

```bash
# Настроить переменные окружения
export YC_REGISTRY_ID="your-registry-id"
export YC_FOLDER_ID="your-folder-id"
export YC_SERVICE_ACCOUNT_ID="your-sa-id"
export RABBITMQ_URL="amqp://user:pass@host:5672/"

# Запустить развёртывание
./scripts/deploy_audit_service.sh
```

Подробнее: [Документация по развёртыванию](./docs/AUDIT_SERVICE_DEPLOYMENT.md)

## Архитектура

### Коммуникация между сервисами

Сервисы взаимодействуют через RabbitMQ используя два типа обмена:

1. **Service Events** (Direct Exchange)
   - Прямая адресация событий конкретным сервисам
   - Используется для критичных бизнес-событий

2. **Topic Workloads** (Topic Exchange)
   - Публикация задач по топикам с символами (*, #, -)
   - Используется для асинхронной обработки задач

### Audit Service

Собирает все события от других сервисов:
- Подписан на очередь сервисных событий `audit`
- Подписан на топик воркера с символом `-`
- Хранит последние 200 событий в памяти (deque)
- Предоставляет API для получения статистики

## Технологии

- **Backend**: FastAPI, Python 3.11+
- **Message Broker**: RabbitMQ (aio-pika)
- **Serialization**: orjson
- **Testing**: pytest, pytest-asyncio
- **CI/CD**: GitHub Actions
- **Cloud**: Yandex Cloud Serverless Containers
- **Container Registry**: Yandex Container Registry
- **Containerization**: Docker

## Переменные окружения

### Общие для всех сервисов

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `SERVICE_NAME` | Имя сервиса | - |
| `SERVICE_ROLE` | Роль сервиса | - |
| `SERVICE_PORT` | Порт сервиса | `8000` |
| `RABBITMQ_URL` | URL подключения к RabbitMQ | `amqp://admin:admin@rabbitmq:5672/` |

### Специфичные для Audit Service

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `SLEEP_SYMBOL` | Символ для подписки на топик | `-` |

## Разработка

### Добавление нового сервиса

1. Создайте директорию в `services/`
2. Добавьте `app/main.py` с FastAPI приложением
3. Добавьте `requirements.txt` с зависимостями
4. Добавьте сервис в `docker-compose.yml`
5. Создайте тесты в `tests/component/`

### Настройка CI/CD для нового сервиса

Используйте `audit-service` как шаблон:
1. Скопируйте `.github/workflows/audit-service-deploy.yml`
2. Измените названия сервиса
3. Настройте переменные окружения
4. Создайте Dockerfile в директории сервиса

### Стиль кода

```bash
# Форматирование
black services/ common/ tests/

# Линтинг
ruff check services/ common/ tests/

# Проверка типов
mypy services/ common/
```

## Мониторинг

### Логи в Yandex Cloud

```bash
# Просмотр логов audit-service
yc serverless container revision logs \
  --container-name audit-service-container \
  --follow

# Логи конкретной ревизии
yc serverless container revision logs \
  --revision-id <REVISION_ID>
```

### Метрики

Метрики доступны в Yandex Cloud Console:
- Количество запросов
- Время выполнения
- Ошибки
- Активные инстансы

## Безопасность

- Сервисный аккаунт с минимальными привилегиями
- Секреты хранятся в GitHub Secrets
- Docker-образы собираются с непривилегированным пользователем
- Регулярное обновление зависимостей

## Стоимость (Yandex Cloud)

Примерная стоимость для audit-service:
- **Малая нагрузка**: ~100-200 ₽/месяц
- **Средняя нагрузка**: ~500-1000 ₽/месяц
- **Высокая нагрузка**: ~2000-5000 ₽/месяц

*Включает бесплатный Free Tier*

## Документация

### Развёртывание сервисов

- [Руководство по развёртыванию Accounts Service](./docs/ACCOUNTS_SERVICE_DEPLOYMENT.md)
- [Руководство по развёртыванию Audit Service](./docs/AUDIT_SERVICE_DEPLOYMENT.md)
- [Быстрый старт развёртывания](./docs/QUICKSTART_DEPLOYMENT.md)

### Общая информация

- [GitHub Actions CI/CD](./docs/GITHUB_ACTIONS.md)
- [Шпаргалка по командам](./docs/CHEATSHEET.md)

## Лицензия

MIT

## Контакты

При возникновении вопросов создайте issue в репозитории.
