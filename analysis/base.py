"""Base analyzer class."""

import json
import time
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from core import get_logger
from config import get_settings


class BaseAnalyzer(ABC):
    """Base class for all AI analyzers."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(self.__class__.__name__)
    
    def call_ollama_api(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        images: Optional[list] = None,
        request_type: str = "generate"
    ) -> Optional[Dict[str, Any]]:
        """Make a call to the Ollama API with usage tracking."""
        start_time = time.time()
        success = False
        error_message = None
        tokens_used = None
        
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            if images:
                payload["images"] = images
            
            response = requests.post(
                self.settings.ollama_endpoint,
                json=payload,
                timeout=120
            )
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                success = True
                
                # Extract token usage if available
                if 'eval_count' in result:
                    tokens_used = result['eval_count']
                
                # Track the successful request
                self._track_request(model, request_type, success, duration, tokens_used)
                
                return result
            else:
                error_message = f"HTTP {response.status_code}: {response.text}"
                self.logger.error(f"Ollama API error: {error_message}")
                
                # Track the failed request
                self._track_request(model, request_type, success, duration, error_message=error_message)
                
                return None
                
        except Exception as e:
            duration = time.time() - start_time
            error_message = str(e)
            self.logger.error(f"Error calling Ollama API: {error_message}")
            
            # Track the failed request
            self._track_request(model, request_type, success, duration, error_message=error_message)
            
            return None
    
    def _track_request(self, model: str, request_type: str, success: bool, 
                      duration: float, tokens_used: Optional[int] = None,
                      error_message: Optional[str] = None):
        """Track Ollama API request for monitoring."""
        try:
            from analysis.ollama_monitor import track_ollama_request
            track_ollama_request(
                model_name=model,
                request_type=request_type,
                success=success,
                duration=duration,
                tokens_used=tokens_used,
                error_message=error_message
            )
        except Exception as e:
            self.logger.debug(f"Failed to track request: {e}")
    
    @abstractmethod
    def analyze(self, content: Any) -> Optional[Dict[str, Any]]:
        """Analyze content and return results."""
        pass
    
    def parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from AI model."""
        try:
            # Try to extract JSON from response
            if '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_str = response_text[start:end]
                return json.loads(json_str)
            else:
                # If no JSON found, return the text as is
                return {"response": response_text}
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON response: {e}")
            return {"response": response_text}
    
    def extract_score(self, response: Dict[str, Any], default: float = 0.0) -> float:
        """Extract numerical score from response."""
        if isinstance(response, dict):
            # Look for common score fields
            for field in ['score', 'confidence', 'probability', 'rating']:
                if field in response:
                    try:
                        return float(response[field])
                    except (ValueError, TypeError):
                        continue
        
        return default
