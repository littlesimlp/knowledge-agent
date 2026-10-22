FROM python:3.12-slim

# Use uv inside the container, same tool as local dev
RUN pip install --no-cache-dir uv

# Flush print()/logs immediately instead of buffering
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy only dependency manifests first: this layer stays cached
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy code after deps: editing code only rebuilds the layers below
COPY app ./app

# lembic upgrade head
COPY alembic.ini ./
COPY alembic ./alembic

# Make uvicorn available inside the container
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Must bind 0.0.0.0, otherwise the published port cannot reach the process
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]