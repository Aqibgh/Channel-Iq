FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Karachi \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Memory optimization
    MALLOC_ARENA_MAX=2 \
    MALLOC_MMAP_THRESHOLD_=131072 \
    MALLOC_TRIM_THRESHOLD_=131072 \
    MALLOC_TOP_PAD_=131072 \
    MALLOC_MMAP_MAX_=65536 \
    # Python optimizations
    PYTHONHASHSEED=random \
    PYTHONOPTIMIZE=1

# Install system dependencies in optimized stages
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
    # Audio/Video processing (optimized)
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    # Essential graphics libraries only
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
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3.11 -m venv /opt/venv

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY requirement.txt /tmp/

# Install Python packages in optimized order with proper CPU utilization
RUN pip install --no-cache-dir numpy && \
    pip install --no-cache-dir scipy && \
    pip install --no-cache-dir cython && \
    pip install --no-cache-dir PyYAML && \
    pip install --no-cache-dir torch torchvision torchaudio && \
    pip install --no-cache-dir -r /tmp/requirement.txt && \
    pip install --no-cache-dir yt-dlp gunicorn[gthread]
RUN pip install -U yt-dlp
# Clean up build dependencies and cache (optimized for 8GB RAM)
RUN apt-get remove -y \
    build-essential \
    gcc \
    g++ \
    gfortran \
    python3.11-dev \
    libopenblas-dev \
    liblapack-dev \
    pkg-config \
    tk-dev \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/* /root/.cache \
    && find /opt/venv -name "*.pyc" -delete \
    && find /opt/venv -name "*.pyo" -delete \
    && find /opt/venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Create optimized non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    # Create app directories with proper permissions
    mkdir -p /app/{logs,media,staticfiles,data,tmp} && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy project files with proper ownership
COPY --chown=appuser:appuser . .

# Create necessary directories (additional)
RUN mkdir -p /app/logs /app/media /app/staticfiles /app/data && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Collect static files with better error handling
RUN python manage.py collectstatic --noinput --clear || \
    (echo "Static files collection failed, but continuing..." && ls -la /app/)

# Optimized health check for 8GB setup
HEALTHCHECK --interval=45s --timeout=20s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/', timeout=15)" || exit 1

# Expose port
EXPOSE 8000

# Optimized gunicorn configuration for 8GB RAM / 4 CPU setup
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--threads", "2", \
     "--worker-class", "gthread", \
     "--worker-connections", "100", \
     "--max-requests", "2000", \
     "--max-requests-jitter", "200", \
     "--timeout", "3000", \
     "--graceful-timeout", "30", \
     "--keep-alive", "10", \
     "--preload", \
     "--worker-tmp-dir", "/dev/shm", \
     "--access-logfile", "/app/logs/gunicorn-access.log", \
     "--error-logfile", "/app/logs/gunicorn-error.log", \
     "--log-level", "info", \
     "--capture-output", \
     "--enable-stdio-inheritance", \
     "backend.wsgi:application"]