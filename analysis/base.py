"""Base analyzer class."""

import json
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
        images: Optional[list] = None
    ) -> Optional[Dict[str, Any]]:
        """Make a call to the Ollama API."""
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
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error calling Ollama API: {e}")
            return None
    
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
