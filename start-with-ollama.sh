#!/usr/bin/env bash

# Noctipede Docker Compose Startup Script with Ollama Configuration
# This script starts Noctipede with Ollama endpoint at http://10.1.1.12:2701

set -e

echo "🚀 Starting Noctipede with Ollama at http://10.1.1.12:2701"
echo "=================================================="

# Check if Docker and Docker Compose are available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed or not in PATH"
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p data output logs

# Create a basic sites.txt if it doesn't exist
if [ ! -f "data/sites.txt" ]; then
    echo "📝 Creating sample sites.txt file..."
    cat > data/sites.txt << 'EOF'
# Sample sites for Noctipede crawler
# Add your target URLs here, one per line
# Supports clearnet, .onion (Tor), and .i2p sites

# Example clearnet sites
http://example.com

# Example .onion sites (Tor)
http://3g2upl4pq6kufc4m.onion  # DuckDuckGo onion
http://facebookwkhpilnemxj7asaniu7vnjjbiltxjqhye3mhbshg7kx5tfyd.onion  # Facebook onion

# Example .i2p sites (I2P)
http://stats.i2p
http://echelon.i2p
EOF
    echo "✅ Created sample sites.txt - edit data/sites.txt to add your target sites"
fi

# Test connectivity to Ollama endpoint
echo "🔍 Testing connectivity to Ollama endpoint..."
if curl -s --connect-timeout 5 http://10.1.1.12:2701/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama endpoint is reachable at http://10.1.1.12:2701"
else
    echo "⚠️  Warning: Cannot reach Ollama endpoint at http://10.1.1.12:2701"
    echo "   Make sure Ollama is running and accessible from this machine"
    echo "   Continuing anyway - you can fix this later..."
fi

# Start the services
echo "🐳 Starting Docker Compose services..."
echo "   Using environment file: .env.ollama"
echo "   Ollama endpoint: http://10.1.1.12:2701/api/generate"
echo ""

# Use docker-compose or docker compose depending on what's available
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

# Start services with the Ollama-configured environment
$COMPOSE_CMD --env-file .env.ollama up -d

echo ""
echo "🎉 Noctipede services are starting up!"
echo "=================================================="
echo ""
echo "📊 Enhanced Metrics Dashboard:"
echo "   • Web Portal: http://localhost:8080"
echo "   • Real-time system metrics with comprehensive monitoring"
echo "   • CPU, Memory, Database, MinIO, Ollama, Crawler, and Network metrics"
echo "   • Service health monitoring and performance tracking"
echo "   • MinIO Console: http://localhost:9001"
echo "   • MariaDB: localhost:3306"
echo "   • Tor Proxy: localhost:9050 (SOCKS5)"
echo "   • I2P Proxy: localhost:4444 (HTTP)"
echo ""
echo "🤖 AI Configuration:"
echo "   • Ollama Endpoint: http://10.1.1.12:2701/api/generate"
echo "   • Vision Model: llama3.2-vision:11b"
echo "   • Text Model: gemma3:12b"
echo "   • Moderation Model: llama3.1:8b"
echo ""
echo "📝 Configuration:"
echo "   • Sites file: data/sites.txt"
echo "   • Output directory: output/"
echo "   • Logs directory: logs/"
echo ""
echo "🔧 Useful commands:"
echo "   • View logs: $COMPOSE_CMD --env-file .env.ollama logs -f"
echo "   • Stop services: $COMPOSE_CMD --env-file .env.ollama down"
echo "   • Restart services: $COMPOSE_CMD --env-file .env.ollama restart"
echo "   • View status: $COMPOSE_CMD --env-file .env.ollama ps"
echo "   • Test metrics: python test-enhanced-metrics.py"
echo ""
echo "⏳ Note: I2P proxy may take 5-15 minutes to fully initialize"
echo "   You can monitor progress with: $COMPOSE_CMD --env-file .env.ollama logs -f i2p-proxy"
echo ""
echo "🚀 Noctipede is now running with your Ollama instance!"
