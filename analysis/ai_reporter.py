"""AI-powered reporting and query service for Noctipede."""

import json
import hashlib
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, func, desc, asc
import requests

from database.models import (
    Site, Page, MediaFile, ContentAnalysis, Entity, TopicCluster,
    UserQuery, GeneratedReport, QueryTemplate
)
from database.session import get_session_manager
from config import get_settings


class AIReporter:
    """AI-powered reporting service for analyzing scraped data."""
    
    def __init__(self):
        try:
            self.settings = get_settings()
            self.ollama_endpoint = self.settings.ollama_endpoint
            self.text_model = self.settings.ollama_text_model
        except:
            # Fallback configuration if settings not available
            self.ollama_endpoint = "http://localhost:11434/api/generate"
            self.text_model = "llama3.1:8b"
        
        self.logger = logging.getLogger(__name__)
        
    def process_user_query(self, query_text: str, user_session: str = None, 
                          ip_address: str = None, user_agent: str = None) -> Dict[str, Any]:
        """Process a user's natural language query and generate a report."""
        
        # Create query hash for deduplication
        query_hash = hashlib.sha256(query_text.encode()).hexdigest()
        
        with get_session_manager().transaction() as db:
            # Check if we've seen this exact query recently
            recent_query = db.query(UserQuery).filter(
                UserQuery.query_hash == query_hash,
                UserQuery.created_at > datetime.utcnow() - timedelta(hours=1),
                UserQuery.status == 'completed'
            ).first()
            
            if recent_query and recent_query.reports:
                self.logger.info(f"Returning cached result for query hash: {query_hash}")
                return {
                    'status': 'completed',
                    'query_id': recent_query.id,
                    'cached': True,
                    'reports': [self._serialize_report(report) for report in recent_query.reports]
                }
            
            # Create new query record
            user_query = UserQuery(
                query_text=query_text,
                query_type=self._classify_query(query_text),
                query_hash=query_hash,
                user_session=user_session,
                ip_address=ip_address,
                user_agent=user_agent,
                status='processing'
            )
            db.add(user_query)
            db.commit()
            
            try:
                # Process the query
                start_time = time.time()
                result = self._process_query_with_ai(user_query, db)
                processing_time = time.time() - start_time
                
                # Update query status
                user_query.processed_at = datetime.utcnow()
                user_query.processing_time = processing_time
                user_query.status = 'completed'
                db.commit()
                
                return {
                    'status': 'completed',
                    'query_id': user_query.id,
                    'cached': False,
                    'processing_time': processing_time,
                    'reports': result
                }
                
            except Exception as e:
                self.logger.error(f"Error processing query {user_query.id}: {e}")
                user_query.status = 'failed'
                user_query.error_message = str(e)
                db.commit()
                
                return {
                    'status': 'failed',
                    'query_id': user_query.id,
                    'error': str(e)
                }
    
    def _classify_query(self, query_text: str) -> str:
        """Classify the type of query based on keywords."""
        query_lower = query_text.lower()
        
        if any(word in query_lower for word in ['report', 'summary', 'overview']):
            return 'report'
        elif any(word in query_lower for word in ['analyze', 'analysis', 'sentiment']):
            return 'analysis'
        elif any(word in query_lower for word in ['search', 'find', 'show', 'list']):
            return 'search'
        elif any(word in query_lower for word in ['chart', 'graph', 'visualization']):
            return 'visualization'
        elif any(word in query_lower for word in ['compare', 'comparison', 'versus']):
            return 'comparison'
        else:
            return 'general'
    
    def _process_query_with_ai(self, user_query: UserQuery, db: Session) -> List[Dict[str, Any]]:
        """Process query using AI and generate appropriate reports."""
        
        # Get relevant data context
        data_context = self._get_data_context(db)
        
        # Generate AI prompt
        ai_prompt = self._generate_ai_prompt(user_query.query_text, data_context)
        user_query.ai_prompt = ai_prompt
        user_query.ai_model = self.text_model
        
        # Query AI
        ai_response = self._query_ollama(ai_prompt)
        user_query.ai_response = ai_response
        
        # Parse AI response and generate reports
        reports = self._generate_reports_from_ai_response(user_query, ai_response, db)
        
        return [self._serialize_report(report) for report in reports]
    
    def _get_data_context(self, db: Session) -> Dict[str, Any]:
        """Get current data context for AI prompt generation."""
        
        # Get basic statistics
        total_sites = db.query(func.count(Site.id)).scalar()
        total_pages = db.query(func.count(Page.id)).scalar()
        total_media = db.query(func.count(MediaFile.id)).scalar()
        
        # Get network breakdown
        network_stats = db.query(
            Site.network_type, 
            func.count(Site.id).label('count')
        ).group_by(Site.network_type).all()
        
        # Get recent activity
        recent_pages = db.query(func.count(Page.id)).filter(
            Page.crawled_at > datetime.utcnow() - timedelta(days=7)
        ).scalar()
        
        # Get top domains
        top_domains = db.query(
            Site.domain,
            func.count(Page.id).label('page_count')
        ).join(Page).group_by(Site.domain).order_by(desc('page_count')).limit(10).all()
        
        # Get content analysis stats
        analysis_stats = db.query(
            ContentAnalysis.analysis_type,
            func.count(ContentAnalysis.id).label('count')
        ).group_by(ContentAnalysis.analysis_type).all()
        
        return {
            'total_sites': total_sites,
            'total_pages': total_pages,
            'total_media': total_media,
            'recent_pages_7d': recent_pages,
            'network_breakdown': {stat.network_type: stat.count for stat in network_stats},
            'top_domains': [{'domain': d.domain, 'pages': d.page_count} for d in top_domains],
            'analysis_types': {stat.analysis_type: stat.count for stat in analysis_stats}
        }
    
    def _generate_ai_prompt(self, query_text: str, data_context: Dict[str, Any]) -> str:
        """Generate a comprehensive AI prompt for query processing."""
        
        prompt = f"""You are an AI assistant helping analyze web crawling data from the Noctipede system. 

CURRENT DATA CONTEXT:
- Total Sites: {data_context['total_sites']}
- Total Pages: {data_context['total_pages']}
- Total Media Files: {data_context['total_media']}
- Recent Pages (7 days): {data_context['recent_pages_7d']}
- Network Types: {json.dumps(data_context['network_breakdown'], indent=2)}
- Top Domains: {json.dumps(data_context['top_domains'][:5], indent=2)}

AVAILABLE DATA TABLES:
1. Sites: Contains website information (URL, domain, network type, crawl status)
2. Pages: Contains crawled page content (title, content, status codes, timestamps)
3. MediaFiles: Contains images, videos, documents found on pages
4. ContentAnalysis: Contains AI analysis results (sentiment, topics, moderation)
5. Entities: Contains extracted entities (people, organizations, locations)
6. TopicClusters: Contains topic clustering results

USER QUERY: "{query_text}"

Please analyze this query and provide:
1. INTERPRETATION: What the user is asking for
2. DATA_NEEDED: Which tables and fields are relevant
3. ANALYSIS_TYPE: What kind of analysis or report would be most helpful
4. REPORT_STRUCTURE: How the results should be presented
5. SQL_HINTS: Suggestions for database queries (if applicable)

Respond in JSON format with these sections. Be specific and actionable."""

        return prompt
    
    def _query_ollama(self, prompt: str) -> str:
        """Send query to Ollama AI service."""
        try:
            response = requests.post(
                self.ollama_endpoint,
                json={
                    'model': self.text_model,
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'temperature': 0.7,
                        'top_p': 0.9,
                        'max_tokens': 2000
                    }
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json().get('response', '')
        except Exception as e:
            self.logger.error(f"Error querying Ollama: {e}")
            raise Exception(f"AI service unavailable: {e}")
    
    def _generate_reports_from_ai_response(self, user_query: UserQuery, ai_response: str, 
                                         db: Session) -> List[GeneratedReport]:
        """Generate reports based on AI response and actual data queries."""
        
        reports = []
        
        try:
            # Try to parse AI response as JSON
            ai_analysis = json.loads(ai_response)
        except json.JSONDecodeError:
            # Fallback: create a simple text report
            ai_analysis = {
                'INTERPRETATION': 'General query analysis',
                'ANALYSIS_TYPE': 'text_summary',
                'REPORT_STRUCTURE': 'Simple text response'
            }
        
        # Generate main report based on AI analysis
        main_report = self._create_data_report(user_query, ai_analysis, db)
        reports.append(main_report)
        
        # Generate additional reports based on query type
        if user_query.query_type == 'visualization':
            chart_report = self._create_chart_report(user_query, ai_analysis, db)
            if chart_report:
                reports.append(chart_report)
        
        return reports
    
    def _create_data_report(self, user_query: UserQuery, ai_analysis: Dict[str, Any], 
                           db: Session) -> GeneratedReport:
        """Create the main data report based on AI analysis."""
        
        start_time = time.time()
        
        # Execute relevant database queries based on AI analysis
        report_data = self._execute_data_queries(ai_analysis, db)
        
        # Generate HTML report content
        html_content = self._generate_html_report(user_query.query_text, ai_analysis, report_data)
        
        # Create report record
        report = GeneratedReport(
            query_id=user_query.id,
            title=f"Analysis: {user_query.query_text[:100]}...",
            description=ai_analysis.get('INTERPRETATION', 'Data analysis report'),
            report_type='detailed',
            format='html',
            content=html_content,
            data_json=report_data,
            summary=self._generate_summary(report_data),
            data_sources=['sites', 'pages', 'media_files'],
            record_count=report_data.get('total_records', 0),
            generation_time=time.time() - start_time
        )
        
        db.add(report)
        db.commit()
        
        return report
    
    def _execute_data_queries(self, ai_analysis: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Execute database queries based on AI analysis."""
        
        data = {}
        
        # Basic statistics
        data['site_stats'] = {
            'total': db.query(func.count(Site.id)).scalar(),
            'by_network': dict(db.query(Site.network_type, func.count(Site.id))
                              .group_by(Site.network_type).all()),
            'active': db.query(func.count(Site.id)).filter(Site.status == 'active').scalar()
        }
        
        data['page_stats'] = {
            'total': db.query(func.count(Page.id)).scalar(),
            'recent_24h': db.query(func.count(Page.id)).filter(
                Page.crawled_at > datetime.utcnow() - timedelta(days=1)
            ).scalar(),
            'by_status_code': dict(db.query(Page.status_code, func.count(Page.id))
                                  .group_by(Page.status_code).all())
        }
        
        data['media_stats'] = {
            'total': db.query(func.count(MediaFile.id)).scalar(),
            'by_type': dict(db.query(MediaFile.file_type, func.count(MediaFile.id))
                           .group_by(MediaFile.file_type).all()),
            'flagged': db.query(func.count(MediaFile.id)).filter(MediaFile.is_flagged == True).scalar()
        }
        
        # Top domains
        data['top_domains'] = [
            {'domain': d.domain, 'page_count': d.page_count}
            for d in db.query(Site.domain, func.count(Page.id).label('page_count'))
            .join(Page).group_by(Site.domain).order_by(desc('page_count')).limit(10).all()
        ]
        
        # Recent activity
        data['recent_activity'] = [
            {
                'date': activity.date,
                'pages_crawled': activity.count
            }
            for activity in db.query(
                func.date(Page.crawled_at).label('date'),
                func.count(Page.id).label('count')
            ).filter(
                Page.crawled_at > datetime.utcnow() - timedelta(days=30)
            ).group_by(func.date(Page.crawled_at)).order_by(desc('date')).limit(30).all()
        ]
        
        data['total_records'] = sum([
            data['site_stats']['total'],
            data['page_stats']['total'],
            data['media_stats']['total']
        ])
        
        return data
    
    def _generate_html_report(self, query_text: str, ai_analysis: Dict[str, Any], 
                             report_data: Dict[str, Any]) -> str:
        """Generate HTML report content."""
        
        html = f"""
        <div class="ai-report">
            <div class="report-header">
                <h2>Analysis Report</h2>
                <p class="query-text"><strong>Query:</strong> {query_text}</p>
                <p class="generated-at">Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            
            <div class="ai-interpretation">
                <h3>AI Interpretation</h3>
                <p>{ai_analysis.get('INTERPRETATION', 'Analysis of your query.')}</p>
            </div>
            
            <div class="data-summary">
                <h3>Data Overview</h3>
                <div class="stats-grid">
                    <div class="stat-card">
                        <h4>Sites</h4>
                        <p class="stat-number">{report_data['site_stats']['total']}</p>
                        <p class="stat-detail">Active: {report_data['site_stats']['active']}</p>
                    </div>
                    <div class="stat-card">
                        <h4>Pages</h4>
                        <p class="stat-number">{report_data['page_stats']['total']}</p>
                        <p class="stat-detail">Last 24h: {report_data['page_stats']['recent_24h']}</p>
                    </div>
                    <div class="stat-card">
                        <h4>Media Files</h4>
                        <p class="stat-number">{report_data['media_stats']['total']}</p>
                        <p class="stat-detail">Flagged: {report_data['media_stats']['flagged']}</p>
                    </div>
                </div>
            </div>
            
            <div class="network-breakdown">
                <h3>Network Distribution</h3>
                <ul>
        """
        
        for network, count in report_data['site_stats']['by_network'].items():
            html += f"<li>{network}: {count} sites</li>"
        
        html += """
                </ul>
            </div>
            
            <div class="top-domains">
                <h3>Top Domains by Page Count</h3>
                <table class="data-table">
                    <thead>
                        <tr><th>Domain</th><th>Pages</th></tr>
                    </thead>
                    <tbody>
        """
        
        for domain_data in report_data['top_domains'][:10]:
            html += f"<tr><td>{domain_data['domain']}</td><td>{domain_data['page_count']}</td></tr>"
        
        html += """
                    </tbody>
                </table>
            </div>
        </div>
        
        <style>
        .ai-report { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; }
        .report-header { border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }
        .query-text { background: #f5f5f5; padding: 10px; border-radius: 5px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .stat-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #007bff; margin: 10px 0; }
        .data-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .data-table th, .data-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .data-table th { background-color: #f2f2f2; }
        </style>
        """
        
        return html
    
    def _generate_summary(self, report_data: Dict[str, Any]) -> str:
        """Generate a text summary of the report."""
        
        summary = f"""
        Data Summary:
        - Total Sites: {report_data['site_stats']['total']} ({report_data['site_stats']['active']} active)
        - Total Pages: {report_data['page_stats']['total']} ({report_data['page_stats']['recent_24h']} in last 24h)
        - Total Media: {report_data['media_stats']['total']} ({report_data['media_stats']['flagged']} flagged)
        - Network Distribution: {', '.join([f"{k}: {v}" for k, v in report_data['site_stats']['by_network'].items()])}
        - Top Domain: {report_data['top_domains'][0]['domain'] if report_data['top_domains'] else 'N/A'}
        """
        
        return summary.strip()
    
    def _create_chart_report(self, user_query: UserQuery, ai_analysis: Dict[str, Any], 
                            db: Session) -> Optional[GeneratedReport]:
        """Create a chart/visualization report."""
        # This would generate chart data and visualization
        # For now, return None - can be implemented later
        return None
    
    def _serialize_report(self, report: GeneratedReport) -> Dict[str, Any]:
        """Serialize report for API response."""
        
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
            'view_count': report.view_count
        }
    
    def get_query_templates(self) -> List[Dict[str, Any]]:
        """Get available query templates."""
        
        with get_session_manager().transaction() as db:
            templates = db.query(QueryTemplate).filter(
                QueryTemplate.is_active == True
            ).order_by(QueryTemplate.category, QueryTemplate.name).all()
            
            return [
                {
                    'id': t.id,
                    'name': t.name,
                    'description': t.description,
                    'category': t.category,
                    'template_text': t.template_text,
                    'example_query': t.example_query,
                    'usage_count': t.usage_count
                }
                for t in templates
            ]
    
    def get_recent_queries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent user queries."""
        
        with get_session_manager().transaction() as db:
            queries = db.query(UserQuery).filter(
                UserQuery.status == 'completed'
            ).order_by(desc(UserQuery.created_at)).limit(limit).all()
            
            return [
                {
                    'id': q.id,
                    'query_text': q.query_text[:200] + '...' if len(q.query_text) > 200 else q.query_text,
                    'query_type': q.query_type,
                    'created_at': q.created_at.isoformat() if q.created_at else None,
                    'processing_time': q.processing_time,
                    'report_count': len(q.reports)
                }
                for q in queries
            ]
