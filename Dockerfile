# syntax=docker/dockerfile:1

FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    FRONTEND_BUILD_DIR=frontend/dist

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY adapters/ ./adapters/
COPY config/ ./config/
COPY models/ ./models/
COPY routers/ ./routers/
COPY prompts/ ./prompts/
COPY schemas/ ./schemas/
COPY services/ ./services/
COPY workflows/ ./workflows/
COPY repositories/ ./repositories/
COPY observability/ ./observability/
COPY utils/ ./utils/
COPY web/ ./web/
COPY wsgi.py gunicorn.conf.py ./
COPY scripts/ ./scripts/

RUN pip install --no-cache-dir ".[prod]"

COPY --from=frontend-build /app/frontend/dist ./frontend/dist

COPY scripts/docker-entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
