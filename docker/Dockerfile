# Dockerfile for Effectful Python library development
# Ubuntu 22.04 LTS + Python 3.12 + Poetry

FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC

# Environment variables (SSoT - all variables defined here, nowhere else)
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_HOME=/usr/local \
    PATH="/usr/local/bin:${PATH}" \
    PYTHONPATH="/app" \
    PYTHONPYCACHEPREFIX="/opt/pycache" \
    XDG_CACHE_HOME="/opt/effectful/cache" \
    MYPY_CACHE_DIR=/opt/effectful/mypy_cache \
    RUFF_CACHE_DIR=/opt/effectful/ruff_cache \
    PYTEST_CACHE_DIR=/opt/effectful/pytest_cache \
    DOCKER_CONTAINER=1

# Install system dependencies and Python 3.12
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.12 \
    python3.12-dev \
    python3-pip \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.12 as default python3 and create python symlink
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
    && update-alternatives --set python3 /usr/bin/python3.12 \
    && ln -sf /usr/bin/python3.12 /usr/bin/python \
    && ln -sf /usr/bin/python3.12 /bin/python

# Install pip for Python 3.12 using get-pip.py
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Install Poetry via pip
RUN python3.12 -m pip install --upgrade pip setuptools wheel \
    && python3.12 -m pip install poetry==1.7.1 \
    && poetry --version

# Create cache directories under /opt/effectful/ namespace
RUN mkdir -p \
    /opt/effectful/cache \
    /opt/effectful/mypy_cache \
    /opt/effectful/pytest_cache \
    /opt/effectful/ruff_cache \
    /opt/pycache

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

# Install pytest wrapper for enforcement
# Move real pytest binary, then install wrapper
RUN if [ -f /usr/local/bin/pytest ]; then \
        mv /usr/local/bin/pytest /usr/local/bin/pytest.real; \
    fi

COPY docker/bin/pytest /usr/local/bin/pytest
RUN chmod +x /usr/local/bin/pytest

# Keep container running for interactive use
CMD ["sleep", "infinity"]
