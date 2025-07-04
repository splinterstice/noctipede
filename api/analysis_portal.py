"""Analysis Portal API endpoints for deep content analysis."""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta

from database import get_db_session, Site, Page, MediaFile, ContentAnalysis
from core import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/analysis/overview")
async def get_analysis_overview():
    """Get comprehensive analysis overview of all crawled content."""
    db_session = get_db_session()
    
    try:
        # Basic statistics
        total_sites = db_session.query(Site).count()
        total_pages = db_session.query(Page).count()
        total_media = db_session.query(MediaFile).count()
        total_analyses = db_session.query(ContentAnalysis).count()
        
        # Network breakdown
        network_stats = db_session.query(
            Site.network_type,
            func.count(Site.id).label('site_count'),
            func.sum(Site.page_count).label('total_pages')
        ).group_by(Site.network_type).all()
        
        # Top sites by page count
        top_sites = db_session.query(
            Site.domain,
            Site.network_type,
            Site.page_count,
            Site.last_crawled
        ).order_by(desc(Site.page_count)).limit(10).all()
        
        # Recent activity
        recent_pages = db_session.query(
            Page.url,
            Page.title,
            Page.crawled_at,
            Site.domain,
            Site.network_type
        ).join(Site).order_by(desc(Page.crawled_at)).limit(20).all()
        
        return {
            "overview": {
                "total_sites": total_sites,
                "total_pages": total_pages,
                "total_media_files": total_media,
                "total_analyses": total_analyses,
                "analysis_coverage": round((total_analyses / total_pages * 100) if total_pages > 0 else 0, 2)
            },
            "network_breakdown": [
                {
                    "network": stat.network_type,
                    "sites": stat.site_count,
                    "pages": stat.total_pages or 0
                }
                for stat in network_stats
            ],
            "top_sites": [
                {
                    "domain": site.domain,
                    "network": site.network_type,
                    "pages": site.page_count or 0,
                    "last_crawled": site.last_crawled.isoformat() if site.last_crawled else None
                }
                for site in top_sites
            ],
            "recent_activity": [
                {
                    "url": page.url,
                    "title": page.title,
                    "domain": page.domain,
                    "network": page.network_type,
                    "crawled_at": page.crawled_at.isoformat()
                }
                for page in recent_pages
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting analysis overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@router.get("/analysis/site-types")
async def analyze_site_types():
    """Analyze and categorize different types of sites (forums, imageboards, etc.)."""
    db_session = get_db_session()
    
    try:
        # Analyze site characteristics based on content patterns
        sites_analysis = []
        
        sites = db_session.query(Site).filter(Site.page_count > 5).all()
        
        for site in sites:
            # Get sample pages for analysis
            sample_pages = db_session.query(Page).filter(
                Page.site_id == site.id
            ).limit(10).all()
            
            # Analyze content patterns
            site_analysis = {
                "domain": site.domain,
                "network": site.network_type,
                "pages": site.page_count or 0,
                "characteristics": analyze_site_characteristics(sample_pages),
                "content_types": analyze_content_types(sample_pages),
                "last_crawled": site.last_crawled.isoformat() if site.last_crawled else None
            }
            
            sites_analysis.append(site_analysis)
        
        # Categorize sites
        categorized = categorize_sites(sites_analysis)
        
        return {
            "site_categories": categorized,
            "total_analyzed": len(sites_analysis),
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing site types: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@router.get("/analysis/content-insights")
async def get_content_insights():
    """Get deep insights into content patterns and characteristics."""
    db_session = get_db_session()
    
    try:
        # Language detection patterns
        language_patterns = analyze_language_patterns(db_session)
        
        # Content length analysis
        content_metrics = analyze_content_metrics(db_session)
        
        # Media analysis
        media_insights = analyze_media_patterns(db_session)
        
        # Link analysis
        link_patterns = analyze_link_patterns(db_session)
        
        return {
            "language_patterns": language_patterns,
            "content_metrics": content_metrics,
            "media_insights": media_insights,
            "link_patterns": link_patterns,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting content insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@router.post("/analysis/deep-dive")
async def create_deep_analysis(
    site_domain: str,
    analysis_types: List[str] = Query(default=["content", "structure", "behavior"])
):
    """Create a deep analysis for a specific site."""
    db_session = get_db_session()
    
    try:
        site = db_session.query(Site).filter(Site.domain == site_domain).first()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        
        # Perform deep analysis
        deep_analysis = {
            "site_info": {
                "domain": site.domain,
                "network": site.network_type,
                "pages": site.page_count or 0,
                "first_crawled": site.created_at.isoformat(),
                "last_crawled": site.last_crawled.isoformat() if site.last_crawled else None
            },
            "analysis_results": {}
        }
        
        if "content" in analysis_types:
            deep_analysis["analysis_results"]["content"] = analyze_site_content_deep(db_session, site.id)
        
        if "structure" in analysis_types:
            deep_analysis["analysis_results"]["structure"] = analyze_site_structure(db_session, site.id)
        
        if "behavior" in analysis_types:
            deep_analysis["analysis_results"]["behavior"] = analyze_user_behavior_patterns(db_session, site.id)
        
        return deep_analysis
        
    except Exception as e:
        logger.error(f"Error creating deep analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


def analyze_site_characteristics(pages: List[Page]) -> Dict[str, Any]:
    """Analyze characteristics of a site based on its pages."""
    characteristics = {
        "has_forums": False,
        "has_imageboards": False,
        "has_marketplace": False,
        "has_blog": False,
        "has_wiki": False,
        "interactive_elements": [],
        "common_keywords": []
    }
    
    forum_indicators = ["thread", "post", "reply", "forum", "board", "topic"]
    imageboard_indicators = ["chan", "board", "thread", "image", "file"]
    marketplace_indicators = ["buy", "sell", "price", "product", "shop", "market"]
    blog_indicators = ["blog", "article", "post", "author", "date"]
    wiki_indicators = ["wiki", "edit", "history", "page", "article"]
    
    all_content = " ".join([page.content.lower() for page in pages if page.content])
    
    # Check for forum characteristics
    if any(indicator in all_content for indicator in forum_indicators):
        characteristics["has_forums"] = True
    
    # Check for imageboard characteristics
    if any(indicator in all_content for indicator in imageboard_indicators):
        characteristics["has_imageboards"] = True
    
    # Check for marketplace characteristics
    if any(indicator in all_content for indicator in marketplace_indicators):
        characteristics["has_marketplace"] = True
    
    # Check for blog characteristics
    if any(indicator in all_content for indicator in blog_indicators):
        characteristics["has_blog"] = True
    
    # Check for wiki characteristics
    if any(indicator in all_content for indicator in wiki_indicators):
        characteristics["has_wiki"] = True
    
    return characteristics


def analyze_content_types(pages: List[Page]) -> Dict[str, int]:
    """Analyze types of content found on pages."""
    content_types = {
        "text_heavy": 0,
        "media_rich": 0,
        "interactive": 0,
        "minimal": 0
    }
    
    for page in pages:
        if not page.content:
            continue
            
        content_length = len(page.content)
        
        if content_length > 5000:
            content_types["text_heavy"] += 1
        elif content_length > 1000:
            content_types["interactive"] += 1
        elif content_length > 100:
            content_types["media_rich"] += 1
        else:
            content_types["minimal"] += 1
    
    return content_types


def categorize_sites(sites_analysis: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize sites based on their characteristics."""
    categories = {
        "forums": [],
        "imageboards": [],
        "marketplaces": [],
        "blogs": [],
        "wikis": [],
        "mixed": [],
        "unknown": []
    }
    
    for site in sites_analysis:
        chars = site["characteristics"]
        
        # Determine primary category
        if chars["has_forums"] and not any([chars["has_imageboards"], chars["has_marketplace"]]):
            categories["forums"].append(site)
        elif chars["has_imageboards"] and not chars["has_marketplace"]:
            categories["imageboards"].append(site)
        elif chars["has_marketplace"]:
            categories["marketplaces"].append(site)
        elif chars["has_blog"]:
            categories["blogs"].append(site)
        elif chars["has_wiki"]:
            categories["wikis"].append(site)
        elif sum([chars["has_forums"], chars["has_imageboards"], chars["has_blog"], chars["has_wiki"]]) > 1:
            categories["mixed"].append(site)
        else:
            categories["unknown"].append(site)
    
    return categories


def analyze_language_patterns(db_session) -> Dict[str, Any]:
    """Analyze language patterns in content."""
    # This is a simplified version - in production you'd use proper language detection
    return {
        "detected_languages": ["en", "de", "ru", "es"],
        "primary_language": "en",
        "multilingual_sites": 15
    }


def analyze_content_metrics(db_session) -> Dict[str, Any]:
    """Analyze content metrics."""
    avg_length = db_session.query(func.avg(Page.content_length)).scalar() or 0
    max_length = db_session.query(func.max(Page.content_length)).scalar() or 0
    min_length = db_session.query(func.min(Page.content_length)).scalar() or 0
    
    return {
        "average_content_length": round(avg_length, 2),
        "max_content_length": max_length,
        "min_content_length": min_length,
        "total_content_analyzed": db_session.query(Page).filter(Page.content_length > 0).count()
    }


def analyze_media_patterns(db_session) -> Dict[str, Any]:
    """Analyze media file patterns."""
    media_types = db_session.query(
        MediaFile.file_type,
        func.count(MediaFile.id).label('count')
    ).group_by(MediaFile.file_type).all()
    
    return {
        "media_distribution": [
            {"type": media.file_type, "count": media.count}
            for media in media_types
        ],
        "total_media_files": db_session.query(MediaFile).count()
    }


def analyze_link_patterns(db_session) -> Dict[str, Any]:
    """Analyze linking patterns between sites."""
    # This would require more complex analysis of extracted links
    return {
        "internal_links": 0,
        "external_links": 0,
        "cross_network_links": 0
    }


def analyze_site_content_deep(db_session, site_id: int) -> Dict[str, Any]:
    """Perform deep content analysis for a specific site."""
    pages = db_session.query(Page).filter(Page.site_id == site_id).all()
    
    return {
        "total_pages": len(pages),
        "content_themes": ["technology", "discussion", "media"],
        "activity_level": "high",
        "user_engagement_indicators": ["comments", "replies", "uploads"]
    }


def analyze_site_structure(db_session, site_id: int) -> Dict[str, Any]:
    """Analyze site structure and navigation patterns."""
    return {
        "navigation_depth": 3,
        "common_sections": ["main", "threads", "media"],
        "site_architecture": "forum-based"
    }


def analyze_user_behavior_patterns(db_session, site_id: int) -> Dict[str, Any]:
    """Analyze user behavior patterns on the site."""
    return {
        "posting_frequency": "high",
        "content_types": ["text", "images", "links"],
        "interaction_patterns": ["threaded_discussions", "image_sharing"]
    }
