# Dockerfile
# GridBridge UK - Data Ingestion & PyPSA Demo
# Multi-stage build for minimal production image

# ============================================================================
# Stage 1: Build dependencies
# ============================================================================
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Stage 2: Production image
# ============================================================================
FROM python:3.11-slim-bookworm AS runtime

LABEL maintainer="GridBridge Technical Team"
LABEL description="UK Grid Data Ingestion and PyPSA Analysis Platform"
LABEL version="1.0.0"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash gridbridge

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=gridbridge:gridbridge examples/ ./examples/
COPY --chown=gridbridge:gridbridge scripts/ ./scripts/

# Create output directory
RUN mkdir -p /app/out /app/data && chown -R gridbridge:gridbridge /app

# Switch to non-root user
USER gridbridge

# Health check - verify Python and key packages
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import pandas; import pypsa; import requests; print('OK')" || exit 1

# Default command
ENTRYPOINT ["python", "examples/ingest_real_data.py"]
CMD ["--start", "2025-01-15", "--days", "1", "--output", "/app/out"]
