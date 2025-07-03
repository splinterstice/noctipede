"""API routes and endpoints."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from core import get_logger
from database import get_db_session, Site, Page, MediaFile, ContentAnalysis
from crawlers import CrawlerManager
from analysis import AnalysisManager

logger = get_logger(__name__)
router = APIRouter()


# Pydantic models for API
class SiteResponse(BaseModel):
    id: int
    url: str
    is_onion: bool
    is_i2p: bool
    last_crawled: Optional[str]
    crawl_count: int
    error_count: int
    status: str

    class Config:
        from_attributes = True


class PageResponse(BaseModel):
    id: int
    url: str
    title: Optional[str]
    status_code: Optional[int]
    crawled_at: str
    content_type: Optional[str]
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]

    class Config:
        from_attributes = True


class CrawlRequest(BaseModel):
    urls: List[str]


class AnalysisRequest(BaseModel):
    page_ids: List[int]
    analysis_types: Optional[List[str]] = None


# Dependency to get database session
def get_db():
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


@router.get("/sites", response_model=List[SiteResponse])
async def get_sites(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db=Depends(get_db)
):
    """Get list of sites."""
    try:
        sites = db.query(Site).offset(skip).limit(limit).all()
        return sites
    except Exception as e:
        logger.error(f"Error getting sites: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving sites")


@router.get("/sites/{site_id}", response_model=SiteResponse)
async def get_site(site_id: int, db=Depends(get_db)):
    """Get a specific site."""
    try:
        site = db.query(Site).filter(Site.id == site_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        return site
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting site {site_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving site")


@router.get("/sites/{site_id}/pages", response_model=List[PageResponse])
async def get_site_pages(
    site_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db=Depends(get_db)
):
    """Get pages for a specific site."""
    try:
        # Check if site exists
        site = db.query(Site).filter(Site.id == site_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        
        pages = db.query(Page).filter(Page.site_id == site_id).offset(skip).limit(limit).all()
        return pages
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pages for site {site_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving pages")


@router.get("/pages/{page_id}")
async def get_page(page_id: int, db=Depends(get_db)):
    """Get a specific page with details."""
    try:
        page = db.query(Page).filter(Page.id == page_id).first()
        if not page:
            raise HTTPException(status_code=404, detail="Page not found")
        
        # Get media files
        media_files = db.query(MediaFile).filter(MediaFile.page_id == page_id).all()
        
        # Get content analyses
        analyses = db.query(ContentAnalysis).filter(ContentAnalysis.page_id == page_id).all()
        
        return {
            "page": page,
            "media_files": [
                {
                    "id": mf.id,
                    "url": mf.url,
                    "filename": mf.filename,
                    "file_type": mf.file_type,
                    "file_size": mf.file_size,
                    "is_flagged": mf.is_flagged
                }
                for mf in media_files
            ],
            "analyses": [
                {
                    "id": a.id,
                    "analysis_type": a.analysis_type,
                    "model_name": a.model_name,
                    "confidence_score": a.confidence_score,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                }
                for a in analyses
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting page {page_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving page")


@router.post("/crawl")
async def start_crawl(request: CrawlRequest):
    """Start crawling specified URLs."""
    try:
        crawler_manager = CrawlerManager()
        results = crawler_manager.crawl_sites(request.urls)
        crawler_manager.shutdown()
        
        return {
            "message": "Crawling completed",
            "results": results
        }
    except Exception as e:
        logger.error(f"Error starting crawl: {e}")
        raise HTTPException(status_code=500, detail="Error starting crawl")


@router.post("/analyze")
async def start_analysis(request: AnalysisRequest):
    """Start analysis for specified pages."""
    try:
        analysis_manager = AnalysisManager()
        results = []
        
        for page_id in request.page_ids:
            result = analysis_manager.analyze_page(page_id, request.analysis_types)
            results.append({
                "page_id": page_id,
                "success": result is not None,
                "result": result
            })
        
        return {
            "message": "Analysis completed",
            "results": results
        }
    except Exception as e:
        logger.error(f"Error starting analysis: {e}")
        raise HTTPException(status_code=500, detail="Error starting analysis")


@router.get("/stats")
async def get_stats(db=Depends(get_db)):
    """Get system statistics."""
    try:
        site_count = db.query(Site).count()
        page_count = db.query(Page).count()
        media_count = db.query(MediaFile).count()
        flagged_media_count = db.query(MediaFile).filter(MediaFile.is_flagged == True).count()
        
        return {
            "sites": site_count,
            "pages": page_count,
            "media_files": media_count,
            "flagged_media": flagged_media_count
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving statistics")


@router.get("/media/{media_id}/flagged")
async def get_flagged_media(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db=Depends(get_db)
):
    """Get flagged media files."""
    try:
        flagged_media = db.query(MediaFile).filter(
            MediaFile.is_flagged == True
        ).offset(skip).limit(limit).all()
        
        return [
            {
                "id": mf.id,
                "url": mf.url,
                "filename": mf.filename,
                "file_type": mf.file_type,
                "flagged_reason": mf.flagged_reason,
                "analysis_score": mf.analysis_score,
                "page_id": mf.page_id
            }
            for mf in flagged_media
        ]
    except Exception as e:
        logger.error(f"Error getting flagged media: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving flagged media")
