"""Analysis management and coordination."""

from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from core import get_logger
from config import get_settings
from .text_analyzer import TextAnalyzer
from .image_analyzer import ImageAnalyzer
from .content_moderator import ContentModerator


class AnalysisManager:
    """Manages different types of analysis and coordinates their execution."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.text_analyzer = TextAnalyzer()
        self.image_analyzer = ImageAnalyzer()
        self.content_moderator = ContentModerator()
    
    def analyze_page(self, page_id: int, analysis_types: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Perform comprehensive analysis on a page."""
        if not analysis_types:
            analysis_types = ['text', 'sentiment', 'entities', 'moderation']
        
        results = {}
        
        try:
            # Text analysis
            if 'text' in analysis_types or 'sentiment' in analysis_types or 'entities' in analysis_types:
                text_result = self.text_analyzer.analyze_page_content(page_id)
                if text_result:
                    results['text_analysis'] = text_result
            
            # Content moderation for text
            if 'moderation' in analysis_types:
                moderation_result = self.content_moderator.moderate_text(page_id)
                if moderation_result:
                    results['text_moderation'] = moderation_result
            
            return results if results else None
            
        except Exception as e:
            self.logger.error(f"Error analyzing page {page_id}: {e}")
            return None
    
    def analyze_media(self, media_file_id: int, analysis_types: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Perform comprehensive analysis on a media file."""
        if not analysis_types:
            analysis_types = ['description', 'moderation']
        
        results = {}
        
        try:
            # Image description
            if 'description' in analysis_types:
                description_result = self.image_analyzer.analyze_image(media_file_id)
                if description_result:
                    results['image_analysis'] = description_result
            
            # Content moderation for images
            if 'moderation' in analysis_types:
                moderation_result = self.content_moderator.moderate_image(media_file_id)
                if moderation_result:
                    results['image_moderation'] = moderation_result
            
            return results if results else None
            
        except Exception as e:
            self.logger.error(f"Error analyzing media {media_file_id}: {e}")
            return None
    
    def batch_analyze_pages(self, page_ids: List[int], analysis_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze multiple pages in batch."""
        results = {
            'total': len(page_ids),
            'processed': 0,
            'errors': 0,
            'results': []
        }
        
        with ThreadPoolExecutor(max_workers=self.settings.worker_threads) as executor:
            # Submit analysis tasks
            future_to_page = {
                executor.submit(self.analyze_page, page_id, analysis_types): page_id
                for page_id in page_ids
            }
            
            # Process completed tasks
            for future in as_completed(future_to_page):
                page_id = future_to_page[future]
                try:
                    result = future.result()
                    if result:
                        results['processed'] += 1
                        results['results'].append({
                            'page_id': page_id,
                            'result': result
                        })
                    else:
                        results['errors'] += 1
                        self.logger.warning(f"No result for page analysis {page_id}")
                except Exception as e:
                    results['errors'] += 1
                    self.logger.error(f"Error in batch page analysis for {page_id}: {e}")
        
        return results
    
    def batch_analyze_media(self, media_file_ids: List[int], analysis_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze multiple media files in batch."""
        results = {
            'total': len(media_file_ids),
            'processed': 0,
            'errors': 0,
            'results': []
        }
        
        with ThreadPoolExecutor(max_workers=self.settings.worker_threads) as executor:
            # Submit analysis tasks
            future_to_media = {
                executor.submit(self.analyze_media, media_id, analysis_types): media_id
                for media_id in media_file_ids
            }
            
            # Process completed tasks
            for future in as_completed(future_to_media):
                media_id = future_to_media[future]
                try:
                    result = future.result()
                    if result:
                        results['processed'] += 1
                        results['results'].append({
                            'media_id': media_id,
                            'result': result
                        })
                    else:
                        results['errors'] += 1
                        self.logger.warning(f"No result for media analysis {media_id}")
                except Exception as e:
                    results['errors'] += 1
                    self.logger.error(f"Error in batch media analysis for {media_id}: {e}")
        
        return results
    
    def moderate_content_batch(self, 
                              page_ids: Optional[List[int]] = None,
                              media_file_ids: Optional[List[int]] = None,
                              threshold: Optional[float] = None) -> Dict[str, Any]:
        """Perform content moderation on multiple items."""
        results = {
            'pages': {'total': 0, 'flagged': 0, 'processed': 0},
            'media': {'total': 0, 'flagged': 0, 'processed': 0}
        }
        
        # Moderate pages
        if page_ids:
            results['pages']['total'] = len(page_ids)
            for page_id in page_ids:
                try:
                    moderation_result = self.content_moderator.moderate_text(page_id, threshold)
                    if moderation_result:
                        results['pages']['processed'] += 1
                        if moderation_result.get('risk_score', 0) >= (threshold or self.settings.moderation_threshold):
                            results['pages']['flagged'] += 1
                except Exception as e:
                    self.logger.error(f"Error moderating page {page_id}: {e}")
        
        # Moderate media files
        if media_file_ids:
            media_results = self.content_moderator.batch_moderate_images(media_file_ids, threshold)
            results['media'] = {
                'total': media_results['total'],
                'flagged': media_results['flagged'],
                'processed': media_results['processed']
            }
        
        return results
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get statistics about analysis performance."""
        # This would be implemented to gather stats from database
        # For now, return basic info
        return {
            'analyzers_available': ['text', 'image', 'moderation'],
            'worker_threads': self.settings.worker_threads,
            'moderation_threshold': self.settings.moderation_threshold
        }
