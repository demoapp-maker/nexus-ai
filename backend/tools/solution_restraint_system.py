"""
Solution Restraint Behavior System for Rohadi AI

Purpose:
Prevent premature solutioning by enforcing diagnostic discipline before strategy generation.

Core Philosophy:
- Context density ≠ Diagnosis completeness
- Long context requires MORE caution, not less
- Solution generation is gated by diagnosis confidence
- Observability > Speed of answering

This module implements:
1. Diagnosis Confidence Scoring
2. Solution Gating Mechanism  
3. Diagnostic Sufficiency Checks
4. Restraint Response Generation
5. TGM-Aware Restraint Logic
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class DiagnosisDimension(Enum):
    """Dimensions that must be clear before generating strategic solutions."""
    MARKET_CLARITY = "market_clarity"
    BOTTLENECK_CLARITY = "bottleneck_clarity"
    VALUE_PROP_CLARITY = "value_prop_clarity"
    ACQUISITION_CLARITY = "acquisition_clarity"
    ACTIVATION_CLARITY = "activation_clarity"
    OPERATIONAL_CLARITY = "operational_clarity"
    GOVERNANCE_CLARITY = "governance_clarity"
    ECONOMICS_CLARITY = "economics_clarity"
    STRATEGIC_TENSION_CLARITY = "strategic_tension_clarity"


class SolutionType(Enum):
    """Types of solutions that require high diagnosis confidence."""
    STRATEGIC_ROADMAP = "strategic_roadmap"
    KPI_PLAN = "kpi_plan"
    BUDGET_ALLOCATION = "budget_allocation"
    FUNNEL_RECOMMENDATION = "funnel_recommendation"
    CAMPAIGN_PLAN = "campaign_plan"
    CONTENT_STRATEGY = "content_strategy"
    FULL_MARKETING_STRATEGY = "full_marketing_strategy"
    PRICING_STRATEGY = "pricing_strategy"


@dataclass
class DiagnosisConfidenceScore:
    """
    Comprehensive diagnosis confidence scoring.
    
    Each dimension scored 0.0 - 1.0
    Overall confidence is weighted average
    """
    dimension_scores: Dict[DiagnosisDimension, float] = field(default_factory=lambda: {
        DiagnosisDimension.MARKET_CLARITY: 0.0,
        DiagnosisDimension.BOTTLENECK_CLARITY: 0.0,
        DiagnosisDimension.VALUE_PROP_CLARITY: 0.0,
        DiagnosisDimension.ACQUISITION_CLARITY: 0.0,
        DiagnosisDimension.ACTIVATION_CLARITY: 0.0,
        DiagnosisDimension.OPERATIONAL_CLARITY: 0.0,
        DiagnosisDimension.GOVERNANCE_CLARITY: 0.0,
        DiagnosisDimension.ECONOMICS_CLARITY: 0.0,
        DiagnosisDimension.STRATEGIC_TENSION_CLARITY: 0.0,
    })
    
    # Weights for each dimension (some are more critical)
    dimension_weights: Dict[DiagnosisDimension, float] = field(default_factory=lambda: {
        DiagnosisDimension.MARKET_CLARITY: 0.15,           # Foundation
        DiagnosisDimension.BOTTLENECK_CLARITY: 0.20,       # Most critical
        DiagnosisDimension.VALUE_PROP_CLARITY: 0.12,       # Differentiation
        DiagnosisDimension.ACQUISITION_CLARITY: 0.10,      # Lead gen
        DiagnosisDimension.ACTIVATION_CLARITY: 0.10,       # Conversion
        DiagnosisDimension.OPERATIONAL_CLARITY: 0.08,      # Execution
        DiagnosisDimension.GOVERNANCE_CLARITY: 0.08,       # Ownership
        DiagnosisDimension.ECONOMICS_CLARITY: 0.10,        # Profitability
        DiagnosisDimension.STRATEGIC_TENSION_CLARITY: 0.07,# Trade-offs
    })
    
    def get_overall_confidence(self) -> float:
        """Calculate weighted overall diagnosis confidence."""
        total_weight = sum(self.dimension_weights.values())
        weighted_sum = sum(
            self.dimension_scores[dim] * self.dimension_weights[dim]
            for dim in DiagnosisDimension
        )
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def get_weakest_dimension(self) -> Tuple[DiagnosisDimension, float]:
        """Find the dimension with lowest clarity score."""
        return min(self.dimension_scores.items(), key=lambda x: x[1])
    
    def get_strongest_dimension(self) -> Tuple[DiagnosisDimension, float]:
        """Find the dimension with highest clarity score."""
        return max(self.dimension_scores.items(), key=lambda x: x[1])
    
    def update_dimension(self, dimension: DiagnosisDimension, new_score: float):
        """Update a specific dimension score with exponential moving average."""
        current = self.dimension_scores.get(dimension, 0.0)
        # EMA: 30% old, 70% new (responsive to recent input)
        self.dimension_scores[dimension] = current * 0.3 + new_score * 0.7
    
    def is_ready_for_solution(self, solution_type: SolutionType) -> bool:
        """
        Check if diagnosis is sufficient for a specific solution type.
        
        Different solution types have different confidence thresholds.
        """
        overall = self.get_overall_confidence()
        
        # Thresholds by solution type (higher = more diagnosis required)
        thresholds = {
            SolutionType.STRATEGIC_ROADMAP: 0.75,
            SolutionType.KPI_PLAN: 0.70,
            SolutionType.BUDGET_ALLOCATION: 0.80,  # Needs economics clarity
            SolutionType.FUNNEL_RECOMMENDATION: 0.65,
            SolutionType.CAMPAIGN_PLAN: 0.60,
            SolutionType.CONTENT_STRATEGY: 0.55,
            SolutionType.FULL_MARKETING_STRATEGY: 0.85,  # Highest bar
            SolutionType.PRICING_STRATEGY: 0.75,
        }
        
        threshold = thresholds.get(solution_type, 0.70)
        
        # Also check critical dimensions individually
        critical_dims = [
            DiagnosisDimension.MARKET_CLARITY,
            DiagnosisDimension.BOTTLENECK_CLARITY,
            DiagnosisDimension.VALUE_PROP_CLARITY,
        ]
        
        all_critical_clear = all(
            self.dimension_scores[dim] >= 0.6
            for dim in critical_dims
        )
        
        return overall >= threshold and all_critical_clear


@dataclass
class RestraintDecision:
    """
    Decision on whether to restrain from providing solution.
    
    Contains reasoning for transparency.
    """
    should_restrain: bool
    confidence_score: float
    weakest_dimensions: List[Tuple[DiagnosisDimension, float]]
    recommended_action: str  # "continue_diagnosis" or "generate_solution"
    restraint_reasoning: str  # Why we're restraining
    suggested_next_focus: str  # What to diagnose next


class SolutionRestraintSystem:
    """
    Enforces diagnostic discipline before solution generation.
    
    Core behaviors:
    1. Scores diagnosis confidence across 9 dimensions
    2. Gates solution generation based on confidence thresholds
    3. Generates restraint responses when diagnosis insufficient
    4. Identifies next diagnostic focus area
    5. Prevents premature solutioning even with long context
    """
    
    def __init__(self):
        self.confidence_thresholds = {
            "minimal_diagnosis": 0.40,   # Can ask clarifying questions
            "tactical_advice": 0.60,     # Can give tactical tips
            "strategic_guidance": 0.75,  # Can give strategic direction
            "full_solution": 0.85,       # Can generate complete strategy
        }
    
    def evaluate_diagnosis_sufficiency(
        self,
        conversation_state,
        user_input: str,
        requested_solution_type: Optional[SolutionType] = None
    ) -> RestraintDecision:
        """
        Evaluate whether diagnosis is sufficient to provide solution.
        
        Args:
            conversation_state: Current ConversationState with TGM layer clarity
            user_input: Latest user message
            requested_solution_type: Type of solution user seems to want
            
        Returns:
            RestraintDecision with recommendation
        """
        # Calculate diagnosis confidence from conversation state
        confidence = self._calculate_diagnosis_confidence(conversation_state)
        
        # Determine what solution type user is implicitly requesting
        if not requested_solution_type:
            requested_solution_type = self._infer_requested_solution_type(user_input)
        
        # Check if ready for this solution type
        is_ready = confidence.is_ready_for_solution(requested_solution_type)
        
        # Get weakest dimensions (priority for next diagnosis)
        weakest = self._get_weakest_dimensions(confidence, top_n=3)
        
        # Generate decision
        if is_ready:
            return RestraintDecision(
                should_restrain=False,
                confidence_score=confidence.get_overall_confidence(),
                weakest_dimensions=weakest,
                recommended_action="generate_solution",
                restraint_reasoning="",
                suggested_next_focus=""
            )
        else:
            # Not ready - need more diagnosis
            next_focus = self._determine_next_diagnostic_focus(weakest, user_input)
            reasoning = self._generate_restraint_reasoning(weakest, requested_solution_type)
            
            return RestraintDecision(
                should_restrain=True,
                confidence_score=confidence.get_overall_confidence(),
                weakest_dimensions=weakest,
                recommended_action="continue_diagnosis",
                restraint_reasoning=reasoning,
                suggested_next_focus=next_focus
            )
    
    def generate_restraint_response(
        self,
        restraint_decision: RestraintDecision,
        conversation_state
    ) -> str:
        """
        Generate response that restrains from premature solutioning.
        
        This response should:
        - Acknowledge user's request
        - Explain why we're not giving full solution yet
        - Identify what needs clarification
        - Ask targeted diagnostic question
        """
        if not restraint_decision.should_restrain:
            return ""  # No restraint needed
        
        # Build restraint response
        response_parts = []
        
        # 1. Acknowledge and validate
        response_parts.append(self._generate_acknowledgment(restraint_decision))
        
        # 2. Explain restraint reasoning
        response_parts.append(f"\n\n{restraint_decision.restraint_reasoning}")
        
        # 3. Identify gaps
        response_parts.append(self._identify_diagnosis_gaps(restraint_decision))
        
        # 4. Suggest next focus
        if restraint_decision.suggested_next_focus:
            response_parts.append(f"\n\n**Yang perlu kita klarifikasi dulu:**\n{restraint_decision.suggested_next_focus}")
        
        return "\n".join(response_parts)
    
    def _calculate_diagnosis_confidence(self, conversation_state) -> DiagnosisConfidenceScore:
        """
        Calculate diagnosis confidence from conversation state.
        
        Maps TGM layer clarity to diagnosis dimensions.
        """
        confidence = DiagnosisConfidenceScore()
        
        # Map TGM layers to diagnosis dimensions
        layer_to_dimension_mapping = {
            "understanding_market": DiagnosisDimension.MARKET_CLARITY,
            "value_creation": DiagnosisDimension.VALUE_PROP_CLARITY,
            "brand_blueprint": DiagnosisDimension.MARKET_CLARITY,  # Contributes to market
            "acquisition": DiagnosisDimension.ACQUISITION_CLARITY,
            "activation": DiagnosisDimension.ACTIVATION_CLARITY,
            "crm_retention": DiagnosisDimension.OPERATIONAL_CLARITY,
            "data_insight": DiagnosisDimension.GOVERNANCE_CLARITY,
            "unit_economics": DiagnosisDimension.ECONOMICS_CLARITY,
            "scalability": DiagnosisDimension.OPERATIONAL_CLARITY,
            "operational_sustainability": DiagnosisDimension.OPERATIONAL_CLARITY,
        }
        
        # Transfer TGM layer clarity to diagnosis dimensions
        for tgm_layer, clarity_score in conversation_state.tgm_layer_clarity.items():
            layer_name = tgm_layer.value if hasattr(tgm_layer, 'value') else str(tgm_layer)
            dimension = layer_to_dimension_mapping.get(layer_name)
            
            if dimension:
                # Use EMA to blend scores
                confidence.update_dimension(dimension, clarity_score)
        
        # Boost bottleneck clarity if bottlenecks detected
        bottleneck_signals = [
            s for s in conversation_state.detected_signals
            if s.get("type") == "bottleneck"
        ]
        if bottleneck_signals:
            current_bottleneck_clarity = confidence.dimension_scores[DiagnosisDimension.BOTTLENECK_CLARITY]
            # More signals = better bottleneck understanding
            boost = min(len(bottleneck_signals) * 0.15, 0.5)
            confidence.update_dimension(
                DiagnosisDimension.BOTTLENECK_CLARITY,
                min(current_bottleneck_clarity + boost, 1.0)
            )
        
        # Boost strategic tension clarity if tensions detected
        tension_signals = [
            s for s in conversation_state.detected_signals
            if s.get("type") == "strategic_tension"
        ]
        if tension_signals:
            current = confidence.dimension_scores[DiagnosisDimension.STRATEGIC_TENSION_CLARITY]
            boost = min(len(tension_signals) * 0.10, 0.4)
            confidence.update_dimension(
                DiagnosisDimension.STRATEGIC_TENSION_CLARITY,
                min(current + boost, 1.0)
            )
        
        return confidence
    
    def _infer_requested_solution_type(self, user_input: str) -> SolutionType:
        """
        Infer what type of solution user is implicitly requesting.
        
        Uses keyword patterns to detect intent.
        """
        input_lower = user_input.lower()
        
        # Pattern matching for solution types
        patterns = {
            SolutionType.FULL_MARKETING_STRATEGY: [
                r'\b(strategi|strategy|plan|rencana)\b.*\b(marketing|pemasaran|digital)\b',
                r'\b(buatkan|buat|generate|create)\b.*\b(strategy|strategi|plan)\b',
            ],
            SolutionType.STRATEGIC_ROADMAP: [
                r'\b(roadmap|timeline|phases|tahap)\b',
                r'\b(3 bulan|6 bulan|1 tahun|quarterly)\b',
            ],
            SolutionType.KPI_PLAN: [
                r'\b(kpi|metric|target|goal)\b',
                r'\b(ukur|measure|track)\b',
            ],
            SolutionType.BUDGET_ALLOCATION: [
                r'\b(budget|anggaran|spend|alokasi)\b',
                r'\b(how much|berapa banyak|berapa budget)\b',
            ],
            SolutionType.FUNNEL_RECOMMENDATION: [
                r'\b(funnel|corong|conversion|konversi)\b',
                r'\b(acquisition|lead|prospek)\b',
            ],
            SolutionType.CAMPAIGN_PLAN: [
                r'\b(campaign|kampanye|ads|iklan)\b',
                r'\b(content plan|content calendar)\b',
            ],
            SolutionType.CONTENT_STRATEGY: [
                r'\b(content|konten|postingan)\b',
                r'\b(social media|instagram|tiktok)\b',
            ],
            SolutionType.PRICING_STRATEGY: [
                r'\b(price|harga|pricing|paket)\b',
                r'\b(murah|expensive|premium)\b',
            ],
        }
        
        # Check patterns
        for solution_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, input_lower):
                    return solution_type
        
        # Default: assume they want strategic guidance
        return SolutionType.STRATEGIC_ROADMAP
    
    def _get_weakest_dimensions(
        self,
        confidence: DiagnosisConfidenceScore,
        top_n: int = 3
    ) -> List[Tuple[DiagnosisDimension, float]]:
        """Get the N weakest diagnosis dimensions."""
        sorted_dims = sorted(
            confidence.dimension_scores.items(),
            key=lambda x: x[1]
        )
        return sorted_dims[:top_n]
    
    def _determine_next_diagnostic_focus(
        self,
        weakest_dimensions: List[Tuple[DiagnosisDimension, float]],
        user_input: str
    ) -> str:
        """Determine what to focus diagnosis on next."""
        if not weakest_dimensions:
            return "General business context"
        
        # Get the absolute weakest dimension
        weakest_dim, weakest_score = weakest_dimensions[0]
        
        # Generate focus recommendation based on dimension
        focus_recommendations = {
            DiagnosisDimension.MARKET_CLARITY: 
                "Target market spesifik, segment economics, dan competitor positioning",
            DiagnosisDimension.BOTTLENECK_CLARITY: 
                "Root cause utama dari masalah yang dihadapi - apakah di acquisition, activation, atau retention?",
            DiagnosisDimension.VALUE_PROP_CLARITY: 
                "Differentiation konkret dan unfair advantage vs kompetitor",
            DiagnosisDimension.ACQUISITION_CLARITY: 
                "Channel strategy, CAC observability, dan lead quality metrics",
            DiagnosisDimension.ACTIVATION_CLARITY: 
                "Conversion bottleneck, sales friction, dan operational capacity",
            DiagnosisDimension.OPERATIONAL_CLARITY: 
                "Process workflow, team capacity, dan execution constraints",
            DiagnosisDimension.GOVERNANCE_CLARITY: 
                "KPI ownership, measurement framework, dan decision-making process",
            DiagnosisDimension.ECONOMICS_CLARITY: 
                "Unit economics, LTV:CAC ratio, dan profitability model",
            DiagnosisDimension.STRATEGIC_TENSION_CLARITY: 
                "Trade-offs yang harus dibuat dan prioritas strategis",
        }
        
        return focus_recommendations.get(weakest_dim, "Business context lebih detail")
    
    def _generate_restraint_reasoning(
        self,
        weakest_dimensions: List[Tuple[DiagnosisDimension, float]],
        requested_solution: SolutionType
    ) -> str:
        """Generate explanation for why we're restraining from solution."""
        if not weakest_dimensions:
            return "Saya perlu memahami konteks bisnis Anda lebih dalam sebelum memberikan rekomendasi."
        
        # Get top 2 weakest dimensions
        top_weak = weakest_dimensions[:2]
        
        dimension_names = {
            DiagnosisDimension.MARKET_CLARITY: "pemahaman market",
            DiagnosisDimension.BOTTLENECK_CLARITY: "identifikasi bottleneck",
            DiagnosisDimension.VALUE_PROP_CLARITY: "value proposition",
            DiagnosisDimension.ACQUISITION_CLARITY: "acquisition strategy",
            DiagnosisDimension.ACTIVATION_CLARITY: "activation flow",
            DiagnosisDimension.OPERATIONAL_CLARITY: "operational reality",
            DiagnosisDimension.GOVERNANCE_CLARITY: "governance structure",
            DiagnosisDimension.ECONOMICS_CLARITY: "unit economics",
            DiagnosisDimension.STRATEGIC_TENSION_CLARITY: "strategic trade-offs",
        }
        
        weak_areas = [
            dimension_names.get(dim, dim.value)
            for dim, _ in top_weak
        ]
        
        solution_names = {
            SolutionType.FULL_MARKETING_STRATEGY: "strategi marketing lengkap",
            SolutionType.STRATEGIC_ROADMAP: "strategic roadmap",
            SolutionType.KPI_PLAN: "KPI plan",
            SolutionType.BUDGET_ALLOCATION: "budget allocation",
            SolutionType.FUNNEL_RECOMMENDATION: "funnel recommendation",
            SolutionType.CAMPAIGN_PLAN: "campaign plan",
            SolutionType.CONTENT_STRATEGY: "content strategy",
            SolutionType.PRICING_STRATEGY: "pricing strategy",
        }
        
        solution_name = solution_names.get(requested_solution, "solusi strategis")
        
        reasoning = (
            f"**Saya belum ingin terburu-buru memberikan {solution_name}.**\n\n"
            f"Alasannya: Saya masih melihat gap dalam **{', '.join(weak_areas)}**. "
            f"Jika saya langsung memberikan solusi sekarang, rekomendasinya akan berbasis asumsi, "
            f"bukan berdasarkan realitas bisnis Anda. Ini berisiko menghasilkan strategi yang tidak actionable "
            f"atau bahkan misleading.\n\n"
            f"Saya lebih memilih untuk memastikan diagnosis cukup solid dulu, "
            f"baru kemudian menyusun rekomendasi yang benar-benar aligned dengan kondisi Anda."
        )
        
        return reasoning
    
    def _generate_acknowledgment(self, restraint_decision: RestraintDecision) -> str:
        """Generate acknowledgment that validates user's request."""
        confidence = restraint_decision.confidence_score
        
        if confidence < 0.3:
            return (
                "Saya appreciate Anda share konteks bisnis yang detail. "
                "Ini membantu saya memahami situasi Anda."
            )
        elif confidence < 0.5:
            return (
                "Saya sudah mulai memahami beberapa aspek bisnis Anda, "
                "tapi masih ada beberapa area kunci yang perlu kita clarify."
            )
        else:
            return (
                "Kita sudah membahas cukup banyak aspek. "
                "Sebelum saya susun rekomendasi lengkap, ada beberapa hal penting yang perlu dipastikan dulu."
            )
    
    def _identify_diagnosis_gaps(self, restraint_decision: RestraintDecision) -> str:
        """Identify specific gaps in diagnosis."""
        if not restraint_decision.weakest_dimensions:
            return ""
        
        gaps = []
        for dim, score in restraint_decision.weakest_dimensions[:2]:
            if score < 0.4:
                gaps.append(f"- **{dim.value.replace('_', ' ').title()}**: Masih sangat unclear (clarity: {score:.0%})")
            elif score < 0.6:
                gaps.append(f"- **{dim.value.replace('_', ' ').title()}**: Cukup jelas tapi butuh validasi lebih (clarity: {score:.0%})")
        
        if gaps:
            return "\n\n**Gap diagnosis yang masih ada:**\n" + "\n".join(gaps)
        
        return ""


# Singleton instance
solution_restraint_system = SolutionRestraintSystem()
