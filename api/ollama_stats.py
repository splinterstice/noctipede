"""API endpoints for Ollama usage statistics."""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from datetime import datetime

from analysis.ollama_monitor import get_ollama_monitor
from core import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/ollama", tags=["ollama-stats"])

@router.get("/stats/summary")
async def get_ollama_summary(
    hours: int = Query(24, description="Hours to look back for statistics", ge=1, le=168)
) -> Dict[str, Any]:
    """Get overall Ollama usage summary statistics."""
    try:
        monitor = get_ollama_monitor()
        stats = monitor.get_summary_stats(hours=hours)
        
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting Ollama summary stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/models")
async def get_model_stats(
    model: Optional[str] = Query(None, description="Specific model name (optional)"),
    hours: int = Query(24, description="Hours to look back for statistics", ge=1, le=168)
) -> Dict[str, Any]:
    """Get statistics for all models or a specific model."""
    try:
        monitor = get_ollama_monitor()
        stats = monitor.get_model_stats(model_name=model, hours=hours)
        
        return {
            "success": True,
            "data": stats,
            "model_filter": model,
            "time_period_hours": hours,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting model stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/memory")
async def get_memory_stats() -> Dict[str, Any]:
    """Get current in-memory statistics (since last restart)."""
    try:
        monitor = get_ollama_monitor()
        stats = monitor.get_memory_stats()
        
        return {
            "success": True,
            "data": stats,
            "note": "Statistics since last application restart",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/models/{model_name}")
async def get_specific_model_stats(
    model_name: str,
    hours: int = Query(24, description="Hours to look back for statistics", ge=1, le=168)
) -> Dict[str, Any]:
    """Get detailed statistics for a specific model."""
    try:
        monitor = get_ollama_monitor()
        stats = monitor.get_model_stats(model_name=model_name, hours=hours)
        
        if not stats:
            raise HTTPException(
                status_code=404, 
                detail=f"No statistics found for model '{model_name}' in the last {hours} hours"
            )
        
        return {
            "success": True,
            "data": stats,
            "model_name": model_name,
            "time_period_hours": hours,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats for model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/maintenance/cleanup")
async def cleanup_old_records(
    days: int = Query(30, description="Delete records older than this many days", ge=1, le=365)
) -> Dict[str, Any]:
    """Clean up old usage records to prevent database bloat."""
    try:
        monitor = get_ollama_monitor()
        deleted_count = monitor.clear_old_records(days=days)
        
        return {
            "success": True,
            "message": f"Cleaned up {deleted_count} old records",
            "deleted_records": deleted_count,
            "cutoff_days": days,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error cleaning up old records: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def ollama_monitor_health() -> Dict[str, Any]:
    """Check if Ollama monitoring is working."""
    try:
        monitor = get_ollama_monitor()
        memory_stats = monitor.get_memory_stats()
        
        return {
            "success": True,
            "status": "healthy",
            "models_tracked": len(memory_stats),
            "total_requests_in_memory": sum(
                stats.get('total_requests', 0) for stats in memory_stats.values()
            ),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Ollama monitor health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
