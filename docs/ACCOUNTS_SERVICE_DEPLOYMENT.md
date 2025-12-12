# Развертывание Accounts Service в Yandex Cloud Serverless Containers

Руководство по настройке и развертыванию accounts-service как бессерверного контейнера через GitHub Actions.

## Обзор

Accounts Service развертывается автоматически в Yandex Cloud Serverless Containers при изменениях в коде сервиса.

### Архитектура

- **Платформа**: Yandex Cloud Serverless Containers
- **Тип**: Бессерверный контейнер (serverless)
- **Язык**: Python 3.11
- **Фреймворк**: FastAPI
- **Хранилище образов**: Yandex Container Registry
- **CI/CD**: GitHub Actions

### Преимущества бессерверного подхода

- ✅ **Автоматическое масштабирование**: от 0 до N экземпляров
- ✅ **Оплата за использование**: платите только за время выполнения запросов
- ✅ **Нулевое управление инфраструктурой**: не нужно настраивать серверы
- ✅ **Высокая доступность**: автоматическое распределение нагрузки
- ✅ **Быстрое развертывание**: ~5-7 минут от коммита до продакшена

## Предварительные требования

### 1. Yandex Cloud аккаунт

Необходимые сервисы:
- **Container Registry** - для хранения Docker-образов
- **Serverless Containers** - для запуска сервиса
- **IAM** - для управления доступом

### 2. Сервисный аккаунт

Создайте сервисный аккаунт с необходимыми ролями:

```bash
# Создать сервисный аккаунт
yc iam service-account create --name github-deployer-accounts \
  --description "Service account for deploying accounts-service via GitHub Actions"

# Назначить роли
SA_ID=$(yc iam service-account get github-deployer-accounts --format json | jq -r '.id')

yc resource-manager folder add-access-binding <FOLDER_ID> \
  --role container-registry.images.pusher \
  --subject serviceAccount:$SA_ID

yc resource-manager folder add-access-binding <FOLDER_ID> \
  --role serverless.containers.admin \
  --subject serviceAccount:$SA_ID

# Создать ключ
yc iam key create \
  --service-account-name github-deployer-accounts \
  --output key.json \
  --description "Key for GitHub Actions"
```

### 3. Container Registry

```bash
# Создать реестр (если ещё не создан)
yc container registry create --name miar-registry

# Получить ID реестра
yc container registry list
```

### 4. RabbitMQ

Accounts Service требует подключения к RabbitMQ для обмена сообщениями.

Варианты:
- **Yandex Cloud Message Queue** (рекомендуется для продакшена)
- **CloudAMQP** (managed RabbitMQ)
- **Собственная установка** RabbitMQ

## Настройка GitHub Secrets

Перейдите в **Settings** → **Secrets and variables** → **Actions** и добавьте:

| Секрет | Описание | Пример |
|--------|----------|--------|
| `YC_SERVICE_ACCOUNT_KEY` | JSON-ключ сервисного аккаунта | Содержимое `key.json` |
| `YC_REGISTRY_ID` | ID Container Registry | `crp1234567890abcdef` |
| `YC_CLOUD_ID` | ID облака | `b1g1234567890abcdef` |
| `YC_FOLDER_ID` | ID каталога | `b1g0987654321fedcba` |
| `YC_SERVICE_ACCOUNT_ID` | ID сервисного аккаунта | `aje1234567890abcdef` |
| `RABBITMQ_URL` | URL RabbitMQ | `amqp://user:pass@host:5672/` |

### Получение значений

```bash
#!/bin/bash

echo "=== Accounts Service - GitHub Secrets ==="
echo ""

echo "YC_CLOUD_ID:"
yc config get cloud-id

echo ""
echo "YC_FOLDER_ID:"
yc config get folder-id

echo ""
echo "YC_REGISTRY_ID:"
yc container registry list --format json | jq -r '.[0].id'

echo ""
echo "YC_SERVICE_ACCOUNT_ID:"
yc iam service-account get github-deployer-accounts --format json | jq -r '.id'

echo ""
echo "YC_SERVICE_ACCOUNT_KEY:"
cat key.json
```

## Workflow Configuration

### Файл workflow

`.github/workflows/accounts-service-deploy.yml`

### Триггеры запуска

Workflow автоматически запускается при:

1. **Push в main** с изменениями в:
   - `services/accounts-service/**`
   - `common/**`
   - `.github/workflows/accounts-service-deploy.yml`

2. **Pull Request** в main с изменениями в тех же путях

3. **Ручной запуск** через GitHub UI:
   ```
   Actions → Accounts Service CI/CD → Run workflow
   ```

### Этапы выполнения

#### 1. Test Job (2-3 минуты)

- Проверка кода из репозитория
- Установка Python 3.11
- Установка зависимостей
- Запуск компонентных тестов

#### 2. Build and Deploy Job (5-7 минут)

- Авторизация в Yandex Container Registry
- Сборка Docker-образа (multi-stage build)
- Публикация образа с тегами `latest` и `<commit-sha>`
- Установка Yandex Cloud CLI
- Создание или обновление Serverless Container
- Health check развернутого сервиса

#### 3. Notify Job (несколько секунд)

- Уведомление о статусе развертывания

## Dockerfile

Используется multi-stage build для оптимизации размера образа:

### Stage 1: Builder
- Установка системных зависимостей (gcc)
- Установка Python пакетов

### Stage 2: Runtime
- Минимальный образ Python 3.11-slim
- Непривилегированный пользователь (appuser)
- Health check для мониторинга
- Оптимизированные переменные окружения

**Преимущества:**
- Маленький размер образа (~200 MB)
- Безопасность (non-root user)
- Быстрый запуск
- Встроенный health check

## API Endpoints

После развертывания сервис предоставляет следующие endpoints:

### Health Check
```bash
GET /health
```

Ответ:
```json
{
  "status": "healthy",
  "service": "accounts-service"
}
```

### Создание платежной инструкции
```bash
POST /accounts/{account_id}/payments
Content-Type: application/json

{
  "to_account": "ACC-002",
  "amount": 100.50,
  "currency": "RUB",
  "description": "Payment description"
}
```

Ответ:
```json
{
  "status": "queued",
  "instruction_id": "uuid-here"
}
```

## Конфигурация Serverless Container

### Параметры ресурсов

```yaml
Cores: 1 vCPU
Memory: 512 MB
Execution Timeout: 30 seconds
Service Account: github-deployer-accounts
```

### Переменные окружения

```yaml
SERVICE_NAME: accounts-service
SERVICE_ROLE: accounts
SERVICE_PORT: 8000
RABBITMQ_URL: <secret>
```

### Масштабирование (можно настроить)

```bash
# Пример настройки масштабирования
yc serverless container revision deploy \
  --container-name accounts-service-container \
  --image cr.yandex/${REGISTRY_ID}/accounts-service:latest \
  --cores 1 \
  --memory 512MB \
  --concurrency 4 \           # Запросов на инстанс
  --min-instances 0 \         # Минимум инстансов
  --max-instances 10 \        # Максимум инстансов
  --execution-timeout 30s
```

## Мониторинг и логи

### Просмотр логов через Yandex Cloud Console

1. Перейти в **Serverless Containers**
2. Выбрать `accounts-service-container`
3. Вкладка **Логи**

### Просмотр логов через CLI

```bash
# Логи последней ревизии
yc serverless container revision logs \
  --container-name accounts-service-container \
  --follow

# Логи за последний час
yc serverless container revision logs \
  --container-name accounts-service-container \
  --since 1h
```

### Метрики в GitHub Actions

- Время выполнения тестов
- Время сборки образа
- Время развертывания
- Результаты health check

## Тестирование развертывания

### 1. Получить URL контейнера

```bash
yc serverless container get accounts-service-container --format json | jq -r '.url'
```

### 2. Проверить health endpoint

```bash
CONTAINER_URL=$(yc serverless container get accounts-service-container --format json | jq -r '.url')
curl -v ${CONTAINER_URL}/health
```

### 3. Тестовый запрос

```bash
curl -X POST "${CONTAINER_URL}/accounts/ACC-001/payments" \
  -H "Content-Type: application/json" \
  -d '{
    "to_account": "ACC-002",
    "amount": 100.00,
    "currency": "RUB",
    "description": "Test payment"
  }'
```

Ожидаемый ответ:
```json
{
  "status": "queued",
  "instruction_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

## Troubleshooting

### Workflow не запускается

**Проблема**: Push в main не запускает workflow

**Решение**:
1. Проверьте, что изменения в правильных путях:
   - `services/accounts-service/**`
   - `common/**`
2. Проверьте синтаксис YAML: `yamllint .github/workflows/accounts-service-deploy.yml`
3. Проверьте Settings → Actions → General → Actions permissions

### Ошибка при сборке Docker образа

**Проблема**: "failed to solve: failed to compute cache key"

**Решение**:
1. Проверьте пути в Dockerfile
2. Убедитесь, что все файлы существуют
3. Проверьте `.dockerignore`

### Ошибка авторизации в Yandex Cloud

**Проблема**: "Error: Invalid service account key"

**Решение**:
1. Пересоздайте ключ: `yc iam key create --service-account-name github-deployer-accounts --output key.json`
2. Обновите секрет `YC_SERVICE_ACCOUNT_KEY` в GitHub
3. Проверьте, что JSON скопирован полностью

### Container не отвечает

**Проблема**: Health check возвращает ошибку

**Решение**:
1. Проверьте логи: `yc serverless container revision logs --container-name accounts-service-container`
2. Проверьте переменные окружения (особенно RABBITMQ_URL)
3. Проверьте, что порт 8000 указан корректно

### Таймаут при выполнении

**Проблема**: "Execution timeout exceeded"

**Решение**:
1. Увеличьте `--execution-timeout` в workflow
2. Оптимизируйте код сервиса
3. Проверьте подключение к RabbitMQ

## Стоимость

### Примерная стоимость для тестового использования

**Serverless Container**:
- Первые 1 млн запросов - бесплатно
- Далее: ~₽1.28 за 1 млн запросов
- Compute: ~₽1.44 за GB-час

**Container Registry**:
- Хранение: ~₽2.56 за GB в месяц
- Трафик: первые 10 GB бесплатно

**Примерный расчет** (для низкой нагрузки):
- 10,000 запросов/месяц
- Среднее время выполнения: 100ms
- Образ: 200 MB

**Итого**: ~₽50-100/месяц

## Откат версии

### Через GitHub Actions

1. Найти успешный деплой в Actions → History
2. Нажать "Re-run all jobs"

### Через Yandex Cloud CLI

```bash
# Посмотреть список ревизий
yc serverless container revision list \
  --container-name accounts-service-container

# Откатить на предыдущую ревизию
yc serverless container revision set-traffic \
  --container-name accounts-service-container \
  --revision-id <previous-revision-id> \
  --percent 100
```

## Best Practices

### Безопасность

- ✅ Используйте непривилегированного пользователя в Docker
- ✅ Не храните секреты в коде - используйте GitHub Secrets
- ✅ Регулярно обновляйте зависимости
- ✅ Используйте минимальный базовый образ

### Производительность

- ✅ Используйте multi-stage builds
- ✅ Кэшируйте слои Docker через GitHub Actions cache
- ✅ Минимизируйте размер образа
- ✅ Оптимизируйте время холодного старта

### Мониторинг

- ✅ Настройте алерты в Yandex Cloud Monitoring
- ✅ Отслеживайте метрики использования
- ✅ Регулярно проверяйте логи
- ✅ Используйте structured logging

## Дополнительные ресурсы

- [Yandex Cloud Serverless Containers](https://cloud.yandex.ru/docs/serverless-containers/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

## Поддержка

При возникновении проблем:
1. Проверьте логи в GitHub Actions
2. Проверьте логи в Yandex Cloud Console
3. Изучите раздел Troubleshooting
4. Создайте issue в репозитории проекта

