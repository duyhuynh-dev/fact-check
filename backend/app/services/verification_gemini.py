"""Gemini API-based verification service (free tier available)."""

from __future__ import annotations

import json
from sqlmodel import Session

from backend.app.core.config import get_settings
from backend.app.db.models import Claim
from backend.app.services.rag import EvidenceRetriever, create_default_evidence_retriever


class GeminiClaimVerifier:
    """Verifies claims using Google Gemini API (free tier available)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        evidence_retriever: EvidenceRetriever | None = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.evidence_retriever = evidence_retriever or create_default_evidence_retriever()

        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY required for Gemini verification")

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
        except ImportError:
            raise ImportError(
                "google-generativeai not installed. Install with: poetry add google-generativeai"
            )

    def verify(self, claim: Claim, session: Session) -> Claim:
        """Verify a claim: FIRST analyze with LLM for antisemitic content, THEN fact-check if needed."""
        from backend.app.core.config import get_settings
        
        settings = get_settings()
        
        # STEP 1: LLM ANALYSIS FIRST - Determine if content is antisemitic or a factual claim
        # This is the PRIMARY analysis - LLM analyzes tone, intent, and content type
        analysis_prompt = f"""You are an expert in identifying antisemitic content and analyzing text tone, intent, and meaning.

CRITICAL TASK: Analyze this text's TONE, INTENT, and CONTENT TYPE. Pay special attention to how the text FEELS and what it's trying to DO.

TEXT TO ANALYZE:
{claim.text}

STEP 1: TONE ANALYSIS
Analyze the emotional tone and attitude:
- Is the tone threatening, hostile, aggressive, or menacing?
- Is there anger, hatred, or contempt?
- Is it neutral/informative or does it carry emotional weight?
- Does it use language that suggests violence, intimidation, or harm?
- Look for: "war", "threaten", "show you", "get you", "example", "influence me", "this ain't a game"

STEP 2: INTENT ANALYSIS
What is the text trying to accomplish?
- Is it trying to intimidate or threaten?
- Is it trying to spread conspiracy theories?
- Is it trying to blame or scapegoat?
- Is it trying to make a factual statement?
- What is the underlying message or purpose?

STEP 3: ANTISEMITIC INDICATORS
Look for these specific patterns:
- Threatening language + references to "Jewish people" or "Jews"
- Conspiracy theories about Jews controlling things
- Stereotypes about Jews (money, power, influence)
- Coded language or dog whistles
- Hostile intent toward Jewish people or groups
- Language that suggests "war" or conflict with Jewish people

STEP 4: CONTENT CLASSIFICATION
Based on tone, intent, and indicators:
- If threatening/hostile + mentions Jews → ANTISEMITIC (content_type: "antisemitic_trope")
- If conspiracy theory about Jews → ANTISEMITIC (content_type: "antisemitic_trope")
- If factual claim about history → FACTUAL (content_type: "factual_claim")
- If religious/mythological → NOT APPLICABLE (content_type: "not_applicable")

Respond with VALID JSON only (no markdown, no extra text):
{{
  "is_antisemitic": true or false,
  "is_factual_claim": true or false,
  "content_type": "antisemitic_trope" or "factual_claim" or "not_applicable",
  "tone": "threatening" or "hostile" or "aggressive" or "menacing" or "neutral" or "informative",
  "emotional_weight": "high" or "medium" or "low",
  "intent": "detailed description of what the text is trying to do",
  "detected_patterns": ["pattern1", "pattern2"] or [],
  "confidence": 0.0 to 1.0,
  "explanation": "detailed explanation including tone, intent, and why it's antisemitic or not"
}}

TONE EXAMPLES:
- "This is war against Jewish people" → tone: "threatening", emotional_weight: "high", is_antisemitic: true
- "This ain't a game. Imma use you as an example to show the Jewish people..." → tone: "threatening", emotional_weight: "high", is_antisemitic: true
- "Jews control the media" → tone: "hostile", emotional_weight: "medium", is_antisemitic: true
- "The Holocaust happened in 1941-1945" → tone: "informative", emotional_weight: "low", is_antisemitic: false
"""

        try:
            analysis_response = self.client.generate_content(analysis_prompt)
            analysis_content = analysis_response.text.strip()
            
            # Extract JSON - try multiple methods
            json_start = None
            json_end = None
            
            if "```json" in analysis_content:
                json_start = analysis_content.find("```json") + 7
                json_end = analysis_content.find("```", json_start)
            elif "```" in analysis_content:
                json_start = analysis_content.find("```") + 3
                json_end = analysis_content.find("```", json_start)
            elif "{" in analysis_content:
                json_start = analysis_content.find("{")
                json_end = analysis_content.rfind("}") + 1
            
            if json_start is not None and json_end is not None and json_end > json_start:
                analysis_content = analysis_content[json_start:json_end].strip()
            
            import json
            import re
            try:
                analysis_data = json.loads(analysis_content)
            except json.JSONDecodeError as json_err:
                # Enhanced fallback: Extract tone and intent from text even if JSON is malformed
                content_lower = analysis_content.lower()
                
                # Extract tone from response text
                tone = "neutral"
                if "threatening" in content_lower:
                    tone = "threatening"
                elif "hostile" in content_lower or "aggressive" in content_lower:
                    tone = "hostile"
                elif "menacing" in content_lower:
                    tone = "menacing"
                elif "informative" in content_lower or "neutral" in content_lower:
                    tone = "informative"
                
                # Extract emotional weight
                emotional_weight = "low"
                if "high" in content_lower and ("emotional" in content_lower or "weight" in content_lower):
                    emotional_weight = "high"
                elif "medium" in content_lower:
                    emotional_weight = "medium"
                
                # Detect antisemitic indicators
                is_antisemitic = (
                    "antisemitic" in content_lower or
                    "antisemitic_trope" in content_lower or
                    '"is_antisemitic": true' in analysis_content or
                    '"is_antisemitic":true' in analysis_content or
                    (tone in ["threatening", "hostile", "menacing"] and any(word in content_lower for word in ["jewish", "jew", "war", "threaten"]))
                )
                
                # Extract intent from response
                intent_match = re.search(r'"intent":\s*"([^"]+)"', analysis_content, re.IGNORECASE)
                intent = intent_match.group(1) if intent_match else "Unable to determine intent"
                
                # Extract patterns
                patterns = []
                if "threatening" in content_lower or "war" in content_lower:
                    patterns.append("threatening_language")
                if "conspiracy" in content_lower:
                    patterns.append("conspiracy_trope")
                if "control" in content_lower:
                    patterns.append("secret_control")
                
                # Extract explanation
                explanation_match = re.search(r'"explanation":\s*"([^"]+)"', analysis_content, re.IGNORECASE)
                explanation = explanation_match.group(1) if explanation_match else f"Content appears {tone} with {emotional_weight} emotional weight. {intent}"
                
                content_type = "antisemitic_trope" if is_antisemitic else "factual_claim"
                
                # If we detect antisemitic indicators, treat as antisemitic
                if is_antisemitic or (tone in ["threatening", "hostile", "menacing"] and any(word in content_lower for word in ["jewish", "jew"])):
                    analysis_data = {
                        "is_antisemitic": True,
                        "content_type": "antisemitic_trope",
                        "tone": tone,
                        "emotional_weight": emotional_weight,
                        "intent": intent,
                        "detected_patterns": patterns if patterns else ["threatening_language"],
                        "confidence": 0.85 if tone in ["threatening", "hostile", "menacing"] else 0.7,
                        "explanation": explanation,
                    }
                else:
                    # If not clearly antisemitic, try to continue with fact-checking
                    analysis_data = {
                        "is_antisemitic": False,
                        "content_type": "factual_claim",
                        "tone": tone,
                        "emotional_weight": emotional_weight,
                        "intent": intent,
                        "detected_patterns": [],
                        "confidence": 0.5,
                        "explanation": explanation,
                    }
            
            # STEP 2: If antisemitic, flag immediately (NO evidence lookup needed)
            if analysis_data.get("is_antisemitic", False) or analysis_data.get("content_type") == "antisemitic_trope":
                patterns = analysis_data.get("detected_patterns", [])
                explanation = analysis_data.get("explanation", "Content contains antisemitic messaging.")
                intent = analysis_data.get("intent", "")
                tone = analysis_data.get("tone", "")
                emotional_weight = analysis_data.get("emotional_weight", "")
                
                # Get educational context about the trope (not for verification, for explanation)
                trope_evidence = self.evidence_retriever.retrieve(
                    f"antisemitic trope {', '.join(patterns) if patterns else 'antisemitic content'}",
                    limit=2,
                    min_similarity=0.2
                )
                trope_context = "\n\n".join([e.snippet for e in trope_evidence]) if trope_evidence else ""
                
                # Build comprehensive rationale with tone analysis
                rationale_parts = [f"This content is antisemitic. {explanation}"]
                
                if tone:
                    rationale_parts.append(f"Tone: {tone}")
                if emotional_weight:
                    rationale_parts.append(f"Emotional weight: {emotional_weight}")
                if intent:
                    rationale_parts.append(f"Intent: {intent}")
                if patterns:
                    rationale_parts.append(f"Detected patterns: {', '.join(patterns)}")
                if trope_context:
                    rationale_parts.append(f"\n\nContext: {trope_context}")
                
                rationale = ". ".join([p for p in rationale_parts if p])
                
                claim.verdict = "antisemitic_trope"
                claim.rationale = rationale
                claim.score = None
                if claim.metadata_json is None:
                    claim.metadata_json = {}
                claim.metadata_json["llm_analysis"] = analysis_data
                claim.metadata_json["antisemitic_trope_detected"] = True
                session.add(claim)
                session.commit()
                session.refresh(claim)
                return claim
            
            # STEP 3: If not antisemitic, check if it's a factual claim to verify
            # Only retrieve evidence for factual claims
            if analysis_data.get("content_type") == "not_applicable":
                # Religious/mythological content
                claim.verdict = "not_applicable"
                claim.rationale = analysis_data.get("explanation", "This is not a factual claim to verify.")
                claim.score = None
                if claim.metadata_json is None:
                    claim.metadata_json = {}
                claim.metadata_json["llm_analysis"] = analysis_data
                session.add(claim)
                session.commit()
                session.refresh(claim)
                return claim
            
            # STEP 4: For factual claims, retrieve evidence and compare
            evidence = self.evidence_retriever.retrieve(
                claim.text, 
                limit=settings.evidence_retrieval_limit,
                min_similarity=settings.evidence_min_similarity
            )

            evidence_text = "\n\n".join(
                [
                    f"[{e.source_name}" + (f" - {e.author}" if e.author else "") + f"]: {e.snippet}"
                    + (f"\n  Citation: {e.citation}" if e.citation else "")
                    for e in evidence
                ]
            ) if evidence else "No evidence retrieved from knowledge base."

            # LLM fact-checking prompt
            fact_check_prompt = f"""You are a fact-checker specializing in antisemitism and Jewish history.

Based on the LLM analysis, this appears to be a factual claim. Verify it against the evidence.

TEXT TO VERIFY:
{claim.text}

LLM ANALYSIS:
- Content Type: {analysis_data.get('content_type', 'factual_claim')}
- Tone: {analysis_data.get('tone', 'unknown')}
- Intent: {analysis_data.get('intent', 'unknown')}

EVIDENCE FROM KNOWLEDGE BASE:
{evidence_text}

Provide your response as JSON:
{{
  "verdict": "supported" | "partial" | "contradicted" | "no_evidence",
  "rationale": "explanation based on evidence",
  "score": <0-100>
}}
"""
            
            fact_check_response = self.client.generate_content(fact_check_prompt)
            fact_check_content = fact_check_response.text.strip()
            
            if "```json" in fact_check_content:
                fact_check_content = fact_check_content.split("```json")[1].split("```")[0].strip()
            elif "```" in fact_check_content:
                fact_check_content = fact_check_content.split("```")[1].split("```")[0].strip()
            
            fact_check_data = json.loads(fact_check_content)
            
            claim.verdict = fact_check_data.get("verdict", "no_evidence")
            claim.rationale = fact_check_data.get("rationale", "")
            claim.score = fact_check_data.get("score")
            if claim.metadata_json is None:
                claim.metadata_json = {}
            claim.metadata_json["llm_analysis"] = analysis_data
            claim.metadata_json["verification_model"] = self.model
            claim.metadata_json["verification_provider"] = "gemini"
            claim.metadata_json["evidence_count"] = len(evidence)

        except Exception as e:
            # Fallback: try semantic analysis to detect antisemitic content
            try:
                from backend.app.services.semantic_analysis import create_semantic_analyzer
                analyzer = create_semantic_analyzer()
                sem_result = analyzer.analyze(claim.text)
                if sem_result.is_antisemitic and sem_result.confidence > 0.6:
                    # Detected as antisemitic - flag it!
                    claim.verdict = "antisemitic_trope"
                    claim.rationale = f"Content contains antisemitic messaging. {sem_result.explanation}"
                    if sem_result.detected_patterns:
                        claim.rationale += f" Detected patterns: {', '.join(sem_result.detected_patterns)}."
                    claim.score = None
                    if claim.metadata_json is None:
                        claim.metadata_json = {}
                    claim.metadata_json["antisemitic_trope_detected"] = True
                    claim.metadata_json["trope_patterns"] = sem_result.detected_patterns
                    claim.metadata_json["fallback_used"] = "semantic_analysis"
                    claim.metadata_json["verification_error"] = f"LLM analysis failed, used semantic analysis: {str(e)}"
                    session.add(claim)
                    session.commit()
                    session.refresh(claim)
                    return claim
                else:
                    # Not detected as antisemitic, but LLM failed - try fact-checking
                    evidence = self.evidence_retriever.retrieve(
                        claim.text, 
                        limit=settings.evidence_retrieval_limit,
                        min_similarity=settings.evidence_min_similarity
                    )
                    if evidence:
                        claim.verdict = "supported"
                        claim.rationale = f"Found evidence supporting this claim. (LLM analysis failed: {str(e)})"
                        claim.score = 70.0
                    else:
                        claim.verdict = "no_evidence"
                        claim.rationale = f"No evidence found. (LLM analysis failed: {str(e)})"
                        claim.score = 50.0
            except Exception as fallback_error:
                # Complete fallback failure
                claim.verdict = "no_evidence"
                claim.rationale = f"Verification failed: {str(e)}. Fallback also failed: {str(fallback_error)}"
                claim.score = 50.0
            
            if claim.metadata_json is None:
                claim.metadata_json = {}
            claim.metadata_json["verification_error"] = str(e)

        session.add(claim)
        session.commit()
        session.refresh(claim)
        return claim

