FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Karachi \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/conda/bin:$PATH" \
    # Memory optimization for 48GB RAM
    MALLOC_ARENA_MAX=4 \
    MALLOC_MMAP_THRESHOLD_=262144 \
    MALLOC_TRIM_THRESHOLD_=262144 \
    MALLOC_TOP_PAD_=262144 \
    MALLOC_MMAP_MAX_=131072 \
    # Python optimizations
    PYTHONHASHSEED=random \
    PYTHONOPTIMIZE=1 \
    # GPU optimizations
    CUDA_LAUNCH_BLOCKING=0 \
    CUDA_CACHE_DISABLE=0 \
    CUDA_DEVICE_ORDER=PCI_BUS_ID \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Update system and install dependencies optimized for GPU workloads
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build dependencies
    build-essential \
    gcc \
    g++ \
    gfortran \
    # Database
    libpq-dev \
    libpq5 \
    # Audio/Video processing (GPU accelerated)
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    # Essential graphics libraries
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    # Math libraries optimized for GPU
    libopenblas-dev \
    liblapack-dev \
    libblas-dev \
    # Utilities
    libmagic1 \
    pkg-config \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY requirement.txt /tmp/

# Install Python packages in optimized order for GPU workloads
RUN pip install --no-cache-dir numpy scipy cython PyYAML && \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 && \
    pip install --no-cache-dir -r /tmp/requirement.txt && \
    pip install --no-cache-dir yt-dlp gunicorn[gthread]

# Update yt-dlp to latest version
RUN pip install -U yt-dlp

# Clean up build dependencies and cache (optimized for 48GB RAM)
RUN apt-get remove -y \
    build-essential \
    gcc \
    g++ \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    pkg-config \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/* /root/.cache \
    && find /opt/conda -name "*.pyc" -delete \
    && find /opt/conda -name "*.pyo" -delete \
    && find /opt/conda -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Create optimized non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    # Create app directories with proper permissions
    mkdir -p /app/{logs,media,staticfiles,data,tmp} && \
    chown -R appuser:appuser /app && \
    # Set proper permissions for clipsai media directory for appuser
    chown -R appuser:appuser /opt/conda/lib/python3.11/site-packages/clipsai/media 2>/dev/null || true && \
    chmod -R 755 /opt/conda/lib/python3.11/site-packages/clipsai/media 2>/dev/null || true

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

# Optimized health check for GPU server
HEALTHCHECK --interval=45s --timeout=20s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/', timeout=15)" || exit 1

# Expose port
EXPOSE 8000

# Set proper permissions for clipsai media directory
RUN chmod -R 755 /opt/conda/lib/python3.11/site-packages/clipsai/media 2>/dev/null || true

# Optimized gunicorn configuration for 48GB RAM / 9 vCPU setup
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "8", \
     "--threads", "3", \
     "--worker-class", "gthread", \
     "--worker-connections", "200", \
     "--max-requests", "3000", \
     "--max-requests-jitter", "300", \
     "--timeout", "3000", \
     "--graceful-timeout", "3000", \
     "--keep-alive", "10", \
     "--preload", \
     "--worker-tmp-dir", "/dev/shm", \
     "--access-logfile", "/app/logs/gunicorn-access.log", \
     "--error-logfile", "/app/logs/gunicorn-error.log", \
     "--log-level", "info", \
     "--capture-output", \
     "--enable-stdio-inheritance", \
     "backend.wsgi:application"]