FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Karachi \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

# Install system dependencies in stages
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build dependencies
    build-essential \
    gcc \
    g++ \
    gfortran \
    # Python development
    python3.11-dev \
    python3.11-venv \
    # Database
    libpq-dev \
    libpq5 \
    # Audio/Video processing
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    # Graphics/Display
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    # Math libraries
    libopenblas-dev \
    liblapack-dev \
    libblas-dev \
    # Utilities
    libmagic1 \
    pkg-config \
    python3-tk \
    tk-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3.11 -m venv /opt/venv

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY requirement.txt /tmp/

# Install Python packages in optimized order
RUN pip install --no-cache-dir numpy && \
    pip install --no-cache-dir scipy && \
    pip install --no-cache-dir cython && \
    pip install --no-cache-dir PyYAML && \
    pip install --no-cache-dir --find-links https://download.pytorch.org/whl/torch_stable.html \
        torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /tmp/requirement.txt

# Clean up build dependencies and cache
RUN apt-get remove -y \
    build-essential \
    gcc \
    g++ \
    gfortran \
    python3.11-dev \
    libopenblas-dev \
    liblapack-dev \
    pkg-config \
    wget \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/* /root/.cache \
    && find /opt/venv -name "*.pyc" -delete \
    && find /opt/venv -name "*.pyo" -delete \
    && find /opt/venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy project files
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN mkdir -p /app/logs /app/media /app/staticfiles /app/data && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser
# Collect static files
RUN python manage.py collectstatic --noinput || echo "Static files collection failed, continuing..."

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health/', timeout=10)" || exit 1

# Expose port
EXPOSE 8000

# Use a more memory-efficient gunicorn configuration
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "1", \
     "--threads", "2", \
     "--worker-class", "gthread", \
     "--worker-connections", "50", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--timeout", "300", \
     "--keep-alive", "5", \
     "--preload", \
     "--access-logfile", "/app/logs/gunicorn-access.log", \
     "--error-logfile", "/app/logs/gunicorn-error.log", \
     "--log-level", "info", \
     "backend.wsgi:application"]