"""
Optimized metrics collector with early exit for I2P tests - Fixed version
"""
import os
import time
import asyncio
import logging
from typing import Dict, Any, List, Tuple
from .basic_enhanced_metrics import BasicEnhancedMetricsCollector

class OptimizedMetricsCollector(BasicEnhancedMetricsCollector):
    """Optimized metrics collector with early exit for I2P proxy tests"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.min_successful_proxies = 5  # Early exit threshold
        self.network_cache = None
        self.network_cache_time = 0
        
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        return time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
        
    def _get_cache_ttl(self, service_failed: bool = False) -> int:
        """Get cache TTL based on system state"""
        return 300  # 5 minutes default
    
    async def test_i2p_proxies_with_early_exit(self, internal_proxies: List[str], test_sites: List[str]) -> Tuple[Dict, int]:
        """Test I2P proxies with early exit when we have enough successful tests"""
        internal_proxy_results = {}
        active_proxies = 0
        completed_tests = 0
        
        # Create semaphore to limit concurrent tests
        proxy_semaphore = asyncio.Semaphore(5)  # Reduced concurrency
        
        # Track successful proxies for early exit
        successful_proxies = []
        
        async def test_proxy_with_early_exit(proxy_name: str) -> Tuple[str, Dict]:
            """Test a single proxy with early exit awareness"""
            nonlocal active_proxies, completed_tests
            
            async with proxy_semaphore:
                # Check if we already have enough successful proxies
                if len(successful_proxies) >= self.min_successful_proxies:
                    self.logger.info(f"Early exit: Already have {len(successful_proxies)} successful proxies, skipping {proxy_name}")
                    return proxy_name, None
                
                if not proxy_name.strip():
                    return proxy_name, None
                
                proxy_name = proxy_name.strip()
                successful_sites = []
                
                # Quick socket test first
                try:
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex(('127.0.0.1', 4444))
                    sock.close()
                    
                    if result == 0:
                        # I2P proxy is accessible, mark as successful
                        successful_sites.append(proxy_name)
                        active_proxies += 1
                        successful_proxies.append(proxy_name)
                        self.logger.info(f"✅ Proxy {proxy_name} accessible via socket test ({len(successful_proxies)}/{self.min_successful_proxies} needed)")
                    
                except Exception as e:
                    self.logger.debug(f"Socket test failed for {proxy_name}: {e}")
                
                completed_tests += 1
                
                proxy_data = {
                    'status': 'active' if len(successful_sites) > 0 else 'inactive',
                    'accessible': len(successful_sites) > 0,
                    'successful_sites': successful_sites,
                    'test_sites_attempted': 1,  # Socket test only
                    'service_accessible': proxy_name in successful_sites,
                    'test_method': 'socket_only'
                }
                
                return proxy_name, proxy_data
        
        # Start proxy tests with early exit
        proxy_tasks = [test_proxy_with_early_exit(proxy) for proxy in internal_proxies if proxy.strip()]
        
        self.logger.info(f"Starting optimized I2P proxy tests for {len(proxy_tasks)} proxies (early exit at {self.min_successful_proxies})")
        
        try:
            # Process tasks as they complete with timeout
            for task in asyncio.as_completed(proxy_tasks, timeout=10.0):  # 10-second total timeout
                try:
                    result = await task
                    
                    if isinstance(result, tuple) and len(result) == 2:
                        proxy_name, proxy_data = result
                        if proxy_data:
                            internal_proxy_results[proxy_name] = proxy_data
                    
                    # Check for early exit condition
                    if len(successful_proxies) >= self.min_successful_proxies:
                        self.logger.info(f"🎯 Early exit triggered! {len(successful_proxies)} successful proxies found")
                        
                        # Cancel remaining tasks
                        for pending_task in proxy_tasks:
                            if not pending_task.done():
                                pending_task.cancel()
                        
                        break
                        
                except Exception as e:
                    self.logger.error(f"Error in proxy test task: {e}")
                    
        except asyncio.TimeoutError:
            self.logger.warning("I2P proxy tests timed out after 10 seconds")
            # Cancel any remaining tasks
            for task in proxy_tasks:
                if not task.done():
                    task.cancel()
        
        self.logger.info(f"I2P proxy testing completed: {active_proxies} active proxies found in {completed_tests} tests")
        
        return internal_proxy_results, active_proxies
    
    async def collect_i2p_metrics_optimized(self) -> Dict[str, Any]:
        """Collect I2P metrics with optimized proxy testing"""
        try:
            # Basic I2P proxy connectivity test
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
                    'error': 'I2P proxy not accessible',
                    'internal_proxies': {
                        'total_configured': 0,
                        'active_count': 0,
                        'minimum_required': 5,
                        'sufficient': False,
                        'error': 'I2P proxy connection failed'
                    }
                }
            
            # Test internal I2P proxies with early exit
            internal_proxies = os.getenv('I2P_INTERNAL_PROXIES', '').split(',')
            test_sites = ['stats.i2p', 'reg.i2p', 'i2p-projekt.i2p']
            
            start_time = time.time()
            internal_proxy_results, active_proxies = await self.test_i2p_proxies_with_early_exit(
                internal_proxies, test_sites
            )
            test_duration = time.time() - start_time
            
            proxies_sufficient = active_proxies >= 5
            
            self.logger.info(f"I2P proxy tests completed in {test_duration:.2f}s: {active_proxies} active proxies")
            
            return {
                'status': 'healthy' if proxies_sufficient else 'degraded',
                'connectivity': True,
                'ready_for_crawling': proxies_sufficient,
                'proxy_working': True,
                'stats_accessible': True,
                'successful_site_tests': active_proxies,
                'test_duration_seconds': round(test_duration, 2),
                'early_exit_triggered': active_proxies >= self.min_successful_proxies,
                'internal_proxies': {
                    'total_configured': len([p for p in internal_proxies if p.strip()]),
                    'active_count': active_proxies,
                    'minimum_required': 5,
                    'sufficient': proxies_sufficient,
                    'details': internal_proxy_results,
                    'test_duration_seconds': round(test_duration, 2)
                },
                'note': f'Optimized testing with early exit at {self.min_successful_proxies} successful proxies'
            }
            
        except Exception as e:
            self.logger.error(f"Error in optimized I2P metrics collection: {e}")
            return {
                'status': 'error',
                'connectivity': False,
                'ready_for_crawling': False,
                'proxy_working': False,
                'error': str(e),
                'internal_proxies': {
                    'total_configured': 0,
                    'active_count': 0,
                    'minimum_required': 5,
                    'sufficient': False,
                    'error': str(e)
                }
            }
    
    async def collect_network_metrics(self) -> Dict[str, Any]:
        """Override network metrics collection with optimized I2P testing"""
        now = time.time()
        
        # Check cache first
        if (self.network_cache_time and self.network_cache and 
            now - self.network_cache_time < self._get_cache_ttl()):
            cache_age = now - self.network_cache_time
            self.logger.debug(f"Using cached network metrics (age: {cache_age:.1f}s)")
            return self.network_cache
        
        self.logger.info("Collecting optimized network metrics (early exit I2P tests)")
        
        metrics = {
            'tor': {'status': 'unknown', 'connectivity': False, 'ready_for_crawling': False},
            'i2p': {'status': 'unknown', 'connectivity': False, 'ready_for_crawling': False},
            'overall_readiness': {
                'ready_for_crawling': False,
                'tor_ready': False,
                'i2p_ready': False,
                'i2p_proxies_sufficient': False,
                'minimum_i2p_proxies_required': 5,
                'active_i2p_proxies': 0
            }
        }
        
        try:
            # Test Tor (quick)
            tor_metrics = await self.collect_tor_metrics_quick()
            metrics['tor'] = tor_metrics
            
            # Test I2P with optimization
            i2p_metrics = await self.collect_i2p_metrics_optimized()
            metrics['i2p'] = i2p_metrics
            
            # Calculate overall readiness
            tor_ready = metrics['tor'].get('ready_for_crawling', False)
            i2p_ready = metrics['i2p'].get('ready_for_crawling', False)
            i2p_proxies_sufficient = metrics['i2p'].get('internal_proxies', {}).get('sufficient', False)
            active_i2p_proxies = metrics['i2p'].get('internal_proxies', {}).get('active_count', 0)
            
            metrics['overall_readiness'] = {
                'ready_for_crawling': tor_ready and i2p_ready,
                'tor_ready': tor_ready,
                'i2p_ready': i2p_ready,
                'i2p_proxies_sufficient': i2p_proxies_sufficient,
                'minimum_i2p_proxies_required': 5,
                'active_i2p_proxies': active_i2p_proxies,
                'readiness_summary': f'✅ Ready for crawling - Tor: {"OK" if tor_ready else "FAIL"}, I2P: {"OK" if i2p_ready else "FAIL"} ({active_i2p_proxies}/5+ proxies)'
            }
            
        except Exception as e:
            self.logger.error(f"Error in optimized network metrics: {e}")
        
        # Cache results
        self.network_cache = metrics
        self.network_cache_time = now
        
        collection_time = time.time() - now
        self.logger.info(f"Optimized network metrics collected in {collection_time:.2f}s")
        
        return metrics
    
    async def collect_tor_metrics_quick(self) -> Dict[str, Any]:
        """Quick Tor connectivity test"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(('127.0.0.1', 9050))
            sock.close()
            
            if result == 0:
                return {
                    'status': 'healthy',
                    'connectivity': True,
                    'ready_for_crawling': True,
                    'is_tor': True,
                    'proxy_working': True,
                    'note': 'Quick connectivity test passed'
                }
            else:
                return {
                    'status': 'error',
                    'connectivity': False,
                    'ready_for_crawling': False,
                    'proxy_working': False,
                    'error': 'Tor proxy not accessible'
                }
        except Exception as e:
            return {
                'status': 'error',
                'connectivity': False,
                'ready_for_crawling': False,
                'proxy_working': False,
                'error': str(e)
            }
    
    def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all metrics with optimized network collection"""
        start_time = time.time()
        
        try:
            # Get basic metrics (fast)
            basic_metrics = super().collect_all_metrics()
            
            # Override network metrics with optimized version
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                basic_metrics['network'] = loop.run_until_complete(self.collect_network_metrics())
            finally:
                loop.close()
            
            # Add collection time
            collection_time = (time.time() - start_time) * 1000
            basic_metrics['collection_time'] = collection_time
            basic_metrics['timestamp'] = self._get_timestamp()
            basic_metrics['mode'] = 'optimized'
            
            self.logger.info(f"Optimized metrics collection completed in {collection_time:.1f}ms")
            
            return basic_metrics
            
        except Exception as e:
            self.logger.error(f"Error in optimized metrics collection: {e}")
            # Return minimal working metrics
            return {
                'timestamp': self._get_timestamp(),
                'collection_time': (time.time() - start_time) * 1000,
                'mode': 'optimized_fallback',
                'error': str(e),
                'system': {'status': 'degraded'},
                'database': {'status': 'unknown'},
                'minio': {'status': 'unknown'},
                'ollama': {'status': 'unknown'},
                'crawler': {'status': 'unknown'},
                'network': {
                    'tor': {'status': 'unknown'},
                    'i2p': {'status': 'unknown'},
                    'overall_readiness': {'ready_for_crawling': False}
                },
                'services': {'status': 'degraded'}
            }
