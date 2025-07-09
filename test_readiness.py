#!/usr/bin/env python3
"""
Test script for crawler readiness system
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_readiness():
    """Test the readiness endpoint"""
    print("🔍 Testing crawler readiness system...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test readiness endpoint
            print("\n📡 Checking /api/readiness endpoint...")
            async with session.get("http://localhost:8080/api/readiness") as response:
                data = await response.json()
                
                print(f"Status Code: {response.status}")
                print(f"Ready for Crawling: {data.get('ready_for_crawling', False)}")
                print(f"Readiness Summary: {data.get('readiness_details', {}).get('readiness_summary', 'N/A')}")
                
                # Network status details
                network_status = data.get('network_status', {})
                print(f"\n🧅 Tor Status: {network_status.get('tor', {}).get('status', 'unknown')} (Ready: {network_status.get('tor', {}).get('ready', False)})")
                
                i2p_status = network_status.get('i2p', {})
                i2p_proxies = i2p_status.get('internal_proxies', {})
                print(f"🌐 I2P Status: {i2p_status.get('status', 'unknown')} (Ready: {i2p_status.get('ready', False)})")
                print(f"   Internal Proxies: {i2p_proxies.get('active_count', 0)}/{i2p_proxies.get('minimum_required', 5)} active")
                print(f"   Stats.i2p Accessible: {data.get('network_status', {}).get('i2p', {}).get('details', {}).get('stats_accessible', False)}")
                
                # Show successful sites if available
                successful_sites = data.get('network_status', {}).get('i2p', {}).get('details', {}).get('successful_sites', [])
                if successful_sites:
                    print(f"   Accessible Sites: {', '.join(successful_sites)}")
                
                if i2p_proxies.get('details'):
                    print("   Proxy Details:")
                    for proxy_name, proxy_info in i2p_proxies.get('details', {}).items():
                        status = proxy_info.get('status', 'unknown')
                        accessible = proxy_info.get('accessible', False)
                        successful_sites_proxy = proxy_info.get('successful_sites', [])
                        sites_info = f" ({', '.join(successful_sites_proxy)})" if successful_sites_proxy else ""
                        print(f"     - {proxy_name}: {status} ({'✅' if accessible else '❌'}){sites_info}")
                
                return data.get('ready_for_crawling', False)
                
    except Exception as e:
        print(f"❌ Error testing readiness: {e}")
        return False

async def test_full_metrics():
    """Test the full metrics endpoint for network data"""
    print("\n📊 Checking /api/metrics endpoint for network data...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8080/api/metrics") as response:
                data = await response.json()
                
                network_data = data.get('network', {})
                overall_readiness = network_data.get('overall_readiness', {})
                
                print(f"Overall Ready: {overall_readiness.get('ready_for_crawling', False)}")
                print(f"Tor Ready: {overall_readiness.get('tor_ready', False)}")
                print(f"I2P Ready: {overall_readiness.get('i2p_ready', False)}")
                print(f"I2P Proxies Sufficient: {overall_readiness.get('i2p_proxies_sufficient', False)}")
                print(f"Active I2P Proxies: {overall_readiness.get('active_i2p_proxies', 0)}")
                
                return True
                
    except Exception as e:
        print(f"❌ Error testing metrics: {e}")
        return False

async def main():
    """Main test function"""
    print("🧪 Noctipede Readiness Test")
    print("=" * 50)
    
    # Test readiness endpoint
    ready = await test_readiness()
    
    # Test full metrics
    await test_full_metrics()
    
    print("\n" + "=" * 50)
    if ready:
        print("✅ System is ready for crawling!")
    else:
        print("❌ System is NOT ready for crawling")
    
    print(f"🕐 Test completed at {datetime.now().isoformat()}")

if __name__ == "__main__":
    asyncio.run(main())
