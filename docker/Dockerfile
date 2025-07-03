FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies including WebP support
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    git \
    libmariadb-dev \
    pkg-config \
    # WebP and image processing libraries
    libwebp-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libgif-dev \
    libopenjp2-7-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libfribidi-dev \
    libharfbuzz-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/data /app/output /app/logs

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Verify WebP support in Pillow
RUN python -c "from PIL import Image; print('WebP support:', 'WEBP' in Image.EXTENSION)"

# Copy application code
COPY . .

# Create a non-root user first
RUN useradd -m -u 1000 noctipede && \
    chown -R noctipede:noctipede /app && \
    chmod -R 755 /app/logs /app/output /app/data

# Switch to non-root user
USER noctipede

# Install the package in development mode as the non-root user
RUN pip install --user -e .

# Expose port
EXPOSE 8080

# Default command
CMD ["python", "-m", "noctipede.api.main"]
