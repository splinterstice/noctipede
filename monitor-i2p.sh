#!/bin/bash

echo "=== I2P Proxy Startup Monitor ==="
echo "This will monitor I2P proxy startup progress..."
echo "I2P typically takes 5-15 minutes to fully initialize"
echo

while true; do
    echo "$(date): Checking I2P proxy status..."
    
    # Get pod status
    POD_STATUS=$(kubectl get pods -l app=i2p-proxy -n noctipede --no-headers | head -1)
    echo "Pod Status: $POD_STATUS"
    
    # Test connectivity to I2P proxy port
    POD_NAME=$(kubectl get pods -l app=i2p-proxy -n noctipede --no-headers -o custom-columns=":metadata.name" | head -1)
    if [ ! -z "$POD_NAME" ]; then
        echo "Testing connectivity to $POD_NAME:4444..."
        kubectl exec -n noctipede $POD_NAME -- timeout 5s nc -z localhost 4444 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "✅ I2P HTTP proxy is responding on port 4444!"
            echo "I2P router startup appears successful"
            break
        else
            echo "❌ I2P HTTP proxy not yet ready on port 4444"
        fi
    fi
    
    echo "Waiting 60 seconds before next check..."
    echo "----------------------------------------"
    sleep 60
done

echo "=== I2P Proxy Monitor Complete ==="
