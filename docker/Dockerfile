# Dockerfile for Effectful Python library development
# Ubuntu 24.04 LTS + system Python + Poetry

FROM ubuntu:24.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC

# Environment variables (SSoT - all variables defined here, nowhere else)
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PIP_IGNORE_INSTALLED=1 \
    PIP_ROOT_USER_ACTION=ignore \
    POETRY_NO_INTERACTION=1 \
    POETRY_HOME=/usr/local \
    PATH="/usr/local/bin:${PATH}" \
    PYTHONPATH="/app/src/python" \
    PYTHONPYCACHEPREFIX="/opt/pycache" \
    XDG_CACHE_HOME="/opt/effectful/cache" \
    MYPY_CACHE_DIR=/opt/effectful/mypy_cache \
    RUFF_CACHE_DIR=/opt/effectful/ruff_cache \
    PYTEST_CACHE_DIR=/opt/effectful/pytest_cache \
    DOCKER_CONTAINER=1 \
    JWT_REFRESH_TOKEN_TTL_SECONDS=3600 \
    JWT_REVOCATION_DEFAULT_TTL_SECONDS=86400 \
    PASSWORD_HASH_ITERATIONS=100000 \
    PULSAR_SEND_TIMEOUT_MS=5000

# Create cache directories under /opt/effectful/ namespace
RUN mkdir -p \
    /opt/effectful/cache \
    /opt/effectful/mypy_cache \
    /opt/effectful/pytest_cache \
    /opt/effectful/ruff_cache \
    /opt/pycache

WORKDIR /app

# Install system dependencies and Python
RUN apt-get update && apt-get install -y \
    python3 \
    python3-dev \
    python3-pip \
    python-is-python3 \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Poetry expects /bin/python; ensure it resolves to system Python.
RUN ln -sf /usr/bin/python3 /usr/bin/python && ln -sf /usr/bin/python3 /bin/python

# Install Poetry via pip
RUN python3 -m pip install --upgrade pip setuptools wheel poetry \
    && poetry --version

# Copy dependency files
COPY pyproject.toml ./

# Copy application code
COPY . .

# Configure Poetry to not create virtualenvs (install to system Python)
RUN poetry config virtualenvs.create false

# Install runtime + tooling groups (no dev group)
RUN poetry install --with check,test

# Install pytest wrapper for enforcement
# Move real pytest binary, then install wrapper
RUN if [ -f /usr/local/bin/pytest ]; then \
        mv /usr/local/bin/pytest /usr/local/bin/pytest.real; \
    fi

COPY docker/bin/pytest /usr/local/bin/pytest
RUN chmod +x /usr/local/bin/pytest

# Keep container running for interactive use
CMD ["sleep", "infinity"]
