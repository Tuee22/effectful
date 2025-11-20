# Multi-stage Dockerfile for Effectful Python library development
# Base: Python 3.12 slim with Poetry
# Services: Main library development + Mock client for integration tests

FROM python:3.12-slim as base

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Poetry configuration
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_VIRTUALENVS_CREATE=false \
    # Path
    PATH="/opt/poetry/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && poetry --version

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies (without dev dependencies for production stage)
RUN poetry install --no-root --only main

# Development stage with all dependencies
FROM base as development

# Install all dependencies including dev
RUN poetry install --no-root

# Copy application code
COPY . .

# Install the package in editable mode
RUN poetry install

# Create entrypoint scripts
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Starting Effectful main service..."\n\
exec poetry run python -m effectful.main "$@"' > /usr/local/bin/effectful-main \
    && chmod +x /usr/local/bin/effectful-main

RUN echo '#!/bin/bash\n\
set -e\n\
echo "Starting Effectful mock client service..."\n\
exec poetry run python -m effectful.testing.mock_client "$@"' > /usr/local/bin/effectful-mock-client \
    && chmod +x /usr/local/bin/effectful-mock-client

# Default entrypoint: main service
ENTRYPOINT ["effectful-main"]

# Production stage (minimal, no dev dependencies)
FROM base as production

# Copy application code
COPY . .

# Install only the package (no dev dependencies)
RUN poetry install --only main

# Create production entrypoint
RUN echo '#!/bin/bash\n\
set -e\n\
exec python -m effectful "$@"' > /usr/local/bin/effectful \
    && chmod +x /usr/local/bin/effectful

ENTRYPOINT ["effectful"]

# Default to development stage
FROM development as default
