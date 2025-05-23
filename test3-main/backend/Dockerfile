FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Karachi \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

# Install build and runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    python3.11-dev \
    python3.11-tk \
    python3.11-venv \
    libpq5 \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    libsndfile1 \
    libmagic1 \
    libportaudio2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create virtual environment
RUN python3.11 -m venv /opt/venv

# Set temp directory for pip
ENV TMPDIR=/tmp/pip-build
RUN mkdir -p $TMPDIR

# Copy requirements and install dependencies
COPY requirement.txt .

RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir PyYAML tf-keras && \
    TMPDIR=/tmp/pip-build pip install --no-cache-dir torch torchvision torchaudio && \
    TMPDIR=/tmp/pip-build pip install --no-cache-dir -r requirement.txt && \
    pip cache purge && \
    rm -rf /tmp/* /var/tmp/* /root/.cache && \
    find /opt/venv -name "*.pyc" -delete && \
    find /opt/venv -name "*.pyo" -delete && \
    find /opt/venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -name "*.so" -exec strip {} \; 2>/dev/null || true

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory and copy project files
WORKDIR /app
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/media /app/staticfiles /app/data && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "backend.wsgi:application"]
