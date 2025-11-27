FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy poetry configuration
COPY pyproject.toml ./

# Configure poetry to not create virtualenv
RUN poetry config virtualenvs.create false

# Generate lock file and install dependencies
RUN poetry lock --no-update
RUN poetry install --no-root --no-interaction --no-ansi

# Copy application code
COPY app /app/app
COPY scripts /app/scripts
COPY tests /app/tests

# Expose port
EXPOSE 8850

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8850/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8850"]
