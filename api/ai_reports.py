"""API endpoints for AI-powered reporting system."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.session import get_session_manager
from database.models import UserQuery, GeneratedReport, QueryTemplate
from analysis.ai_reporter import AIReporter


# Request/Response models
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000, description="Natural language query")
    user_session: Optional[str] = Field(None, description="User session identifier")


class QueryResponse(BaseModel):
    status: str
    query_id: int
    cached: bool = False
    processing_time: Optional[float] = None
    reports: List[Dict[str, Any]] = []
    error: Optional[str] = None


class TemplateResponse(BaseModel):
    id: int
    name: str
    description: str
    category: str
    template_text: str
    example_query: Optional[str] = None
    usage_count: int


class RecentQueryResponse(BaseModel):
    id: int
    query_text: str
    query_type: str
    created_at: str
    processing_time: Optional[float]
    report_count: int


# Initialize router and services
router = APIRouter(prefix="/api/ai-reports", tags=["AI Reports"])
logger = logging.getLogger(__name__)


def get_ai_reporter() -> AIReporter:
    """Dependency to get AI reporter instance."""
    return AIReporter()


def get_client_info(request: Request) -> Dict[str, str]:
    """Extract client information from request."""
    return {
        'ip_address': request.client.host if request.client else None,
        'user_agent': request.headers.get('user-agent', '')[:500]  # Limit length
    }


@router.post("/query", response_model=QueryResponse)
async def submit_query(
    query_request: QueryRequest,
    request: Request,
    ai_reporter: AIReporter = Depends(get_ai_reporter)
):
    """Submit a natural language query for AI analysis."""
    
    try:
        client_info = get_client_info(request)
        
        # Process the query
        result = ai_reporter.process_user_query(
            query_text=query_request.query,
            user_session=query_request.user_session,
            ip_address=client_info['ip_address'],
            user_agent=client_info['user_agent']
        )
        
        return QueryResponse(**result)
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")


@router.get("/templates", response_model=List[TemplateResponse])
async def get_query_templates(ai_reporter: AIReporter = Depends(get_ai_reporter)):
    """Get available query templates."""
    
    try:
        templates = ai_reporter.get_query_templates()
        return [TemplateResponse(**template) for template in templates]
        
    except Exception as e:
        logger.error(f"Error fetching templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch templates")


@router.get("/recent", response_model=List[RecentQueryResponse])
async def get_recent_queries(
    limit: int = 20,
    ai_reporter: AIReporter = Depends(get_ai_reporter)
):
    """Get recent user queries."""
    
    try:
        if limit > 100:
            limit = 100  # Prevent excessive queries
            
        queries = ai_reporter.get_recent_queries(limit=limit)
        return [RecentQueryResponse(**query) for query in queries]
        
    except Exception as e:
        logger.error(f"Error fetching recent queries: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent queries")


@router.get("/report/{report_id}")
async def get_report(report_id: int):
    """Get a specific report by ID."""
    
    try:
        with get_session_manager().transaction() as db:
            report = db.query(GeneratedReport).filter(
                GeneratedReport.id == report_id
            ).first()
            
            if not report:
                raise HTTPException(status_code=404, detail="Report not found")
            
            # Increment view count
            report.view_count += 1
            db.commit()
            
            return {
                'id': report.id,
                'title': report.title,
                'description': report.description,
                'type': report.report_type,
                'format': report.format,
                'content': report.content,
                'summary': report.summary,
                'data': report.data_json,
                'record_count': report.record_count,
                'generation_time': report.generation_time,
                'created_at': report.created_at.isoformat() if report.created_at else None,
                'view_count': report.view_count,
                'query': {
                    'id': report.query.id,
                    'text': report.query.query_text,
                    'type': report.query.query_type
                } if report.query else None
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching report {report_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch report")


@router.get("/stats")
async def get_ai_reports_stats():
    """Get statistics about AI reports usage."""
    
    try:
        with get_session_manager().transaction() as db:
            # Query statistics
            total_queries = db.query(UserQuery).count()
            completed_queries = db.query(UserQuery).filter(
                UserQuery.status == 'completed'
            ).count()
            failed_queries = db.query(UserQuery).filter(
                UserQuery.status == 'failed'
            ).count()
            
            # Report statistics
            total_reports = db.query(GeneratedReport).count()
            total_views = db.query(
                func.sum(GeneratedReport.view_count)
            ).scalar() or 0
            
            # Recent activity (last 7 days)
            recent_queries = db.query(UserQuery).filter(
                UserQuery.created_at > datetime.utcnow() - timedelta(days=7)
            ).count()
            
            # Query types breakdown
            query_types = db.query(
                UserQuery.query_type,
                func.count(UserQuery.id).label('count')
            ).group_by(UserQuery.query_type).all()
            
            # Average processing time
            avg_processing_time = db.query(
                func.avg(UserQuery.processing_time)
            ).filter(UserQuery.processing_time.isnot(None)).scalar()
            
            return {
                'queries': {
                    'total': total_queries,
                    'completed': completed_queries,
                    'failed': failed_queries,
                    'success_rate': (completed_queries / total_queries * 100) if total_queries > 0 else 0,
                    'recent_7d': recent_queries
                },
                'reports': {
                    'total': total_reports,
                    'total_views': total_views,
                    'avg_views_per_report': (total_views / total_reports) if total_reports > 0 else 0
                },
                'performance': {
                    'avg_processing_time': float(avg_processing_time) if avg_processing_time else 0
                },
                'query_types': {qt.query_type: qt.count for qt in query_types}
            }
            
    except Exception as e:
        logger.error(f"Error fetching AI reports stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")


@router.delete("/query/{query_id}")
async def delete_query(query_id: int):
    """Delete a query and its associated reports."""
    
    try:
        with get_session_manager().transaction() as db:
            query = db.query(UserQuery).filter(UserQuery.id == query_id).first()
            
            if not query:
                raise HTTPException(status_code=404, detail="Query not found")
            
            # Delete the query (reports will be cascade deleted)
            db.delete(query)
            db.commit()
            
            return {"message": "Query deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting query {query_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete query")


# Initialize default query templates
async def initialize_default_templates():
    """Initialize default query templates if they don't exist."""
    
    default_templates = [
        {
            'name': 'Site Overview Report',
            'description': 'Generate a comprehensive overview of all crawled sites',
            'category': 'overview',
            'template_text': 'Generate a comprehensive report showing an overview of all crawled sites, including network distribution, activity levels, and key statistics.',
            'example_query': 'Generate a comprehensive report showing an overview of all crawled sites, including network distribution, activity levels, and key statistics.'
        },
        {
            'name': 'Network Comparison',
            'description': 'Compare activity between different networks (Tor, I2P, Clearnet)',
            'category': 'network',
            'template_text': 'Compare the crawling activity and content between {network1} and {network2} networks, showing differences in site types, content, and activity levels.',
            'example_query': 'Compare the crawling activity and content between Tor and I2P networks, showing differences in site types, content, and activity levels.'
        },
        {
            'name': 'Content Analysis',
            'description': 'Analyze content sentiment and topics across crawled pages',
            'category': 'content',
            'template_text': 'Analyze the sentiment and main topics found in content from {network_type} sites crawled in the last {time_period}.',
            'example_query': 'Analyze the sentiment and main topics found in content from Tor sites crawled in the last week.'
        },
        {
            'name': 'Media File Analysis',
            'description': 'Report on types and analysis of media files found',
            'category': 'media',
            'template_text': 'Generate a report on all media files found during crawling, including file types, sizes, flagged content, and analysis results.',
            'example_query': 'Generate a report on all media files found during crawling, including file types, sizes, flagged content, and analysis results.'
        },
        {
            'name': 'Security Insights',
            'description': 'Identify potentially suspicious or flagged content',
            'category': 'security',
            'template_text': 'Identify and report on potentially suspicious content, flagged media files, and security-related findings from the crawled data.',
            'example_query': 'Identify and report on potentially suspicious content, flagged media files, and security-related findings from the crawled data.'
        },
        {
            'name': 'Activity Timeline',
            'description': 'Show crawling activity over time',
            'category': 'timeline',
            'template_text': 'Show the timeline of crawling activity over the last {time_period}, including peaks, trends, and network-specific patterns.',
            'example_query': 'Show the timeline of crawling activity over the last month, including peaks, trends, and network-specific patterns.'
        },
        {
            'name': 'Domain Analysis',
            'description': 'Analyze specific domains or find top domains by activity',
            'category': 'domains',
            'template_text': 'Analyze the top {number} most active domains, showing page counts, content types, and activity patterns.',
            'example_query': 'Analyze the top 10 most active domains, showing page counts, content types, and activity patterns.'
        },
        {
            'name': 'Error Analysis',
            'description': 'Report on crawling errors and failed requests',
            'category': 'errors',
            'template_text': 'Generate a report on crawling errors, failed requests, and problematic sites, including error types and frequency.',
            'example_query': 'Generate a report on crawling errors, failed requests, and problematic sites, including error types and frequency.'
        }
    ]
    
    try:
        with get_session_manager().transaction() as db:
            # Check if templates already exist
            existing_count = db.query(QueryTemplate).count()
            
            if existing_count == 0:
                logger.info("Initializing default query templates...")
                
                for template_data in default_templates:
                    template = QueryTemplate(**template_data)
                    db.add(template)
                
                db.commit()
                logger.info(f"Initialized {len(default_templates)} default query templates")
            
    except Exception as e:
        logger.error(f"Error initializing default templates: {e}")


# Initialize templates on module import
import asyncio
try:
    asyncio.create_task(initialize_default_templates())
except RuntimeError:
    # If no event loop is running, we'll initialize later
    pass
