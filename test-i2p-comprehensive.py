#!/usr/bin/env python3
"""
Comprehensive I2P Proxy Test Script
Tests various aspects of I2P functionality
"""

import requests
import time
import socket
import sys

def test_proxy_port():
    """Test if I2P proxy port is accessible"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('i2p-proxy', 4444))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Port test error: {e}")
        return False

def test_i2p_sites():
    """Test multiple I2P sites with detailed timing"""
    proxies = {'http': 'http://i2p-proxy:4444', 'https': 'http://i2p-proxy:4444'}
    
    test_sites = [
        ('walker.i2p', 'Walker I2P Search'),
        ('planet.i2p', 'Planet I2P'),
        ('i2p-projekt.i2p', 'I2P Project'),
        ('stats.i2p', 'I2P Network Stats'),
    ]
    
    results = []
    
    for site, description in test_sites:
        try:
            print(f"Testing {site} ({description})...")
            start_time = time.time()
            
            response = requests.get(
                f'http://{site}/', 
                proxies=proxies, 
                timeout=30,
                headers={'User-Agent': 'Noctipede-Test/1.0'}
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            result = {
                'site': site,
                'success': True,
                'status_code': response.status_code,
                'response_size': len(response.text),
                'duration': duration,
                'error': None
            }
            
            print(f"  ✅ SUCCESS: {response.status_code} - {len(response.text)} bytes in {duration:.2f}s")
            
        except Exception as e:
            result = {
                'site': site,
                'success': False,
                'status_code': None,
                'response_size': 0,
                'duration': 0,
                'error': str(e)
            }
            print(f"  ❌ FAILED: {str(e)}")
        
        results.append(result)
        time.sleep(2)  # Be nice to the I2P network
    
    return results

def test_proxy_functionality():
    """Test basic proxy functionality"""
    try:
        # Test a request that should fail without proxy
        requests.get('http://walker.i2p/', timeout=5)
        return False  # Should not reach here
    except:
        # This is expected - .i2p domains don't resolve without proxy
        pass
    
    try:
        # Test with proxy
        proxies = {'http': 'http://i2p-proxy:4444'}
        response = requests.get('http://walker.i2p/', proxies=proxies, timeout=30)
        return response.status_code == 200
    except Exception as e:
        print(f"Proxy test error: {e}")
        return False

def main():
    print("🧅 Comprehensive I2P Proxy Test")
    print("=" * 50)
    
    # Test 1: Port accessibility
    print("\n1. Testing I2P proxy port accessibility...")
    port_accessible = test_proxy_port()
    print(f"   Port 4444 accessible: {'✅ YES' if port_accessible else '❌ NO'}")
    
    if not port_accessible:
        print("❌ I2P proxy port not accessible. Exiting.")
        sys.exit(1)
    
    # Test 2: Basic proxy functionality
    print("\n2. Testing basic proxy functionality...")
    proxy_works = test_proxy_functionality()
    print(f"   Proxy routing works: {'✅ YES' if proxy_works else '❌ NO'}")
    
    # Test 3: Multiple I2P sites
    print("\n3. Testing multiple I2P sites...")
    site_results = test_i2p_sites()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    successful_sites = sum(1 for r in site_results if r['success'])
    total_sites = len(site_results)
    
    print(f"Port Accessibility: {'✅ PASS' if port_accessible else '❌ FAIL'}")
    print(f"Proxy Functionality: {'✅ PASS' if proxy_works else '❌ FAIL'}")
    print(f"Site Connectivity: {successful_sites}/{total_sites} sites accessible")
    
    if successful_sites > 0:
        avg_duration = sum(r['duration'] for r in site_results if r['success']) / successful_sites
        print(f"Average Response Time: {avg_duration:.2f} seconds")
    
    # Overall assessment
    if port_accessible and proxy_works and successful_sites >= 2:
        print("\n🎉 OVERALL: I2P proxy is WORKING")
        return True
    else:
        print("\n❌ OVERALL: I2P proxy has ISSUES")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
