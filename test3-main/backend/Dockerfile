# Use multi-stage build for smaller final image
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
RUN apt-get install python3.11-tk

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirement.txt .
COPY .env .env
RUN mkdir -p /home/user/tmp
ENV TMPDIR=/home/user/tmp
RUN pip install --upgrade pip setuptools wheel && \
RUN pip install --no-cache-dir PyYAML
RUN pip install -no-cache-dir tf-keras
RUN TMPDIR=/home/user/tmp pip install --no-cache-dir numpy torch torchaudio
RUN TMPDIR=/home/user/tmp pip install --no-cache-dir -r requirement.txt

# Final stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11-dev \
    libpq-dev \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    libsndfile1 \
    libmagic1 \
    portaudio19-dev \
    python3.11-tk \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/media /app/staticfiles /app/data \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "backend.wsgi:application"] 