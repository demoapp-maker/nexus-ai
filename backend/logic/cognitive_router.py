import asyncio
import json
from typing import Any, Dict, List, Optional

from logic.ai_service import ai_service
from pydantic import BaseModel


class IntentProfile(BaseModel):
    domain: str
    abstraction_level: float  # 0.0 (tactical) to 1.0 (visionary)
    reasoning_complexity: float # 0.0 (simple) to 1.0 (systemic)
    ambiguity_score: float # 0.0 (clear) to 1.0 (vague)
    strategic_impact: float # 0.0 (low) to 1.0 (high)
    operational_impact: float # 0.0 (low) to 1.0 (high)
    governance_relevance: float # 0.0 (low) to 1.0 (high)
    hidden_assumption_risk: float # 0.0 (low) to 1.0 (high)
    contradiction_risk: float # 0.0 (low) to 1.0 (high)
    suggested_mode: str
    suggested_model: str # Autonomous model selection
    requires_grill_me: bool
    diagnosis_confidence: float
    confidence: float
    reasoning_rationale: str

class CognitiveRouter:
    def __init__(self):
        self.intent_model = "liquid/lfm-2.5-1.2b-instruct:free" # Fast free model for analysis

    def _default_profile_data(self) -> Dict[str, Any]:
        return {
            "domain": "general",
            "abstraction_level": 0.5,
            "reasoning_complexity": 0.5,
            "ambiguity_score": 0.5,
            "strategic_impact": 0.4,
            "operational_impact": 0.4,
            "governance_relevance": 0.3,
            "hidden_assumption_risk": 0.5,
            "contradiction_risk": 0.3,
            "suggested_mode": "factual_mode",
            "suggested_model": "liquid/lfm-2.5-1.2b-instruct:free",
            "requires_grill_me": False,
            "diagnosis_confidence": 0.5,
            "confidence": 0.2,
            "reasoning_rationale": "Default profile used.",
        }

    def _heuristic_features(self, message: str) -> Dict[str, Any]:
        text = (message or "").lower()

        factual_markers = ["kapan", "apa", "siapa", "where", "when", "what", "jelaskan"]
        strategy_markers = ["strategi", "growth", "positioning", "go-to-market"]
        ops_markers = ["bottleneck", "operasi", "closing", "funnel", "lead"]
        governance_markers = ["governance", "policy", "risk", "audit", "compliance", "otoritas"]
        architecture_markers = ["microservice", "kubernetes", "dashboard", "observability", "architecture"]
        crypto_markers = ["bitcoin", "ethereum", "crypto", "trading", "investment", "oi ", "rsi", "cvd", "whale", "funding", "verdict", "lunc", "doge", "xrp", "sol", "usdt", "binance"]
        ambiguity_markers = ["gimana", "bagaimana", "bingung", "belum jelas", "pokoknya", "tolong"]

        if any(marker in text for marker in architecture_markers):
            domain = "architecture"
        elif any(marker in text for marker in governance_markers):
            domain = "governance"
        elif any(marker in text for marker in crypto_markers):
            domain = "investment"  # Crypto/trading analysis
        elif any(marker in text for marker in ops_markers):
            domain = "operations"
        elif any(marker in text for marker in strategy_markers):
            domain = "strategic_marketing"
        elif any(marker in text for marker in factual_markers):
            domain = "factual"
        else:
            domain = "general"

        ambiguity = 0.55 if any(marker in text for marker in ambiguity_markers) else 0.35
        complexity = (
            0.7
            if domain in {"architecture", "governance"}
            else (0.5 if domain == "investment" else (0.3 if domain == "factual" else 0.45))
        )
        strategic_impact = 0.72 if domain in {"strategic_marketing", "governance"} else (0.65 if domain == "investment" else 0.45)
        operational_impact = 0.7 if domain == "operations" else 0.45
        governance_relevance = 0.78 if domain == "governance" else 0.35

        return {
            "domain": domain,
            "reasoning_complexity": complexity,
            "ambiguity_score": ambiguity,
            "strategic_impact": strategic_impact,
            "operational_impact": operational_impact,
            "governance_relevance": governance_relevance,
        }

    def _compute_derived_scores(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ambiguity = float(data["ambiguity_score"])
        complexity = float(data["reasoning_complexity"])
        governance = float(data["governance_relevance"])
        strategic = float(data["strategic_impact"])
        operational = float(data["operational_impact"])

        hidden_assumption = min(1.0, max(0.0, 0.55 * ambiguity + 0.25 * complexity + 0.20 * strategic))
        contradiction = min(1.0, max(0.0, 0.50 * ambiguity + 0.25 * governance + 0.25 * operational))

        data["hidden_assumption_risk"] = hidden_assumption
        data["contradiction_risk"] = contradiction

        evidence_coverage = max(0.0, 1.0 - ambiguity)
        evidence_quality = max(0.0, 1.0 - (0.5 * hidden_assumption + 0.5 * contradiction))
        causal_plausibility = max(0.0, 1.0 - (0.6 * contradiction + 0.4 * ambiguity))
        diagnosis_confidence = max(0.0, min(1.0, evidence_coverage * evidence_quality * causal_plausibility))
        data["diagnosis_confidence"] = diagnosis_confidence

        return data

    def _coerce_profile_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        coerced = dict(data)

        float_fields = [
            "abstraction_level",
            "reasoning_complexity",
            "ambiguity_score",
            "strategic_impact",
            "operational_impact",
            "governance_relevance",
            "hidden_assumption_risk",
            "contradiction_risk",
            "diagnosis_confidence",
            "confidence",
        ]
        for field in float_fields:
            try:
                coerced[field] = float(coerced.get(field, 0.5))
            except (TypeError, ValueError):
                coerced[field] = self._default_profile_data()[field]

        # Keep numeric scores within [0, 1]
        for field in float_fields:
            coerced[field] = max(0.0, min(1.0, coerced[field]))

        requires_grill_me = coerced.get("requires_grill_me", False)
        if isinstance(requires_grill_me, str):
            coerced["requires_grill_me"] = requires_grill_me.strip().lower() in {
                "true", "1", "yes", "ya"
            }
        else:
            coerced["requires_grill_me"] = bool(requires_grill_me)

        for field in ["domain", "suggested_mode", "suggested_model", "reasoning_rationale"]:
            value = coerced.get(field)
            if not isinstance(value, str) or not value.strip():
                coerced[field] = self._default_profile_data()[field]

        return coerced
        
    async def analyze_intent(
        self, message: str, history: Optional[List[Dict]] = None
    ) -> IntentProfile:
        """
        Analyze the user's message to determine the cognitive profile and routing.
        Uses a fallback chain to ensure analysis succeeds even if the primary model fails.
        """
        system_prompt = """You are the Nexus Cognitive Intent Analyzer. 
Your task is to analyze user input and categorize it across multiple cognitive dimensions.

DIMENSIONS:
1. DOMAIN: factual, coding, product, strategic_marketing, organizational_capability, governance, operations, architecture, investment, educational, tactical.
2. ABSTRACTION_LEVEL: 0.0 (tactical) to 1.0 (strategic).
3. REASONING_COMPLEXITY: 0.0 (simple) to 1.0 (systemic).
4. AMBIGUITY_SCORE: 0.0 (clear) to 1.0 (vague/contradictory).
5. STRATEGIC_IMPACT: 0.0 (low) to 1.0 (high).
6. OPERATIONAL_IMPACT: 0.0 (low) to 1.0 (high).
7. GOVERNANCE_RELEVANCE: 0.0 (low) to 1.0 (high).

ROUTING LOGIC (suggested_mode):
- factual_mode: Low ambiguity, low complexity, factual domain.
- educational_mode: User wants to learn or understand a concept.
- investment_mode: Crypto/trading analysis, market signals, investment data.
- diagnosis_mode: High ambiguity, operational/marketing domain.
- strategic_mode: High abstraction, high impact.
- systems_mode: Architecture/Operations.

MODEL SELECTION (suggested_model):
- For crypto/investment: "google/gemma-4-31b-it:free" (balanced reasoning)
- For coding: "qwen/qwen3-coder:free"
- For complex reasoning/strategy: "google/gemma-4-31b-it:free" or "qwen/qwen3-next-80b-a3b-instruct:free"
- For fast factual: "liquid/lfm-2.5-1.2b-instruct:free" or "meta-llama/llama-3.1-8b-instruct:free"
- For general/educational: "z-ai/glm-4.5-air:free" or "meta-llama/llama-3.1-8b-instruct:free"

GRILL-ME TRIGGER:
- requires_grill_me: true IF (Ambiguity > 0.6 AND Impact > 0.5).

Return ONLY a JSON object."""

        user_context = f"Message: {message}\n"
        if history:
            last_3 = history[-3:]
            user_context += "Recent History:\n"
            for m in last_3:
                role = m.role if hasattr(m, "role") else m.get("role", "user")
                content = m.content if hasattr(m, "content") else m.get("content", "")
                content = str(content)[:200]
                user_context += f"- {role}: {content}\n"

        # Build fallback chain for analysis
        models_to_try = ai_service.get_fallback_chain(self.intent_model)
        
        for model in models_to_try[:5]: # Try top 5 models for analysis
            try:
                response = await asyncio.to_thread(
                    ai_service.call_ai,
                    user_context,
                    system_prompt=system_prompt,
                    model=model
                )
                
                if not response:
                    continue
                    
                # Extract JSON from response
                clean_json = response.strip()
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                    
                data = json.loads(clean_json)
                if not isinstance(data, dict):
                    continue
                
                # Normalize keys to lowercase for Pydantic
                normalized_data = {k.lower(): v for k, v in data.items()}

                heuristic_data = self._heuristic_features(message)

                merged_data = {
                    **self._default_profile_data(),
                    **heuristic_data,
                    **normalized_data,
                }

                lower_message = (message or "").lower()
                if heuristic_data.get("domain") == "architecture" and any(
                    term in lower_message for term in ["observability", "dashboard", "kubernetes", "microservice"]
                ):
                    merged_data["domain"] = "architecture"
                    merged_data["reasoning_complexity"] = max(float(merged_data.get("reasoning_complexity", 0.0)), 0.72)
                    merged_data["operational_impact"] = max(float(merged_data.get("operational_impact", 0.0)), 0.62)

                if heuristic_data.get("domain") == "operations" and any(
                    term in lower_message for term in ["lead", "leads", "closing", "funnel", "konversi"]
                ):
                    merged_data["domain"] = "operations"
                    merged_data["operational_impact"] = max(float(merged_data.get("operational_impact", 0.0)), 0.72)
                    merged_data["ambiguity_score"] = max(float(merged_data.get("ambiguity_score", 0.0)), 0.55)

                merged_data = self._compute_derived_scores(merged_data)
                safe_data = self._coerce_profile_data(merged_data)

                return IntentProfile(**safe_data)
            except Exception as e:
                print(f"[COGNITIVE-ROUTER] Attempt with {model} failed: {e}")
                continue

        # Deterministic fallback: preserve the local intent signals instead of
        # routing every provider outage to an unrelated generic profile.
        fallback = {
            **self._default_profile_data(),
            **self._heuristic_features(message),
        }
        domain = fallback.get("domain")
        fallback["suggested_mode"] = {
            "factual": "factual_mode",
            "educational": "educational_mode",
            "investment": "investment_mode",
            "architecture": "systems_mode",
            "governance": "diagnosis_mode",
            "operations": "diagnosis_mode",
            "strategic_marketing": "strategic_mode",
        }.get(domain, "factual_mode")
        fallback["suggested_model"] = {
            "architecture": "qwen/qwen3-coder:free",
            "investment": "google/gemma-4-31b-it:free",
            "strategic_marketing": "google/gemma-4-31b-it:free",
        }.get(domain, self.intent_model)
        fallback = self._compute_derived_scores(fallback)
        fallback["confidence"] = 0.1
        fallback["reasoning_rationale"] = (
            "Model analysis failed; deterministic heuristic fallback used."
        )
        fallback = self._coerce_profile_data(fallback)
        return IntentProfile(**fallback)

    def get_system_prompt_for_mode(self, mode: str, profile: IntentProfile) -> str:
        """
        Get a calibrated system prompt based on the reasoning mode.
        """
        base_identity = "Kamu adalah Rohadi, asisten AI pribadi yang cerdas. "
        
        mode_prompts = {
            "factual_mode": "Fokus pada jawaban langsung, akurat, dan singkat. Jangan berbelit-belit dengan framework jika tidak diminta. Berikan fakta teknis atau data yang diminta secara efisien.",
            "direct_factual_mode": "Jawab langsung dalam 2-4 kalimat, tanpa framing berlebih. Hanya tambah konteks jika diminta.",
            
            "educational_mode": "Gunakan analogi yang sederhana dan bahasa yang mudah dimengerti. Hindari jargon teknis berlebihan. Fokus pada pemahaman konsep dasar sebelum masuk ke detail.",
            
            "diagnosis_mode": "Jangan langsung memberi solusi. Fokus pada identifikasi bottleneck. Tanyakan data atau observabilitas yang hilang. Gunakan pola pikir 'Diagnosis-First'. Cari tahu di mana kebocoran sistem/proses terjadi.",
            "diagnosis_first_mode": "Mulai dengan diagnosis. Tahan rekomendasi besar sampai bottleneck dan constraint tervalidasi.",
            
            "investment_mode": "Analisis technical dan fundamental dari aset/market yang diberikan. Fokus pada risk/reward, entry/exit signals, dan posisi sizing. Berikan verdict yang jelas (BULLISH/NEUTRAL/BEARISH) dengan reasoning yang actionable.",
            
            "strategic_mode": "Berperan sebagai strategic facilitator. Fokus pada trade-off, alokasi sumber daya, dan dampak tata kelola (governance). Bantu user melihat gambaran besar dan implikasi jangka panjang dari keputusan mereka.",
            "strategic_facilitation_mode": "Berikan opsi strategis beserta trade-off. Wajib validasi asumsi utama sebelum keputusan final.",
            
            "systems_mode": "Fokus pada arsitektur, aliran data (flow), dan observabilitas. Analisis dampak hulu dan hilir. Pastikan sistem yang dibangun skalabel dan memiliki visibilitas yang cukup.",
            "systems_thinking_mode": "Prioritaskan observability-first design, reliability, dan phased rollout.",
            "governance_analysis_mode": "Soroti decision rights, ownership, risk exposure, dan policy implication sebelum rekomendasi.",
            "operational_bottleneck_mode": "Petakan funnel atau proses kerja, identifikasi constraint utama, lalu rekomendasikan eksperimen terukur.",
            "tactical_execution_mode": "Berikan langkah implementasi praktis dengan prioritas dan acceptance criteria yang jelas.",
        }
        
        prompt = base_identity + mode_prompts.get(mode, mode_prompts["factual_mode"])
        
        # Add solution restraint if ambiguity is high
        if profile.ambiguity_score > 0.7:
            prompt += "\n\n[RESTRAINT]: Ambiguitas sangat tinggi. JANGAN memberikan strategi lengkap sekarang. Fokuslah pada bertanya untuk memperjelas asumsi atau mencari variabel yang hilang."
        elif profile.ambiguity_score > 0.4:
            prompt += "\n\n[RESTRAINT]: Berikan arah solusi secara umum, tapi prioritaskan validasi bottleneck terlebih dahulu."
            
        return prompt

cognitive_router = CognitiveRouter()
