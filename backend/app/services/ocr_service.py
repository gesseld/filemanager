"""OCR service for extracting text from images using Tesseract and Mistral OCR."""
from .base import BaseService
import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import requests
import pytesseract
from PIL import Image
import cv2
import numpy as np
import subprocess

from app.core.config import settings

# Configure pytesseract to use WSL Tesseract
pytesseract.tesseract_cmd = 'wsl /usr/bin/tesseract'

class OCRService(BaseService):
    """Service for extracting text from images using OCR."""
    
    def __init__(self):
        """Initialize OCR service with Tesseract and Mistral configuration."""
        super().__init__()
        self.mistral_api_key = self.config.mistral_api_key
        self.mistral_api_url = self.config.mistral_api_url
        self.timeout = 300  # 5 minutes timeout
        
    def health_check(self) -> dict:
        """Check OCR service health including Tesseract availability."""
        status = {
            "service": "OCRService",
            "tesseract_available": self._check_tesseract_health(),
            "mistral_configured": bool(self.mistral_api_key),
            "status": "healthy"
        }
        
        if not status["tesseract_available"]:
            status["status"] = "degraded"
            status["warning"] = "Tesseract not available via WSL"
            
        if not status["mistral_configured"]:
            status["status"] = "degraded"
            status["warning"] = "Mistral API key not configured"
            
        return status
        
    async def extract_image_text(self, image_path: str, language: str = "eng") -> Tuple[str, Dict[str, Any]]:
        """
        Extract text from an image using OCR.
        
        Args:
            image_path: Path to the image file
            language: Language code for OCR (default: eng)
            
        Returns:
            Tuple of (extracted_text, metadata_dict)
            
        Raises:
            Exception: If OCR extraction fails
        """
        try:
            # Try Tesseract first
            text, metadata = await self._extract_with_tesseract(image_path, language)
            
            if text and len(text.strip()) > 10:
                logger.info(f"Successfully extracted text using Tesseract: {len(text)} chars")
                return text, metadata
            else:
                # Fallback to Mistral OCR
                logger.info("Tesseract extraction yielded poor results, falling back to Mistral OCR")
                return await self._extract_with_mistral(image_path, language)
                
        except Exception as e:
            logger.error(f"Error extracting text from image {image_path}: {e}")
            # Final fallback to Mistral OCR
            return await self._extract_with_mistral(image_path, language)
    
    async def _extract_with_tesseract(self, image_path: str, language: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text using Tesseract OCR service."""
        try:
            with open(image_path, 'rb') as f:
                files = {'file': f}
                data = {'lang': language}
                response = requests.post(
                    f"{TESSERACT_URL}/tesseract",
                    files=files,
                    data=data,
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()
                text = result.get('text', '').strip()
            
            # Calculate confidence based on text quality metrics
            metadata = {
                'engine': 'tesseract',
                'language': language,
                'confidence': self._calculate_tesseract_confidence(text),
                'word_count': len(text.split()),
                'character_count': len(text),
                'empty_lines': text.count('\n\n')
            }
            
            return text, metadata
                
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {e}")
            raise
    
    async def _extract_with_mistral(self, image_path: str, language: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text using Mistral OCR API."""
        try:
            # Read and encode image
            with open(image_path, 'rb') as file:
                image_data = base64.b64encode(file.read()).decode('utf-8')
            
            # Determine MIME type
            mime_type = self._get_image_mime_type(image_path)
            
            payload = {
                'image': f"data:{mime_type};base64,{image_data}",
                'language': language,
                'model': 'mistral-ocr-latest'
            }
            
            headers = {
                'Authorization': f'Bearer {self.mistral_api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                self.mistral_api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"Mistral OCR failed: {response.status_code} - {response.text}")
            
            result = response.json()
            text = result.get('text', '').strip()
            
            metadata = {
                'engine': 'mistral',
                'language': language,
                'confidence': result.get('confidence', 0.0),
                'word_count': len(text.split()),
                'character_count': len(text),
                'model': result.get('model', 'unknown'),
                'processing_time': result.get('processing_time', 0)
            }
            
            logger.info(f"Successfully extracted text using Mistral OCR: {len(text)} chars")
            return text, metadata
            
        except Exception as e:
            logger.error(f"Mistral OCR extraction failed: {e}")
            raise
    
    def _check_tesseract_health(self) -> bool:
        """Check if Tesseract is available via WSL."""
        try:
            result = subprocess.run(
                ['wsl', 'which', 'tesseract'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _calculate_tesseract_confidence(self, text: str) -> float:
        """Calculate confidence score for Tesseract extraction."""
        if not text:
            return 0.0
        
        # Simple heuristic based on text characteristics
        words = text.split()
        if not words:
            return 0.0
        
        # Check for common OCR errors
        avg_word_length = sum(len(word) for word in words) / len(words)
        if avg_word_length < 2:
            return 0.3
        
        # Check for special characters ratio
        special_chars = sum(1 for char in text if not char.isalnum() and not char.isspace())
        special_ratio = special_chars / len(text)
        
        if special_ratio > 0.3:
            return 0.4
        
        # Base confidence
        confidence = min(0.9, len(text) / 1000)
        return max(0.1, confidence)
    
    def _get_image_mime_type(self, image_path: str) -> str:
        """Get MIME type from image file extension."""
        extension = Path(image_path).suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.bmp': 'image/bmp',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return mime_types.get(extension, 'image/jpeg')
    
    def is_supported_image(self, mime_type: str) -> bool:
        """Check if the MIME type is a supported image format."""
        supported_types = {
            'image/jpeg',
            'image/png',
            'image/tiff',
            'image/bmp',
            'image/gif',
            'image/webp'
        }
        return mime_type in supported_types
    
    def preprocess_image(self, image_path: str) -> str:
        """Preprocess image for better OCR results."""
        try:
            # Read image with OpenCV
            image = cv2.imread(image_path)
            if image is None:
                return image_path
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply noise reduction
            denoised = cv2.medianBlur(gray, 5)
            
            # Apply threshold to get better contrast
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Save preprocessed image
            preprocessed_path = str(Path(image_path).with_suffix('.preprocessed.jpg'))
            cv2.imwrite(preprocessed_path, thresh)
            
            return preprocessed_path
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return image_path


# Global OCR service instance
ocr_service = OCRService()
