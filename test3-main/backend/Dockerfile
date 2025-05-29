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
    OPENBLAS_NUM_THREADS=9 \
    # CRITICAL: ONNX Runtime CUDA library path - Updated for cuDNN 9
    LD_LIBRARY_PATH="/usr/local/cuda/lib64:/opt/venv/lib/python3.11/site-packages/onnxruntime/capi:/opt/venv/lib/python3.11/site-packages/nvidia/cuda_runtime/lib:/opt/venv/lib/python3.11/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH" \
    CUDA_HOME="/usr/local/cuda" \
    CUDA_ROOT="/usr/local/cuda"

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
    # CUDA runtime libraries (CRITICAL for ONNX Runtime)
    cuda-runtime-12-1 \
    cuda-libraries-12-1 \
    cuda-libraries-dev-12-1 \
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
    # SSL/TLS support
    openssl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment with Python 3.11
RUN python3.11 -m venv /opt/venv

# Upgrade pip and install build tools
RUN /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY requirement.txt /tmp/

# Install Python packages optimized for GPU and high memory
# CRITICAL: Install in correct order for ONNX Runtime GPU compatibility
RUN /opt/venv/bin/pip install --no-cache-dir numpy scipy cython && \
    # Install PyTorch with CUDA 12.1 support first
    /opt/venv/bin/pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 && \
    /opt/venv/bin/pip install --no-cache-dir PyYAML && \
    # CRITICAL: Install ONNX Runtime GPU with CUDA and cuDNN dependencies
    # This installs the NVIDIA packages automatically for compatibility
    /opt/venv/bin/pip install --no-cache-dir "onnxruntime-gpu[cuda,cudnn]" && \
    /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirement.txt && \
    # Install optimized media processing tools
    /opt/venv/bin/pip install --no-cache-dir yt-dlp gunicorn[gthread] && \
    # Update yt-dlp to latest
    /opt/venv/bin/pip install -U yt-dlp

# Verify CUDA library availability and update ldconfig
RUN ldconfig && \
    # Verify CUDA libraries are available
    ldconfig -p | grep cuda || echo "CUDA libraries not found in ldconfig" && \
    # List NVIDIA packages installed
    /opt/venv/bin/pip list | grep nvidia || echo "No NVIDIA packages found"

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
RUN mkdir -p /app/logs /app/media /app/staticfiles /app/data /app/tmp /app/models /app/models/cache /app/ssl

# Generate self-signed SSL certificate for development/testing
RUN openssl req -x509 -newkey rsa:4096 -keyout /app/ssl/key.pem -out /app/ssl/cert.pem -days 365 -nodes \
    -subj "/C=PK/ST=Sindh/L=Karachi/O=Development/CN=localhost"

# Create optimized non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    # Set ownership of app directories
    chown -R appuser:appuser /app && \
    # Set proper permissions for clipsai media directory
    chown -R appuser:appuser /opt/venv/lib/python3.11/site-packages/clipsai/media 2>/dev/null || true && \
    chmod -R 755 /opt/venv/lib/python3.11/site-packages/clipsai/media 2>/dev/null || true && \
    # Set SSL certificate permissions
    chmod 600 /app/ssl/key.pem && \
    chmod 644 /app/ssl/cert.pem

# Set working directory
WORKDIR /app

# Copy project files with proper ownership
COPY --chown=appuser:appuser . .

# Ensure proper ownership of all directories
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Test ONNX Runtime GPU functionality before finalizing
RUN python3 -c "import onnxruntime as ort; print('ONNX Runtime version:', ort.__version__); print('Available providers:', ort.get_available_providers()); import torch; print('PyTorch CUDA available:', torch.cuda.is_available()); print('PyTorch version:', torch.__version__)"

# Collect static files with better error handling
RUN python manage.py collectstatic --noinput --clear || \
    (echo "Static files collection failed, but continuing..." && ls -la /app/)

# GPU-optimized health check (updated for HTTPS)
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -k -f https://localhost:8443/health/ || python -c "import urllib.request, ssl; ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE; urllib.request.urlopen('https://localhost:8443/health/', timeout=10, context=ctx)" || exit 1

# Expose HTTPS port
EXPOSE 8443

# Set final permissions
RUN chmod -R 755 /opt/venv/lib/python3.11/site-packages/clipsai/media 2>/dev/null || true

# Optimized gunicorn configuration with HTTPS support
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8443", \
     "--certfile", "/app/ssl/cert.pem", \
     "--keyfile", "/app/ssl/key.pem", \
     "--ssl-version", "TLSv1_2", \
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