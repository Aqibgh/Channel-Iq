FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Karachi \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Memory optimization for 25GB RAM
    MALLOC_ARENA_MAX=4 \
    MALLOC_MMAP_THRESHOLD_=262144 \
    MALLOC_TRIM_THRESHOLD_=262144 \
    MALLOC_TOP_PAD_=262144 \
    MALLOC_MMAP_MAX_=131072 \
    # Python optimizations
    PYTHONHASHSEED=random \
    PYTHONOPTIMIZE=1 \
    # CUDA and cuDNN environment (pre-configured in base image)
    CUDA_VISIBLE_DEVICES=0 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    # PyTorch optimizations for RTX A5000
    TORCH_CUDA_ARCH_LIST="8.6" \
    CUDA_LAUNCH_BLOCKING=0 \
    TORCH_CUDNN_V8_API_ENABLED=1 \
    # OMP optimization for 9 vCPU
    OMP_NUM_THREADS=9 \
    MKL_NUM_THREADS=9 \
    OPENBLAS_NUM_THREADS=9

# Install Python 3.11 and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python 3.11 installation
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3.11-distutils \
    # cuDNN (not included in devel image)
    libcudnn8 \
    libcudnn8-dev \
    # Build dependencies
    build-essential \
    gcc \
    g++ \
    gfortran \
    # Database
    libpq-dev \
    libpq5 \
    # Audio/Video processing with GPU acceleration
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    # Graphics libraries for GPU computing
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    # Optimized math libraries
    libopenblas-dev \
    liblapack-dev \
    libblas-dev \
    # Utilities
    libmagic1 \
    pkg-config \
    python3-tk \
    tk-dev \
    curl \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment with Python 3.11
RUN python3.11 -m venv /opt/venv

# Upgrade pip and install build tools
RUN /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY requirement.txt /tmp/

# Install Python packages optimized for GPU and high memory
# Install PyTorch with CUDA 12.1 support first
RUN /opt/venv/bin/pip install --no-cache-dir numpy scipy cython && \
    # Install PyTorch with CUDA 12.1 support
    /opt/venv/bin/pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 && \
    /opt/venv/bin/pip install --no-cache-dir PyYAML && \
    /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirement.txt && \
    # Install optimized media processing tools
    /opt/venv/bin/pip install --no-cache-dir yt-dlp gunicorn[gthread] && \
    # Update yt-dlp to latest
    /opt/venv/bin/pip install -U yt-dlp

# Clean up build dependencies but keep CUDA runtime (optimized for 25GB RAM)
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
    software-properties-common \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/* /root/.cache \
    && find /opt/venv -name "*.pyc" -delete \
    && find /opt/venv -name "*.pyo" -delete \
    && find /opt/venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Create app directories first
RUN mkdir -p /app/{logs,media,staticfiles,data,tmp,models,models/cache}

# Create optimized non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    # Set ownership of app directories
    chown -R appuser:appuser /app && \
    # Set proper permissions for clipsai media directory
    chown -R appuser:appuser /opt/venv/lib/python3.11/site-packages/clipsai/media && \
    chmod -R 755 /opt/venv/lib/python3.11/site-packages/clipsai/media

# Set working directory
WORKDIR /app

# Copy project files with proper ownership
COPY --chown=appuser:appuser . .

# Ensure proper ownership of all directories
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Collect static files with better error handling
RUN python manage.py collectstatic --noinput --clear || \
    (echo "Static files collection failed, but continuing..." && ls -la /app/)

# GPU-optimized health check
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/', timeout=10)" || exit 1

# Expose port
EXPOSE 8000

# Set final permissions
RUN chmod -R 755 /opt/venv/lib/python3.11/site-packages/clipsai/media || true

# Optimized gunicorn configuration for RTX A5000 setup (25GB RAM / 9 vCPU)
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "9", \
     "--threads", "3", \
     "--worker-class", "gthread", \
     "--worker-connections", "200", \
     "--max-requests", "5000", \
     "--max-requests-jitter", "500", \
     "--timeout", "300000", \
     "--graceful-timeout", "180000", \
     "--keep-alive", "5", \
     "--preload", \
     "--worker-tmp-dir", "/dev/shm", \
     "--access-logfile", "/app/logs/gunicorn-access.log", \
     "--error-logfile", "/app/logs/gunicorn-error.log", \
     "--log-level", "info", \
     "--capture-output", \
     "--enable-stdio-inheritance", \
     "backend.wsgi:application"]