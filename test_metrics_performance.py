#!/usr/bin/env python3
"""
Performance test for /api/metrics endpoint
"""

import asyncio
import aiohttp
import time
from datetime import datetime

async def test_metrics_performance():
    """Test the performance of the metrics endpoint"""
    print("⚡ Testing /api/metrics performance...")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: First call (should be slow due to fresh I2P testing)
        print("🔍 Test 1: First call (fresh I2P testing)")
        start_time = time.time()
        
        try:
            async with session.get("http://localhost:8080/api/metrics", timeout=aiohttp.ClientTimeout(total=120)) as response:
                end_time = time.time()
                duration = end_time - start_time
                
                print(f"Status: {response.status}")
                print(f"Duration: {duration:.2f} seconds")
                
                if response.status == 200:
                    data = await response.json()
                    network_data = data.get('network', {})
                    overall_readiness = network_data.get('overall_readiness', {})
                    
                    print(f"Ready for crawling: {overall_readiness.get('ready_for_crawling', False)}")
                    print(f"Active I2P proxies: {overall_readiness.get('active_i2p_proxies', 0)}")
                    print(f"Readiness summary: {overall_readiness.get('readiness_summary', 'N/A')}")
                else:
                    print(f"Error: HTTP {response.status}")
                    
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"Error after {duration:.2f}s: {e}")
        
        print()
        
        # Test 2: Second call (should be fast due to caching)
        print("🚀 Test 2: Second call (should use cache)")
        start_time = time.time()
        
        try:
            async with session.get("http://localhost:8080/api/metrics", timeout=aiohttp.ClientTimeout(total=30)) as response:
                end_time = time.time()
                duration = end_time - start_time
                
                print(f"Status: {response.status}")
                print(f"Duration: {duration:.2f} seconds")
                
                if response.status == 200:
                    print("✅ Cached response received")
                else:
                    print(f"Error: HTTP {response.status}")
                    
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"Error after {duration:.2f}s: {e}")
        
        print()
        
        # Test 3: Readiness endpoint (should be fast)
        print("⚡ Test 3: /api/readiness endpoint")
        start_time = time.time()
        
        try:
            async with session.get("http://localhost:8080/api/readiness", timeout=aiohttp.ClientTimeout(total=30)) as response:
                end_time = time.time()
                duration = end_time - start_time
                
                print(f"Status: {response.status}")
                print(f"Duration: {duration:.2f} seconds")
                
                if response.status in [200, 503]:
                    data = await response.json()
                    print(f"Ready for crawling: {data.get('ready_for_crawling', False)}")
                else:
                    print(f"Error: HTTP {response.status}")
                    
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"Error after {duration:.2f}s: {e}")

async def main():
    """Main test function"""
    print("🧪 Noctipede Metrics Performance Test")
    print(f"🕐 Started at {datetime.now().isoformat()}")
    print("=" * 60)
    
    await test_metrics_performance()
    
    print("=" * 60)
    print("📊 Performance Test Summary:")
    print("• First /api/metrics call should be ~10-15 seconds (concurrent I2P testing)")
    print("• Second /api/metrics call should be <2 seconds (cached)")
    print("• /api/readiness call should be <2 seconds (uses cached data)")
    print(f"🕐 Completed at {datetime.now().isoformat()}")

if __name__ == "__main__":
    asyncio.run(main())
