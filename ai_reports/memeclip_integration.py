"""MemeCLIP integration for advanced image analysis."""

import os
import json
import subprocess
import tempfile
from typing import Dict, List, Optional, Any
from pathlib import Path
import requests
from PIL import Image
import numpy as np

from core import get_logger
from config import get_settings
from database import get_db_session
from sqlalchemy import text

logger = get_logger(__name__)


class MemeCLIPService:
    """Service for integrating MemeCLIP image analysis capabilities."""
    
    def __init__(self):
        self.settings = get_settings()
        self.model_path = getattr(self.settings, 'memeclip_model_path', '/app/memeclip')
        self.batch_size = getattr(self.settings, 'memeclip_batch_size', 32)
        self.gpu_enabled = getattr(self.settings, 'memeclip_gpu_enabled', False)
        self.cache_dir = getattr(self.settings, 'memeclip_model_cache', '/app/cache/memeclip')
        
        self.setup_environment()
    
    def setup_environment(self) -> None:
        """Setup MemeCLIP environment and dependencies."""
        try:
            # Ensure cache directory exists
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Check if MemeCLIP is already installed
            if not os.path.exists(self.model_path):
                logger.info("Setting up MemeCLIP environment...")
                self._install_memeclip()
            
            # Verify installation
            if self._verify_installation():
                logger.info("MemeCLIP environment ready")
            else:
                logger.error("MemeCLIP setup failed")
                
        except Exception as e:
            logger.error(f"Failed to setup MemeCLIP environment: {e}")
    
    def analyze_image(self, image_path: str, dataset_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyze a single image using MemeCLIP.
        
        Args:
            image_path: Path to the image file
            dataset_id: Optional dataset ID for storing results
            
        Returns:
            Analysis results dictionary
        """
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            # Prepare image for analysis
            processed_image = self._preprocess_image(image_path)
            
            # Run MemeCLIP analysis
            result = self._run_memeclip_analysis([processed_image])
            
            if result and len(result) > 0:
                analysis_result = result[0]
                
                # Store results in database if dataset_id provided
                if dataset_id:
                    self._store_analysis_result(image_path, dataset_id, analysis_result)
                
                return analysis_result
            else:
                return {'error': 'Analysis failed', 'confidence_score': 0.0}
                
        except Exception as e:
            logger.error(f"Failed to analyze image {image_path}: {e}")
            return {'error': str(e), 'confidence_score': 0.0}
    
    def batch_analyze(self, image_paths: List[str], dataset_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Batch analyze multiple images using MemeCLIP.
        
        Args:
            image_paths: List of image file paths
            dataset_id: Optional dataset ID for storing results
            
        Returns:
            List of analysis results
        """
        try:
            results = []
            
            # Process images in batches
            for i in range(0, len(image_paths), self.batch_size):
                batch = image_paths[i:i + self.batch_size]
                
                # Preprocess batch
                processed_images = []
                valid_paths = []
                
                for path in batch:
                    if os.path.exists(path):
                        try:
                            processed = self._preprocess_image(path)
                            processed_images.append(processed)
                            valid_paths.append(path)
                        except Exception as e:
                            logger.warning(f"Failed to preprocess {path}: {e}")
                            results.append({'error': str(e), 'confidence_score': 0.0})
                
                # Run batch analysis
                if processed_images:
                    batch_results = self._run_memeclip_analysis(processed_images)
                    
                    # Store results
                    for j, result in enumerate(batch_results):
                        if dataset_id and j < len(valid_paths):
                            self._store_analysis_result(valid_paths[j], dataset_id, result)
                        results.append(result)
            
            logger.info(f"Completed batch analysis of {len(image_paths)} images")
            return results
            
        except Exception as e:
            logger.error(f"Failed to batch analyze images: {e}")
            return [{'error': str(e), 'confidence_score': 0.0} for _ in image_paths]
    
    def get_analysis_results(self, dataset_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get stored analysis results for a dataset."""
        try:
            with get_db_session() as session:
                query = text("""
                    SELECT ma.*, mf.url, mf.filename, mf.file_type
                    FROM memeclip_analysis ma
                    JOIN media_files mf ON ma.media_file_id = mf.id
                    WHERE ma.dataset_id = :dataset_id
                    ORDER BY ma.analysis_timestamp DESC
                    LIMIT :limit
                """)
                
                result = session.execute(query, {
                    'dataset_id': dataset_id,
                    'limit': limit
                })
                
                return [dict(row._mapping) for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get analysis results for dataset {dataset_id}: {e}")
            return []
    
    def search_similar_images(self, query_image_path: str, dataset_id: int, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Search for similar images in a dataset."""
        try:
            # Analyze query image
            query_result = self.analyze_image(query_image_path)
            if 'error' in query_result:
                return []
            
            # Get all analysis results for the dataset
            all_results = self.get_analysis_results(dataset_id)
            
            # Calculate similarities
            similar_images = []
            query_features = query_result.get('features', [])
            
            for result in all_results:
                if result['classification_result']:
                    stored_features = json.loads(result['classification_result']).get('features', [])
                    similarity = self._calculate_similarity(query_features, stored_features)
                    
                    if similarity >= threshold:
                        result['similarity_score'] = similarity
                        similar_images.append(result)
            
            # Sort by similarity
            similar_images.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return similar_images
            
        except Exception as e:
            logger.error(f"Failed to search similar images: {e}")
            return []
    
    def _install_memeclip(self) -> None:
        """Install MemeCLIP from GitHub repository."""
        try:
            # Clone repository
            clone_cmd = [
                'git', 'clone', 
                'https://github.com/SiddhantBikram/MemeCLIP.git',
                self.model_path
            ]
            subprocess.run(clone_cmd, check=True, capture_output=True)
            
            # Install dependencies
            requirements_path = os.path.join(self.model_path, 'requirements.txt')
            if os.path.exists(requirements_path):
                install_cmd = ['pip', 'install', '-r', requirements_path]
                subprocess.run(install_cmd, check=True, capture_output=True)
            
            # Download pre-trained models if available
            self._download_pretrained_models()
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install MemeCLIP: {e}")
            raise
    
    def _verify_installation(self) -> bool:
        """Verify MemeCLIP installation."""
        try:
            # Check if main files exist
            main_files = ['model.py', 'inference.py', 'utils.py']
            for file in main_files:
                if not os.path.exists(os.path.join(self.model_path, file)):
                    return False
            
            # Try to import MemeCLIP modules
            import sys
            sys.path.append(self.model_path)
            
            try:
                import model  # MemeCLIP model module
                return True
            except ImportError:
                return False
                
        except Exception:
            return False
    
    def _preprocess_image(self, image_path: str) -> str:
        """Preprocess image for MemeCLIP analysis."""
        try:
            # Load and validate image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large (MemeCLIP typically works with smaller images)
                max_size = 512
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Save preprocessed image to temp file
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    img.save(temp_file.name, 'JPEG', quality=95)
                    return temp_file.name
                    
        except Exception as e:
            logger.error(f"Failed to preprocess image {image_path}: {e}")
            raise
    
    def _run_memeclip_analysis(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """Run MemeCLIP analysis on preprocessed images."""
        try:
            # Import MemeCLIP modules
            import sys
            sys.path.append(self.model_path)
            
            # This is a placeholder - actual implementation depends on MemeCLIP API
            # The real implementation would use MemeCLIP's inference functions
            
            results = []
            for image_path in image_paths:
                # Placeholder analysis result
                result = {
                    'classification_result': {
                        'is_meme': False,
                        'meme_type': 'unknown',
                        'features': [],
                        'categories': []
                    },
                    'confidence_score': 0.5,
                    'meme_detected': False,
                    'similarity_scores': {}
                }
                
                # TODO: Replace with actual MemeCLIP inference
                # result = memeclip_model.analyze(image_path)
                
                results.append(result)
                
                # Cleanup temp file
                if os.path.exists(image_path) and image_path.startswith('/tmp'):
                    os.unlink(image_path)
            
            return results
            
        except Exception as e:
            logger.error(f"MemeCLIP analysis failed: {e}")
            return [{'error': str(e), 'confidence_score': 0.0} for _ in image_paths]
    
    def _store_analysis_result(self, image_path: str, dataset_id: int, result: Dict[str, Any]) -> None:
        """Store analysis result in database."""
        try:
            # Find corresponding media file
            with get_db_session() as session:
                # Try to match by filename or path
                filename = os.path.basename(image_path)
                
                query = text("""
                    SELECT id FROM media_files 
                    WHERE filename = :filename OR url LIKE :url_pattern
                    LIMIT 1
                """)
                
                media_result = session.execute(query, {
                    'filename': filename,
                    'url_pattern': f'%{filename}'
                }).fetchone()
                
                if media_result:
                    media_file_id = media_result.id
                    
                    # Insert analysis result
                    insert_query = text("""
                        INSERT INTO memeclip_analysis (
                            media_file_id, dataset_id, classification_result,
                            similarity_scores, meme_detected, confidence_score
                        ) VALUES (
                            :media_file_id, :dataset_id, :classification_result,
                            :similarity_scores, :meme_detected, :confidence_score
                        )
                    """)
                    
                    session.execute(insert_query, {
                        'media_file_id': media_file_id,
                        'dataset_id': dataset_id,
                        'classification_result': json.dumps(result.get('classification_result', {})),
                        'similarity_scores': json.dumps(result.get('similarity_scores', {})),
                        'meme_detected': result.get('meme_detected', False),
                        'confidence_score': result.get('confidence_score', 0.0)
                    })
                    
                    session.commit()
                    
        except Exception as e:
            logger.error(f"Failed to store analysis result: {e}")
    
    def _download_pretrained_models(self) -> None:
        """Download pre-trained MemeCLIP models."""
        try:
            # This would download pre-trained models if available
            # Implementation depends on MemeCLIP's model distribution
            pass
            
        except Exception as e:
            logger.warning(f"Failed to download pre-trained models: {e}")
    
    def _calculate_similarity(self, features1: List[float], features2: List[float]) -> float:
        """Calculate cosine similarity between feature vectors."""
        try:
            if not features1 or not features2 or len(features1) != len(features2):
                return 0.0
            
            # Convert to numpy arrays
            f1 = np.array(features1)
            f2 = np.array(features2)
            
            # Calculate cosine similarity
            dot_product = np.dot(f1, f2)
            norm1 = np.linalg.norm(f1)
            norm2 = np.linalg.norm(f2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
