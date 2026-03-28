FROM python:3.11-slim

ARG INSTALL_AI=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Minimal OS dependencies for scientific wheels and health checks.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first to leverage Docker layer caching.
COPY Dashboard/requirements-core.txt /app/Dashboard/requirements-core.txt
COPY Dashboard/requirements-ai.txt /app/Dashboard/requirements-ai.txt
COPY Dashboard/requirements.txt /app/Dashboard/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/Dashboard/requirements-core.txt \
    && if [ "$INSTALL_AI" = "true" ]; then pip install -r /app/Dashboard/requirements-ai.txt; fi

# Copy application code and required runtime assets.
COPY Dashboard /app/Dashboard
COPY Scripts /app/Scripts
RUN mkdir -p /app/Data /app/Database

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

WORKDIR /app/Dashboard
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
