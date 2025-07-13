#!/usr/bin/env python3
"""
Test script for enhanced metrics endpoint
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, '/app')

async def test_enhanced_metrics():
    """Test the enhanced metrics collection"""
    print("Testing enhanced metrics collection...")
    
    try:
        # Test simple combined metrics collector
        from portal.simple_combined_metrics import SimpleCombinedMetricsCollector
        
        collector = SimpleCombinedMetricsCollector()
        print("✅ SimpleCombinedMetricsCollector imported successfully")
        
        # Test collection
        metrics = await collector.collect_all_metrics()
        print("✅ Metrics collected successfully")
        print(f"Status: {metrics.get('status', 'unknown')}")
        print(f"Collection time: {metrics.get('collection_time', 0)}s")
        
        # Print structure
        print("\nMetrics structure:")
        for key in metrics.keys():
            if key not in ['timestamp', 'collection_time', 'status']:
                print(f"  - {key}: {type(metrics[key])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing enhanced metrics: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_full_combined_metrics():
    """Test the full combined metrics collector"""
    print("\nTesting full combined metrics collection...")
    
    try:
        from portal.combined_metrics_collector import CombinedMetricsCollector
        
        collector = CombinedMetricsCollector()
        print("✅ CombinedMetricsCollector imported successfully")
        
        # Test collection
        metrics = await collector.collect_all_metrics()
        print("✅ Full metrics collected successfully")
        print(f"Status: {metrics.get('status', 'unknown')}")
        print(f"Collection time: {metrics.get('collection_time', 0)}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing full combined metrics: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🕷️ Noctipede Enhanced Metrics Test")
    print("=" * 50)
    
    # Test simple version
    simple_success = asyncio.run(test_enhanced_metrics())
    
    # Test full version
    full_success = asyncio.run(test_full_combined_metrics())
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Simple Combined Metrics: {'✅ PASS' if simple_success else '❌ FAIL'}")
    print(f"Full Combined Metrics: {'✅ PASS' if full_success else '❌ FAIL'}")
    
    if simple_success or full_success:
        print("\n✅ At least one metrics collector is working!")
        print("The enhanced dashboard should now work.")
    else:
        print("\n❌ Both metrics collectors failed!")
        print("Check the error messages above for debugging.")
