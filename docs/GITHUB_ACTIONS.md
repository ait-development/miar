# GitHub Actions CI/CD

Документация по настройке и использованию GitHub Actions для автоматизации CI/CD процессов.

## Обзор

Проект использует GitHub Actions для автоматического тестирования и развёртывания сервисов в Яндекс.Облако.

## Workflows

### Audit Service CI/CD

**Файл:** `.github/workflows/audit-service-deploy.yml`

**Badge:** 
```markdown
[![Audit Service CI/CD](../../actions/workflows/audit-service-deploy.yml/badge.svg)](../../actions/workflows/audit-service-deploy.yml)
```

#### Триггеры

Workflow запускается автоматически при:

1. **Push в main** с изменениями в:
   - `services/audit-service/**`
   - `common/**`
   - `.github/workflows/audit-service-deploy.yml`

2. **Pull Request** в main с изменениями в тех же путях

3. **Ручной запуск** через GitHub UI:
   - Перейти в `Actions` → `Audit Service CI/CD`
   - Нажать `Run workflow`
   - Выбрать ветку
   - Нажать `Run workflow`

#### Джобы

##### 1. Test Job

Запускает тесты перед развёртыванием.

**Шаги:**
1. Checkout кода
2. Установка Python 3.11
3. Установка зависимостей
4. Запуск компонентных тестов для audit-service

**Условие выполнения:** Всегда

##### 2. Build and Deploy Job

Собирает Docker-образ и разворачивает в Yandex Cloud.

**Шаги:**
1. Checkout кода
2. Авторизация в Yandex Container Registry
3. Настройка Docker Buildx
4. Сборка и публикация Docker-образа
5. Установка Yandex Cloud CLI
6. Конфигурация Yandex Cloud CLI
7. Развёртывание в Serverless Containers
8. Получение URL контейнера
9. Health check

**Условие выполнения:** 
- После успешного завершения Test Job
- Только для push в main (не для PR)

**Используемые образы:**
- `cr.yandex/${{ REGISTRY_ID }}/audit-service:latest`
- `cr.yandex/${{ REGISTRY_ID }}/audit-service:${{ github.sha }}`

##### 3. Notify Job

Уведомляет о статусе развёртывания.

**Условие выполнения:** Всегда (даже при ошибках)

**Шаги:**
- ✅ Успешное развёртывание (exit code 0)
- ❌ Неудачное развёртывание (exit code 1)

#### Переменные окружения

```yaml
env:
  SERVICE_NAME: audit-service
  REGISTRY_ID: ${{ secrets.YC_REGISTRY_ID }}
  IMAGE_NAME: audit-service
  CONTAINER_NAME: audit-service-container
```

#### Используемые Actions

- `actions/checkout@v4` - Получение кода из репозитория
- `actions/setup-python@v5` - Установка Python
- `docker/login-action@v3` - Авторизация в Docker Registry
- `docker/setup-buildx-action@v3` - Настройка Docker Buildx
- `docker/build-push-action@v5` - Сборка и публикация образа

## Секреты GitHub

### Настройка секретов

1. Перейти в `Settings` → `Secrets and variables` → `Actions`
2. Нажать `New repository secret`
3. Добавить каждый из секретов ниже

### Список секретов

| Секрет | Описание | Как получить |
|--------|----------|--------------|
| `YC_SERVICE_ACCOUNT_KEY` | JSON-ключ сервисного аккаунта | `cat key.json` |
| `YC_REGISTRY_ID` | ID Container Registry | `yc container registry list` |
| `YC_CLOUD_ID` | ID облака Yandex Cloud | `yc config get cloud-id` |
| `YC_FOLDER_ID` | ID каталога Yandex Cloud | `yc config get folder-id` |
| `YC_SERVICE_ACCOUNT_ID` | ID сервисного аккаунта | `yc iam service-account get github-deployer --format json \| jq -r '.id'` |
| `RABBITMQ_URL` | URL подключения к RabbitMQ | `amqp://user:password@host:5672/` |

### Пример получения всех значений

```bash
#!/bin/bash

echo "=== GitHub Secrets Configuration ==="
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
yc iam service-account get github-deployer --format json | jq -r '.id'
echo ""

echo "YC_SERVICE_ACCOUNT_KEY:"
echo "(Содержимое файла key.json)"
cat key.json
echo ""

echo "RABBITMQ_URL:"
echo "amqp://username:password@your-rabbitmq-host:5672/"
echo ""
```

## Конфигурация Serverless Container

### Параметры развёртывания

```bash
yc serverless container revision deploy \
  --container-name audit-service-container \
  --image cr.yandex/${REGISTRY_ID}/audit-service:${GITHUB_SHA} \
  --cores 1 \                      # 1 vCPU
  --memory 512MB \                 # 512 MB RAM
  --execution-timeout 30s \        # Таймаут 30 секунд
  --service-account-id ${SA_ID} \  # Сервисный аккаунт
  --environment KEY=VALUE          # Переменные окружения
```

### Переменные окружения контейнера

```yaml
SERVICE_NAME: audit-service
SERVICE_ROLE: audit
SERVICE_PORT: 8000
SLEEP_SYMBOL: -
RABBITMQ_URL: ${{ secrets.RABBITMQ_URL }}
```

### Настройка масштабирования

Можно изменить в workflow:

```yaml
--cores 1 \              # 0.5, 1, 2
--memory 512MB \         # 128MB-4GB
--concurrency 4 \        # 1-16 запросов на инстанс
--min-instances 0 \      # 0-10 минимум инстансов
--max-instances 10 \     # 0-10 максимум инстансов
```

## Мониторинг workflow

### Просмотр логов

1. Перейти в `Actions` на GitHub
2. Выбрать workflow `Audit Service CI/CD`
3. Выбрать конкретный запуск
4. Кликнуть на джобу (Test / Build and Deploy / Notify)
5. Просмотреть логи каждого шага

### Статусы

- ✅ **Success** - Все шаги выполнены успешно
- ❌ **Failure** - Один или несколько шагов завершились с ошибкой
- ⏸️ **Cancelled** - Workflow был отменён
- 🔄 **In progress** - Workflow выполняется

### Артефакты

Workflow не создаёт артефактов, но Docker-образы сохраняются в Yandex Container Registry.

## Кэширование

### Docker layer cache

Используется GitHub Actions cache для ускорения сборки:

```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

**Преимущества:**
- Быстрая сборка при повторных запусках
- Экономия времени на установке зависимостей
- Уменьшение использования bandwidth

### Python dependencies cache

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'  # Кэширование pip зависимостей
```

## Оптимизация workflow

### Параллельное выполнение

Несколько workflow могут выполняться параллельно для разных сервисов.

### Условное выполнение

Deploy выполняется только:
- После успешных тестов
- Для push в main (не для PR)

```yaml
if: github.ref == 'refs/heads/main' && github.event_name == 'push'
```

### Тригеры на изменения в путях

Workflow запускается только при изменениях в релевантных файлах:

```yaml
paths:
  - 'services/audit-service/**'
  - 'common/**'
  - '.github/workflows/audit-service-deploy.yml'
```

## Безопасность

### Секреты

- ✅ Секреты не выводятся в логах
- ✅ Секреты недоступны в форках
- ✅ Секреты шифруются в GitHub

### Permissions

Workflow использует минимальные необходимые разрешения:

```yaml
permissions:
  contents: read    # Чтение кода
  packages: write   # Публикация в Container Registry
```

### Service Account

Сервисный аккаунт имеет только необходимые роли:
- `container-registry.images.pusher` - Публикация образов
- `serverless.containers.admin` - Управление контейнерами

## Откат изменений

### Через GitHub UI

1. Перейти в `Actions` → History
2. Найти последний успешный деплой
3. Нажать `Re-run all jobs`

### Через Yandex Cloud CLI

```bash
# Получить список ревизий
yc serverless container revision list \
  --container-name audit-service-container

# Откатить на предыдущую ревизию
yc serverless container revision set-traffic \
  --container-name audit-service-container \
  --revision-id <previous-revision-id> \
  --percent 100
```

## Добавление workflow для нового сервиса

### 1. Копировать существующий workflow

```bash
cp .github/workflows/audit-service-deploy.yml \
   .github/workflows/new-service-deploy.yml
```

### 2. Изменить переменные

```yaml
name: New Service CI/CD

env:
  SERVICE_NAME: new-service
  IMAGE_NAME: new-service
  CONTAINER_NAME: new-service-container

on:
  push:
    paths:
      - 'services/new-service/**'
      - 'common/**'
```

### 3. Обновить пути и команды

- Изменить пути к тестам
- Обновить Dockerfile path
- Изменить переменные окружения контейнера

### 4. Закоммитить и запушить

```bash
git add .github/workflows/new-service-deploy.yml
git commit -m "ci: add CI/CD for new-service"
git push origin main
```

## Уведомления

### Email уведомления

GitHub автоматически отправляет email при:
- Failure workflow (только автору коммита)
- Первом failure после успешных запусков

### Настройка дополнительных уведомлений

Можно добавить:
- Slack notifications
- Discord notifications
- Telegram notifications

Через GitHub Actions Marketplace.

## Troubleshooting

### Workflow не запускается

**Проблема:** Push в main не запускает workflow

**Решение:**
1. Проверить, что изменения в правильных путях
2. Проверить синтаксис YAML файла
3. Проверить права доступа в Settings → Actions

### Ошибка авторизации в Yandex Cloud

**Проблема:** "Error: Invalid service account key"

**Решение:**
1. Проверить секрет `YC_SERVICE_ACCOUNT_KEY`
2. Убедиться, что скопирован весь JSON целиком
3. Проверить срок действия ключа

### Docker build timeout

**Проблема:** "Error: Docker build exceeded timeout"

**Решение:**
1. Оптимизировать Dockerfile (multi-stage build)
2. Использовать .dockerignore
3. Увеличить timeout в workflow

### Deployment failed

**Проблема:** "Error: Failed to deploy container"

**Решение:**
1. Проверить логи workflow
2. Проверить права сервисного аккаунта
3. Проверить квоты в Yandex Cloud
4. Проверить логи контейнера

## Дополнительные ресурсы

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Yandex Cloud CLI](https://cloud.yandex.ru/docs/cli/)
- [Serverless Containers](https://cloud.yandex.ru/docs/serverless-containers/)
- [Docker Build Push Action](https://github.com/docker/build-push-action)

## Метрики и статистика

### Среднее время выполнения

- **Test Job**: ~2-3 минуты
- **Build and Deploy Job**: ~5-7 минут
- **Общее время**: ~7-10 минут

### Использование минут GitHub Actions

Примерное использование для audit-service:
- 1 деплой = ~10 минут
- 10 деплоев в месяц = ~100 минут
- Бесплатный лимит для public репозиториев: неограничено
- Бесплатный лимит для private репозиториев: 2000 минут/месяц

