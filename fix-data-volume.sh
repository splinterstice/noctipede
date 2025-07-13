#!/usr/bin/env bash

# Script to add /app/data volume mounts to deploy.sh

set -e

echo "🔧 Adding /app/data volume mounts to deploy.sh..."

# Backup the original file
cp k8s/deploy.sh k8s/deploy.sh.backup

# Add data volume mount to init containers (2 occurrences)
sed -i '/- name: output-data/{
    a\        - name: data-storage
    a\          mountPath: /app/data
}' k8s/deploy.sh

# Add data volume mount to main containers (2 occurrences)  
sed -i '/- name: log-data/{
    /mountPath: \/app\/logs/{
        a\        - name: data-storage
        a\          mountPath: /app/data
    }
}' k8s/deploy.sh

# Add data volume to volumes sections (2 occurrences)
sed -i '/- name: log-data/{
    /persistentVolumeClaim:/{
        /claimName: noctipede-logs-pvc/{
            a\      - name: data-storage
            a\        persistentVolumeClaim:
            a\          claimName: noctipede-data-pvc
        }
    }
}' k8s/deploy.sh

echo "✅ Added /app/data volume mounts to deploy.sh"
echo "📋 Changes made:"
echo "   - Added data-storage volume mount to init containers"
echo "   - Added data-storage volume mount to main containers"  
echo "   - Added data-storage volume definition"
echo ""
echo "🔍 Verifying changes..."
grep -n -A 2 -B 2 "data-storage\|noctipede-data-pvc" k8s/deploy.sh || echo "No matches found - check manually"
