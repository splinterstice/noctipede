#!/bin/bash

# Noctipede Setup Script

set -e

echo "🕷️  Setting up Noctipede..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before proceeding!"
    echo "   Required: OLLAMA_ENDPOINT, MARIADB_PASSWORD, MINIO_ACCESS_KEY, MINIO_SECRET_KEY"
    read -p "Press Enter after editing .env file..."
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data output logs

# Check if sites.txt exists and has content
if [ ! -s data/sites.txt ]; then
    echo "📝 sites.txt is empty or missing. Please add URLs to crawl."
    echo "Example content has been added to data/sites.txt"
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Setup completed!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Add URLs to data/sites.txt"
echo "3. Run: make run (or docker-compose up -d)"
echo "4. Access web interface at http://localhost:8080"
echo ""
echo "For Kubernetes deployment:"
echo "1. Ensure you have kubectl configured"
echo "2. Run: ./deploy.sh"
