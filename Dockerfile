FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY . .
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

CMD ["/app/docker-entrypoint.sh"]
