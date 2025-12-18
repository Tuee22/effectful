# Dockerfile for Effectful Python library development
# Python 3.12 slim with Poetry for testing and development

FROM python:3.12-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONPYCACHEPREFIX=/opt/pycache \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/usr/local" \
    POETRY_NO_INTERACTION=1 \
    PATH="/usr/local/bin:$PATH" \
    MYPY_CACHE_DIR=/opt/mypy_cache \
    XDG_CACHE_HOME=/opt/cache \
    RUFF_CACHE_DIR=/opt/ruff_cache

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create cache directories under /opt to avoid bind-mounted source paths
RUN mkdir -p /opt/cache /opt/mypy_cache /opt/pytest_cache /opt/ruff_cache /opt/pycache

# Install Poetry via pip
RUN python3 -m pip install --upgrade pip setuptools wheel poetry \
    && poetry --version

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Copy application code
COPY . .

# Configure Poetry to not create virtualenvs (install to system Python)
RUN poetry config virtualenvs.create false

# Install runtime + tooling groups (no dev group)
RUN poetry install --with check,test

# Keep container running for interactive use
CMD ["sleep", "infinity"]
