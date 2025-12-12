# Настройка GitHub Secrets для CI/CD

Быстрое руководство по настройке секретов для автоматического развертывания сервисов через GitHub Actions.

## Краткая инструкция

### 1. Получите все необходимые значения

Запустите скрипт-помощник:

```bash
./scripts/get_github_secrets.sh
```

Скрипт покажет все значения, которые нужно добавить в GitHub Secrets.

### 2. Добавьте секреты в GitHub

1. Откройте ваш репозиторий на GitHub
2. Перейдите в **Settings** → **Secrets and variables** → **Actions**
3. Нажмите **New repository secret**
4. Добавьте каждый секрет из списка ниже

## Список секретов

| Имя секрета | Описание | Пример |
|-------------|----------|--------|
| `YC_SERVICE_ACCOUNT_KEY` | **Полный JSON** ключа сервисного аккаунта | См. ниже |
| `YC_REGISTRY_ID` | ID Container Registry | `crp9h6abc123def456` |
| `YC_CLOUD_ID` | ID облака Yandex Cloud | `b1g9h6abc123def456` |
| `YC_FOLDER_ID` | ID каталога Yandex Cloud | `b1g9h6xyz987uvw654` |
| `YC_SERVICE_ACCOUNT_ID` | ID сервисного аккаунта | `aje9h6abc123def456` |
| `RABBITMQ_URL` | URL подключения к RabbitMQ | `amqp://user:pass@host:5672/` |

## Подробные инструкции

### YC_SERVICE_ACCOUNT_KEY

**ВАЖНО**: Это должен быть полный JSON-файл, включающий как публичный, так и приватный ключ.

#### Шаг 1: Создайте сервисный аккаунт

```bash
yc iam service-account create \
  --name github-deployer \
  --description "Service account for GitHub Actions CI/CD"
```

#### Шаг 2: Назначьте необходимые роли

```bash
# Получить ID сервисного аккаунта
SA_ID=$(yc iam service-account get github-deployer --format json | jq -r '.id')

# Получить ID каталога
FOLDER_ID=$(yc config get folder-id)

# Назначить роль для работы с Container Registry
yc resource-manager folder add-access-binding $FOLDER_ID \
  --role container-registry.images.pusher \
  --subject serviceAccount:$SA_ID

# Назначить роль для управления Serverless Containers
yc resource-manager folder add-access-binding $FOLDER_ID \
  --role serverless.containers.admin \
  --subject serviceAccount:$SA_ID
```

#### Шаг 3: Создайте JSON ключ

```bash
yc iam key create \
  --service-account-name github-deployer \
  --output key.json \
  --description "Key for GitHub Actions"
```

#### Шаг 4: Скопируйте содержимое

```bash
cat key.json
```

**Правильный формат ключа:**

```json
{
   "id": "aje...",
   "service_account_id": "aje...",
   "created_at": "2024-01-01T00:00:00Z",
   "key_algorithm": "RSA_2048",
   "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n",
   "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
}
```

**Скопируйте ВЕСЬ JSON** (включая фигурные скобки) в GitHub Secret `YC_SERVICE_ACCOUNT_KEY`.

⚠️ **Частые ошибки:**
- ❌ Копирование только публичного ключа (BEGIN PUBLIC KEY)
- ❌ Копирование только приватного ключа (BEGIN PRIVATE KEY)
- ✅ Копирование всего JSON целиком

### YC_REGISTRY_ID

ID вашего Container Registry для хранения Docker-образов.

```bash
# Получить ID существующего реестра
yc container registry list --format json | jq -r '.[0].id'

# Или создать новый
yc container registry create --name miar-registry
```

### YC_CLOUD_ID

```bash
yc config get cloud-id
```

### YC_FOLDER_ID

```bash
yc config get folder-id
```

### YC_SERVICE_ACCOUNT_ID

```bash
yc iam service-account get github-deployer --format json | jq -r '.id'
```

### RABBITMQ_URL

URL для подключения к RabbitMQ в формате AMQP.

**Формат:**
```
amqp://username:password@hostname:5672/vhost
```

**Примеры:**

1. **CloudAMQP** (рекомендуется для продакшена):
   ```
   amqp://username:password@hawk.cloudamqp.com/vhost
   ```
   Зарегистрируйтесь на https://www.cloudamqp.com/ (есть бесплатный план)

2. **Yandex Message Queue**:
   ```
   amqp://username:password@message-queue.yandexcloud.net:5672/
   ```

3. **Локальный RabbitMQ** (только для тестирования):
   ```
   amqp://admin:admin@localhost:5672/
   ```

## Проверка настройки

### 1. Проверьте, что все секреты добавлены

В GitHub: **Settings** → **Secrets and variables** → **Actions**

Должны быть видны 6 секретов:
- ✅ YC_SERVICE_ACCOUNT_KEY
- ✅ YC_REGISTRY_ID
- ✅ YC_CLOUD_ID
- ✅ YC_FOLDER_ID
- ✅ YC_SERVICE_ACCOUNT_ID
- ✅ RABBITMQ_URL

### 2. Проверьте права сервисного аккаунта

```bash
SA_ID=$(yc iam service-account get github-deployer --format json | jq -r '.id')

# Должны быть две роли
yc resource-manager folder list-access-bindings $(yc config get folder-id) \
  --format json | jq ".[] | select(.subject.id==\"$SA_ID\")"
```

Ожидаемый вывод должен включать:
- `container-registry.images.pusher`
- `serverless.containers.admin`

### 3. Протестируйте workflow

Сделайте небольшое изменение в коде сервиса:

```bash
# Добавьте комментарий в файл
echo "# Test deployment" >> services/accounts-service/app/main.py

# Закоммитьте и запушьте
git add services/accounts-service/app/main.py
git commit -m "test: trigger accounts-service deployment"
git push origin main
```

Workflow должен запуститься автоматически. Проверьте статус в:
**Actions** → **Accounts Service CI/CD**

## Troubleshooting

### "Error: Password required"

**Проблема**: Неправильный формат ключа в `YC_SERVICE_ACCOUNT_KEY`

**Решение**: 
1. Убедитесь, что скопировали ВЕСЬ JSON из `key.json`
2. JSON должен содержать и `public_key`, и `private_key`
3. Пересоздайте ключ, если потеряли `key.json`

### "Error: Unauthorized"

**Проблема**: Неверный ключ или истек срок действия

**Решение**:
1. Создайте новый ключ: `yc iam key create --service-account-name github-deployer --output key.json`
2. Обновите секрет `YC_SERVICE_ACCOUNT_KEY` в GitHub

### "Error: Permission denied"

**Проблема**: У сервисного аккаунта недостаточно прав

**Решение**:
```bash
SA_ID=$(yc iam service-account get github-deployer --format json | jq -r '.id')
FOLDER_ID=$(yc config get folder-id)

# Добавить недостающие роли
yc resource-manager folder add-access-binding $FOLDER_ID \
  --role container-registry.images.pusher \
  --subject serviceAccount:$SA_ID

yc resource-manager folder add-access-binding $FOLDER_ID \
  --role serverless.containers.admin \
  --subject serviceAccount:$SA_ID
```

### "Error: Registry not found"

**Проблема**: Неверный `YC_REGISTRY_ID`

**Решение**:
```bash
# Показать все реестры
yc container registry list

# Обновить секрет с правильным ID
```

## Безопасность

### ✅ Хорошие практики

- Используйте отдельный сервисный аккаунт для CI/CD
- Назначайте минимальные необходимые роли
- Регулярно ротируйте ключи (каждые 90 дней)
- Никогда не коммитьте `key.json` в Git
- Используйте GitHub Secrets, а не переменные окружения

### ❌ Чего НЕ делать

- Не храните ключи в коде
- Не используйте персональные аккаунты для CI/CD
- Не давайте излишние права (например, `admin`)
- Не публикуйте ключи в логах или Issues

### Ротация ключей

Рекомендуется менять ключи каждые 3 месяца:

```bash
# 1. Создать новый ключ
yc iam key create \
  --service-account-name github-deployer \
  --output key-new.json

# 2. Обновить GitHub Secret

# 3. Протестировать deployment

# 4. Удалить старый ключ
yc iam key delete <OLD_KEY_ID>

# 5. Удалить локальные файлы
rm key-new.json
```

## Дополнительные ресурсы

- [Документация Yandex Cloud IAM](https://cloud.yandex.ru/docs/iam/)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Yandex Container Registry](https://cloud.yandex.ru/docs/container-registry/)
- [Serverless Containers](https://cloud.yandex.ru/docs/serverless-containers/)

## Быстрые команды

```bash
# Получить все значения для секретов
./scripts/get_github_secrets.sh

# Проверить существующие роли
yc resource-manager folder list-access-bindings $(yc config get folder-id)

# Проверить ключи сервисного аккаунта
yc iam key list --service-account-name github-deployer

# Удалить старый ключ
yc iam key delete <KEY_ID>

# Проверить реестры
yc container registry list

# Проверить контейнеры
yc serverless container list
```

