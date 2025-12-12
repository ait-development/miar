# Scripts Directory

Коллекция скриптов для автоматизации развёртывания, тестирования и управления проектом.

## Скрипты развёртывания

### `deploy_audit_service.sh`

Автоматическое развёртывание audit-service в Yandex Cloud Serverless Containers.

> **Примечание**: Для accounts-service используется автоматическое развёртывание через GitHub Actions. См. [документацию по развёртыванию Accounts Service](../docs/ACCOUNTS_SERVICE_DEPLOYMENT.md).

**Использование:**
```bash
./scripts/deploy_audit_service.sh [environment]
```

**Параметры:**
- `environment` (опционально) - Окружение для развёртывания (по умолчанию: `production`)

**Требуемые переменные окружения:**
```bash
export YC_REGISTRY_ID="crp..."        # ID Container Registry
export YC_FOLDER_ID="b1g..."          # ID каталога Yandex Cloud
export YC_SERVICE_ACCOUNT_ID="aje..." # ID сервисного аккаунта
export RABBITMQ_URL="amqp://..."      # URL подключения к RabbitMQ
```

**Что делает скрипт:**
1. ✅ Проверяет наличие необходимых инструментов (yc, docker, jq)
2. 🔨 Собирает Docker-образ для audit-service
3. ⬆️ Загружает образ в Yandex Container Registry
4. 🚀 Разворачивает или обновляет Serverless Container
5. 🏥 Выполняет health check развёрнутого сервиса

**Пример:**
```bash
# Загрузить переменные из файла
source .env

# Запустить развёртывание
./scripts/deploy_audit_service.sh production
```

**Вывод:**
- ✅ Цветной вывод с индикацией прогресса
- 🔗 URL развёрнутого контейнера
- ❌ Информативные сообщения об ошибках

---

## Скрипты тестирования

### `run_component_tests.sh` (Linux/macOS)

Запуск компонентных тестов для всех сервисов.

**Использование:**
```bash
./scripts/run_component_tests.sh
```

**Что делает:**
- Запускает все тесты из директории `tests/component/`
- Выводит подробный отчёт о прохождении тестов
- Возвращает код выхода 0 при успехе, 1 при ошибке

**Пример вывода:**
```
===================================== test session starts ======================================
tests/component/test_accounts_service.py::test_accounts_service_health_check PASSED    [ 25%]
tests/component/test_audit_service.py::test_audit_service_health_check PASSED          [ 50%]
...
====================================== 10 passed in 5.23s ======================================
```

---

### `run_component_tests.bat` (Windows)

Windows-версия скрипта запуска компонентных тестов.

**Использование:**
```cmd
scripts\run_component_tests.bat
```

Функционал аналогичен `run_component_tests.sh`.

---

### `test_accounts_service.sh`

Тестирование развёрнутого accounts-service в Yandex Cloud Serverless Containers.

**Использование:**
```bash
# Автоматически получить URL из Yandex Cloud
./scripts/test_accounts_service.sh

# Или указать URL вручную
./scripts/test_accounts_service.sh https://your-container-url
```

**Что делает:**
1. ✅ Проверяет health endpoint
2. 📚 Проверяет доступность OpenAPI документации
3. 💸 Создаёт тестовую платежную инструкцию
4. ✔️ Тестирует валидацию запросов

**Пример вывода:**
```
Testing Accounts Service at: https://d5d...serverless.yandexcloud.net

[1/4] Testing health endpoint...
✅ Health check passed
Response: {"status":"healthy","service":"accounts-service"}

[2/4] Testing OpenAPI docs endpoint...
✅ OpenAPI docs available
URL: https://d5d...serverless.yandexcloud.net/docs

[3/4] Testing payment creation...
✅ Payment instruction created
Response: {"status":"queued","instruction_id":"550e8400-e29b-41d4-a716-446655440000"}

[4/4] Testing validation (invalid request)...
✅ Validation working correctly

========================================
✅ All tests completed!
========================================
```

**Требуемые инструменты:**
- `curl` - для HTTP запросов
- `jq` - для парсинга JSON
- `yc` (опционально) - для автоматического получения URL

---

### `smoke_test.py`

Быстрая проверка работоспособности всех сервисов в запущенной системе.

**Использование:**
```bash
# Запустить все сервисы
docker-compose up -d

# Подождать несколько секунд для инициализации
sleep 10

# Запустить smoke test
python scripts/smoke_test.py
```

**Проверяемые сервисы:**
- ✅ auth-service (port 8001)
- ✅ customers-service (port 8002)
- ✅ accounts-service (port 8003)
- ✅ payments-service (port 8004)
- ✅ cards-service (port 8005)
- ✅ loans-service (port 8006)
- ✅ notifications-service (port 8007)
- ✅ audit-service (port 8008)

**Проверки:**
- HTTP GET `/health` для каждого сервиса
- Ожидаемый response: `{"service": "service-name", "status": "ok"}`

**Пример вывода:**
```
🏥 Running smoke tests...

✅ auth-service is healthy (port 8001)
✅ customers-service is healthy (port 8002)
✅ accounts-service is healthy (port 8003)
...
✅ audit-service is healthy (port 8008)

🎉 All services are healthy!
```

**В случае ошибки:**
```
❌ audit-service is NOT healthy (port 8008)
   Error: Connection refused

⚠️ Some services failed health check!
```

---

## Рабочие процессы

### Локальная разработка и тестирование

```bash
# 1. Запустить все сервисы
docker-compose up -d

# 2. Проверить работоспособность
python scripts/smoke_test.py

# 3. Запустить компонентные тесты
./scripts/run_component_tests.sh

# 4. Внести изменения в код
vim services/audit-service/app/main.py

# 5. Пересобрать и перезапустить сервис
docker-compose up -d --build audit-service

# 6. Повторить тесты
pytest tests/component/test_audit_service.py -v
```

### Развёртывание в production

```bash
# 1. Настроить переменные окружения
cp env.example .env
vim .env  # Заполнить реальными значениями

# 2. Загрузить переменные
source .env

# 3. Запустить развёртывание
./scripts/deploy_audit_service.sh production

# 4. Проверить deployment
CONTAINER_URL=$(yc serverless container get audit-service-container --format json | jq -r '.url')
curl ${CONTAINER_URL}/health
```

### CI/CD Pipeline

При push в `main`:
1. GitHub Actions автоматически запускает тесты
2. Если тесты проходят, собирается Docker-образ
3. Образ загружается в Yandex Container Registry
4. Разворачивается новая ревизия Serverless Container
5. Выполняется health check

---

## Добавление новых скриптов

### Рекомендации

1. **Именование**: Используйте понятные имена с префиксом действия
   - `deploy_*` - для скриптов развёртывания
   - `test_*` или `run_*_tests` - для тестовых скриптов
   - `setup_*` - для скриптов настройки

2. **Shebang**: Всегда указывайте shebang в начале скрипта
   ```bash
   #!/bin/bash
   ```

3. **Безопасность**: Используйте `set -e` для остановки при ошибках
   ```bash
   set -e  # Exit on error
   ```

4. **Документация**: Добавьте комментарий с описанием использования
   ```bash
   # Deploy service to Yandex Cloud
   # Usage: ./script.sh [environment]
   ```

5. **Права выполнения**: Сделайте скрипт исполняемым
   ```bash
   chmod +x scripts/new_script.sh
   ```

6. **Обновите README**: Добавьте описание нового скрипта в этот файл

---

## Переменные окружения

Скрипты используют следующие переменные окружения:

### Для Yandex Cloud (deploy_audit_service.sh)

| Переменная | Описание | Обязательна |
|------------|----------|-------------|
| `YC_REGISTRY_ID` | ID Container Registry | ✅ |
| `YC_FOLDER_ID` | ID каталога Yandex Cloud | ✅ |
| `YC_SERVICE_ACCOUNT_ID` | ID сервисного аккаунта | ✅ |
| `RABBITMQ_URL` | URL подключения к RabbitMQ | ⚠️ |

⚠️ - Если не указана, используется значение по умолчанию

### Для тестирования (smoke_test.py)

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `SERVICE_HOST` | Хост для подключения к сервисам | `localhost` |
| `TIMEOUT` | Таймаут для HTTP запросов (сек) | `5` |

---

## Troubleshooting

### deploy_audit_service.sh

**Ошибка: "yc is not installed"**
```bash
# Установить Yandex Cloud CLI
curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
source ~/.bashrc
```

**Ошибка: "YC_REGISTRY_ID is not set"**
```bash
# Получить ID реестра
yc container registry list
export YC_REGISTRY_ID="crp..."
```

**Ошибка: "Docker push failed"**
```bash
# Настроить Docker для работы с Yandex Container Registry
yc container registry configure-docker
```

### smoke_test.py

**Ошибка: "Connection refused"**
```bash
# Проверить, что сервисы запущены
docker-compose ps

# Запустить сервисы
docker-compose up -d

# Подождать инициализации
sleep 10
```

**Ошибка: "Service returned wrong status"**
```bash
# Проверить логи сервиса
docker-compose logs audit-service

# Перезапустить сервис
docker-compose restart audit-service
```

---

## Дополнительные ресурсы

- [Документация по развёртыванию Accounts Service](../docs/ACCOUNTS_SERVICE_DEPLOYMENT.md)
- [Документация по развёртыванию Audit Service](../docs/AUDIT_SERVICE_DEPLOYMENT.md)
- [Быстрый старт](../docs/QUICKSTART_DEPLOYMENT.md)
- [GitHub Actions CI/CD](../docs/GITHUB_ACTIONS.md)
- [Шпаргалка по командам](../docs/CHEATSHEET.md)
- [Главный README](../README.md)

