"""
Smart I2P Test Optimizer - Two-phase approach:
1. Initial comprehensive test with early exit at 5 successful jumpsites
2. Subsequent minimal tests to just verify known-good jumpsites are reachable
"""
import os
import time
import json
import asyncio
import logging
from typing import Dict, Any, List, Set
from pathlib import Path

class SmartI2POptimizer:
    """Smart I2P testing with adaptive optimization"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cache_file = Path("/tmp/i2p_known_good_sites.json")
        self.known_good_sites: Set[str] = set()
        self.last_full_test = 0
        self.full_test_interval = 3600  # 1 hour between full tests
        self.min_good_sites = 5
        self.quick_test_timeout = 5  # 5 seconds for quick tests
        self.full_test_timeout = 15  # 15 seconds for full tests
        
        # Load known good sites from cache
        self._load_known_good_sites()
    
    def _load_known_good_sites(self):
        """Load previously discovered good I2P sites"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.known_good_sites = set(data.get('sites', []))
                    self.last_full_test = data.get('last_full_test', 0)
                    self.logger.info(f"Loaded {len(self.known_good_sites)} known good I2P sites from cache")
        except Exception as e:
            self.logger.warning(f"Could not load I2P site cache: {e}")
    
    def _save_known_good_sites(self):
        """Save discovered good I2P sites to cache"""
        try:
            data = {
                'sites': list(self.known_good_sites),
                'last_full_test': self.last_full_test,
                'updated': time.time()
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f)
            self.logger.debug(f"Saved {len(self.known_good_sites)} known good I2P sites to cache")
        except Exception as e:
            self.logger.warning(f"Could not save I2P site cache: {e}")
    
    def _should_do_full_test(self) -> bool:
        """Determine if we should do a full test or quick test"""
        now = time.time()
        
        # Do full test if:
        # 1. We don't have enough known good sites
        # 2. It's been more than 1 hour since last full test
        # 3. We have no cached data
        
        if len(self.known_good_sites) < self.min_good_sites:
            self.logger.info("Full I2P test needed: insufficient known good sites")
            return True
        
        if now - self.last_full_test > self.full_test_interval:
            self.logger.info("Full I2P test needed: cache expired")
            return True
        
        self.logger.info(f"Quick I2P test sufficient: {len(self.known_good_sites)} known good sites, cache age {(now - self.last_full_test)/60:.1f}m")
        return False
    
    async def _test_site_connectivity(self, site: str, timeout: int = 3) -> bool:
        """Test if a single I2P site is reachable"""
        try:
            import aiohttp
            client_timeout = aiohttp.ClientTimeout(total=timeout)
            proxy_url = "http://127.0.0.1:4444"
            
            async with aiohttp.ClientSession(timeout=client_timeout) as session:
                async with session.get(f"http://{site}/", proxy=proxy_url) as response:
                    return response.status == 200
        except Exception as e:
            self.logger.debug(f"Site {site} not reachable: {e}")
            return False
    
    async def _quick_test_known_sites(self) -> Dict[str, Any]:
        """Quick test of known good sites only"""
        start_time = time.time()
        self.logger.info(f"🚀 Quick I2P test: checking {len(self.known_good_sites)} known good sites")
        
        # Test known good sites concurrently
        tasks = [self._test_site_connectivity(site, self.quick_test_timeout) 
                for site in list(self.known_good_sites)[:8]]  # Limit to 8 sites max
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.quick_test_timeout + 2
            )
            
            successful_count = sum(1 for result in results if result is True)
            test_duration = time.time() - start_time
            
            # If most known sites are still good, we're healthy
            success_rate = successful_count / len(self.known_good_sites) if self.known_good_sites else 0
            is_healthy = success_rate >= 0.6  # 60% success rate is acceptable
            
            self.logger.info(f"✅ Quick I2P test completed in {test_duration:.2f}s: {successful_count}/{len(self.known_good_sites)} sites reachable")
            
            return {
                'status': 'healthy' if is_healthy else 'degraded',
                'connectivity': True,
                'ready_for_crawling': is_healthy,
                'proxy_working': True,
                'test_type': 'quick_known_sites',
                'test_duration_seconds': round(test_duration, 2),
                'sites_tested': len(self.known_good_sites),
                'sites_successful': successful_count,
                'success_rate': round(success_rate * 100, 1),
                'internal_proxies': {
                    'total_configured': len(self.known_good_sites),
                    'active_count': successful_count,
                    'minimum_required': 5,
                    'sufficient': successful_count >= 5,
                    'test_method': 'quick_verification'
                },
                'note': f'Quick test of {len(self.known_good_sites)} known good I2P sites'
            }
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Quick I2P test timed out after {self.quick_test_timeout + 2}s")
            return {
                'status': 'timeout',
                'connectivity': False,
                'ready_for_crawling': False,
                'proxy_working': True,
                'error': 'Quick test timed out',
                'test_type': 'quick_timeout'
            }
    
    async def _full_test_with_early_exit(self) -> Dict[str, Any]:
        """Full test of all I2P proxies with early exit at 5 successful"""
        start_time = time.time()
        internal_proxies = os.getenv('I2P_INTERNAL_PROXIES', '').split(',')
        internal_proxies = [p.strip() for p in internal_proxies if p.strip()]
        
        self.logger.info(f"🔍 Full I2P test: testing {len(internal_proxies)} proxies (early exit at {self.min_good_sites})")
        
        successful_sites = set()
        proxy_results = {}
        
        # Create semaphore to limit concurrent tests
        semaphore = asyncio.Semaphore(5)
        
        async def test_single_proxy(proxy_name: str) -> tuple:
            """Test a single proxy site"""
            async with semaphore:
                # Early exit check
                if len(successful_sites) >= self.min_good_sites:
                    self.logger.debug(f"Early exit: skipping {proxy_name} (already have {len(successful_sites)} good sites)")
                    return proxy_name, None
                
                success = await self._test_site_connectivity(proxy_name, 3)
                
                if success:
                    successful_sites.add(proxy_name)
                    self.logger.info(f"✅ {proxy_name} reachable ({len(successful_sites)}/{self.min_good_sites} needed)")
                    
                    proxy_data = {
                        'status': 'active',
                        'accessible': True,
                        'test_method': 'full_http_test'
                    }
                else:
                    proxy_data = {
                        'status': 'inactive',
                        'accessible': False,
                        'test_method': 'full_http_test'
                    }
                
                return proxy_name, proxy_data
        
        # Start all proxy tests
        tasks = [test_single_proxy(proxy) for proxy in internal_proxies]
        
        try:
            # Process tasks as they complete with early exit
            for task in asyncio.as_completed(tasks, timeout=self.full_test_timeout):
                try:
                    proxy_name, proxy_data = await task
                    if proxy_data:
                        proxy_results[proxy_name] = proxy_data
                    
                    # Check for early exit
                    if len(successful_sites) >= self.min_good_sites:
                        self.logger.info(f"🎯 Early exit triggered! {len(successful_sites)} successful sites found")
                        
                        # Cancel remaining tasks
                        for pending_task in tasks:
                            if not pending_task.done():
                                pending_task.cancel()
                        break
                        
                except Exception as e:
                    self.logger.error(f"Error testing proxy: {e}")
                    
        except asyncio.TimeoutError:
            self.logger.warning(f"Full I2P test timed out after {self.full_test_timeout}s")
            # Cancel remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
        
        test_duration = time.time() - start_time
        
        # Update known good sites and cache
        if successful_sites:
            self.known_good_sites.update(successful_sites)
            self.last_full_test = time.time()
            self._save_known_good_sites()
        
        is_sufficient = len(successful_sites) >= self.min_good_sites
        
        self.logger.info(f"✅ Full I2P test completed in {test_duration:.2f}s: {len(successful_sites)} successful sites")
        
        return {
            'status': 'healthy' if is_sufficient else 'degraded',
            'connectivity': True,
            'ready_for_crawling': is_sufficient,
            'proxy_working': True,
            'test_type': 'full_with_early_exit',
            'test_duration_seconds': round(test_duration, 2),
            'early_exit_triggered': len(successful_sites) >= self.min_good_sites,
            'sites_discovered': len(successful_sites),
            'internal_proxies': {
                'total_configured': len(internal_proxies),
                'active_count': len(successful_sites),
                'minimum_required': self.min_good_sites,
                'sufficient': is_sufficient,
                'details': proxy_results,
                'test_method': 'full_discovery'
            },
            'note': f'Full test with early exit at {self.min_good_sites} successful sites'
        }
    
    async def test_i2p_optimized(self) -> Dict[str, Any]:
        """Main entry point - choose between quick and full test"""
        try:
            # Check I2P proxy basic connectivity first
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', 4444))
            sock.close()
            
            if result != 0:
                return {
                    'status': 'error',
                    'connectivity': False,
                    'ready_for_crawling': False,
                    'proxy_working': False,
                    'error': 'I2P proxy not accessible on port 4444',
                    'test_type': 'socket_test_failed'
                }
            
            # Decide between quick and full test
            if self._should_do_full_test():
                return await self._full_test_with_early_exit()
            else:
                return await self._quick_test_known_sites()
                
        except Exception as e:
            self.logger.error(f"Error in optimized I2P testing: {e}")
            return {
                'status': 'error',
                'connectivity': False,
                'ready_for_crawling': False,
                'proxy_working': False,
                'error': str(e),
                'test_type': 'exception'
            }
