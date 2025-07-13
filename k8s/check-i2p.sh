#!/bin/bash

# Script to check I2P proxy status
echo "🌐 Checking I2P Proxy Status..."
echo "================================"

# Check pod status
echo "Pod Status:"
kubectl get pods -n noctipede -l app=i2p-proxy

echo ""
echo "Checking if HTTP proxy (port 4444) is ready..."

POD_NAME=$(kubectl get pods -n noctipede -l app=i2p-proxy -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD_NAME" ]; then
    echo "❌ No I2P proxy pod found"
    exit 1
fi

echo "Pod: $POD_NAME"

# Check if port 4444 is listening
if kubectl exec -n noctipede "$POD_NAME" -- netstat -tln | grep -q ':4444 '; then
    echo "✅ I2P HTTP proxy is ready on port 4444"
    
    # Test the proxy
    echo ""
    echo "Testing proxy connectivity..."
    if kubectl exec -n noctipede "$POD_NAME" -- curl -s --connect-timeout 5 -x 127.0.0.1:4444 http://stats.i2p/ | grep -q "I2P"; then
        echo "✅ I2P proxy is working - can access I2P sites"
    else
        echo "⚠️  I2P proxy is listening but may not be fully ready for I2P sites"
    fi
else
    echo "⏳ I2P HTTP proxy not ready yet (port 4444 not listening)"
    echo ""
    echo "Current listening ports:"
    kubectl exec -n noctipede "$POD_NAME" -- netstat -tln 2>/dev/null || echo "Could not check ports"
    echo ""
    echo "💡 I2P can take 5-15 minutes to fully start. Check again in a few minutes."
fi

echo ""
echo "I2P Console: http://<node-ip>:7070 (if LoadBalancer is configured)"
echo "To check logs: kubectl logs -n noctipede -l app=i2p-proxy"
