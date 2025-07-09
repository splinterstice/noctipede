"""
Unified Portal for Noctipede System
Serves all three dashboard variants: Basic, Enhanced, and Combined
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

class UnifiedPortal:
    """Unified portal serving all dashboard variants"""
    
    def __init__(self):
        self.app = FastAPI(title="Noctipede Unified Portal")
        self.metrics_collector = CombinedMetricsCollector()
        self.templates = Jinja2Templates(directory="/app/portal/templates")
        
        # Setup routes
        self.setup_routes()
        
        # Cache for metrics
        self.metrics_cache = {}
        self.last_update = None
        self.cache_duration = 30  # seconds
    
    def setup_routes(self):
        """Setup FastAPI routes for all dashboard variants"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_selector(request: Request):
            """Dashboard selector page"""
            return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Noctipede Portal - Dashboard Selection</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #fff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .container {
            text-align: center;
            max-width: 800px;
            padding: 2rem;
        }
        
        .header {
            margin-bottom: 3rem;
        }
        
        .header h1 {
            font-size: 3rem;
            margin-bottom: 1rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        .dashboards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 2rem;
            margin-top: 2rem;
        }
        
        .dashboard-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 2rem;
            text-decoration: none;
            color: white;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }
        
        .dashboard-card:hover {
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.2);
            border-color: rgba(255, 255, 255, 0.3);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .dashboard-card h3 {
            font-size: 1.5rem;
            margin-bottom: 1rem;
        }
        
        .dashboard-card p {
            opacity: 0.8;
            line-height: 1.6;
        }
        
        .icon {
            font-size: 3rem;
            margin-bottom: 1rem;
            display: block;
        }
        
        .status {
            margin-top: 2rem;
            padding: 1rem;
            background: rgba(0, 255, 0, 0.1);
            border-radius: 10px;
            border: 1px solid rgba(0, 255, 0, 0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🕷️ Noctipede Portal</h1>
            <p>Deep Web Analysis System - Choose Your Dashboard</p>
        </div>
        
        <div class="dashboards">
            <a href="/basic" class="dashboard-card">
                <span class="icon">📊</span>
                <h3>Basic Dashboard</h3>
                <p>Simple, clean interface with essential metrics. Perfect for quick status checks and overview monitoring.</p>
            </a>
            
            <a href="/enhanced" class="dashboard-card">
                <span class="icon">🚀</span>
                <h3>Enhanced Dashboard</h3>
                <p>Advanced metrics with detailed analytics, AI reports, and comprehensive system monitoring.</p>
            </a>
            
            <a href="/combined" class="dashboard-card">
                <span class="icon">⚡</span>
                <h3>Combined Dashboard</h3>
                <p>Best of both worlds - comprehensive metrics with intelligent fallbacks and real-time updates.</p>
            </a>
        </div>
        
        <div class="status">
            <strong>✅ System Status: All Dashboards Online</strong><br>
            API Endpoints: /api/metrics | /api/health | /api/crawler | /api/system | /api/readiness
        </div>
    </div>
</body>
</html>
            """)
        
        @self.app.get("/basic", response_class=HTMLResponse)
        async def basic_dashboard(request: Request):
            """Basic dashboard page"""
            return self.templates.TemplateResponse(
                "dashboard.html", 
                {"request": request, "title": "Noctipede Basic Dashboard"}
            )
        
        @self.app.get("/enhanced", response_class=HTMLResponse)
        async def enhanced_dashboard(request: Request):
            """Enhanced dashboard page"""
            return self.templates.TemplateResponse(
                "enhanced_dashboard.html", 
                {"request": request}
            )
        
        @self.app.get("/combined", response_class=HTMLResponse)
        async def combined_dashboard(request: Request):
            """Combined dashboard page"""
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
        
        @self.app.get("/api/readiness")
        async def get_readiness():
            """Get crawler readiness status"""
            try:
                # Get network metrics to check readiness
                network_metrics = await self.metrics_collector.collect_network_metrics()
                overall_readiness = network_metrics.get('overall_readiness', {})
                
                ready_for_crawling = overall_readiness.get('ready_for_crawling', False)
                
                response_data = {
                    'ready_for_crawling': ready_for_crawling,
                    'timestamp': datetime.now().isoformat(),
                    'readiness_details': overall_readiness,
                    'network_status': {
                        'tor': {
                            'ready': network_metrics.get('tor', {}).get('ready_for_crawling', False),
                            'status': network_metrics.get('tor', {}).get('status', 'unknown')
                        },
                        'i2p': {
                            'ready': network_metrics.get('i2p', {}).get('ready_for_crawling', False),
                            'status': network_metrics.get('i2p', {}).get('status', 'unknown'),
                            'internal_proxies': network_metrics.get('i2p', {}).get('internal_proxies', {})
                        }
                    }
                }
                
                # Return appropriate HTTP status code
                status_code = 200 if ready_for_crawling else 503
                return JSONResponse(response_data, status_code=status_code)
                
            except Exception as e:
                logger.error(f"Error getting readiness status: {e}")
                return JSONResponse({
                    'ready_for_crawling': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }, status_code=500)
        
        @self.app.get("/api/health")
        async def health_check():
            """Health check endpoint"""
            return JSONResponse({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "unified-portal-1.0",
                "dashboards": ["basic", "enhanced", "combined"]
            })
    
    def run(self, host: str = "0.0.0.0", port: int = 8080):
        """Run the portal server"""
        logger.info(f"Starting Unified Noctipede Portal on {host}:{port}")
        logger.info("Available dashboards: /basic, /enhanced, /combined")
        uvicorn.run(self.app, host=host, port=port)

def main():
    """Main entry point"""
    portal = UnifiedPortal()
    
    # Get configuration from environment
    host = os.getenv('WEB_SERVER_HOST', '0.0.0.0')
    port = int(os.getenv('WEB_SERVER_PORT', 8080))
    
    portal.run(host=host, port=port)

if __name__ == "__main__":
    main()
