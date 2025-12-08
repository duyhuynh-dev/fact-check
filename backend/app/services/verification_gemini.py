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
        """Verify a claim: FIRST use policy engine to classify, THEN fact-check if needed."""
        from backend.app.core.config import get_settings
        from backend.app.services.policy_engine import create_classification_prompt
        
        settings = get_settings()
        
        # STEP 1: POLICY ENGINE CLASSIFICATION - Use IHRA-based policy to classify content
        # This is the PRIMARY analysis - distinguishes legitimate criticism from antisemitism
        analysis_prompt = create_classification_prompt(claim.text)

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
                
                # Map policy engine categories to verdicts
                category = analysis_data.get("category", "").lower()
                if category == "antisemitic":
                    analysis_data["is_antisemitic"] = True
                    analysis_data["content_type"] = "antisemitic_trope"
                elif category == "critical_but_not_antisemitic":
                    analysis_data["is_antisemitic"] = False
                    analysis_data["content_type"] = "factual_claim"  # Treat as factual for fact-checking
                elif category == "not_applicable":
                    analysis_data["is_antisemitic"] = False
                    analysis_data["content_type"] = "not_applicable"
                
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
            
            # STEP 3: Handle legitimate criticism of Israel
            # If it's legitimate criticism, treat as factual claim for fact-checking
            if category == "critical_but_not_antisemitic" or is_legitimate_criticism:
                # This is legitimate criticism - proceed to fact-checking
                analysis_data["content_type"] = "factual_claim"
                analysis_data["is_factual_claim"] = True
            
            # STEP 4: If not applicable, mark and return
            if category == "not_applicable" or analysis_data.get("content_type") == "not_applicable":
                # Not applicable content
                claim.verdict = "not_applicable"
                rationale = analysis_data.get("reasoning") or analysis_data.get("explanation", "This is not a factual claim to verify.")
                claim.rationale = rationale
                claim.score = None
                if claim.metadata_json is None:
                    claim.metadata_json = {}
                claim.metadata_json["llm_analysis"] = analysis_data
                claim.metadata_json["policy_classification"] = category
                session.add(claim)
                session.commit()
                session.refresh(claim)
                return claim
            
            # STEP 5: For factual claims, retrieve evidence and compare
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

