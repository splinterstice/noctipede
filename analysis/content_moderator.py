"""Content moderation using AI models with enhanced WebP and dark web format support."""

import base64
from typing import Dict, Any, Optional, List
from datetime import datetime

from database import get_db_session, MediaFile, Page
from storage import get_storage_client
from core import validate_and_process_image, convert_to_standard_format, is_image_safe_to_process
from .base import BaseAnalyzer


class ContentModerator(BaseAnalyzer):
    """Content moderator for detecting potentially harmful content."""
    
    def moderate_image(self, media_file_id: int, threshold: float = None) -> Optional[Dict[str, Any]]:
        """Moderate an image for potentially harmful content."""
        threshold = threshold or self.settings.moderation_threshold
        db_session = get_db_session()
        storage_client = get_storage_client()
        
        try:
            # Get media file record
            media_file = db_session.query(MediaFile).filter_by(id=media_file_id).first()
            if not media_file or media_file.file_type != 'image':
                return None
            
            # Download image from storage
            if not media_file.minio_object_name:
                return None
            
            image_data = storage_client.download_file(
                media_file.minio_object_name,
                media_file.minio_bucket
            )
            
            if not image_data:
                return None
            
            # Perform moderation analysis
            moderation_result = self.analyze_image_content(image_data)
            
            if moderation_result:
                risk_score = moderation_result.get('risk_score', 0.0)
                
                # Flag if above threshold
                if risk_score >= threshold:
                    media_file.is_flagged = True
                    media_file.flagged_reason = moderation_result.get('reason', 'High risk content detected')
                    media_file.analysis_score = risk_score
                    
                    self.logger.warning(f"Flagged media file {media_file_id}: {media_file.flagged_reason}")
                else:
                    media_file.is_flagged = False
                    media_file.analysis_score = risk_score
                
                media_file.analyzed_at = datetime.utcnow()
                db_session.commit()
            
            return moderation_result
            
        except Exception as e:
            self.logger.error(f"Error moderating image {media_file_id}: {e}")
            db_session.rollback()
            return None
        finally:
            db_session.close()
    
    def moderate_text(self, page_id: int, db_session=None, threshold: float = None) -> Optional[Dict[str, Any]]:
        """Moderate text content for potentially harmful material."""
        threshold = threshold or self.settings.moderation_threshold
        should_close = False
        
        if not db_session:
            from database.session import get_session_manager
            session_manager = get_session_manager()
            db_session = session_manager.get_session()
            should_close = True
        
        try:
            from database.models import Page
            # Get page record
            page = db_session.query(Page).filter_by(id=page_id).first()
            if not page or not page.content:
                if should_close:
                    db_session.close()
                return None
            
            # Perform text moderation
            moderation_result = self.analyze_text_content(page.content)
            
            if moderation_result:
                risk_score = moderation_result.get('risk_score', 0.0)
                
                # You could add a flagged field to Page model if needed
                # For now, just log high-risk content
                if risk_score >= threshold:
                    self.logger.warning(f"High-risk text content detected on page {page_id}: {moderation_result.get('reason', 'Unknown')}")
            
            return moderation_result
            
        except Exception as e:
            self.logger.error(f"Error moderating text {page_id}: {e}")
            return None
        finally:
            if should_close:
                db_session.close()
    
    def analyze_image_content(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """Analyze image for potentially harmful content with WebP support."""
        try:
            # Validate image first
            if not is_image_safe_to_process(image_data):
                return {
                    'risk_score': 100.0,
                    'categories': ['malicious_file'],
                    'reason': 'Image failed safety validation - potentially malicious file',
                    'confidence': 1.0,
                    'safe': False
                }
            
            # Process and validate image
            image_info = validate_and_process_image(image_data)
            if not image_info:
                return {
                    'risk_score': 50.0,
                    'categories': ['processing_error'],
                    'reason': 'Could not process image file',
                    'confidence': 0.8,
                    'safe': False
                }
            
            # Convert WebP or other formats for better analysis
            processed_image_data = image_data
            if image_info['format'] in ['webp', 'bmp', 'tiff']:
                self.logger.debug(f"Converting {image_info['format']} to JPEG for moderation analysis")
                converted_data = convert_to_standard_format(image_data, 'JPEG')
                if converted_data:
                    processed_image_data = converted_data
            
            image_b64 = base64.b64encode(processed_image_data).decode('utf-8')
            
            # Enhanced system prompt for dark web content moderation
            system_prompt = """You are a content moderation expert specializing in dark web content analysis. 
            Analyze this image for potentially harmful, illegal, or inappropriate content commonly found on Tor and I2P networks.
            
            Pay special attention to:
            - Violence, gore, or graphic content
            - Adult/sexual content, especially involving minors
            - Illegal drug manufacturing, sales, or use
            - Weapons, explosives, or dangerous items
            - Hate symbols, extremist content, or terrorist materials
            - Identity documents, credit cards, or fraud materials
            - Hacking tools, malware, or cybercrime evidence
            - Human trafficking or exploitation indicators
            - Illegal marketplaces or transaction evidence
            
            Consider the context that this image was found on a deep web site.
            
            Respond with a JSON object containing:
            - "risk_score": float from 0.0 (safe) to 100.0 (extremely high risk)
            - "categories": list of concerning categories detected
            - "reason": detailed explanation of why content might be problematic
            - "confidence": confidence in the assessment (0.0-1.0)
            - "safe": boolean indicating if content appears safe
            - "dark_web_indicators": specific indicators suggesting dark web criminal activity
            - "recommended_action": suggested action (monitor, flag, report, block)"""
            
            format_context = f"Image format: {image_info['format'].upper()}, dimensions: {image_info['width']}x{image_info['height']}"
            if image_info.get('webp_animated') or image_info.get('gif_animated'):
                format_context += " (animated image - check all frames for content)"
            
            prompt = f"Analyze this image for potentially harmful or illegal content. {format_context}"
            
            response = self.call_ollama_api(
                model=self.settings.ollama_moderation_model,
                prompt=prompt,
                system_prompt=system_prompt,
                images=[image_b64]
            )
            
            if response and 'response' in response:
                moderation_result = self.parse_json_response(response['response'])
                if moderation_result:
                    # Add technical context
                    moderation_result['technical_info'] = {
                        'original_format': image_info['format'],
                        'file_size': image_info['file_size'],
                        'dimensions': f"{image_info['width']}x{image_info['height']}",
                        'animated': image_info.get('webp_animated', False) or image_info.get('gif_animated', False)
                    }
                return moderation_result
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in image content analysis: {e}")
            return None
    
    def analyze_text_content(self, text: str) -> Optional[Dict[str, Any]]:
        """Analyze text for potentially harmful content."""
        try:
            system_prompt = """You are a content moderation expert. Analyze this text for potentially harmful, illegal, or inappropriate content. Consider:
            - Hate speech or discriminatory language
            - Threats or violence
            - Illegal activities or instructions
            - Extremist content
            - Harassment or bullying
            - Adult content descriptions
            
            Respond with a JSON object containing:
            - "risk_score": float from 0.0 (safe) to 100.0 (high risk)
            - "categories": list of concerning categories detected
            - "reason": explanation of why content might be problematic
            - "confidence": confidence in the assessment (0.0-1.0)
            - "safe": boolean indicating if content appears safe"""
            
            prompt = f"Analyze this text for potentially harmful or inappropriate content:\n\n{text[:3000]}"
            
            response = self.call_ollama_api(
                model=self.settings.ollama_moderation_model,
                prompt=prompt,
                system_prompt=system_prompt
            )
            
            if response and 'response' in response:
                return self.parse_json_response(response['response'])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in text content analysis: {e}")
            return None
    
    def analyze(self, content: Any) -> Optional[Dict[str, Any]]:
        """General content moderation method."""
        if isinstance(content, bytes):
            # Assume it's image data
            return self.analyze_image_content(content)
        elif isinstance(content, str):
            # Assume it's text content
            return self.analyze_text_content(content)
        else:
            self.logger.warning(f"Unsupported content type for moderation: {type(content)}")
            return None
    
    def batch_moderate_images(self, media_file_ids: List[int], threshold: float = None) -> Dict[str, Any]:
        """Moderate multiple images in batch."""
        results = {
            'total': len(media_file_ids),
            'processed': 0,
            'flagged': 0,
            'errors': 0,
            'results': []
        }
        
        for media_id in media_file_ids:
            try:
                result = self.moderate_image(media_id, threshold)
                if result:
                    results['processed'] += 1
                    if result.get('risk_score', 0) >= (threshold or self.settings.moderation_threshold):
                        results['flagged'] += 1
                    results['results'].append({
                        'media_id': media_id,
                        'result': result
                    })
                else:
                    results['errors'] += 1
            except Exception as e:
                self.logger.error(f"Error in batch moderation for media {media_id}: {e}")
                results['errors'] += 1
        
        return results
