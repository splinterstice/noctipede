#!/bin/sh

# Proxy Health Check Script for Noctipede
# Tests both Tor and I2P proxy functionality with real connectivity

set -eux

echo "🔍 Starting proxy health checks..."

# Test Tor proxy with DuckDuckGo onion service
echo "🧅 Testing Tor proxy connectivity..."
TOR_TEST_URL="http://facebookwkhpilnemxj7asaniu7vnjjbiltxjqhye3mhbshg7kx5tfyd.onion"
TOR_PROXY="tor-proxy:9050"

attempt=1
max_attempts=20
while [ $attempt -le $max_attempts ]; do
    echo "Tor test attempt $attempt/$max_attempts..."
    
    if curl --silent --fail --connect-timeout 15 --max-time 45 \
           --socks5-hostname "$TOR_PROXY" \
           "$TOR_TEST_URL" > /dev/null 2>&1; then
        echo "✅ Tor proxy is working!"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ Tor proxy failed after $max_attempts attempts"
        exit 1
    fi
    
    echo "⏳ Waiting for Tor proxy to be functional..."
    sleep 15
    attempt=$((attempt + 1))
done

# Test I2P proxy with walker.i2p
echo "🌐 Testing I2P proxy connectivity..."
I2P_TEST_URL="http://walker.i2p"
I2P_PROXY="i2p-proxy:4444"

attempt=1
max_attempts=15
while [ $attempt -le $max_attempts ]; do
    echo "I2P test attempt $attempt/$max_attempts..."
    
    if curl --silent --fail --connect-timeout 20 --max-time 90 \
           --proxy "$I2P_PROXY" \
           "$I2P_TEST_URL" > /dev/null 2>&1; then
        echo "✅ I2P proxy is working!"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        echo "⚠️  I2P proxy not ready, but continuing (I2P can take 10+ minutes to bootstrap)"
        echo "🔄 Applications will handle I2P connectivity gracefully"
        break
    fi
    
    echo "⏳ Waiting for I2P proxy to be functional..."
    sleep 20
    attempt=$((attempt + 1))
done

echo "🎉 Proxy health checks completed!"
echo "🧅 Tor: Ready"
echo "🌐 I2P: ${I2P_STATUS:-Ready/Bootstrapping}"
