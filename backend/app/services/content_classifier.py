"""Content classification to detect religious texts, myths, and non-factual content."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ContentClassification:
    """Classification result for document content."""

    is_religious_text: bool
    is_mythological: bool
    is_historical_fiction: bool
    is_factual_claim: bool
    confidence: float  # 0.0-1.0
    content_type: str  # "religious", "mythological", "fiction", "factual", "mixed"
    explanation: str


class ContentClassifier(Protocol):
    """Interface for content classification."""

    def classify(self, text: str) -> ContentClassification: ...


class HeuristicContentClassifier:
    """Rule-based classifier for religious/mythological content."""

    # Religious text indicators (expanded list)
    religious_indicators = [
        # Book names
        "genesis", "exodus", "leviticus", "numbers", "deuteronomy",
        # Common phrases
        "in the beginning", "god created", "god said", "the lord", "and god",
        "let there be", "it was good", "god saw", "god called",
        # Religious terms
        "bible", "torah", "talmud", "quran", "scripture", "holy book",
        "verse", "chapter", "psalm", "prophet", "apostle", "gospel",
        # Religious figures
        "jesus", "moses", "abraham", "isaac", "jacob", "david", "adam", "eve",
        "adam and eve", "noah", "ark", "covenant", "testament",
        # Religious concepts
        "heaven", "earth", "firmament", "waters", "light", "darkness",
        "day and night", "beast", "creature", "fowl", "herb", "fruit"
    ]

    # Mythological indicators
    mythological_indicators = [
        "once upon a time", "legend", "myth", "fable", "tale",
        "ancient story", "creation story", "origin story"
    ]

    def classify(self, text: str) -> ContentClassification:
        """Classify content type using heuristics."""
        text_lower = text.lower()
        
        # Check for religious text
        religious_matches = sum(1 for indicator in self.religious_indicators if indicator in text_lower)
        # More lenient: if we find key phrases like "in the beginning" + "god created", it's likely religious
        has_beginning_phrase = any(phrase in text_lower for phrase in ["in the beginning", "god created", "and god"])
        is_religious = religious_matches >= 2 or (has_beginning_phrase and religious_matches >= 1)
        
        # Check for mythological content
        mythological_matches = sum(1 for indicator in self.mythological_indicators if indicator in text_lower)
        is_mythological = mythological_matches >= 2
        
        # Determine content type
        if is_religious:
            content_type = "religious"
            confidence = min(0.7 + (religious_matches * 0.05), 0.95)
            explanation = f"Detected religious text indicators (e.g., biblical references, religious terminology)"
        elif is_mythological:
            content_type = "mythological"
            confidence = min(0.6 + (mythological_matches * 0.1), 0.9)
            explanation = "Detected mythological or legendary content"
        else:
            content_type = "factual"
            confidence = 0.5
            explanation = "Appears to be factual content"
        
        return ContentClassification(
            is_religious_text=is_religious,
            is_mythological=is_mythological,
            is_historical_fiction=False,  # Could be enhanced
            is_factual_claim=not (is_religious or is_mythological),
            confidence=confidence,
            content_type=content_type,
            explanation=explanation,
        )


class LLMContentClassifier:
    """LLM-based classifier for more accurate detection."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        from backend.app.core.config import get_settings
        
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model

        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY required for LLM classification")

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
        except ImportError:
            raise ImportError("google-generativeai not installed")

    def classify(self, text: str) -> ContentClassification:
        """Classify content using LLM."""
        # Sample first 2000 chars for classification
        sample_text = text[:2000] + ("..." if len(text) > 2000 else "")
        
        prompt = f"""Classify the following text content. Determine if it is:
1. Religious text (Bible, Torah, Quran, religious scripture)
2. Mythological/legendary content
3. Historical fiction
4. Factual claims about real events

TEXT:
{sample_text}

Respond with JSON:
{{
  "is_religious_text": <boolean>,
  "is_mythological": <boolean>,
  "is_historical_fiction": <boolean>,
  "is_factual_claim": <boolean>,
  "content_type": "<religious|mythological|fiction|factual|mixed>",
  "confidence": <0.0-1.0>,
  "explanation": "<brief explanation>"
}}
"""

        try:
            response = self.client.generate_content(prompt)
            content = response.text.strip()
            
            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            import json
            data = json.loads(content)
            
            return ContentClassification(
                is_religious_text=data.get("is_religious_text", False),
                is_mythological=data.get("is_mythological", False),
                is_historical_fiction=data.get("is_historical_fiction", False),
                is_factual_claim=data.get("is_factual_claim", True),
                confidence=data.get("confidence", 0.5),
                content_type=data.get("content_type", "factual"),
                explanation=data.get("explanation", ""),
            )
        except Exception:
            # Fallback to heuristic
            classifier = HeuristicContentClassifier()
            return classifier.classify(text)


def create_content_classifier() -> ContentClassifier:
    """Factory to create appropriate classifier."""
    from backend.app.core.config import get_settings
    settings = get_settings()
    
    if settings.gemini_api_key:
        try:
            return LLMContentClassifier()
        except Exception:
            pass
    
    return HeuristicContentClassifier()

