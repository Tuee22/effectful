# HealthHub Backend Dockerfile
# Ubuntu 22.04 LTS + Python 3.12 + Poetry + Node.js 20 + Playwright

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
    PYTHONPATH="/app/effectful-root:/app/effectful-root/demo/healthhub:/app/effectful-root/demo/healthhub/backend" \
    PYTHONPYCACHEPREFIX="/opt/healthhub/pycache" \
    XDG_CACHE_HOME="/opt/healthhub/cache" \
    MYPY_CACHE_DIR=/opt/healthhub/mypy_cache \
    RUFF_CACHE_DIR=/opt/healthhub/ruff_cache \
    PYTEST_CACHE_DIR=/opt/healthhub/pytest_cache \
    DOCKER_CONTAINER=1

WORKDIR /app

# Create cache directories under /opt/healthhub/ namespace
RUN mkdir -p \
    /opt/healthhub/cache \
    /opt/healthhub/mypy_cache \
    /opt/healthhub/pytest_cache \
    /opt/healthhub/ruff_cache \
    /opt/healthhub/pycache \
    /opt/healthhub/backend-build \
    /opt/healthhub/frontend-build

# Install system dependencies including Python 3.12 and Node.js
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
    wget \
    gnupg \
    ca-certificates \
    postgresql-client \
    # Playwright browser dependencies
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    libgtk-3-0 \
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

# Install Node.js 20 LTS for Playwright
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && node --version && npm --version \
    && rm -rf /var/lib/apt/lists/*

# Configure poetry to not create virtualenv
RUN poetry config virtualenvs.create false

# ============================================
# Step 1: Install effectful (parent library)
# ============================================

# Copy effectful library from root
COPY pyproject.toml /app/effectful-root/
COPY README.md /app/effectful-root/
COPY CLAUDE.md /app/effectful-root/
COPY configs/ /app/effectful-root/configs/
COPY documents/ /app/effectful-root/documents/
COPY examples/ /app/effectful-root/examples/
COPY effectful_tools/ /app/effectful-root/effectful_tools/
COPY effectful/ /app/effectful-root/effectful/

# Install effectful
WORKDIR /app/effectful-root
RUN poetry install --only main --no-interaction --no-ansi

# ============================================
# Step 2: Install healthhub application
# ============================================

RUN mkdir -p /app/effectful-root/demo/healthhub
WORKDIR /app/effectful-root/demo/healthhub

# Copy healthhub pyproject.toml
COPY demo/healthhub/pyproject.toml /app/effectful-root/demo/healthhub/

# Copy healthhub code
COPY demo/healthhub/backend/ /app/effectful-root/demo/healthhub/backend/
COPY demo/healthhub/documents/ /app/effectful-root/demo/healthhub/documents/
COPY demo/healthhub/tools/ /app/effectful-root/demo/healthhub/tools/
COPY demo/healthhub/tests/ /app/effectful-root/demo/healthhub/tests/
COPY demo/healthhub/stubs/ /app/effectful-root/demo/healthhub/stubs/

# Install healthhub dependencies with lock guard and fallback
RUN poetry lock --no-update 2>/dev/null || true && \
    poetry install --with dev --no-root --no-interaction --no-ansi 2>/dev/null || \
    pip install \
    fastapi "uvicorn[standard]" "pydantic[email]" pydantic-settings \
    asyncpg redis pulsar-client bcrypt pyjwt python-multipart \
    "python-jose[cryptography]" "passlib[bcrypt]" boto3 prometheus-client \
    email-validator pytest pytest-asyncio pytest-cov pytest-mock pytest-timeout httpx \
    mypy black ruff mdformat mdformat-gfm mdformat-frontmatter mdformat-footnote mdformat-tables \
    pymarkdownlnt codespell playwright pytest-playwright

# Install Playwright browsers
RUN python -m playwright install --with-deps chromium firefox webkit

# ============================================
# Step 3: Build Frontend
# ============================================

# Copy frontend source
COPY demo/healthhub/frontend/package.json /opt/healthhub/frontend-build/
COPY demo/healthhub/frontend/src /opt/healthhub/frontend-build/src
COPY demo/healthhub/frontend/index.html /opt/healthhub/frontend-build/
COPY demo/healthhub/frontend/vite.config.ts /opt/healthhub/frontend-build/
COPY demo/healthhub/frontend/tsconfig.json /opt/healthhub/frontend-build/
COPY demo/healthhub/frontend/tsconfig.node.json /opt/healthhub/frontend-build/

# Install frontend dependencies and build
WORKDIR /opt/healthhub/frontend-build
RUN npm install --quiet && \
    BUILD_PATH=build npm run build && \
    ls -la build/index.html

# Return to healthhub workdir
WORKDIR /app/effectful-root/demo/healthhub

# ============================================
# Policy Enforcement
# ============================================

# Block direct pytest command (enforces using Poetry scripts)
RUN if [ -f /usr/local/bin/pytest ]; then mv /usr/local/bin/pytest /usr/local/bin/pytest.real; fi && \
    echo '#!/bin/sh\necho "❌ ERROR: Direct pytest forbidden"\necho "✅ USE: poetry run test-<category> (test-all, test-backend, test-integration, test-e2e)"\nexit 1' > /usr/local/bin/pytest && \
    chmod +x /usr/local/bin/pytest

# Expose port
EXPOSE 8851

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8851/health || exit 1

# Run application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8851"]
