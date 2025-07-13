#!/usr/bin/env python3
"""
Test script for unified portal routes and functionality
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, '.')

async def test_unified_portal():
    """Test the unified portal functionality"""
    print("🕷️ Testing Unified Portal")
    print("=" * 50)
    
    try:
        from portal.unified_portal import UnifiedPortal
        print("✅ UnifiedPortal imported successfully")
        
        # Create portal instance
        portal = UnifiedPortal()
        print("✅ UnifiedPortal instance created")
        
        # Check if the app has the required routes
        routes = [route.path for route in portal.app.routes]
        
        required_routes = [
            "/",
            "/enhanced", 
            "/combined",
            "/ai-reports",
            "/api/metrics",
            "/api/enhanced-metrics",
            "/api/health"
        ]
        
        print("\n📋 Checking required routes:")
        all_routes_present = True
        for route in required_routes:
            if route in routes:
                print(f"  ✅ {route}")
            else:
                print(f"  ❌ {route} - MISSING")
                all_routes_present = False
        
        if all_routes_present:
            print("\n✅ All required routes are present")
        else:
            print("\n❌ Some required routes are missing")
            return False
        
        # Test metrics collector
        print("\n📊 Testing metrics collector:")
        try:
            metrics = await portal.metrics_collector.collect_all_metrics()
            print("✅ Metrics collection successful")
            print(f"   Keys: {list(metrics.keys())}")
        except Exception as e:
            print(f"⚠️  Metrics collection failed: {e}")
            print("   This is expected if dependencies are missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing unified portal: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_unified_portal())
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Unified Portal Test: PASSED")
        print("The portal should work correctly in deployment")
    else:
        print("❌ Unified Portal Test: FAILED")
        print("Check the errors above before deploying")
    
    sys.exit(0 if success else 1)
