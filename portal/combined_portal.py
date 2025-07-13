"""
Combined Portal for Noctipede System
Merges basic portal functionality with enhanced metrics
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Import the combined metrics collector
from portal.combined_metrics_collector import CombinedMetricsCollector

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CombinedPortal:
    """Combined portal with merged metrics functionality"""
    
    def __init__(self):
        self.app = FastAPI(title="Noctipede Combined Portal")
        self.metrics_collector = CombinedMetricsCollector()
        self.templates = Jinja2Templates(directory="/app/portal/templates")
        
        # Setup routes
        self.setup_routes()
        
        # Cache for metrics
        self.metrics_cache = {}
        self.last_update = None
        self.cache_duration = 30  # seconds
    
    def setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard(request: Request):
            """Main dashboard page"""
            return self.templates.TemplateResponse(
                "combined_dashboard.html", 
                {"request": request}
            )
        
        @self.app.get("/api/metrics")
        async def get_metrics():
            """Get all system metrics"""
            try:
                # Check cache first
                now = datetime.now()
                if (self.last_update and 
                    (now - self.last_update).total_seconds() < self.cache_duration and
                    self.metrics_cache):
                    return JSONResponse(self.metrics_cache)
                
                # Collect fresh metrics
                metrics = await self.metrics_collector.collect_all_metrics()
                
                # Update cache
                self.metrics_cache = metrics
                self.last_update = now
                
                return JSONResponse(metrics)
                
            except Exception as e:
                logger.error(f"Error getting metrics: {e}")
                return JSONResponse(
                    {"error": str(e), "timestamp": datetime.now().isoformat()},
                    status_code=500
                )
        
        @self.app.get("/api/crawler")
        async def get_crawler_metrics():
            """Get detailed crawler metrics"""
            try:
                crawler_metrics = await self.metrics_collector.collect_combined_crawler_metrics()
                return JSONResponse(crawler_metrics)
            except Exception as e:
                logger.error(f"Error getting crawler metrics: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.app.get("/api/system")
        async def get_system_metrics():
            """Get system metrics"""
            try:
                system_metrics = await self.metrics_collector.collect_system_metrics()
                return JSONResponse(system_metrics)
            except Exception as e:
                logger.error(f"Error getting system metrics: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.app.get("/api/health")
        async def health_check():
            """Health check endpoint"""
            return JSONResponse({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "combined-portal-1.0"
            })
    
    def run(self, host: str = "0.0.0.0", port: int = 8080):
        """Run the portal server"""
        logger.info(f"Starting Combined Noctipede Portal on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)

def main():
    """Main entry point"""
    portal = CombinedPortal()
    
    # Get configuration from environment
    host = os.getenv('WEB_SERVER_HOST', '0.0.0.0')
    port = int(os.getenv('WEB_SERVER_PORT', 8080))
    
    portal.run(host=host, port=port)

if __name__ == "__main__":
    main()
