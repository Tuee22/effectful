# HealthHub Backend Dockerfile
# Based on ShipNorth patterns for E2E testing

FROM python:3.12-slim

ARG DEBIAN_FRONTEND=noninteractive

# Environment variables (ShipNorth pattern)
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    PYTHONPATH=/app/effectful-root:/app/healthhub \
    DOCKER_CONTAINER=1

WORKDIR /app

# Create directories for build artifacts (ShipNorth pattern)
RUN mkdir -p /opt/healthhub/backend-build /opt/healthhub/frontend-build

# Install system dependencies including Node.js for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
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

# Install Node.js 20 LTS for Playwright (ShipNorth pattern)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && node --version && npm --version \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Configure poetry to not create virtualenv
RUN poetry config virtualenvs.create false

# ============================================
# Step 1: Install effectful (parent library)
# ============================================

# Copy effectful library from root
COPY pyproject.toml poetry.lock /app/effectful-root/
COPY effectful/ /app/effectful-root/effectful/

# Install effectful
WORKDIR /app/effectful-root
RUN poetry install --only main --no-interaction --no-ansi

# ============================================
# Step 2: Install healthhub application
# ============================================

WORKDIR /app/healthhub

# Copy healthhub pyproject.toml
COPY demo/healthhub/pyproject.toml /app/healthhub/

# Copy healthhub code
COPY demo/healthhub/backend/ /app/healthhub/backend/
COPY demo/healthhub/tools/ /app/healthhub/tools/
COPY demo/healthhub/tests/ /app/healthhub/tests/
COPY demo/healthhub/stubs/ /app/healthhub/stubs/

# Install healthhub dependencies (including dev for Playwright)
RUN poetry lock --no-update 2>/dev/null || true && \
    poetry install --with dev --no-root --no-interaction --no-ansi 2>/dev/null || \
    pip install \
    fastapi uvicorn[standard] pydantic[email] pydantic-settings \
    asyncpg redis pulsar-client bcrypt pyjwt python-multipart \
    python-jose[cryptography] passlib[bcrypt] boto3 prometheus-client \
    email-validator pytest pytest-asyncio pytest-cov pytest-mock httpx \
    mypy black ruff playwright pytest-playwright

# Install Playwright browsers (ShipNorth pattern)
RUN python -m playwright install --with-deps chromium firefox webkit

# ============================================
# Step 3: Build Frontend
# ============================================

# Copy frontend source
COPY demo/healthhub/frontend/package.json demo/healthhub/frontend/package-lock.json /opt/healthhub/frontend-build/
COPY demo/healthhub/frontend/src /opt/healthhub/frontend-build/src
COPY demo/healthhub/frontend/index.html /opt/healthhub/frontend-build/
COPY demo/healthhub/frontend/vite.config.ts /opt/healthhub/frontend-build/
COPY demo/healthhub/frontend/tsconfig.json /opt/healthhub/frontend-build/
COPY demo/healthhub/frontend/tsconfig.node.json /opt/healthhub/frontend-build/

# Install frontend dependencies and build
WORKDIR /opt/healthhub/frontend-build
RUN npm ci --quiet && \
    BUILD_PATH=build npm run build && \
    ls -la build/index.html

# Return to healthhub workdir
WORKDIR /app/healthhub

# ============================================
# Policy Enforcement (ShipNorth pattern)
# ============================================

# Block direct pytest command (enforces using Poetry scripts)
RUN if [ -f /usr/local/bin/pytest ]; then mv /usr/local/bin/pytest /usr/local/bin/pytest.real; fi && \
    echo '#!/bin/sh\necho "❌ ERROR: Direct pytest forbidden"\necho "✅ USE: poetry run test-<category> (test-all, test-backend, test-integration, test-e2e)"\nexit 1' > /usr/local/bin/pytest && \
    chmod +x /usr/local/bin/pytest

# Set PYTHONPATH so both effectful and healthhub are importable
ENV PYTHONPATH=/app/effectful-root:/app/healthhub:/app/healthhub/backend

# Expose port
EXPOSE 8850

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8850/health || exit 1

# Run application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8850"]
