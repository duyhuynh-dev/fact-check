"""Semantic/conceptual analysis for detecting coded antisemitic language."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.app.core.config import get_settings


@dataclass
class SemanticAnalysis:
    """Results of semantic analysis of text."""

    is_antisemitic: bool
    confidence: float  # 0.0-1.0
    detected_patterns: list[str]  # e.g., ["conspiracy_trope", "dog_whistle", "dual_loyalty"]
    explanation: str
    coded_language_detected: bool
    implicit_meaning: str | None = None
    tone: str | None = None  # e.g., "threatening", "hostile", "neutral", "informative"
    emotional_weight: str | None = None  # e.g., "high", "medium", "low"
    intent: str | None = None  # Description of what the text is trying to do


class SemanticAnalyzer(Protocol):
    """Interface for semantic analysis."""

    def analyze(self, text: str, context: str | None = None) -> SemanticAnalysis: ...


class LLMSemanticAnalyzer:
    """Uses LLM to analyze semantic meaning and detect coded antisemitic language."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model

        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY required for semantic analysis")

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
        except ImportError:
            raise ImportError(
                "google-generativeai not installed. Install with: poetry add google-generativeai"
            )

    def analyze(self, text: str, context: str | None = None) -> SemanticAnalysis:
        """Analyze text for antisemitic content, including coded language and implicit meaning."""
        context_text = f"\n\nContext from surrounding text:\n{context}" if context else ""

        prompt = f"""You are an expert in identifying antisemitic content, analyzing tone, intent, and meaning.

CRITICAL: Analyze the TONE, INTENT, and CONTENT of this text. Pay special attention to how it FEELS and what it's trying to DO.

TEXT TO ANALYZE:
{text}{context_text}

STEP 1: TONE ANALYSIS
Analyze the emotional tone:
- Is it threatening, hostile, aggressive, menacing, or intimidating?
- Does it carry anger, hatred, contempt, or malice?
- Is it neutral/informative or emotionally charged?
- Look for language suggesting violence, harm, or conflict (e.g., "war", "threaten", "show you", "get you", "this ain't a game")

STEP 2: INTENT ANALYSIS
What is the text trying to accomplish?
- Intimidate or threaten Jewish people?
- Spread conspiracy theories?
- Blame or scapegoat?
- Make a factual statement?
- What is the underlying message?

STEP 3: ANTISEMITIC INDICATORS
Look for:
1. THREATENING LANGUAGE directed at Jewish people (e.g., "war", "threaten", "example", "show you", "get you", "influence me", "this is war")
2. Coded language and dog whistles (terms with antisemitic meaning in context)
3. Implicit messaging (suggestions without explicit statements)
4. Conspiracy theory patterns (especially about Jews controlling organizations)
5. Dual loyalty tropes
6. Scapegoating language
7. Historical antisemitic tropes used in modern contexts
8. Money-related stereotypes (financial engineering, making money, etc.)

IMPORTANT: Analyze the FULL text together. Don't just look at individual sentences - understand the complete context, tone, and intent.

Provide your analysis as JSON with these fields:
{{
  "is_antisemitic": <boolean>,
  "confidence": <0.0-1.0>,
  "tone": "<threatening | hostile | aggressive | menacing | neutral | informative>",
  "emotional_weight": "<high | medium | low>",
  "intent": "<detailed description of what the text is trying to do>",
  "detected_patterns": [<array of pattern names>],
  "explanation": "<detailed explanation including tone, intent, and why this is antisemitic>",
  "coded_language_detected": <boolean>,
  "implicit_meaning": "<what the text implicitly suggests, if any>"
}}

Pattern names can include: "conspiracy_trope", "dog_whistle", "dual_loyalty", "scapegoating", "blood_libel", "secret_control", "historical_trope", "coded_language", "money_trope", "financial_stereotype", "threatening_language"

Pay special attention to:
- Threatening language directed at Jewish people (very high priority) - analyze the TONE
- References to money, finance, or "financial engineering" in connection with Jewish people, Jewish holidays, or Jewish culture
- Stereotypes about Jews being motivated by money or primarily interested in financial gain
- Coded references to Jewish people through money-related language
- Conspiracy theories claiming Jews control organizations or institutions
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
            import re

            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # Fallback: try to extract fields from malformed JSON
                content_lower = content.lower()
                tone = None
                if "threatening" in content_lower:
                    tone = "threatening"
                elif "hostile" in content_lower:
                    tone = "hostile"
                elif "neutral" in content_lower:
                    tone = "neutral"
                
                emotional_weight = None
                if "high" in content_lower and "emotional" in content_lower:
                    emotional_weight = "high"
                elif "medium" in content_lower:
                    emotional_weight = "medium"
                elif "low" in content_lower:
                    emotional_weight = "low"
                
                is_antisemitic = "antisemitic" in content_lower or "true" in content_lower
                
                data = {
                    "is_antisemitic": is_antisemitic,
                    "confidence": 0.7 if is_antisemitic else 0.0,
                    "tone": tone,
                    "emotional_weight": emotional_weight,
                    "detected_patterns": ["threatening_language"] if tone == "threatening" else [],
                    "explanation": "Analysis completed but JSON parsing had issues",
                    "coded_language_detected": False,
                    "implicit_meaning": None,
                }

            return SemanticAnalysis(
                is_antisemitic=data.get("is_antisemitic", False),
                confidence=data.get("confidence", 0.0),
                detected_patterns=data.get("detected_patterns", []),
                explanation=data.get("explanation", ""),
                coded_language_detected=data.get("coded_language_detected", False),
                implicit_meaning=data.get("implicit_meaning"),
                tone=data.get("tone"),
                emotional_weight=data.get("emotional_weight"),
                intent=data.get("intent"),
            )
        except Exception as e:
            # Fallback: return neutral analysis
            return SemanticAnalysis(
                is_antisemitic=False,
                confidence=0.0,
                detected_patterns=[],
                explanation=f"Analysis failed: {str(e)}",
                coded_language_detected=False,
            )


class HeuristicSemanticAnalyzer:
    """Rule-based semantic analyzer (fallback when LLM unavailable)."""

    def analyze(self, text: str, context: str | None = None) -> SemanticAnalysis:
        """Basic heuristic analysis."""
        text_lower = text.lower()

        # Coded language patterns
        coded_patterns = [
            ("they", "them", "those people"),  # Vague references
            ("international", "global", "network"),  # Conspiracy language
            ("behind the scenes", "shadow", "secret"),
            ("control", "influence", "manipulate"),
        ]

        detected = []
        coded_detected = False

        # Define Jewish indicators early (used in multiple checks)
        # Include variations and common phrases
        jewish_indicators = [
            "jewish", "jew", "jews", "the jewish", "jewish people", "jewish person",
            "hanukkah", "hanukah", "hannukah", "kushner", 
            "zionist", "zionism", "judah", "judaism", "hebrew", "israeli"
        ]

        # Check for vague references with negative context
        if any(word in text_lower for word in ["they", "them"]) and any(
            word in text_lower for word in ["control", "influence", "responsible", "blame"]
        ):
            detected.append("coded_language")
            coded_detected = True

        # Check for conspiracy patterns
        conspiracy_keywords = ["secret", "conspiracy", "plot", "network", "control", "kkk", "klan"]
        if any(word in text_lower for word in conspiracy_keywords):
            detected.append("conspiracy_trope")
        
        # Check for antisemitic conspiracy theories (control + Jewish reference)
        control_keywords = ["control", "dominate", "manipulate", "influence", "run", "own"]
        has_control_language = any(word in text_lower for word in control_keywords)
        has_jewish_reference = any(indicator in text_lower for indicator in jewish_indicators)
        
        # If text talks about "controlling" + Jewish people, it's an antisemitic conspiracy trope
        if has_control_language and has_jewish_reference:
            if "conspiracy_trope" not in detected:
                detected.append("conspiracy_trope")
            detected.append("secret_control")
            coded_detected = True

        # Check for scapegoating
        if any(
            phrase in text_lower
            for phrase in ["bear responsibility", "to blame", "caused", "responsible for"]
        ):
            detected.append("scapegoating")

        # Check for threatening language directed at Jewish people
        # More comprehensive threat detection
        threat_indicators = [
            "war", "threaten", "threatening", "example", "show", "get you", "gone get",
            "use you", "influence me", "no one can", "imma use", "this is war",
            "show you", "show the", "told you", "this ain't a game"
        ]
        has_threat_language = any(indicator in text_lower for indicator in threat_indicators)
        
        # Also check for threatening patterns even without explicit "jewish" if context suggests it
        # Pattern: threatening language + "jewish" or "jew" anywhere in text
        has_jewish_reference = any(indicator in text_lower for indicator in jewish_indicators)
        
        # Special case: if text has "jewish" + threatening language, it's antisemitic
        # Even if "jewish" appears in a different part of the sentence
        if has_threat_language and has_jewish_reference:
            detected.append("threatening_language")
            coded_detected = True
            # Also mark as conspiracy/control if it mentions "influence" or "control"
            if any(word in text_lower for word in ["influence", "control", "threaten"]):
                detected.append("secret_control")
                if "conspiracy_trope" not in detected:
                    detected.append("conspiracy_trope")
        
        # Check for money-related antisemitic tropes
        money_trope_indicators = [
            "financial engineering", "making money", "about money", "all about money",
            "money", "finance", "banking", "financial", "financial gain"
        ]
        
        # Also check for implicit Jewish references through context
        # If text mentions a Jewish holiday alongside money references, it's likely antisemitic
        has_jewish_holiday = any(holiday in text_lower for holiday in ["hanukkah", "hanukah", "hannukah", "passover", "yom kippur", "rosh hashanah"])
        
        has_money_reference = any(indicator in text_lower for indicator in money_trope_indicators)
        has_jewish_reference = any(indicator in text_lower for indicator in jewish_indicators)
        
        # If text mentions money/finance AND Jewish people/holidays, likely money trope
        # Also catch cases where Jewish holiday is mentioned with money references (even if "jewish" not explicitly stated)
        if (has_money_reference and has_jewish_reference) or (has_money_reference and has_jewish_holiday):
            detected.append("money_trope")
            coded_detected = True

        is_antisemitic = len(detected) > 0
        # Money tropes, conspiracy tropes, and threatening language are particularly harmful
        if "threatening_language" in detected:
            confidence = 0.90  # Very high confidence for threatening language directed at Jews
        elif "money_trope" in detected:
            confidence = 0.75  # High confidence for money-related antisemitic tropes
        elif "conspiracy_trope" in detected and has_jewish_reference:
            confidence = 0.85  # Very high confidence for antisemitic conspiracy theories
        elif "secret_control" in detected:
            confidence = 0.90  # Very high confidence for control conspiracies
        else:
            confidence = min(len(detected) * 0.3, 0.9) if is_antisemitic else 0.0
        
        # Analyze tone
        tone = "neutral"
        emotional_weight = "low"
        if "threatening_language" in detected:
            tone = "threatening"
            emotional_weight = "high"
        elif "conspiracy_trope" in detected and has_jewish_reference:
            tone = "hostile"
            emotional_weight = "medium"
        elif coded_detected:
            tone = "hostile"
            emotional_weight = "medium"
        
        # Analyze intent
        intent_parts = []
        if "threatening_language" in detected:
            intent_parts.append("To intimidate or threaten Jewish people")
        if "conspiracy_trope" in detected:
            intent_parts.append("To spread conspiracy theories about Jews")
        if "money_trope" in detected:
            intent_parts.append("To perpetuate antisemitic money stereotypes")
        if "secret_control" in detected:
            intent_parts.append("To suggest Jews control or influence things")
        intent = ". ".join(intent_parts) if intent_parts else "To communicate a message"
        
        # Build explanation
        explanation_parts = []
        if "threatening_language" in detected:
            explanation_parts.append("Contains threatening language directed at Jewish people.")
        if "conspiracy_trope" in detected:
            explanation_parts.append("Uses antisemitic conspiracy theories.")
        if "money_trope" in detected:
            explanation_parts.append("Uses antisemitic money-related stereotypes.")
        if "secret_control" in detected:
            explanation_parts.append("Suggests Jewish people control or influence things.")
        if coded_detected:
            explanation_parts.append("Uses coded language or dog whistles.")
        
        explanation = " ".join(explanation_parts) if explanation_parts else "Heuristic analysis based on pattern matching"

        return SemanticAnalysis(
            is_antisemitic=is_antisemitic,
            confidence=confidence,
            detected_patterns=detected,
            explanation=explanation,
            coded_language_detected=coded_detected,
            tone=tone,
            emotional_weight=emotional_weight,
            intent=intent,
        )


def create_semantic_analyzer() -> SemanticAnalyzer:
    """Factory to create appropriate semantic analyzer."""
    settings = get_settings()

    if settings.gemini_api_key:
        return LLMSemanticAnalyzer()
    else:
        return HeuristicSemanticAnalyzer()

