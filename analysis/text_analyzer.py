"""Text content analysis using AI models."""

from typing import Dict, Any, Optional, List
from datetime import datetime

from database import get_db_session, Page, ContentAnalysis, Entity
from .base import BaseAnalyzer


class TextAnalyzer(BaseAnalyzer):
    """Analyzer for text content using AI models."""
    
    def analyze_page_content(self, page_id: int, db_session=None) -> Optional[Dict[str, Any]]:
        """Analyze text content of a page."""
        should_close = False
        if not db_session:
            from database.session import get_session_manager
            session_manager = get_session_manager()
            db_session = session_manager.get_session()
            should_close = True
        
        try:
            from database.models import Page
            page = db_session.query(Page).filter_by(id=page_id).first()
            if not page or not page.content:
                if should_close:
                    db_session.close()
                return None
            
            # Perform different types of analysis
            results = {}
            
            # Sentiment analysis
            sentiment_result = self.analyze_sentiment(page.content)
            if sentiment_result:
                results['sentiment'] = sentiment_result
                
                # Update page with sentiment info
                page.sentiment_score = sentiment_result.get('score', 0.0)
                page.sentiment_label = sentiment_result.get('label', 'neutral')
            
            # Topic analysis
            topic_result = self.analyze_topics(page.content)
            if topic_result:
                results['topics'] = topic_result
            
            # Entity extraction
            entities_result = self.extract_entities(page.content)
            if entities_result:
                results['entities'] = entities_result
                self._save_entities(page_id, entities_result)
            
            # Language detection
            language_result = self.detect_language(page.content)
            if language_result:
                results['language'] = language_result
                page.language = language_result.get('language', 'unknown')
            
            # Save analysis results
            if results:
                self._save_content_analysis(page_id, 'comprehensive', results)
            
            # Commit changes if we're managing our own session
            if should_close:
                db_session.commit()
            else:
                # Just flush changes to make them visible in the current session
                db_session.flush()
                
            return results
            
        except Exception as e:
            self.logger.error(f"Error analyzing page content {page_id}: {e}")
            if should_close:
                db_session.rollback()
            return None
        finally:
            if should_close:
                db_session.close()
    
    def analyze_sentiment(self, text: str) -> Optional[Dict[str, Any]]:
        """Analyze sentiment of text."""
        system_prompt = """You are a sentiment analysis expert. Analyze the sentiment of the given text and respond with a JSON object containing:
        - "label": one of "positive", "negative", "neutral"
        - "score": a float between -1.0 (very negative) and 1.0 (very positive)
        - "confidence": a float between 0.0 and 1.0 indicating confidence in the analysis"""
        
        prompt = f"Analyze the sentiment of this text:\n\n{text[:2000]}"  # Limit text length
        
        response = self.call_ollama_api(
            model=self.settings.ollama_text_model,
            prompt=prompt,
            system_prompt=system_prompt,
            request_type="sentiment_analysis"
        )
        
        if response and 'response' in response:
            return self.parse_json_response(response['response'])
        
        return None
    
    def analyze_topics(self, text: str) -> Optional[Dict[str, Any]]:
        """Analyze topics in text."""
        system_prompt = """You are a topic analysis expert. Identify the main topics in the given text and respond with a JSON object containing:
        - "topics": a list of main topics (strings)
        - "keywords": a list of important keywords
        - "categories": a list of content categories
        - "summary": a brief summary of the content"""
        
        prompt = f"Analyze the topics in this text:\n\n{text[:3000]}"
        
        response = self.call_ollama_api(
            model=self.settings.ollama_text_model,
            prompt=prompt,
            system_prompt=system_prompt
        )
        
        if response and 'response' in response:
            return self.parse_json_response(response['response'])
        
        return None
    
    def extract_entities(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract named entities from text."""
        system_prompt = """You are a named entity recognition expert. Extract named entities from the given text and respond with a JSON object containing:
        - "entities": a list of objects, each with "text", "type" (PERSON, ORG, GPE, etc.), and "confidence" (0.0-1.0)"""
        
        prompt = f"Extract named entities from this text:\n\n{text[:2000]}"
        
        response = self.call_ollama_api(
            model=self.settings.ollama_text_model,
            prompt=prompt,
            system_prompt=system_prompt
        )
        
        if response and 'response' in response:
            return self.parse_json_response(response['response'])
        
        return None
    
    def detect_language(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect language of text."""
        system_prompt = """You are a language detection expert. Detect the language of the given text and respond with a JSON object containing:
        - "language": the ISO 639-1 language code (e.g., "en", "es", "fr")
        - "confidence": a float between 0.0 and 1.0 indicating confidence"""
        
        prompt = f"Detect the language of this text:\n\n{text[:1000]}"
        
        response = self.call_ollama_api(
            model=self.settings.ollama_text_model,
            prompt=prompt,
            system_prompt=system_prompt
        )
        
        if response and 'response' in response:
            return self.parse_json_response(response['response'])
        
        return None
    
    def analyze(self, content: str) -> Optional[Dict[str, Any]]:
        """General text analysis method."""
        if not content:
            return None
        
        results = {}
        
        # Run all analysis types
        sentiment = self.analyze_sentiment(content)
        if sentiment:
            results['sentiment'] = sentiment
        
        topics = self.analyze_topics(content)
        if topics:
            results['topics'] = topics
        
        entities = self.extract_entities(content)
        if entities:
            results['entities'] = entities
        
        language = self.detect_language(content)
        if language:
            results['language'] = language
        
        return results if results else None
    
    def _save_content_analysis(self, page_id: int, analysis_type: str, results: Dict[str, Any]):
        """Save analysis results to database."""
        db_session = get_db_session()
        
        try:
            analysis = ContentAnalysis(
                page_id=page_id,
                analysis_type=analysis_type,
                model_name=self.settings.ollama_text_model,
                analysis_result=results,
                confidence_score=self._extract_average_confidence(results),
                created_at=datetime.utcnow()
            )
            
            db_session.add(analysis)
            db_session.commit()
            
        except Exception as e:
            self.logger.error(f"Error saving content analysis: {e}")
            db_session.rollback()
        finally:
            db_session.close()
    
    def _save_entities(self, page_id: int, entities_result: Dict[str, Any]):
        """Save extracted entities to database."""
        if 'entities' not in entities_result:
            return
        
        db_session = get_db_session()
        
        try:
            for entity_data in entities_result['entities']:
                if isinstance(entity_data, dict):
                    entity = Entity(
                        page_id=page_id,
                        entity_type=entity_data.get('type', 'UNKNOWN'),
                        entity_text=entity_data.get('text', ''),
                        confidence_score=entity_data.get('confidence', 0.0),
                        created_at=datetime.utcnow()
                    )
                    
                    db_session.add(entity)
            
            db_session.commit()
            
        except Exception as e:
            self.logger.error(f"Error saving entities: {e}")
            db_session.rollback()
        finally:
            db_session.close()
    
    def _extract_average_confidence(self, results: Dict[str, Any]) -> float:
        """Extract average confidence score from results."""
        confidences = []
        
        for analysis_type, data in results.items():
            if isinstance(data, dict) and 'confidence' in data:
                try:
                    confidences.append(float(data['confidence']))
                except (ValueError, TypeError):
                    continue
        
        return sum(confidences) / len(confidences) if confidences else 0.0
