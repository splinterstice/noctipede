"""Main crawler entry point with enhanced I2P support."""

import sys
import signal
import asyncio
from datetime import datetime

from core import setup_logging, get_logger
from config import get_settings
from database import get_db_manager
from .manager import CrawlerManager


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger = get_logger(__name__)
    logger.info("Received shutdown signal, stopping crawler...")
    sys.exit(0)


async def main_async():
    """Main async crawler function."""
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🚀 Starting Noctipede Crawler with Enhanced I2P Support")
    
    try:
        # Initialize database
        db_manager = get_db_manager()
        if not db_manager.test_connection():
            logger.error("❌ Database connection failed")
            return 1
        
        # Create tables if they don't exist
        db_manager.create_tables()
        logger.info("✅ Database initialized")
        
        # Initialize crawler manager
        crawler_manager = CrawlerManager()
        
        # Load sites to crawl
        sites = crawler_manager.load_sites_from_file()
        if not sites:
            logger.error("❌ No sites to crawl")
            return 1
        
        logger.info(f"📋 Loaded {len(sites)} sites to crawl")
        
        # Group sites by network type for reporting
        from core import get_network_type
        sites_by_network = {}
        for site in sites:
            network_type = get_network_type(site)
            if network_type not in sites_by_network:
                sites_by_network[network_type] = []
            sites_by_network[network_type].append(site)
        
        for network, network_sites in sites_by_network.items():
            logger.info(f"  📡 {network.upper()}: {len(network_sites)} sites")
        
        # Start crawling with enhanced async support
        logger.info("🕷️ Starting crawl process...")
        start_time = datetime.now()
        
        results = await crawler_manager.crawl_sites_async(sites)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Report results
        logger.info("=" * 60)
        logger.info("🎯 CRAWL RESULTS SUMMARY")
        logger.info("=" * 60)
        logger.info(f"📊 Total Sites: {results['total_sites']}")
        logger.info(f"✅ Successful: {results['successful']}")
        logger.info(f"❌ Failed: {results['failed']}")
        logger.info(f"⏱️ Duration: {duration:.2f} seconds")
        logger.info(f"📈 Success Rate: {(results['successful'] / results['total_sites'] * 100):.1f}%")
        
        # Detailed results by network type
        network_stats = {}
        for result in results['results']:
            network = result['network_type']
            if network not in network_stats:
                network_stats[network] = {'success': 0, 'failed': 0}
            
            if result['success']:
                network_stats[network]['success'] += 1
            else:
                network_stats[network]['failed'] += 1
        
        logger.info("\n📡 Results by Network Type:")
        for network, stats in network_stats.items():
            total = stats['success'] + stats['failed']
            success_rate = (stats['success'] / total * 100) if total > 0 else 0
            logger.info(f"  {network.upper()}: {stats['success']}/{total} ({success_rate:.1f}% success)")
        
        # Show some successful crawls
        successful_results = [r for r in results['results'] if r['success']]
        if successful_results:
            logger.info(f"\n🎉 Sample Successful Crawls:")
            for result in successful_results[:5]:  # Show first 5
                if isinstance(result.get('result'), dict) and result['result'].get('pages'):
                    pages = result['result']['pages']
                    total_content = sum(len(p.get('content', '')) for p in pages)
                    logger.info(f"  ✅ {result['url']} - {len(pages)} pages, {total_content} chars")
        
        logger.info("=" * 60)
        
        return 0 if results['successful'] > 0 else 1
        
    except KeyboardInterrupt:
        logger.info("🛑 Crawler interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Crawler failed: {e}")
        return 1


def main():
    """Main synchronous entry point."""
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
