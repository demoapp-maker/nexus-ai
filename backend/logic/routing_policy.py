from typing import Optional, Tuple

from logic.cognitive_router import IntentProfile
from pydantic import BaseModel


class RoutingPolicy(BaseModel):
    reasoning_mode: str
    restraint_level: str
    response_depth: str
    observability_requirement: str
    communication_style: str
    allow_direct_answer: bool
    require_clarification: bool
    max_clarifying_questions: int
    enable_tools: bool
    auto_grill_me: bool
    grill_reason: Optional[str] = None
    diagnosis_confidence: float
    preferred_model: str


class GrillEscalationPolicy:
    """Determine whether Grill-Me should activate as a diagnostic escalation."""

    def evaluate(self, profile: IntentProfile) -> Tuple[bool, str, float]:
        score = (
            0.24 * profile.ambiguity_score
            + 0.20 * profile.hidden_assumption_risk
            + 0.16 * profile.contradiction_risk
            + 0.14 * profile.strategic_impact
            + 0.14 * profile.governance_relevance
            + 0.12 * profile.reasoning_complexity
        )

        factual_fast_path = (
            profile.domain == "factual"
            and profile.ambiguity_score < 0.35
            and profile.reasoning_complexity < 0.45
        )
        if factual_fast_path:
            return False, "factual_fast_path", score

        if profile.diagnosis_confidence < 0.45 and score > 0.58:
            return True, "high_ambiguity_low_confidence", score

        if profile.governance_relevance > 0.72 and profile.ambiguity_score > 0.5:
            return True, "governance_sensitive", score

        return False, "not_required", score


class PolicyEngine:
    def __init__(self):
        self.grill_policy = GrillEscalationPolicy()

    def _select_mode(self, profile: IntentProfile) -> str:
        if profile.domain == "factual" and profile.reasoning_complexity < 0.45:
            return "direct_factual_mode"
        if profile.domain == "educational":
            return "educational_mode"
        if profile.governance_relevance >= 0.7:
            return "governance_analysis_mode"
        if profile.domain == "operations" or profile.operational_impact >= 0.6:
            return "operational_bottleneck_mode"
        if profile.domain in {"architecture", "coding"} or profile.reasoning_complexity >= 0.75:
            return "systems_thinking_mode"
        if profile.ambiguity_score >= 0.62 or profile.hidden_assumption_risk >= 0.6:
            return "diagnosis_first_mode"
        if profile.strategic_impact >= 0.72 and profile.abstraction_level >= 0.58:
            return "strategic_facilitation_mode"
        return "tactical_execution_mode"

    def _derive_communication_style(self, profile: IntentProfile) -> str:
        if profile.domain in {"educational", "factual"}:
            return "beginner_explainer"
        if profile.abstraction_level > 0.72:
            return "executive_brief"
        if profile.operational_impact > 0.65:
            return "manager_coach"
        return "executor_playbook"

    def _needs_tools(self, message: str, profile: IntentProfile) -> bool:
        lower = message.lower()
        tool_markers = [
            "research", "search", "current", "latest", "today", "real-time",
            "riset", "cari", "berita", "update", "sekarang", "pencarian",
            "dashboard", "observability", "market", "trend",
        ]
        if any(marker in lower for marker in tool_markers):
            return True
        return profile.domain in {"strategic_marketing", "operations", "governance"}

    def build_policy(
        self,
        profile: IntentProfile,
        message: str,
        explicit_grill_mode: bool = False,
    ) -> RoutingPolicy:
        mode = self._select_mode(profile)
        communication_style = self._derive_communication_style(profile)
        tools_enabled = self._needs_tools(message, profile)

        auto_grill, grill_reason, _score = self.grill_policy.evaluate(profile)
        auto_grill = explicit_grill_mode or auto_grill

        if mode in {"direct_factual_mode", "educational_mode"}:
            restraint = "low"
            depth = "short"
            allow_direct_answer = True
            require_clarification = False
            max_questions = 0
        elif mode in {"diagnosis_first_mode", "operational_bottleneck_mode", "governance_analysis_mode"}:
            restraint = "high"
            depth = "phased"
            allow_direct_answer = False
            require_clarification = True
            max_questions = 1
        else:
            restraint = "medium"
            depth = "structured"
            allow_direct_answer = profile.diagnosis_confidence >= 0.55
            require_clarification = profile.ambiguity_score >= 0.55
            max_questions = 1 if require_clarification else 0

        observability = "mandatory" if mode in {
            "systems_thinking_mode", "operational_bottleneck_mode", "governance_analysis_mode"
        } else "basic"

        return RoutingPolicy(
            reasoning_mode=mode,
            restraint_level=restraint,
            response_depth=depth,
            observability_requirement=observability,
            communication_style=communication_style,
            allow_direct_answer=allow_direct_answer,
            require_clarification=require_clarification,
            max_clarifying_questions=max_questions,
            enable_tools=tools_enabled,
            auto_grill_me=auto_grill,
            grill_reason=grill_reason,
            diagnosis_confidence=profile.diagnosis_confidence,
            preferred_model=profile.suggested_model,
        )


policy_engine = PolicyEngine()
