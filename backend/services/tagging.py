"""Document tagging service using AI."""

import logging
import json
from typing import List, Optional

from openai import OpenAI
from openai.types.chat import ChatCompletion

from ..config import settings
from ..models.document import Document
from ..exceptions import TaggingError

logger = logging.getLogger(__name__)

class TaggingService:
    """Service for generating document tags using AI."""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE
    
    def tag_document(self, document: Document) -> List[str]:
        """Generate tags for a document based on its content.
        
        Args:
            document: Document to tag
            
        Returns:
            List of generated tags
            
        Raises:
            TaggingError: If tagging fails
        """
        if not document.ocr_text or not document.ocr_text.strip():
            raise TaggingError("Document has no text content to analyze")
        
        try:
            prompt = f"""
            Analyze the following document text and generate 3-5 relevant tags.
            Return ONLY a JSON array of tag strings.
            
            Document text:
            {document.ocr_text}
            """
            
            response: ChatCompletion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful document tagging assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            if not response.choices:
                raise TaggingError("No response from tagging service")
                
            content = response.choices[0].message.content
            if not content:
                raise TaggingError("Empty response from tagging service")
                
            try:
                tags = json.loads(content)
                if not isinstance(tags, list):
                    raise ValueError("Response is not a list")
                    
                return [str(tag) for tag in tags]
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse tags: {str(e)}")
                raise TaggingError("Invalid tag response format")
                
        except Exception as e:
            logger.error(f"Tagging failed: {str(e)}")
            raise TaggingError(f"Tagging service error: {str(e)}")