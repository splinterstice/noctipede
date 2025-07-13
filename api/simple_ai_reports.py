"""Simple AI Reports API endpoints without selenium dependency."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json

from core import get_logger
from database import get_db_session, Site, Page, MediaFile, ContentAnalysis

logger = get_logger(__name__)
router = APIRouter(prefix="/api/ai-reports", tags=["AI Reports"])


class QueryRequest(BaseModel):
    query: str
    context: Optional[str] = None


class QueryResponse(BaseModel):
    success: bool
    response: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
async def natural_language_query(request: QueryRequest):
    """Process natural language queries about crawled data."""
    try:
        logger.info(f"Processing natural language query: {request.query}")
        logger.debug(f"Full request: {request}")
        
        # Get database session
        db = get_db_session()
        logger.debug("Database session obtained")
        
        try:
            # Get basic statistics
            logger.debug("Querying database for statistics...")
            site_count = db.query(Site).count()
            page_count = db.query(Page).count()
            media_count = db.query(MediaFile).count()
            flagged_media_count = db.query(MediaFile).filter(MediaFile.is_flagged == True).count()
            logger.debug(f"Stats: sites={site_count}, pages={page_count}, media={media_count}, flagged={flagged_media_count}")
            
            # Get network type breakdown
            logger.debug("Querying network type breakdown...")
            onion_sites = db.query(Site).filter(Site.is_onion == True).count()
            i2p_sites = db.query(Site).filter(Site.is_i2p == True).count()
            clearnet_sites = site_count - onion_sites - i2p_sites
            logger.debug(f"Networks: clearnet={clearnet_sites}, tor={onion_sites}, i2p={i2p_sites}")
            
            # Get recent crawls
            logger.debug("Querying recent crawls...")
            recent_sites = db.query(Site).filter(Site.last_crawled.isnot(None)).order_by(Site.last_crawled.desc()).limit(10).all()
            logger.debug(f"Found {len(recent_sites)} recent sites")
            
            # Get top domains by page count
            logger.debug("Querying top sites by page count...")
            top_sites = db.query(Site).filter(Site.page_count > 0).order_by(Site.page_count.desc()).limit(10).all()
            logger.debug(f"Found {len(top_sites)} top sites")
            
            # Build response based on query content
            query_lower = request.query.lower()
            logger.debug(f"Query keywords: {query_lower}")
            
            if "overview" in query_lower or "summary" in query_lower:
                logger.debug("Generating overview response...")
                response = f"""# Noctipede Crawled Data Overview

## Summary Statistics
- **Total Sites**: {site_count:,}
- **Total Pages**: {page_count:,}
- **Total Media Files**: {media_count:,}
- **Flagged Media**: {flagged_media_count:,}

## Network Distribution
- **Clearnet Sites**: {clearnet_sites:,}
- **Tor (.onion) Sites**: {onion_sites:,}
- **I2P Sites**: {i2p_sites:,}

## Top Sites by Page Count
"""
                for i, site in enumerate(top_sites, 1):
                    network_type = "🧅 Tor" if site.is_onion else "🌐 I2P" if site.is_i2p else "🌍 Clearnet"
                    response += f"{i}. {site.url} ({network_type}) - {site.page_count:,} pages\n"
                
                if recent_sites:
                    response += "\n## Recently Crawled Sites\n"
                    for site in recent_sites[:5]:
                        network_type = "🧅" if site.is_onion else "🌐" if site.is_i2p else "🌍"
                        response += f"- {network_type} {site.url} (Last crawled: {site.last_crawled.strftime('%Y-%m-%d %H:%M')})\n"
            
            elif "network" in query_lower or "tor" in query_lower or "onion" in query_lower:
                logger.debug("Generating network analysis response...")
                response = f"""# Network Analysis

## Network Distribution
- **Clearnet Sites**: {clearnet_sites:,} ({clearnet_sites/site_count*100:.1f}%)
- **Tor (.onion) Sites**: {onion_sites:,} ({onion_sites/site_count*100:.1f}%)
- **I2P Sites**: {i2p_sites:,} ({i2p_sites/site_count*100:.1f}%)

## Tor Network Details
"""
                if onion_sites > 0:
                    tor_sites = db.query(Site).filter(Site.is_onion == True).order_by(Site.page_count.desc()).limit(10).all()
                    response += "### Top Tor Sites by Page Count\n"
                    for i, site in enumerate(tor_sites, 1):
                        response += f"{i}. {site.url} - {site.page_count:,} pages\n"
                else:
                    response += "No Tor sites found in the database.\n"
            
            elif "media" in query_lower or "image" in query_lower or "flag" in query_lower:
                response = f"""# Media Analysis

## Media Statistics
- **Total Media Files**: {media_count:,}
- **Flagged Media**: {flagged_media_count:,}
- **Flagged Percentage**: {flagged_media_count/media_count*100:.1f}% (if media > 0)

"""
                if flagged_media_count > 0:
                    flagged_media = db.query(MediaFile).filter(MediaFile.is_flagged == True).limit(10).all()
                    response += "### Recent Flagged Media\n"
                    for media in flagged_media:
                        response += f"- {media.filename} ({media.file_type}) - Reason: {media.flagged_reason or 'Not specified'}\n"
                else:
                    response += "No flagged media found.\n"
            
            elif "recent" in query_lower or "latest" in query_lower:
                response = f"""# Recent Activity

## Recently Crawled Sites
"""
                if recent_sites:
                    for site in recent_sites:
                        network_type = "🧅 Tor" if site.is_onion else "🌐 I2P" if site.is_i2p else "🌍 Clearnet"
                        response += f"- {network_type} {site.url}\n"
                        response += f"  - Last crawled: {site.last_crawled.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        response += f"  - Pages: {site.page_count:,}, Crawl count: {site.crawl_count}\n"
                        response += f"  - Status: {site.status}\n\n"
                else:
                    response += "No recently crawled sites found.\n"
            
            else:
                # Generic response with basic stats
                logger.debug("Generating generic response...")
                response = f"""# Noctipede Data Query Response

Based on your query: "{request.query}"

## Current Database Statistics
- **Sites**: {site_count:,} total ({onion_sites:,} Tor, {i2p_sites:,} I2P, {clearnet_sites:,} Clearnet)
- **Pages**: {page_count:,} total
- **Media Files**: {media_count:,} total ({flagged_media_count:,} flagged)

For more specific information, try queries like:
- "Generate an overview of all crawled data"
- "Show me network analysis"
- "What media has been flagged?"
- "Show recent crawling activity"
"""
            
            logger.debug(f"Generated response length: {len(response)} characters")
            
            # Prepare data for potential further processing
            logger.debug("Preparing structured data response...")
            data = {
                "stats": {
                    "sites": site_count,
                    "pages": page_count,
                    "media": media_count,
                    "flagged_media": flagged_media_count
                },
                "networks": {
                    "clearnet": clearnet_sites,
                    "tor": onion_sites,
                    "i2p": i2p_sites
                },
                "recent_sites": [
                    {
                        "url": site.url,
                        "network_type": "tor" if site.is_onion else "i2p" if site.is_i2p else "clearnet",
                        "last_crawled": site.last_crawled.isoformat() if site.last_crawled else None,
                        "page_count": site.page_count
                    }
                    for site in recent_sites
                ]
            }
            
            logger.info(f"Successfully processed query: {request.query}")
            logger.debug(f"Response data keys: {list(data.keys())}")
            
            return QueryResponse(
                success=True,
                response=response,
                data=data
            )
            
        finally:
            logger.debug("Closing database session")
            db.close()
            
    except Exception as e:
        logger.error(f"Error processing natural language query: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception args: {e.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return QueryResponse(
            success=False,
            response="",
            error=f"Error processing query: {str(e)}"
        )


@router.get("/recent")
async def get_recent_queries():
    """Get recent AI Reports queries."""
    try:
        # For now, return some sample recent queries
        # In a full implementation, this would come from a query history table
        recent_queries = [
            {
                "id": 1,
                "query": "Generate an overview of all crawled data",
                "timestamp": "2025-07-12T00:00:00Z",
                "response_preview": "Noctipede Crawled Data Overview - Total Sites: 54, Total Pages: 6,090..."
            },
            {
                "id": 2,
                "query": "Show me network analysis",
                "timestamp": "2025-07-11T23:45:00Z",
                "response_preview": "Network Analysis - Clearnet Sites: 25, Tor Sites: 27, I2P Sites: 2..."
            },
            {
                "id": 3,
                "query": "What media has been flagged?",
                "timestamp": "2025-07-11T23:30:00Z",
                "response_preview": "Media Analysis - Total Media Files: 15,721, Flagged Media: 0..."
            }
        ]
        
        logger.info(f"Returning {len(recent_queries)} recent queries")
        return recent_queries
        
    except Exception as e:
        logger.error(f"Error getting recent queries: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting recent queries: {str(e)}")


@router.get("/templates")
async def get_query_templates():
    """Get predefined query templates for AI Reports."""
    try:
        templates = [
            {
                "id": 1,
                "name": "Data Overview",
                "description": "Get a comprehensive overview of all crawled data including sites, pages, and media statistics",
                "query": "Generate an overview of all crawled data",
                "category": "General",
                "sql_equivalent": "SELECT COUNT(*) as sites FROM sites; SELECT COUNT(*) as pages FROM pages; SELECT COUNT(*) as media FROM media_files;"
            },
            {
                "id": 2,
                "name": "Network Analysis",
                "description": "Analyze the distribution across different networks (Clearnet, Tor, I2P)",
                "query": "Show me network analysis and distribution",
                "category": "Network",
                "sql_equivalent": "SELECT network_type, COUNT(*) FROM sites GROUP BY network_type;"
            },
            {
                "id": 3,
                "name": "Recent Activity",
                "description": "Show recently crawled sites and activity",
                "query": "Show recent crawling activity",
                "category": "Activity",
                "sql_equivalent": "SELECT * FROM sites WHERE last_crawled IS NOT NULL ORDER BY last_crawled DESC LIMIT 10;"
            },
            {
                "id": 4,
                "name": "Media Analysis",
                "description": "Analyze media files and flagged content",
                "query": "What media has been flagged and analyzed?",
                "category": "Media",
                "sql_equivalent": "SELECT COUNT(*) as total_media, COUNT(CASE WHEN is_flagged = 1 THEN 1 END) as flagged FROM media_files;"
            },
            {
                "id": 5,
                "name": "Tor Network Focus",
                "description": "Focus specifically on Tor (.onion) sites",
                "query": "Show me analysis of Tor network sites",
                "category": "Network",
                "sql_equivalent": "SELECT * FROM sites WHERE is_onion = 1 ORDER BY page_count DESC;"
            },
            {
                "id": 6,
                "name": "Site Statistics",
                "description": "Get detailed statistics about crawled sites",
                "query": "What are the top sites by page count and activity?",
                "category": "Statistics",
                "sql_equivalent": "SELECT url, page_count, last_crawled FROM sites WHERE page_count > 0 ORDER BY page_count DESC LIMIT 20;"
            },
            {
                "id": 7,
                "name": "Content Summary",
                "description": "Summarize the types of content and pages crawled",
                "query": "Summarize the types of content and pages crawled",
                "category": "Content",
                "sql_equivalent": "SELECT content_type, COUNT(*) FROM pages GROUP BY content_type;"
            },
            {
                "id": 8,
                "name": "Crawl Performance",
                "description": "Analyze crawling performance and success rates",
                "query": "How is the crawling performance and what are the success rates?",
                "category": "Performance",
                "sql_equivalent": "SELECT status, COUNT(*) FROM sites GROUP BY status;"
            },
            {
                "id": 9,
                "name": "I2P Network Analysis",
                "description": "Analyze I2P network sites and their characteristics",
                "query": "Show me I2P network analysis",
                "category": "Network",
                "sql_equivalent": "SELECT * FROM sites WHERE is_i2p = 1;"
            },
            {
                "id": 10,
                "name": "Large Sites Analysis",
                "description": "Find sites with the most pages and content",
                "query": "Which sites have the most content and pages?",
                "category": "Statistics",
                "sql_equivalent": "SELECT url, page_count, media_count FROM sites WHERE page_count > 10 ORDER BY page_count DESC;"
            },
            {
                "id": 11,
                "name": "Failed Crawls",
                "description": "Identify sites that failed to crawl or had issues",
                "query": "Show me sites that failed to crawl or had problems",
                "category": "Troubleshooting",
                "sql_equivalent": "SELECT url, status, error_message FROM sites WHERE status != 'completed';"
            },
            {
                "id": 12,
                "name": "Content Analysis Summary",
                "description": "Get summary of AI content analysis results",
                "query": "What has the AI content analysis found?",
                "category": "AI Analysis",
                "sql_equivalent": "SELECT analysis_type, COUNT(*) FROM content_analysis GROUP BY analysis_type;"
            }
        ]
        
        logger.info(f"Returning {len(templates)} query templates")
        return templates
        
    except Exception as e:
        logger.error(f"Error getting query templates: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting query templates: {str(e)}")


@router.get("/health")
async def ai_reports_health():
    """Health check for AI Reports service."""
    return {"status": "healthy", "service": "ai-reports", "selenium_available": False}
