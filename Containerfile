FROM python:3.11-slim as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.4.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/var/cache/pypoetry

WORKDIR /app
RUN pip install "poetry==$POETRY_VERSION"
COPY pyproject.toml poetry.lock /app/
RUN poetry config virtualenvs.in-project true
RUN poetry install --no-ansi

# ---
FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /app /app
ADD . /app
RUN groupadd -g 1001 application && \
    useradd -d /app -g 1001 -u 1001 application -M && \
    chown -R 1001:1001 /app
USER 1001
CMD /app/.venv/bin/python main.py