# Сервис опросов и голосования

## стек

- python
- fastapi
- pydantic
- uvicorn
- postgresql
- alembic
- sqlalchemy
- pytest

## структура проекта

```text
app/
  api/        # роуты fastapi
  core/       # настройки и обработка ошибок
  db/         # подключение к бд и базовый класс моделей
  models/     # sqlalchemy-модели
  schemas/    # pydantic-схемы
  services/   # бизнес-логика
alembic/      # миграции
tests/        # pytest-тесты
```

## api

### 1. создать опрос

`post /api/v1/polls`

пример тела запроса:

```json
{
  "question": "какой язык выбрать для первого pet-проекта?",
  "options": ["python", "go", "java"],
  "close_after_seconds": 60
}
```

пояснения:
- `question` — непустой вопрос
- `options` — от 2 до 5 непустых вариантов
- `close_after_seconds` — необязательный таймер автозакрытия в секундах

### 2. получить список опросов

`get /api/v1/polls`

### 3. проголосовать

`post /api/v1/polls/{poll_id}/votes`

пример тела запроса:

```json
{
  "voter_id": "user-42",
  "option_id": 1
}
```

### 4. получить результаты

`get /api/v1/polls/{poll_id}/results`

### 5. закрыть опрос

`post /api/v1/polls/{poll_id}/close`

повторное закрытие возвращает `409 conflict` с кодом ошибки `poll_already_closed`

## error contract

все ошибки возвращаются в одном формате:

```json
{
  "error": {
    "code": "duplicate_vote",
    "message": "один участник не может голосовать дважды в одном опросе",
    "details": {
      "poll_id": 1,
      "voter_id": "user-42"
    }
  }
}
```

примеры кодов ошибок:
- `validation_error` — ошибка входной валидации
- `poll_not_found` — опрос не найден
- `option_not_found` — вариант не найден в рамках опроса
- `duplicate_vote` — повторное голосование
- `poll_closed` — попытка проголосовать в закрытый опрос
- `poll_already_closed` — повторное закрытие

## быстрый запуск

### вариант 1. через makefile

```bash
make install
make db-up
make migrate
make run
```

проверка сервиса:

```bash
curl http://localhost:8000/docs
```

остановка postgresql:

```bash
make db-down
```

### вариант 2. в docker

```bash
make docker-build
make docker-up
make docker-migrate
```

проверка сервиса:

```bash
curl http://localhost:8000/api/v1/polls
```

остановка контейнеров:

```bash
make docker-down
```

## команды для проверки

запуск тестов:

```bash
make test
```

или напрямую:

```bash
PYTHONPATH=. pytest -q
```

откат последней миграции:

```bash
make migrate-down
```

логи postgresql:

```bash
make db-logs
```

сборка и запуск в docker:

```bash
make docker-build
make docker-up
make docker-migrate
```

логи контейнеров:

```bash
make docker-logs
```

## примеры запросов для ручной проверки

### создание опроса

```bash
curl -X POST http://localhost:8000/api/v1/polls \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "какой фреймворк выбрать?",
    "options": ["fastapi", "django", "flask"],
    "close_after_seconds": 120
  }'
```

### получение списка опросов

```bash
curl http://localhost:8000/api/v1/polls
```

### голосование

```bash
curl -X POST http://localhost:8000/api/v1/polls/1/votes \
  -H 'Content-Type: application/json' \
  -d '{
    "voter_id": "user-1",
    "option_id": 1
  }'
```

### получение результатов

```bash
curl http://localhost:8000/api/v1/polls/1/results
```

### закрытие опроса

```bash
curl -X POST http://localhost:8000/api/v1/polls/1/close
```

## сценарии ручной проверки

1. создать опрос с валидным вопросом и 2-5 вариантами и убедиться, что статус `open`
2. попробовать создать опрос с пустым вопросом и убедиться, что приходит `422` и `validation_error`
3. попробовать создать опрос с одним вариантом ответа и убедиться, что приходит `422`
4. проголосовать за существующий вариант и проверить, что в результатах увеличился `total_votes` и счетчик нужного варианта
5. проголосовать повторно тем же `voter_id` в том же опросе и убедиться, что приходит `409` и `duplicate_vote`
6. закрыть опрос и попробовать проголосовать после закрытия и убедиться, что приходит `409` и `poll_closed`
7. создать опрос с `close_after_seconds=1`, подождать 1-2 секунды и попробовать проголосовать и убедиться, что опрос закрылся автоматически

## как определяется повторное голосование и почему

повторное голосование определяется по паре `(poll_id, voter_id)`

это значит:
- один и тот же участник может голосовать в разных опросах
- один и тот же участник не может отправить второй голос в тот же самый опрос
- правило закреплено не только в коде сервиса, но и в базе данных через уникальное ограничение `uq_votes_poll_voter`

почему так:
- клиент сам передает, кто голосует
- настоящей авторизации нет, значит самым простым и прозрачным идентификатором становится `voter_id`
- уникальное ограничение в бд защищает от гонок и от двойной записи даже при параллельных запросах
