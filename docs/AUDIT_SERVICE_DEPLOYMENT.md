# Развёртывание Audit Service в Яндекс.Облаке

Данное руководство описывает процесс настройки непрерывной интеграции и развёртывания (CI/CD) для `audit-service` в виде бессерверного контейнера в Яндекс.Облаке.

## Содержание

1. [Предварительные требования](#предварительные-требования)
2. [Настройка Яндекс.Облака](#настройка-яндексоблака)
3. [Настройка GitHub Secrets](#настройка-github-secrets)
4. [GitHub Actions Workflow](#github-actions-workflow)
5. [Локальное развёртывание](#локальное-развёртывание)
6. [Мониторинг и отладка](#мониторинг-и-отладка)

## Предварительные требования

- Аккаунт в [Яндекс.Облаке](https://cloud.yandex.ru/)
- Репозиторий проекта на GitHub
- Установленный [Yandex Cloud CLI](https://cloud.yandex.ru/docs/cli/quickstart)
- Docker для локальной разработки

## Настройка Яндекс.Облака

### 1. Создание Container Registry

Container Registry используется для хранения Docker-образов.

```bash
# Создать Container Registry
yc container registry create --name miar-registry

# Получить ID реестра
yc container registry list
```

Сохраните `ID` реестра - он понадобится для настройки GitHub Secrets.

### 2. Создание сервисного аккаунта

Сервисный аккаунт используется для автоматического развёртывания из GitHub Actions.

```bash
# Создать сервисный аккаунт
yc iam service-account create --name github-deployer \
  --description "Service account for GitHub Actions deployments"

# Получить ID сервисного аккаунта
SERVICE_ACCOUNT_ID=$(yc iam service-account get github-deployer --format json | jq -r '.id')

# Назначить необходимые роли
yc resource-manager folder add-access-binding <FOLDER_ID> \
  --role container-registry.images.pusher \
  --subject serviceAccount:$SERVICE_ACCOUNT_ID

yc resource-manager folder add-access-binding <FOLDER_ID> \
  --role serverless.containers.admin \
  --subject serviceAccount:$SERVICE_ACCOUNT_ID

# Создать авторизованный ключ для сервисного аккаунта
yc iam key create \
  --service-account-name github-deployer \
  --output key.json \
  --format json
```

Сохраните содержимое файла `key.json` - оно понадобится для GitHub Secrets.

### 3. Создание Serverless Container (опционально)

Контейнер будет создан автоматически при первом развёртывании, но можно создать его вручную:

```bash
yc serverless container create \
  --name audit-service-container \
  --description "Audit Service - Serverless Container"
```

### 4. Настройка RabbitMQ (если используется облачный инстанс)

Если вы используете RabbitMQ в облаке, убедитесь, что он доступен из Serverless Containers:

```bash
# Пример для Yandex Managed Service for RabbitMQ
yc managed-rabbitmq cluster create \
  --name miar-rabbitmq \
  --environment production \
  --network-name default \
  --user name=admin,password=<SECURE_PASSWORD> \
  --host zone-id=ru-central1-a
```

## Настройка GitHub Secrets

В настройках репозитория на GitHub (`Settings` → `Secrets and variables` → `Actions`) добавьте следующие секреты:

### Обязательные секреты

| Секрет | Описание | Пример получения |
|--------|----------|------------------|
| `YC_SERVICE_ACCOUNT_KEY` | JSON-ключ сервисного аккаунта | Содержимое файла `key.json` |
| `YC_REGISTRY_ID` | ID Container Registry | `yc container registry list` |
| `YC_CLOUD_ID` | ID облака | `yc config list` |
| `YC_FOLDER_ID` | ID каталога | `yc config list` |
| `YC_SERVICE_ACCOUNT_ID` | ID сервисного аккаунта | `yc iam service-account get github-deployer --format json \| jq -r '.id'` |
| `RABBITMQ_URL` | URL подключения к RabbitMQ | `amqp://user:password@host:5672/` |

### Получение значений для секретов

```bash
# Получить Cloud ID
yc config get cloud-id

# Получить Folder ID
yc config get folder-id

# Получить Registry ID
yc container registry list --format json | jq -r '.[0].id'

# Получить Service Account ID
yc iam service-account get github-deployer --format json | jq -r '.id'

# Содержимое key.json (весь файл целиком)
cat key.json
```

## GitHub Actions Workflow

Workflow автоматически запускается при:
- Push в ветку `main` с изменениями в `services/audit-service/`, `common/` или в самом workflow
- Pull Request с изменениями в указанных директориях
- Ручном запуске через GitHub UI (`Actions` → `Audit Service CI/CD` → `Run workflow`)

### Этапы workflow

1. **Test** - Запуск компонентных тестов для audit-service
2. **Build and Deploy** - Сборка Docker-образа и развёртывание в Yandex Cloud
3. **Notify** - Уведомление о статусе развёртывания

### Файл workflow

Workflow находится в `.github/workflows/audit-service-deploy.yml`.

## Локальное развёртывание

Для развёртывания из локальной машины используйте скрипт `scripts/deploy_audit_service.sh`.

### Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```bash
# .env
export YC_REGISTRY_ID="crp..."
export YC_FOLDER_ID="b1g..."
export YC_SERVICE_ACCOUNT_ID="aje..."
export RABBITMQ_URL="amqp://admin:password@rabbitmq.example.com:5672/"
```

Загрузите переменные:

```bash
source .env
```

### Авторизация в Yandex Cloud

```bash
# Авторизация через OAuth-токен
yc init

# Или через сервисный аккаунт
yc config profile create sa-profile
yc config set service-account-key key.json
yc config set cloud-id <CLOUD_ID>
yc config set folder-id <FOLDER_ID>
```

### Запуск развёртывания

```bash
# Развёртывание в production
./scripts/deploy_audit_service.sh production

# Или просто
./scripts/deploy_audit_service.sh
```

Скрипт выполнит следующие действия:
1. Проверит необходимые зависимости
2. Соберёт Docker-образ
3. Загрузит образ в Container Registry
4. Развернёт новую ревизию Serverless Container
5. Проверит работоспособность через health endpoint

## Мониторинг и отладка

### Просмотр логов

```bash
# Логи последней ревизии
yc serverless container revision logs \
  --container-name audit-service-container \
  --follow

# Логи конкретной ревизии
yc serverless container revision logs \
  --container-name audit-service-container \
  --revision-id <REVISION_ID>
```

### Получение информации о контейнере

```bash
# Информация о контейнере
yc serverless container get audit-service-container

# Список ревизий
yc serverless container revision list \
  --container-name audit-service-container

# URL контейнера
yc serverless container get audit-service-container \
  --format json | jq -r '.url'
```

### Тестирование endpoints

```bash
# Получить URL контейнера
CONTAINER_URL=$(yc serverless container get audit-service-container \
  --format json | jq -r '.url')

# Health check
curl ${CONTAINER_URL}/health

# Проверка количества событий аудита
curl ${CONTAINER_URL}/audit/events
```

### Мониторинг метрик

Метрики доступны в консоли Яндекс.Облака:
1. Перейдите в Serverless Containers
2. Выберите `audit-service-container`
3. Перейдите на вкладку "Мониторинг"

Доступные метрики:
- Количество запросов
- Время выполнения
- Ошибки
- Количество активных инстансов

### Откат на предыдущую версию

```bash
# Получить список ревизий
yc serverless container revision list \
  --container-name audit-service-container

# Установить процент трафика для конкретной ревизии
yc serverless container revision set-traffic \
  --container-name audit-service-container \
  --revision-id <OLD_REVISION_ID> \
  --percent 100
```

## Настройка автомасштабирования

Serverless Containers автоматически масштабируются, но можно настроить параметры:

```bash
yc serverless container revision deploy \
  --container-name audit-service-container \
  --image cr.yandex/${REGISTRY_ID}/audit-service:latest \
  --cores 1 \
  --memory 512MB \
  --execution-timeout 30s \
  --concurrency 4 \
  --min-instances 0 \
  --max-instances 10 \
  --service-account-id ${SERVICE_ACCOUNT_ID}
```

Параметры:
- `--cores` - количество vCPU (0.5, 1, 2)
- `--memory` - объём RAM (128MB-4GB)
- `--execution-timeout` - таймаут выполнения (1-600s)
- `--concurrency` - количество одновременных запросов на инстанс (1-16)
- `--min-instances` - минимальное количество инстансов (0-10)
- `--max-instances` - максимальное количество инстансов (0-10)

## Безопасность

### Рекомендации

1. **Используйте минимальные привилегии** для сервисного аккаунта
2. **Храните секреты в GitHub Secrets**, а не в коде
3. **Регулярно обновляйте зависимости** в `requirements.txt`
4. **Используйте HTTPS** для всех внешних подключений
5. **Настройте сетевую изоляцию** через VPC, если требуется

### Ротация ключей

```bash
# Создать новый ключ
yc iam key create \
  --service-account-name github-deployer \
  --output new-key.json

# Удалить старый ключ
yc iam key delete <OLD_KEY_ID>

# Обновить GitHub Secret YC_SERVICE_ACCOUNT_KEY
```

## Стоимость

Serverless Containers тарифицируются за:
- Количество запросов
- Время выполнения (GB×секунды)
- Исходящий трафик

Первые запросы и время выполнения в рамках [Free Tier](https://cloud.yandex.ru/docs/serverless-containers/pricing) бесплатны.

Примерная стоимость для audit-service с низкой нагрузкой: **~100-500 ₽/месяц**.

## Дополнительные ресурсы

- [Документация Serverless Containers](https://cloud.yandex.ru/docs/serverless-containers/)
- [Документация Container Registry](https://cloud.yandex.ru/docs/container-registry/)
- [Yandex Cloud CLI](https://cloud.yandex.ru/docs/cli/)
- [GitHub Actions для Yandex Cloud](https://github.com/yc-actions)

## Troubleshooting

### Проблема: Ошибка авторизации в Container Registry

**Решение:**
```bash
yc container registry configure-docker
docker login cr.yandex --username json_key --password "$(cat key.json)"
```

### Проблема: Контейнер не может подключиться к RabbitMQ

**Решение:**
1. Проверьте, что RABBITMQ_URL корректен
2. Убедитесь, что RabbitMQ доступен из интернета или настроена VPC
3. Проверьте логи контейнера

### Проблема: Health check падает

**Решение:**
1. Проверьте логи: `yc serverless container revision logs --container-name audit-service-container --follow`
2. Убедитесь, что порт 8000 правильно настроен
3. Проверьте переменные окружения

### Проблема: Deployment timeout

**Решение:**
1. Увеличьте `execution-timeout` в workflow
2. Оптимизируйте Dockerfile (используйте многостадийную сборку)
3. Проверьте размер образа

## Поддержка

При возникновении проблем:
1. Проверьте логи в Yandex Cloud Console
2. Посмотрите логи GitHub Actions
3. Изучите документацию Yandex Cloud
4. Создайте issue в репозитории проекта

