# Changelog

Все значимые изменения в проекте будут документироваться в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
и этот проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Added

- Настроена CI/CD для audit-service через GitHub Actions
- Добавлен production Dockerfile для audit-service с multi-stage build
- Создан скрипт автоматического развёртывания `scripts/deploy_audit_service.sh`
- Добавлена полная документация по развёртыванию в Яндекс.Облако
- Создано руководство быстрого старта для деплоя
- Добавлена шпаргалка с полезными командами
- Настроен автоматический деплой в Yandex Cloud Serverless Containers
- Добавлен health check в production Dockerfile
- Создан пример файла переменных окружения `env.example`
- Добавлен .gitignore для исключения конфиденциальных данных

### Changed

- Обновлён README.md с описанием архитектуры и CI/CD процессов
- Улучшена структура документации проекта

### Security

- Docker-образы теперь собираются с непривилегированным пользователем
- Добавлена защита от случайной публикации секретов через .gitignore

## [0.1.0] - 2024-12-12

### Added

- Начальная версия проекта с микросервисной архитектурой
- 8 микросервисов: auth, customers, accounts, payments, cards, loans, notifications, audit
- Интеграция с RabbitMQ для асинхронной коммуникации
- Компонентные и интеграционные тесты
- Docker Compose для локальной разработки
- Базовая структура проекта

### Features

- **Audit Service**: Сервис для сбора событий аудита
  - Подписка на сервисные события
  - Подписка на топик воркеры
  - API для получения статистики событий
  - Ограничение хранилища (200 событий)

- **RabbitMQ Integration**:
  - Service Events (Direct Exchange)
  - Topic Workloads (Topic Exchange)
  - Автоматическое переподключение

- **Testing**:
  - Компонентные тесты для accounts-service
  - Компонентные тесты для audit-service
  - Интеграционные тесты топологии RabbitMQ

[Unreleased]: https://github.com/username/miar/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/username/miar/releases/tag/v0.1.0

