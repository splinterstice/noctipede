"""AI Reports API endpoints."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from core import get_logger
from ai_reports import (
    DatasetManager, QueryEngine, MemeCLIPService, 
    ScreenshotService, ReportGenerator
)

logger = get_logger(__name__)
router = APIRouter(prefix="/ai-reports", tags=["AI Reports"])

# Initialize services
dataset_manager = DatasetManager()
query_engine = QueryEngine()
memeclip_service = MemeCLIPService()
screenshot_service = ScreenshotService()
report_generator = ReportGenerator()


# Pydantic models for API
class DatasetCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    partition_strategy: Optional[str] = "by_domain"
    schema: Optional[Dict[str, Any]] = {}
    auto_partition: Optional[bool] = True
    created_by: Optional[str] = "api_user"


class DatasetUpdateRequest(BaseModel):
    description: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class QueryRequest(BaseModel):
    sql: str
    dataset_ids: Optional[List[int]] = None
    cache_key: Optional[str] = None


class MemeCLIPAnalysisRequest(BaseModel):
    image_paths: List[str]
    dataset_id: Optional[int] = None


class ScreenshotRequest(BaseModel):
    url: str
    site_id: int
    page_id: Optional[int] = None
    dataset_id: Optional[int] = None


class BatchScreenshotRequest(BaseModel):
    urls_info: List[Dict[str, Any]]


class ReportGenerationRequest(BaseModel):
    query_result: Dict[str, Any]
    report_config: Dict[str, Any]


# Dataset Management Endpoints
@router.post("/datasets")
async def create_dataset(request: DatasetCreateRequest):
    """Create a new dataset."""
    try:
        dataset_id = dataset_manager.create_dataset(request.dict())
        if dataset_id:
            return {"success": True, "dataset_id": dataset_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to create dataset")
    except Exception as e:
        logger.error(f"Dataset creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/datasets")
async def list_datasets(status: Optional[str] = Query(None)):
    """List all datasets."""
    try:
        datasets = dataset_manager.list_datasets(status)
        return {"success": True, "datasets": datasets}
    except Exception as e:
        logger.error(f"Failed to list datasets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: int):
    """Get dataset details."""
    try:
        dataset = dataset_manager.get_dataset(dataset_id)
        if dataset:
            return {"success": True, "dataset": dataset}
        else:
            raise HTTPException(status_code=404, detail="Dataset not found")
    except Exception as e:
        logger.error(f"Failed to get dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/datasets/{dataset_id}")
async def update_dataset(dataset_id: int, request: DatasetUpdateRequest):
    """Update dataset configuration."""
    try:
        success = dataset_manager.update_dataset(dataset_id, request.dict(exclude_unset=True))
        if success:
            return {"success": True, "message": "Dataset updated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Dataset not found")
    except Exception as e:
        logger.error(f"Dataset update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: int):
    """Delete dataset and cleanup storage."""
    try:
        success = dataset_manager.delete_dataset(dataset_id)
        if success:
            return {"success": True, "message": "Dataset deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Dataset not found")
    except Exception as e:
        logger.error(f"Dataset deletion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/datasets/{dataset_id}/export-hive")
async def export_dataset_to_hive(dataset_id: int, background_tasks: BackgroundTasks):
    """Export dataset to HIVE format."""
    try:
        # Run export in background
        background_tasks.add_task(dataset_manager.export_to_hive, dataset_id)
        return {"success": True, "message": "HIVE export started in background"}
    except Exception as e:
        logger.error(f"HIVE export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/datasets/{dataset_id}/populate")
async def populate_dataset(dataset_id: int, filters: Optional[Dict[str, Any]] = None):
    """Populate dataset with crawled data."""
    try:
        record_count = dataset_manager.populate_from_crawl_data(dataset_id, filters or {})
        return {"success": True, "records_processed": record_count}
    except Exception as e:
        logger.error(f"Dataset population failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Query Engine Endpoints
@router.post("/query")
async def execute_query(request: QueryRequest):
    """Execute SQL query against datasets."""
    try:
        result = query_engine.execute_query(
            request.sql, 
            request.dataset_ids, 
            request.cache_key
        )
        return result
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables")
async def get_available_tables(dataset_id: Optional[int] = Query(None)):
    """Get list of available tables/datasets for querying."""
    try:
        tables = query_engine.get_available_tables(dataset_id)
        return {"success": True, "tables": tables}
    except Exception as e:
        logger.error(f"Failed to get tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{dataset_id}/schema")
async def get_table_schema(dataset_id: int):
    """Get detailed schema information for a dataset."""
    try:
        schema = query_engine.get_table_schema(dataset_id)
        if schema:
            return {"success": True, "schema": schema}
        else:
            raise HTTPException(status_code=404, detail="Dataset not found")
    except Exception as e:
        logger.error(f"Failed to get table schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query-history")
async def get_query_history(limit: int = Query(50, ge=1, le=100)):
    """Get recent query history."""
    try:
        history = query_engine.get_query_history(limit)
        return {"success": True, "history": history}
    except Exception as e:
        logger.error(f"Failed to get query history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# MemeCLIP Integration Endpoints
@router.post("/memeclip/analyze")
async def analyze_image_memeclip(image_path: str, dataset_id: Optional[int] = None):
    """Analyze single image using MemeCLIP."""
    try:
        result = memeclip_service.analyze_image(image_path, dataset_id)
        return {"success": True, "analysis": result}
    except Exception as e:
        logger.error(f"MemeCLIP analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memeclip/batch-analyze")
async def batch_analyze_memeclip(request: MemeCLIPAnalysisRequest, background_tasks: BackgroundTasks):
    """Batch analyze images using MemeCLIP."""
    try:
        # Run analysis in background for large batches
        if len(request.image_paths) > 10:
            background_tasks.add_task(
                memeclip_service.batch_analyze, 
                request.image_paths, 
                request.dataset_id
            )
            return {"success": True, "message": "Batch analysis started in background"}
        else:
            results = memeclip_service.batch_analyze(request.image_paths, request.dataset_id)
            return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Batch MemeCLIP analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memeclip/results/{dataset_id}")
async def get_memeclip_results(dataset_id: int, limit: int = Query(100, ge=1, le=500)):
    """Get MemeCLIP analysis results for a dataset."""
    try:
        results = memeclip_service.get_analysis_results(dataset_id, limit)
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Failed to get MemeCLIP results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memeclip/search-similar")
async def search_similar_images(
    query_image_path: str, 
    dataset_id: int, 
    threshold: float = Query(0.8, ge=0.0, le=1.0)
):
    """Search for similar images in a dataset."""
    try:
        results = memeclip_service.search_similar_images(query_image_path, dataset_id, threshold)
        return {"success": True, "similar_images": results}
    except Exception as e:
        logger.error(f"Similar image search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Screenshot Service Endpoints
@router.post("/screenshots/capture")
async def capture_screenshot(request: ScreenshotRequest):
    """Capture screenshot of a website."""
    try:
        result = screenshot_service.capture_screenshot(
            request.url, 
            request.site_id, 
            request.page_id, 
            request.dataset_id
        )
        if result:
            return {"success": True, "screenshot": result}
        else:
            raise HTTPException(status_code=400, detail="Screenshot capture failed")
    except Exception as e:
        logger.error(f"Screenshot capture failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screenshots/batch")
async def batch_capture_screenshots(request: BatchScreenshotRequest, background_tasks: BackgroundTasks):
    """Batch capture screenshots."""
    try:
        # Run in background for large batches
        if len(request.urls_info) > 5:
            background_tasks.add_task(screenshot_service.capture_batch, request.urls_info)
            return {"success": True, "message": "Batch screenshot capture started in background"}
        else:
            results = await screenshot_service.capture_batch(request.urls_info)
            return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Batch screenshot capture failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screenshots/site/{site_id}")
async def get_site_screenshots(site_id: int, limit: int = Query(10, ge=1, le=50)):
    """Get screenshots for a specific site."""
    try:
        screenshots = screenshot_service.get_site_screenshots(site_id, limit)
        return {"success": True, "screenshots": screenshots}
    except Exception as e:
        logger.error(f"Failed to get site screenshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screenshots/dataset/{dataset_id}")
async def get_dataset_screenshots(dataset_id: int, limit: int = Query(50, ge=1, le=200)):
    """Get screenshots for a specific dataset."""
    try:
        screenshots = screenshot_service.get_dataset_screenshots(dataset_id, limit)
        return {"success": True, "screenshots": screenshots}
    except Exception as e:
        logger.error(f"Failed to get dataset screenshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/screenshots/cleanup")
async def cleanup_old_screenshots(days_old: int = Query(30, ge=1, le=365)):
    """Cleanup screenshots older than specified days."""
    try:
        cleaned_count = screenshot_service.cleanup_old_screenshots(days_old)
        return {"success": True, "cleaned_count": cleaned_count}
    except Exception as e:
        logger.error(f"Screenshot cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Report Generation Endpoints
@router.post("/reports/generate")
async def generate_report(request: ReportGenerationRequest, background_tasks: BackgroundTasks):
    """Generate AI-powered report from query results."""
    try:
        # Run report generation in background for complex reports
        if len(request.query_result.get('data', [])) > 100:
            background_tasks.add_task(
                report_generator.generate_report, 
                request.query_result, 
                request.report_config
            )
            return {"success": True, "message": "Report generation started in background"}
        else:
            result = report_generator.generate_report(request.query_result, request.report_config)
            return result
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/summary/{dataset_id}")
async def generate_summary_report(dataset_id: int, filters: Optional[Dict[str, Any]] = None):
    """Generate summary report for a dataset."""
    try:
        result = report_generator.generate_summary_report(dataset_id, filters or {})
        return result
    except Exception as e:
        logger.error(f"Summary report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/security/{dataset_id}")
async def generate_security_report(dataset_id: int, threat_indicators: Optional[List[str]] = None):
    """Generate security-focused report."""
    try:
        result = report_generator.generate_security_report(dataset_id, threat_indicators or [])
        return result
    except Exception as e:
        logger.error(f"Security report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health and Status Endpoints
@router.get("/health")
async def health_check():
    """Health check for AI Reports services."""
    try:
        status = {
            "ai_reports_service": "healthy",
            "services": {
                "dataset_manager": "available",
                "query_engine": "available",
                "memeclip_service": "available" if memeclip_service else "unavailable",
                "screenshot_service": "available" if screenshot_service.screenshot_enabled else "disabled",
                "report_generator": "available"
            }
        }
        return status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_service_status():
    """Get detailed status of AI Reports services."""
    try:
        # Get dataset statistics
        datasets = dataset_manager.list_datasets()
        
        # Get query engine status
        tables = query_engine.get_available_tables()
        
        status = {
            "timestamp": "2024-01-01T00:00:00Z",  # This would be datetime.now().isoformat()
            "datasets": {
                "total": len(datasets),
                "active": len([d for d in datasets if d.get('status') == 'active'])
            },
            "tables": {
                "available": len(tables)
            },
            "services": {
                "memeclip": {
                    "enabled": bool(memeclip_service),
                    "model_path": getattr(memeclip_service, 'model_path', None) if memeclip_service else None
                },
                "screenshots": {
                    "enabled": screenshot_service.screenshot_enabled if screenshot_service else False,
                    "driver_pool_size": len(screenshot_service.driver_pool) if screenshot_service else 0
                },
                "query_engine": {
                    "type": query_engine.engine_type,
                    "cache_size": len(query_engine.query_cache)
                }
            }
        }
        
        return {"success": True, "status": status}
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
