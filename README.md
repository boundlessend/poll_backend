# сервис опросов и голосования

## стек

- python
- fastapi
- pydantic
- uvicorn
- postgresql
- alembic
- sqlalchemy
- pytest

## что реализовано

- создание опроса с 2-5 вариантами ответа
- список опросов
- голосование за один вариант
- результаты с количеством голосов по каждому варианту
- ручное закрытие опроса
- автоматическое закрытие по таймеру
- единый error contract
- простая обязательная авторизация для голосования через заголовок `X-User-Id`
- uuid для основных сущностей
- отдельный `option_id` внутри опроса
- все даты и время в ответах по москве

## структура проекта

```text
app/
  api/        # роуты fastapi
  core/       # настройки, время, авторизация и обработка ошибок
  db/         # подключение к бд и базовый класс моделей
  models/     # sqlalchemy-модели
  schemas/    # pydantic-схемы
  services/   # бизнес-логика
alembic/      # миграции
tests/        # pytest-тесты
```

## api

### создать опрос

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

### получить список опросов

`get /api/v1/polls`

### проголосовать

`post /api/v1/polls/{poll_id}/votes`

для голосования нужен обязательный заголовок `X-User-Id`

пример тела запроса:

```json
{
  "option_id": 1
}
```

пример заголовка:

```text
X-User-Id: user-42
```

`poll_id` — uuid опроса

`option_id` — номер варианта внутри конкретного опроса

### получить результаты

`get /api/v1/polls/{poll_id}/results`

### закрыть опрос

`post /api/v1/polls/{poll_id}/close`

повторное закрытие возвращает `409 conflict` с кодом ошибки `poll_already_closed`

## error contract

все ошибки возвращаются в одном формате:

```json
{
  "error": {
    "code": "duplicate_vote",
    "message": "один пользователь не может голосовать дважды в одном опросе",
    "details": {
      "poll_id": "426f2d84-5b97-45bd-8b8e-b16e279e32bf",
      "user_id": "user-42"
    }
  }
}
```

логика http-статусов:
- `401` — не передан обязательный `X-User-Id` или он пустой
- `404` — опрос или вариант ответа не найден
- `409` — состояние конфликтует с правилом бизнеса
- `422` — входные данные не прошли валидацию

примеры кодов ошибок:
- `validation_error` — ошибка входной валидации
- `authentication_required` — не передан `X-User-Id`
- `poll_not_found` — опрос не найден
- `option_not_found` — вариант не найден в рамках опроса
- `duplicate_vote` — повторное голосование
- `poll_closed` — попытка проголосовать в закрытый опрос
- `poll_already_closed` — повторное закрытие

## быстрый запуск

### вариант 1 через makefile

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

### вариант 2 через docker

```bash
make docker-build
make docker-up
```

при старте контейнера приложение само дожидается postgresql, накатывает alembic-миграции и только после этого запускает api

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
make db-up
make test
```

тесты используют реальный postgresql и поднимают схему только через alembic-миграции

если postgresql доступен не на `localhost:5432`, можно передать `TEST_DATABASE_ADMIN_URL`:

```bash
export TEST_DATABASE_ADMIN_URL=postgresql+psycopg://postgres:postgres@localhost:5432/postgres
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
curl -X POST http://localhost:8000/api/v1/polls/<poll_uuid>/votes \
  -H 'Content-Type: application/json' \
  -H 'X-User-Id: user-1' \
  -d '{
    "option_id": 1
  }'
```

### получение результатов

```bash
curl http://localhost:8000/api/v1/polls/<poll_uuid>/results
```

### закрытие опроса

```bash
curl -X POST http://localhost:8000/api/v1/polls/<poll_uuid>/close
```

## сценарии ручной проверки

1. создать опрос с валидным вопросом и 2-5 вариантами и убедиться, что `id` выглядит как uuid, а варианты имеют `option_id` 1, 2, 3 и так далее
2. попробовать создать опрос с пустым вопросом и убедиться, что приходит `422` и `validation_error`
3. попробовать создать опрос с одним вариантом ответа и убедиться, что приходит `422`
4. попробовать проголосовать без `X-User-Id` и убедиться, что приходит `401` и `authentication_required`
5. проголосовать за существующий вариант и проверить, что в результатах увеличился `total_votes` и счетчик нужного варианта
6. проголосовать повторно тем же `X-User-Id` в том же опросе и убедиться, что приходит `409` и `duplicate_vote`
7. закрыть опрос и попробовать проголосовать после закрытия и убедиться, что приходит `409` и `poll_closed`

## как определяется повторное голосование и почему

повторное голосование определяется по паре `(poll_id, user_id)`

почему так:
- `poll_id` как uuid делает внешний идентификатор опроса стабильным и не завязанным на простой инкремент
- `user_id` берется из обязательного заголовка `X-User-Id`
- уникальное ограничение в базе дополнительно защищает от двойной записи при параллельных запросах

## как устроен `option_id`

в таблице `poll_options` есть внутренний uuid `id` и отдельный числовой `option_id`

это сделано затем, чтобы:
- внешний контракт оставался простым
- вариант ответа был понятен клиенту как `1`, `2`, `3`
- `option_id` считался только внутри конкретного опроса, а не глобально по всей таблице
