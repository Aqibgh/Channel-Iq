FROM nvidia/cuda:12.1.1-devel-ubuntu22.04
RUN sed -i 's|http://archive.ubuntu.com|https://archive.ubuntu.com|g' /etc/apt/sources.list
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
    # CRITICAL: Updated library paths for cuDNN 8
    LD_LIBRARY_PATH="/usr/local/cuda/lib64:/usr/lib/x86_64-linux-gnu:/opt/venv/lib/python3.11/site-packages/onnxruntime/capi:/opt/venv/lib/python3.11/site-packages/nvidia/cuda_runtime/lib:/opt/venv/lib/python3.11/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH" \
    CUDA_HOME="/usr/local/cuda" \
    CUDA_ROOT="/usr/local/cuda" \
    # FIX: Set writable cache directories for libraries
    NLTK_DATA="/app/data/nltk_data" \
    MPLCONFIGDIR="/app/data/matplotlib" \
    TRANSFORMERS_CACHE="/app/data/transformers" \
    HF_HOME="/app/data/huggingface" \
    TORCH_HOME="/app/data/torch"

# Install Python 3.11, Nginx and system dependencies INCLUDING cuDNN
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python 3.11 installation
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3.11-distutils \
    # Nginx and supervisor for process management
    nginx \
    supervisor \
    # CRITICAL: Install cuDNN 8 libraries (compatible with CUDA 12.1)
    libcudnn8 \
    libcudnn8-dev \
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
    # CRITICAL: Install ONNX Runtime GPU - Use specific version compatible with cuDNN 8
    /opt/venv/bin/pip install --no-cache-dir "onnxruntime-gpu==1.16.3" && \
    /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirement.txt && \
    # Install optimized media processing tools
    /opt/venv/bin/pip install --no-cache-dir yt-dlp gunicorn[gthread] && \
    # Update yt-dlp to latest
    /opt/venv/bin/pip install -U yt-dlp

# CRITICAL: Create symbolic links for cuDNN libraries if needed
RUN ldconfig && \
    # Verify CUDA libraries are available
    ldconfig -p | grep cuda || echo "CUDA libraries not found in ldconfig" && \
    # Verify cuDNN libraries are available
    ldconfig -p | grep cudnn || echo "cuDNN libraries not found in ldconfig" && \
    # List NVIDIA packages installed
    /opt/venv/bin/pip list | grep nvidia || echo "No NVIDIA packages found" && \
    # Create symbolic links for cuDNN if they don't exist
    find /usr/lib/x86_64-linux-gnu -name "libcudnn*" -type f 2>/dev/null || echo "cuDNN files not found" && \
    # Ensure cuDNN libraries are in the system path
    echo "/usr/lib/x86_64-linux-gnu" >> /etc/ld.so.conf.d/cudnn.conf && \
    ldconfig

# Create app directories first - INCLUDING cache directories for libraries
RUN mkdir -p /app/logs /app/media /app/staticfiles /app/data /app/tmp /app/models /app/models/cache \
    /app/data/nltk_data /app/data/matplotlib /app/data/transformers /app/data/huggingface /app/data/torch

# Create runtime directories. TLS certificates must be mounted at runtime and
# are intentionally not copied from the source tree.
RUN mkdir -p /etc/nginx/ssl /var/log/nginx /var/lib/nginx/body /var/lib/nginx/fastcgi /var/lib/nginx/proxy /var/lib/nginx/scgi /var/lib/nginx/uwsgi

# Copy nginx configuration files
COPY nginx/nginx.conf /etc/nginx/nginx.conf

# Copy supervisor configuration
COPY supervisor/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

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

# Create optimized non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    # Set ownership of app directories - INCLUDING cache directories
    chown -R appuser:appuser /app && \
    # Set proper permissions for clipsai media directory
    chown -R appuser:appuser /opt/venv/lib/python3.11/site-packages/clipsai/media 2>/dev/null || true && \
    chmod -R 755 /opt/venv/lib/python3.11/site-packages/clipsai/media 2>/dev/null || true && \
    # Set nginx permissions
    chown -R www-data:www-data /var/lib/nginx /var/log/nginx

# Set working directory
WORKDIR /app

# Copy project files with proper ownership
COPY --chown=appuser:appuser . .

# Ensure proper ownership of all directories INCLUDING cache directories
RUN chown -R appuser:appuser /app && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app/logs && \
    chmod 755 /app/logs

# Pre-download NLTK data as appuser to avoid runtime permission issues
USER appuser
RUN python3 -c "import nltk; nltk.download('punkt', download_dir='/app/data/nltk_data')" || echo "NLTK download failed, will try at runtime"
USER root

# Verify libraries are properly linked
RUN ldconfig

# Collect static files with better error handling
RUN python manage.py collectstatic --noinput --clear || \
    (echo "Static files collection failed, but continuing..." && ls -la /app/)

# GPU-optimized health check (updated for domain)
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -k -f https://localhost/health/ || exit 1

# Expose HTTP and HTTPS ports
EXPOSE 80 443

# Set final permissions
RUN chmod -R 755 /opt/venv/lib/python3.11/site-packages/clipsai/media 2>/dev/null || true

# Start supervisor to manage both nginx and django
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
