# Быстрый старт: Развёртывание Audit Service

Краткое руководство по настройке CI/CD для audit-service в Яндекс.Облаке.

## 1. Подготовка Яндекс.Облака (10 минут)

```bash
# Установить Yandex Cloud CLI
curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash

# Инициализация
yc init

# Создать Container Registry
yc container registry create --name miar-registry
export YC_REGISTRY_ID=$(yc container registry list --format json | jq -r '.[0].id')

# Создать сервисный аккаунт
yc iam service-account create --name github-deployer
export YC_SERVICE_ACCOUNT_ID=$(yc iam service-account get github-deployer --format json | jq -r '.id')
export YC_FOLDER_ID=$(yc config get folder-id)

# Назначить роли
yc resource-manager folder add-access-binding $YC_FOLDER_ID \
  --role container-registry.images.pusher \
  --subject serviceAccount:$YC_SERVICE_ACCOUNT_ID

yc resource-manager folder add-access-binding $YC_FOLDER_ID \
  --role serverless.containers.admin \
  --subject serviceAccount:$YC_SERVICE_ACCOUNT_ID

# Создать ключ
yc iam key create \
  --service-account-name github-deployer \
  --output key.json \
  --format json
```

## 2. Настройка GitHub Secrets (5 минут)

Перейдите в `Settings` → `Secrets and variables` → `Actions` и добавьте:

```bash
# YC_SERVICE_ACCOUNT_KEY
cat key.json  # Скопируйте весь вывод

# YC_REGISTRY_ID
echo $YC_REGISTRY_ID

# YC_CLOUD_ID
yc config get cloud-id

# YC_FOLDER_ID
echo $YC_FOLDER_ID

# YC_SERVICE_ACCOUNT_ID
echo $YC_SERVICE_ACCOUNT_ID

# RABBITMQ_URL (замените на ваши данные)
# amqp://admin:password@your-rabbitmq-host:5672/
```

## 3. Проверка настройки (2 минуты)

```bash
# Проверить, что все переменные установлены
yc config list
yc container registry list
yc iam service-account list
```

## 4. Запуск развёртывания

### Автоматически через GitHub Actions

1. Сделайте изменение в `services/audit-service/`
2. Закоммитьте и запушьте в ветку `main`
3. Перейдите в `Actions` на GitHub и наблюдайте за процессом

### Вручную из локальной машины

```bash
# Загрузить переменные окружения
export YC_REGISTRY_ID="crp..."
export YC_FOLDER_ID="b1g..."
export YC_SERVICE_ACCOUNT_ID="aje..."
export RABBITMQ_URL="amqp://admin:password@host:5672/"

# Запустить развёртывание
./scripts/deploy_audit_service.sh
```

## 5. Проверка работы

```bash
# Получить URL контейнера
CONTAINER_URL=$(yc serverless container get audit-service-container --format json | jq -r '.url')

# Проверить health endpoint
curl ${CONTAINER_URL}/health

# Проверить audit endpoint
curl ${CONTAINER_URL}/audit/events
```

## Готово! 🎉

Ваш audit-service теперь развёрнут в Яндекс.Облаке и автоматически обновляется при каждом push в main.

## Дополнительные команды

```bash
# Просмотр логов
yc serverless container revision logs \
  --container-name audit-service-container \
  --follow

# Просмотр информации о контейнере
yc serverless container get audit-service-container

# Список ревизий
yc serverless container revision list \
  --container-name audit-service-container
```

## Следующие шаги

- Настройте мониторинг в Yandex Cloud Console
- Настройте алерты на ошибки
- Изучите [полную документацию](./AUDIT_SERVICE_DEPLOYMENT.md)

