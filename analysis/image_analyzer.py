"""Image analysis using AI vision models with WebP and dark web format support."""

import base64
from typing import Dict, Any, Optional
from datetime import datetime

from database import get_db_session, MediaFile
from storage import get_storage_client
from core import validate_and_process_image, convert_to_standard_format, extract_image_metadata
from .base import BaseAnalyzer


class ImageAnalyzer(BaseAnalyzer):
    """Analyzer for image content using AI vision models."""
    
    def analyze_image(self, media_file_id: int) -> Optional[Dict[str, Any]]:
        """Analyze an image file."""
        db_session = get_db_session()
        storage_client = get_storage_client()
        
        try:
            # Get media file record
            media_file = db_session.query(MediaFile).filter_by(id=media_file_id).first()
            if not media_file or media_file.file_type != 'image':
                return None
            
            # Download image from storage
            if not media_file.minio_object_name:
                self.logger.warning(f"No storage object name for media file {media_file_id}")
                return None
            
            image_data = storage_client.download_file(
                media_file.minio_object_name,
                media_file.minio_bucket
            )
            
            if not image_data:
                self.logger.error(f"Could not download image {media_file_id}")
                return None
            
            # Analyze the image
            analysis_result = self.analyze(image_data)
            
            if analysis_result:
                # Update media file with analysis results
                media_file.description = analysis_result.get('description', '')
                media_file.analysis_score = self.extract_score(analysis_result)
                media_file.analyzed_at = datetime.utcnow()
                
                db_session.commit()
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing image {media_file_id}: {e}")
            db_session.rollback()
            return None
        finally:
            db_session.close()
    
    def analyze(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """Analyze image data using vision model with WebP support."""
        try:
            # Validate and process the image first
            image_info = validate_and_process_image(image_data)
            if not image_info:
                self.logger.error("Image validation failed")
                return None
            
            # Extract metadata for additional context
            metadata = extract_image_metadata(image_data)
            
            # Convert WebP or other formats to JPEG for Ollama if needed
            # Some vision models work better with standard formats
            processed_image_data = image_data
            if image_info['format'] in ['webp', 'bmp', 'tiff']:
                self.logger.debug(f"Converting {image_info['format']} to JPEG for analysis")
                converted_data = convert_to_standard_format(image_data, 'JPEG')
                if converted_data:
                    processed_image_data = converted_data
                else:
                    self.logger.warning("Format conversion failed, using original")
            
            # Convert image to base64
            image_b64 = base64.b64encode(processed_image_data).decode('utf-8')
            
            # Create enhanced prompt for image analysis
            format_info = f"Format: {image_info['format'].upper()}, Size: {image_info['width']}x{image_info['height']}"
            if image_info.get('webp_animated'):
                format_info += " (Animated WebP)"
            elif image_info.get('gif_animated'):
                format_info += f" (Animated GIF, {image_info.get('gif_frames', 1)} frames)"
            
            prompt = f"""Analyze this image ({format_info}) and provide a detailed description. 
            This image was found on a deep web site, so pay special attention to:
            
            1. What objects, people, or scenes are visible
            2. Any text, symbols, or logos that might be visible
            3. The overall mood, atmosphere, or context
            4. The quality and apparent purpose of the image
            5. Any concerning or notable elements
            
            Respond with a JSON object containing:
            - "description": detailed description of the image
            - "objects": list of objects detected
            - "people_count": number of people visible (if any)
            - "text_detected": any text visible in the image
            - "symbols": any symbols, logos, or emblems detected
            - "mood": overall mood/atmosphere
            - "quality": assessment of image quality (low/medium/high)
            - "purpose": likely purpose of the image (photo, artwork, screenshot, etc.)
            - "notable_elements": any particularly notable or concerning elements
            - "confidence": confidence score (0.0-1.0)"""
            
            response = self.call_ollama_api(
                model=self.settings.ollama_vision_model,
                prompt=prompt,
                images=[image_b64]
            )
            
            if response and 'response' in response:
                analysis_result = self.parse_json_response(response['response'])
                if analysis_result:
                    # Add technical metadata to the result
                    analysis_result['technical_info'] = {
                        'original_format': image_info['format'],
                        'dimensions': f"{image_info['width']}x{image_info['height']}",
                        'file_size': image_info['file_size'],
                        'has_transparency': image_info.get('has_transparency', False),
                        'animated': image_info.get('webp_animated', False) or image_info.get('gif_animated', False)
                    }
                    
                    # Add metadata if available
                    if metadata:
                        analysis_result['metadata'] = metadata
                
                return analysis_result
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in image analysis: {e}")
            return None
    
    def generate_description(self, image_data: bytes) -> Optional[str]:
        """Generate a simple description of the image."""
        try:
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            prompt = "Describe this image in 1-2 sentences. Be concise and factual."
            
            response = self.call_ollama_api(
                model=self.settings.ollama_vision_model,
                prompt=prompt,
                images=[image_b64]
            )
            
            if response and 'response' in response:
                return response['response'].strip()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error generating image description: {e}")
            return None
