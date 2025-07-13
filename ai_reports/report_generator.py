"""AI-powered report generator for datasets."""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import pandas as pd
from jinja2 import Template
import requests

from core import get_logger
from config import get_settings
from database import get_db_session
from sqlalchemy import text

logger = get_logger(__name__)


class ReportGenerator:
    """Generates AI-powered reports from dataset queries and analysis."""
    
    def __init__(self):
        self.settings = get_settings()
        self.ollama_endpoint = getattr(self.settings, 'ollama_endpoint', 'http://ollama:11434')
        self.text_model = getattr(self.settings, 'ollama_text_model', 'gemma3:12b')
        self.report_templates_path = '/app/ai_reports/templates'
        
        # Report generation settings
        self.max_context_length = 8000  # Max tokens for AI context
        self.max_report_length = 5000   # Max tokens for generated report
        
    def generate_report(self, query_result: Dict[str, Any], report_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI-powered report from query results.
        
        Args:
            query_result: Results from query engine
            report_config: Report configuration (type, format, etc.)
            
        Returns:
            Generated report information
        """
        try:
            report_type = report_config.get('type', 'summary')
            report_format = report_config.get('format', 'html')
            
            # Prepare data for AI analysis
            context_data = self._prepare_context_data(query_result)
            
            # Generate AI analysis
            ai_analysis = self._generate_ai_analysis(context_data, report_type)
            
            if not ai_analysis:
                return {'success': False, 'error': 'AI analysis failed'}
            
            # Format report based on requested format
            formatted_report = self._format_report(ai_analysis, report_format, report_config)
            
            # Store report in database
            report_id = self._store_report(formatted_report, query_result, report_config)
            
            return {
                'success': True,
                'report_id': report_id,
                'report': formatted_report,
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'report_type': report_type,
                    'format': report_format,
                    'data_points': len(query_result.get('data', [])),
                    'ai_model': self.text_model
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_summary_report(self, dataset_id: int, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate summary report for a dataset."""
        try:
            # Get dataset statistics
            stats = self._get_dataset_statistics(dataset_id, filters)
            
            # Generate AI summary
            summary_prompt = self._build_summary_prompt(stats)
            ai_summary = self._call_ollama(summary_prompt)
            
            if not ai_summary:
                return {'success': False, 'error': 'Failed to generate AI summary'}
            
            # Create comprehensive summary report
            report = {
                'title': f'Dataset Summary Report - Dataset {dataset_id}',
                'generated_at': datetime.now().isoformat(),
                'dataset_id': dataset_id,
                'statistics': stats,
                'ai_summary': ai_summary,
                'filters_applied': filters or {},
                'report_type': 'summary'
            }
            
            # Store report
            report_id = self._store_summary_report(report)
            report['report_id'] = report_id
            
            return {'success': True, 'report': report}
            
        except Exception as e:
            logger.error(f"Failed to generate summary report: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_security_report(self, dataset_id: int, threat_indicators: List[str] = None) -> Dict[str, Any]:
        """Generate security-focused report analyzing potential threats."""
        try:
            # Get security-relevant data
            security_data = self._get_security_data(dataset_id, threat_indicators)
            
            # Generate AI security analysis
            security_prompt = self._build_security_prompt(security_data)
            ai_analysis = self._call_ollama(security_prompt)
            
            if not ai_analysis:
                return {'success': False, 'error': 'Failed to generate security analysis'}
            
            report = {
                'title': f'Security Analysis Report - Dataset {dataset_id}',
                'generated_at': datetime.now().isoformat(),
                'dataset_id': dataset_id,
                'security_data': security_data,
                'ai_analysis': ai_analysis,
                'threat_indicators': threat_indicators or [],
                'report_type': 'security'
            }
            
            report_id = self._store_security_report(report)
            report['report_id'] = report_id
            
            return {'success': True, 'report': report}
            
        except Exception as e:
            logger.error(f"Failed to generate security report: {e}")
            return {'success': False, 'error': str(e)}
    
    def _prepare_context_data(self, query_result: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for AI context, ensuring it fits within token limits."""
        try:
            data = query_result.get('data', [])
            
            if not data:
                return {'summary': 'No data available', 'sample_records': []}
            
            # Calculate basic statistics
            total_records = len(data)
            
            # Get sample of data for AI analysis
            sample_size = min(50, total_records)  # Limit sample size
            sample_data = data[:sample_size]
            
            # Extract key fields for analysis
            key_fields = ['url', 'domain', 'title', 'network_type', 'status_code', 'content_type']
            simplified_data = []
            
            for record in sample_data:
                simplified_record = {}
                for field in key_fields:
                    if field in record:
                        value = record[field]
                        # Truncate long text fields
                        if isinstance(value, str) and len(value) > 200:
                            value = value[:200] + "..."
                        simplified_record[field] = value
                simplified_data.append(simplified_record)
            
            # Generate summary statistics
            summary_stats = self._calculate_summary_stats(data)
            
            return {
                'total_records': total_records,
                'sample_records': simplified_data,
                'summary_stats': summary_stats,
                'columns': query_result.get('columns', [])
            }
            
        except Exception as e:
            logger.error(f"Failed to prepare context data: {e}")
            return {'summary': 'Error preparing data', 'sample_records': []}
    
    def _generate_ai_analysis(self, context_data: Dict[str, Any], report_type: str) -> Optional[str]:
        """Generate AI analysis based on context data and report type."""
        try:
            prompt = self._build_analysis_prompt(context_data, report_type)
            return self._call_ollama(prompt)
            
        except Exception as e:
            logger.error(f"Failed to generate AI analysis: {e}")
            return None
    
    def _build_analysis_prompt(self, context_data: Dict[str, Any], report_type: str) -> str:
        """Build prompt for AI analysis."""
        
        base_prompt = f"""
You are an expert data analyst specializing in web crawling and cybersecurity analysis. 
Analyze the following dataset and provide a comprehensive {report_type} report.

Dataset Information:
- Total Records: {context_data.get('total_records', 0)}
- Available Columns: {', '.join(context_data.get('columns', []))}

Summary Statistics:
{json.dumps(context_data.get('summary_stats', {}), indent=2)}

Sample Data (first few records):
{json.dumps(context_data.get('sample_records', []), indent=2)}

Please provide a detailed analysis including:
1. Key findings and patterns
2. Data quality assessment
3. Notable anomalies or interesting observations
4. Security implications (if applicable)
5. Recommendations for further investigation

Format your response as a structured report with clear sections and bullet points.
"""
        
        if report_type == 'security':
            base_prompt += """
Focus particularly on:
- Suspicious domains or URLs
- Unusual network patterns
- Potential security threats
- Content that might indicate malicious activity
- Recommendations for security measures
"""
        elif report_type == 'content':
            base_prompt += """
Focus particularly on:
- Content themes and topics
- Language and sentiment analysis
- Media file patterns
- Content quality and relevance
- Trends in content types
"""
        
        return base_prompt
    
    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Call Ollama API for text generation."""
        try:
            url = f"{self.ollama_endpoint}/api/generate"
            
            payload = {
                "model": self.text_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": self.max_report_length
                }
            }
            
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '')
            
        except Exception as e:
            logger.error(f"Ollama API call failed: {e}")
            return None
    
    def _format_report(self, ai_analysis: str, format_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Format the AI analysis into the requested report format."""
        try:
            if format_type == 'html':
                return self._format_html_report(ai_analysis, config)
            elif format_type == 'json':
                return self._format_json_report(ai_analysis, config)
            elif format_type == 'markdown':
                return self._format_markdown_report(ai_analysis, config)
            else:
                # Default to plain text
                return {
                    'content': ai_analysis,
                    'format': 'text',
                    'title': config.get('title', 'Analysis Report')
                }
                
        except Exception as e:
            logger.error(f"Failed to format report: {e}")
            return {
                'content': ai_analysis,
                'format': 'text',
                'error': str(e)
            }
    
    def _format_html_report(self, ai_analysis: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Format report as HTML."""
        
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { border-bottom: 2px solid #333; padding-bottom: 10px; }
        .section { margin: 20px 0; }
        .metadata { background: #f5f5f5; padding: 15px; border-radius: 5px; }
        pre { background: #f8f8f8; padding: 10px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p>Generated on {{ generated_at }}</p>
    </div>
    
    <div class="section">
        <h2>Analysis Report</h2>
        <div>{{ content | safe }}</div>
    </div>
    
    <div class="metadata">
        <h3>Report Metadata</h3>
        <ul>
            <li>Report Type: {{ report_type }}</li>
            <li>AI Model: {{ ai_model }}</li>
            <li>Data Points: {{ data_points }}</li>
        </ul>
    </div>
</body>
</html>
"""
        
        template = Template(html_template)
        
        # Convert AI analysis to HTML (basic markdown-like formatting)
        html_content = ai_analysis.replace('\n\n', '</p><p>').replace('\n', '<br>')
        html_content = f'<p>{html_content}</p>'
        
        html_output = template.render(
            title=config.get('title', 'AI Analysis Report'),
            generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            content=html_content,
            report_type=config.get('type', 'analysis'),
            ai_model=self.text_model,
            data_points=config.get('data_points', 0)
        )
        
        return {
            'content': html_output,
            'format': 'html',
            'title': config.get('title', 'AI Analysis Report')
        }
    
    def _format_json_report(self, ai_analysis: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Format report as structured JSON."""
        
        # Try to parse AI analysis into structured sections
        sections = self._parse_analysis_sections(ai_analysis)
        
        json_report = {
            'title': config.get('title', 'AI Analysis Report'),
            'generated_at': datetime.now().isoformat(),
            'report_type': config.get('type', 'analysis'),
            'ai_model': self.text_model,
            'analysis': {
                'raw_text': ai_analysis,
                'sections': sections
            },
            'metadata': {
                'data_points': config.get('data_points', 0),
                'format': 'json'
            }
        }
        
        return {
            'content': json.dumps(json_report, indent=2),
            'format': 'json',
            'title': config.get('title', 'AI Analysis Report'),
            'structured_data': json_report
        }
    
    def _format_markdown_report(self, ai_analysis: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Format report as Markdown."""
        
        markdown_content = f"""# {config.get('title', 'AI Analysis Report')}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Report Type:** {config.get('type', 'analysis')}  
**AI Model:** {self.text_model}  
**Data Points:** {config.get('data_points', 0)}

---

## Analysis

{ai_analysis}

---

*Report generated by Noctipede AI Reports*
"""
        
        return {
            'content': markdown_content,
            'format': 'markdown',
            'title': config.get('title', 'AI Analysis Report')
        }
    
    def _parse_analysis_sections(self, analysis_text: str) -> List[Dict[str, str]]:
        """Parse AI analysis text into structured sections."""
        try:
            sections = []
            current_section = None
            current_content = []
            
            lines = analysis_text.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # Check if line looks like a section header
                if line and (line.endswith(':') or line.startswith('#') or line.isupper()):
                    # Save previous section
                    if current_section:
                        sections.append({
                            'title': current_section,
                            'content': '\n'.join(current_content).strip()
                        })
                    
                    # Start new section
                    current_section = line.rstrip(':').strip('#').strip()
                    current_content = []
                else:
                    if line:  # Skip empty lines
                        current_content.append(line)
            
            # Add final section
            if current_section:
                sections.append({
                    'title': current_section,
                    'content': '\n'.join(current_content).strip()
                })
            
            return sections
            
        except Exception as e:
            logger.error(f"Failed to parse analysis sections: {e}")
            return [{'title': 'Full Analysis', 'content': analysis_text}]
    
    def _calculate_summary_stats(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics from data."""
        try:
            if not data:
                return {}
            
            stats = {}
            
            # Count by network type
            network_counts = {}
            domain_counts = {}
            status_counts = {}
            
            for record in data:
                # Network type distribution
                network_type = record.get('network_type', 'unknown')
                network_counts[network_type] = network_counts.get(network_type, 0) + 1
                
                # Domain distribution (top 10)
                domain = record.get('domain', 'unknown')
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
                
                # Status code distribution
                status_code = record.get('status_code', 'unknown')
                status_counts[str(status_code)] = status_counts.get(str(status_code), 0) + 1
            
            stats['network_distribution'] = network_counts
            stats['top_domains'] = dict(sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            stats['status_code_distribution'] = status_counts
            stats['total_unique_domains'] = len(domain_counts)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to calculate summary stats: {e}")
            return {}
    
    def _store_report(self, report: Dict[str, Any], query_result: Dict[str, Any], config: Dict[str, Any]) -> Optional[int]:
        """Store generated report in database."""
        try:
            with get_db_session() as session:
                # Create a dummy query record if needed
                query_text = config.get('query', 'Generated report')
                query_hash = hashlib.sha256(query_text.encode()).hexdigest()
                
                # Insert query record
                query_insert = text("""
                    INSERT INTO user_queries (query_text, query_hash, query_type, status, ai_model)
                    VALUES (:query_text, :query_hash, :query_type, 'completed', :ai_model)
                """)
                
                query_result_db = session.execute(query_insert, {
                    'query_text': query_text,
                    'query_hash': query_hash,
                    'query_type': 'report_generation',
                    'ai_model': self.text_model
                })
                
                query_id = query_result_db.lastrowid
                
                # Insert report record
                report_insert = text("""
                    INSERT INTO generated_reports (
                        query_id, title, description, report_type, format,
                        content, summary, record_count, created_by
                    ) VALUES (
                        :query_id, :title, :description, :report_type, :format,
                        :content, :summary, :record_count, 'ai_system'
                    )
                """)
                
                report_result = session.execute(report_insert, {
                    'query_id': query_id,
                    'title': report.get('title', 'AI Generated Report'),
                    'description': config.get('description', 'AI-generated analysis report'),
                    'report_type': config.get('type', 'analysis'),
                    'format': report.get('format', 'html'),
                    'content': report.get('content', ''),
                    'summary': report.get('content', '')[:500] + '...' if len(report.get('content', '')) > 500 else report.get('content', ''),
                    'record_count': len(query_result.get('data', []))
                })
                
                report_id = report_result.lastrowid
                session.commit()
                
                return report_id
                
        except Exception as e:
            logger.error(f"Failed to store report: {e}")
            return None
