# Шпаргалка по командам

## Yandex Cloud CLI

### Базовые команды

```bash
# Инициализация и авторизация
yc init

# Просмотр конфигурации
yc config list

# Переключение профиля
yc config profile list
yc config profile activate <profile-name>
```

### Container Registry

```bash
# Создать реестр
yc container registry create --name <registry-name>

# Список реестров
yc container registry list

# Получить ID реестра
yc container registry list --format json | jq -r '.[0].id'

# Настроить Docker для работы с реестром
yc container registry configure-docker

# Авторизация Docker
docker login cr.yandex --username json_key --password "$(cat key.json)"
```

### Сервисные аккаунты

```bash
# Создать сервисный аккаунт
yc iam service-account create --name <sa-name>

# Список сервисных аккаунтов
yc iam service-account list

# Получить ID
yc iam service-account get <sa-name> --format json | jq -r '.id'

# Назначить роль
yc resource-manager folder add-access-binding <folder-id> \
  --role <role-name> \
  --subject serviceAccount:<sa-id>

# Создать ключ
yc iam key create \
  --service-account-name <sa-name> \
  --output key.json \
  --format json
```

### Serverless Containers

```bash
# Создать контейнер
yc serverless container create --name <container-name>

# Список контейнеров
yc serverless container list

# Информация о контейнере
yc serverless container get <container-name>

# Получить URL
yc serverless container get <container-name> --format json | jq -r '.url'

# Деплой ревизии
yc serverless container revision deploy \
  --container-name <container-name> \
  --image cr.yandex/<registry-id>/<image-name>:tag \
  --cores 1 \
  --memory 512MB \
  --execution-timeout 30s \
  --service-account-id <sa-id> \
  --environment KEY=VALUE

# Список ревизий
yc serverless container revision list --container-name <container-name>

# Логи
yc serverless container revision logs \
  --container-name <container-name> \
  --follow

# Логи конкретной ревизии
yc serverless container revision logs --revision-id <revision-id>

# Удалить контейнер
yc serverless container delete <container-name>
```

## Docker

### Сборка и публикация

```bash
# Собрать образ
docker build -f services/audit-service/Dockerfile -t audit-service .

# Тегировать для Yandex Container Registry
docker tag audit-service cr.yandex/<registry-id>/audit-service:latest

# Загрузить в реестр
docker push cr.yandex/<registry-id>/audit-service:latest

# Запустить локально
docker run -p 8000:8000 \
  -e SERVICE_NAME=audit-service \
  -e SERVICE_ROLE=audit \
  -e RABBITMQ_URL=amqp://admin:admin@host.docker.internal:5672/ \
  audit-service
```

## Docker Compose

```bash
# Запустить все сервисы
docker-compose up -d

# Запустить конкретный сервис
docker-compose up -d audit-service

# Остановить все
docker-compose down

# Пересобрать и запустить
docker-compose up -d --build

# Логи
docker-compose logs -f audit-service

# Статус
docker-compose ps
```

## Тестирование

```bash
# Все тесты
pytest -v

# Конкретный сервис
pytest tests/component/test_audit_service.py -v

# С покрытием
pytest tests/component/test_audit_service.py --cov=services/audit-service

# Определенный тест
pytest tests/component/test_audit_service.py::test_audit_service_health_check -v

# С выводом print
pytest -v -s

# Остановиться на первой ошибке
pytest -x
```

## Развёртывание Audit Service

```bash
# Настроить переменные (скопируйте env.example в .env и заполните)
source .env

# Локальное развёртывание
./scripts/deploy_audit_service.sh

# Проверить deployment
CONTAINER_URL=$(yc serverless container get audit-service-container --format json | jq -r '.url')
curl ${CONTAINER_URL}/health
curl ${CONTAINER_URL}/audit/events
```

## Git & GitHub Actions

```bash
# Триггер workflow через push
git add .
git commit -m "Update audit-service"
git push origin main

# Просмотр статуса GitHub Actions
# Перейти на https://github.com/<username>/<repo>/actions
```

## RabbitMQ

```bash
# Management UI
# http://localhost:15672
# Login: admin / admin

# Проверить очереди через API
curl -u admin:admin http://localhost:15672/api/queues

# Проверить обмены
curl -u admin:admin http://localhost:15672/api/exchanges
```

## Полезные комбинации

### Полный цикл разработки и деплоя

```bash
# 1. Внести изменения в код
vim services/audit-service/app/main.py

# 2. Запустить тесты локально
pytest tests/component/test_audit_service.py -v

# 3. Закоммитить и запушить
git add services/audit-service/
git commit -m "feat: update audit service logic"
git push origin main

# 4. Наблюдать за GitHub Actions
# https://github.com/<username>/<repo>/actions

# 5. Проверить deployment
CONTAINER_URL=$(yc serverless container get audit-service-container --format json | jq -r '.url')
curl ${CONTAINER_URL}/health
```

### Быстрая отладка

```bash
# 1. Логи контейнера
yc serverless container revision logs \
  --container-name audit-service-container \
  --follow

# 2. Информация о текущей ревизии
yc serverless container revision list \
  --container-name audit-service-container \
  --limit 1

# 3. Проверить образ в реестре
yc container image list --registry-id <registry-id>

# 4. Ручной тест endpoint
curl -v ${CONTAINER_URL}/health
curl -v ${CONTAINER_URL}/audit/events
```

### Откат на предыдущую версию

```bash
# 1. Получить список ревизий
yc serverless container revision list --container-name audit-service-container

# 2. Переключить трафик на предыдущую ревизию
yc serverless container revision set-traffic \
  --container-name audit-service-container \
  --revision-id <previous-revision-id> \
  --percent 100
```

## Переменные окружения

### Для локальной разработки

```bash
export SERVICE_NAME=audit-service
export SERVICE_ROLE=audit
export SERVICE_PORT=8000
export SLEEP_SYMBOL=-
export RABBITMQ_URL=amqp://admin:admin@localhost:5672/
```

### Для Yandex Cloud

```bash
export YC_REGISTRY_ID=$(yc container registry list --format json | jq -r '.[0].id')
export YC_FOLDER_ID=$(yc config get folder-id)
export YC_CLOUD_ID=$(yc config get cloud-id)
export YC_SERVICE_ACCOUNT_ID=$(yc iam service-account get github-deployer --format json | jq -r '.id')
export RABBITMQ_URL=amqp://user:pass@host:5672/
```

## Мониторинг

```bash
# CPU и Memory метрики
yc serverless container revision get <revision-id> --format json | jq '.resources'

# Количество инстансов
yc monitoring metric-data read \
  --folder-id <folder-id> \
  --service serverless-containers \
  --name container.instances

# История деплоев
yc serverless container revision list --container-name audit-service-container
```

## Очистка ресурсов

```bash
# Удалить контейнер
yc serverless container delete audit-service-container

# Удалить образы
yc container image list --registry-id <registry-id>
yc container image delete <image-id>

# Удалить реестр
yc container registry delete <registry-id>

# Удалить сервисный аккаунт
yc iam service-account delete <sa-id>
```

