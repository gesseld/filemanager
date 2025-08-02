from typing import List
import spacy
from transformers import pipeline

class TaggingService:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli"
        )
    
    def auto_tag(self, text: str) -> List[str]:
        """Extract tags from text using NER and zero-shot classification"""
        doc = self.nlp(text)
        entities = [ent.text for ent in doc.ents]
        
        # Load candidate labels from config
        with open("config/tag_labels.yaml") as f:
            candidate_labels = yaml.safe_load(f)
        
        # Classify text against candidate labels
        classification = self.classifier(text, candidate_labels)
        return list(set(entities + classification["labels"]))