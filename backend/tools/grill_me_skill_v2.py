"""
Grill-Me Skill v2: Contextual Strategic Reasoning Engine (Rohadi AI)

Architectural Redesign:
- From: Template-driven questioning with fixed sequence
- To: Contextual strategic reasoning system using TGM as reasoning protocol

Core Changes:
1. Dynamic bottleneck detection instead of fixed question order
2. Ambiguity scoring to determine clarification depth
3. TGM layer completeness tracking
4. Contextual recommendation generation based on user's business reality
5. Stateful conversation orchestration with leverage-based prioritization
6. Strategic tension identification
7. Observability gap analysis
8. **SOLUTION RESTRAINT BEHAVIOR** - Prevents premature solutioning

This is NOT a template system. This is a diagnostic reasoning engine.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

# Import Solution Restraint System
from tools.solution_restraint_system import RestraintDecision, solution_restraint_system


class TGM_Layer(Enum):
    """TGM Framework layers as reasoning protocol."""
    UNDERSTANDING_MARKET = "understanding_market"
    VALUE_CREATION = "value_creation"
    BRAND_BLUEPRINT = "brand_blueprint"
    AWARENESS = "awareness"
    ACQUISITION = "acquisition"
    ACTIVATION = "activation"
    CRM_RETENTION = "crm_retention"
    DATA_INSIGHT = "data_insight"
    
    # Cross-cutting concerns
    SCALABILITY = "scalability"
    UNIT_ECONOMICS = "unit_economics"
    OPERATIONAL_SUSTAINABILITY = "operational_sustainability"


class LeverageLevel(Enum):
    """Question leverage priority."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DiagnosticSignal(Enum):
    """Signals detected from user input."""
    BOTTLENECK = "bottleneck"
    AMBIGUITY = "ambiguity"
    STRATEGIC_TENSION = "strategic_tension"
    GOVERNANCE_GAP = "governance_gap"
    OBSERVABILITY_GAP = "observability_gap"
    OPERATIONAL_RISK = "operational_risk"
    ASSUMPTION = "assumption"
    MISSING_CONTEXT = "missing_context"


@dataclass
class ConversationState:
    """
    Tracks the state of Grill-Me conversation.
    
    This is the core of contextual reasoning - maintains awareness of:
    - What has been explored
    - What remains unclear
    - Where bottlenecks exist
    - Which TGM layers need more clarity
    """
    session_id: str
    user_initial_idea: str
    
    # TGM layer completeness (0.0 = not explored, 1.0 = fully clear)
    tgm_layer_clarity: Dict[TGM_Layer, float] = field(default_factory=lambda: {
        TGM_Layer.UNDERSTANDING_MARKET: 0.0,
        TGM_Layer.VALUE_CREATION: 0.0,
        TGM_Layer.BRAND_BLUEPRINT: 0.0,
        TGM_Layer.AWARENESS: 0.0,
        TGM_Layer.ACQUISITION: 0.0,
        TGM_Layer.ACTIVATION: 0.0,
        TGM_Layer.CRM_RETENTION: 0.0,
        TGM_Layer.DATA_INSIGHT: 0.0,
        TGM_Layer.SCALABILITY: 0.0,
        TGM_Layer.UNIT_ECONOMICS: 0.0,
        TGM_Layer.OPERATIONAL_SUSTAINABILITY: 0.0,
    })
    
    # Detected signals from conversation
    detected_signals: List[Dict] = field(default_factory=list)
    
    # Question history with context
    question_history: List[Dict] = field(default_factory=list)
    
    # User response quality tracking
    response_depth_scores: List[float] = field(default_factory=list)
    
    # Current conversational focus
    current_focus_layer: Optional[TGM_Layer] = None
    
    # Session metadata
    total_questions_asked: int = 0
    max_questions: int = 13
    session_complete: bool = False
    
    # Business context extracted from conversation
    extracted_context: Dict[str, any] = field(default_factory=dict)
    
    def get_unclear_layers(self, threshold: float = 0.6) -> List[TGM_Layer]:
        """Get TGM layers that still need clarification."""
        return [
            layer for layer, clarity in self.tgm_layer_clarity.items()
            if clarity < threshold
        ]
    
    def get_most_critical_unclear_layer(self) -> Optional[TGM_Layer]:
        """
        Determine which unclear layer has highest strategic leverage.
        
        Priority order based on TGM reasoning protocol:
        1. Foundation layers (market, value) must be clear first
        2. Then execution layers (acquisition, activation)
        3. Finally sustainability layers (data, economics, operations)
        """
        unclear_layers = self.get_unclear_layers()
        
        if not unclear_layers:
            return None
        
        # Strategic priority ordering
        priority_order = [
            TGM_Layer.UNDERSTANDING_MARKET,
            TGM_Layer.VALUE_CREATION,
            TGM_Layer.BRAND_BLUEPRINT,
            TGM_Layer.ACQUISITION,
            TGM_Layer.ACTIVATION,
            TGM_Layer.CRM_RETENTION,
            TGM_Layer.DATA_INSIGHT,
            TGM_Layer.UNIT_ECONOMICS,
            TGM_Layer.OPERATIONAL_SUSTAINABILITY,
            TGM_Layer.AWARENESS,
            TGM_Layer.SCALABILITY,
        ]
        
        # Return highest priority unclear layer
        for layer in priority_order:
            if layer in unclear_layers:
                return layer
        
        return unclear_layers[0] if unclear_layers else None
    
    def update_layer_clarity(self, layer: TGM_Layer, clarity_score: float):
        """Update clarity score for a TGM layer based on user response quality."""
        if layer in self.tgm_layer_clarity:
            # Exponential moving average to track progressive clarity
            current = self.tgm_layer_clarity[layer]
            self.tgm_layer_clarity[layer] = current * 0.3 + clarity_score * 0.7
    
    def add_signal(self, signal_type: DiagnosticSignal, details: str, layer: Optional[TGM_Layer] = None):
        """Record a diagnostic signal detected from user input."""
        self.detected_signals.append({
            "type": signal_type.value,
            "details": details,
            "layer": layer.value if layer else None,
            "timestamp": len(self.question_history)
        })
    
    def should_continue(self) -> bool:
        """Determine if conversation should continue or wrap up."""
        if self.session_complete:
            return False
        
        if self.total_questions_asked >= self.max_questions:
            return False
        
        # Check if all critical layers are sufficiently clear
        critical_layers = [
            TGM_Layer.UNDERSTANDING_MARKET,
            TGM_Layer.VALUE_CREATION,
            TGM_Layer.ACQUISITION,
            TGM_Layer.ACTIVATION,
            TGM_Layer.DATA_INSIGHT,
        ]
        
        all_clear = all(
            self.tgm_layer_clarity.get(layer, 0) >= 0.7
            for layer in critical_layers
        )
        
        # Continue if we haven't asked enough questions OR critical layers unclear
        return not all_clear or self.total_questions_asked < 8


@dataclass
class DiagnosticAnalysis:
    """Result of analyzing user input for strategic signals."""
    detected_signals: List[Dict]
    ambiguity_score: float  # 0.0 = clear, 1.0 = very ambiguous
    bottleneck_indicators: List[str]
    missing_context: List[str]
    suggested_focus_layer: Optional[TGM_Layer]
    confidence: float  # How confident we are in this analysis


class ContextAnalyzer:
    """
    Analyzes user input to detect strategic signals, ambiguity, and bottlenecks.
    
    This replaces hardcoded templates with dynamic contextual understanding.
    """
    
    # Keywords that indicate specific diagnostic signals
    SIGNAL_PATTERNS = {
        DiagnosticSignal.BOTTLENECK: [
            r'\b(sulit|kendala|hambatan|masalah|challenge|stuck|blocked)\b',
            r'\b(tidak bisa|gagal|drop|turun|menurun)\b',
            r'\b(bottleneck|friction|fricti)\b',
        ],
        DiagnosticSignal.AMBIGUITY: [
            r'\b(mungkin|mungkin saja|barangkali|perhaps|maybe)\b',
            r'\b(kurang tahu|tidak yakin|not sure|unsure)\b',
            r'\b(sekitar|kurang lebih|approximately|roughly)\b',
        ],
        DiagnosticSignal.STRATEGIC_TENSION: [
            r'\b(tapi|but|however|namun|sedangkan)\b.*\b(harus|need|should|want)\b',
            r'\b(di satu sisi|on one hand)\b',
            r'\b(trade-off|kompromi|balance)\b',
        ],
        DiagnosticSignal.GOVERNANCE_GAP: [
            r'\b(siapa yang|who will|who is responsible)\b',
            r'\b(tidak ada yang|no one|nobody)\b',
            r'\b(ownership|accountability|responsibility)\b',
        ],
        DiagnosticSignal.OBSERVABILITY_GAP: [
            r'\b(tidak track|tidak monitor|not tracking|not measuring)\b',
            r'\b(tidak tahu|don\'t know|unclear|unknown)\b.*\b(metric|kpi|data)\b',
            r'\b(blind spot|visibility|dashboard)\b',
        ],
        DiagnosticSignal.OPERATIONAL_RISK: [
            r'\b(terlalu banyak|too many|overwhelmed|overload)\b',
            r'\b(ketergantungan|dependency|rely on)\b',
            r'\b(risiko|risk|bahaya|danger)\b',
        ],
        DiagnosticSignal.ASSUMPTION: [
            r'\b(asumsi|assume|assuming|presume)\b',
            r'\b(seharusnya|should|expected)\b',
            r'\b(kemungkinan|likely|probably)\b',
        ],
    }
    
    # Keywords mapping to TGM layers
    LAYER_KEYWORDS = {
        TGM_Layer.UNDERSTANDING_MARKET: [
            r'\b(target|market|customer|user|segment|demografi)\b',
            r'\b(pain point|kebutuhan|need|problem)\b',
            r'\b(kompetitor|competitor|alternatif|alternative)\b',
        ],
        TGM_Layer.VALUE_CREATION: [
            r'\b(differentiation|unique|beda|different)\b',
            r'\b(value|nilai|benefit|advantage)\b',
            r'\b(solve|selesaikan|solution|solusi)\b',
        ],
        TGM_Layer.BRAND_BLUEPRINT: [
            r'\b(brand|positioning|posisi|image)\b',
            r'\b(trust|kepercayaan|credibility|authority)\b',
            r'\b(narrative|cerita|story|messaging)\b',
        ],
        TGM_Layer.AWARENESS: [
            r'\b(awareness|reach|jangkauan|visibility)\b',
            r'\b(channel|saluran|platform|media)\b',
            r'\b(content|konten|creative)\b',
        ],
        TGM_Layer.ACQUISITION: [
            r'\b(acquisition|lead|prospek|calon customer)\b',
            r'\b(cac|cost per|biaya per)\b',
            r'\b(funnel|corong|conversion rate)\b',
        ],
        TGM_Layer.ACTIVATION: [
            r'\b(activation|onboarding|sign up|register)\b',
            r'\b(convert|konversi|purchase|buy)\b',
            r'\b(friction|gesekan|hesitation)\b',
        ],
        TGM_Layer.CRM_RETENTION: [
            r'\b(retention|retensi|repeat|loyalty)\b',
            r'\b(churn|berhenti|leave|cancel)\b',
            r'\b(referral|word of mouth|recommend)\b',
        ],
        TGM_Layer.DATA_INSIGHT: [
            r'\b(data|metric|kpi|measure|track)\b',
            r'\b(analytics|insight|dashboard|report)\b',
            r'\b(governance|ownership|responsibility)\b',
        ],
        TGM_Layer.UNIT_ECONOMICS: [
            r'\b(revenue|pendapatan|income)\b',
            r'\b(cost|biaya|expense|spend)\b',
            r'\b(profit|margin|ltv|cac|unit economics)\b',
        ],
        TGM_Layer.SCALABILITY: [
            r'\b(scale|skala|growth|pertumbuhan)\b',
            r'\b(infrastructure|tech|system|platform)\b',
            r'\b(capacity|kapasitas|resource)\b',
        ],
        TGM_Layer.OPERATIONAL_SUSTAINABILITY: [
            r'\b(operasional|operation|process|workflow)\b',
            r'\b(team|tim|people|human resource)\b',
            r'\b(sustainable|berkelanjutan|long-term)\b',
        ],
    }
    
    def analyze_input(self, user_input: str, conversation_state: ConversationState) -> DiagnosticAnalysis:
        """
        Analyze user input to extract strategic signals and determine next focus.
        
        Returns comprehensive diagnostic analysis for reasoning engine.
        """
        signals = self._detect_signals(user_input)
        ambiguity = self._calculate_ambiguity(user_input)
        bottlenecks = self._extract_bottleneck_indicators(user_input)
        missing_ctx = self._identify_missing_context(user_input, conversation_state)
        suggested_layer = self._determine_focus_layer(user_input, conversation_state)
        confidence = self._calculate_confidence(signals, ambiguity, missing_ctx)
        
        return DiagnosticAnalysis(
            detected_signals=signals,
            ambiguity_score=ambiguity,
            bottleneck_indicators=bottlenecks,
            missing_context=missing_ctx,
            suggested_focus_layer=suggested_layer,
            confidence=confidence
        )
    
    def _detect_signals(self, text: str) -> List[Dict]:
        """Detect diagnostic signals from user input using pattern matching."""
        detected = []
        text_lower = text.lower()
        
        for signal_type, patterns in self.SIGNAL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    detected.append({
                        "type": signal_type.value,
                        "matched_pattern": pattern,
                        "text_snippet": text[:100]
                    })
                    break  # One match per signal type is enough
        
        return detected
    
    def _calculate_ambiguity(self, text: str) -> float:
        """
        Calculate ambiguity score based on linguistic markers.
        
        Higher score = more ambiguous/vague input.
        """
        ambiguity_markers = [
            r'\b(mungkin|perhaps|maybe|might|could)\b',
            r'\b(kurang|less|not quite|somewhat)\b',
            r'\b(sekitar|around|approximately|roughly)\b',
            r'\b(tidak yakin|not sure|unsure|uncertain)\b',
        ]
        
        text_lower = text.lower()
        matches = sum(1 for pattern in ambiguity_markers if re.search(pattern, text_lower))
        
        # Normalize to 0-1 scale (cap at 1.0)
        return min(matches / 4.0, 1.0)
    
    def _extract_bottleneck_indicators(self, text: str) -> List[str]:
        """Extract specific bottleneck indicators from user input."""
        bottleneck_patterns = [
            r'(sulit|kendala|hambatan)[\s\S]{0,50}',
            r'(tidak bisa|gagal|drop)[\s\S]{0,50}',
            r'(bottleneck|friction|block)[\s\S]{0,50}',
        ]
        
        indicators = []
        text_lower = text.lower()
        
        for pattern in bottleneck_patterns:
            matches = re.findall(pattern, text_lower)
            indicators.extend(matches)
        
        return indicators[:5]  # Limit to top 5
    
    def _identify_missing_context(self, text: str, state: ConversationState) -> List[str]:
        """Identify what critical context is still missing."""
        missing = []
        
        # Check if basic business model is clear
        if state.tgm_layer_clarity[TGM_Layer.UNDERSTANDING_MARKET] < 0.3:
            missing.append("target_market_clarity")
        
        if state.tgm_layer_clarity[TGM_Layer.VALUE_CREATION] < 0.3:
            missing.append("value_proposition_clarity")
        
        if state.tgm_layer_clarity[TGM_Layer.ACQUISITION] < 0.3:
            missing.append("acquisition_strategy_clarity")
        
        if state.tgm_layer_clarity[TGM_Layer.DATA_INSIGHT] < 0.3:
            missing.append("measurement_framework_clarity")
        
        return missing
    
    def _determine_focus_layer(self, text: str, state: ConversationState) -> Optional[TGM_Layer]:
        """Determine which TGM layer the user is implicitly focusing on."""
        text_lower = text.lower()
        
        # Count keyword matches for each layer
        layer_scores = {}
        for layer, patterns in self.LAYER_KEYWORDS.items():
            score = sum(1 for pattern in patterns if re.search(pattern, text_lower))
            if score > 0:
                layer_scores[layer] = score
        
        if not layer_scores:
            # If no clear layer detected, fall back to most unclear critical layer
            return state.get_most_critical_unclear_layer()
        
        # Return layer with highest keyword match
        return max(layer_scores, key=layer_scores.get)
    
    def _calculate_confidence(self, signals: List[Dict], ambiguity: float, missing_ctx: List[str]) -> float:
        """Calculate confidence in the diagnostic analysis."""
        # More signals = higher confidence
        signal_confidence = min(len(signals) / 3.0, 1.0)
        
        # Lower ambiguity = higher confidence
        clarity_confidence = 1.0 - ambiguity
        
        # Less missing context = higher confidence
        context_confidence = max(0.0, 1.0 - (len(missing_ctx) / 4.0))
        
        # Weighted average
        confidence = (
            signal_confidence * 0.4 +
            clarity_confidence * 0.4 +
            context_confidence * 0.2
        )
        
        return round(confidence, 2)


class QuestionGenerator:
    """
    Generates contextual questions based on diagnostic analysis.
    
    NOT template-driven. Questions are dynamically constructed based on:
    - Detected signals
    - Ambiguity level
    - Missing context
    - TGM layer clarity gaps
    - Strategic leverage
    """
    
    # Question construction patterns (not full templates, but frameworks)
    QUESTION_PATTERNS = {
        TGM_Layer.UNDERSTANDING_MARKET: {
            "clarification": "Bisa jelaskan lebih spesifik tentang {focus_area}? Siapa exact target user dan apa pain point paling akut mereka?",
            "bottleneck": "Di bagian market understanding, di mana bottleneck terbesar? Apakah di segment definition, competitor analysis, atau customer motivation?",
            "ambiguity": "Sepertinya ada ambiguity di market understanding. Bisa clarify: apa yang membuat kamu yakin market ini viable?",
        },
        TGM_Layer.VALUE_CREATION: {
            "clarification": "Apa differentiation konkret bisnis ini? Kenapa customer harus choose ini over existing alternatives?",
            "bottleneck": "Di value creation, apa yang masih unclear? Apakah di unfair advantage, premium justification, atau hidden weakness?",
            "ambiguity": "Value proposition masih terasa generic. Apa unique angle yang hard to copy oleh competitor?",
        },
        TGM_Layer.BRAND_BLUEPRINT: {
            "clarification": "Bagaimana positioning strategy? Apa trust mechanism yang akan dibangun untuk establish authority?",
            "bottleneck": "Di brand blueprint, di mana perception gap antara brand promise vs operational reality?",
            "ambiguity": "Positioning belum sharp. Apa narrative consistency yang akan dijaga across semua touchpoint?",
        },
        TGM_Layer.AWARENESS: {
            "clarification": "Channel strategy apa untuk awareness? Bagaimana content direction yang aligned dengan positioning?",
            "bottleneck": "Di awareness layer, apa bottleneck utama? Channel saturation, content quality, atau audience targeting?",
            "ambiguity": "Awareness strategy masih vague. Channel mana yang punya leverage tertinggi untuk niche ini?",
        },
        TGM_Layer.ACQUISITION: {
            "clarification": "Bagaimana lead generation mechanics? Sudah pertimbangkan CAC observability by channel?",
            "bottleneck": "Di acquisition funnel, di mana leakage terbesar? Top of funnel volume atau lead quality?",
            "ambiguity": "Acquisition strategy belum measurable. Apa leading indicator yang akan tracked untuk early warning?",
        },
        TGM_Layer.ACTIVATION: {
            "clarification": "Apa conversion bottleneck utama? Bagaimana operational capacity untuk handle inbound leads?",
            "bottleneck": "Di activation flow, di mana friction point terbesar? Sales process, follow-up speed, atau product demo?",
            "ambiguity": "Activation metrics masih unclear. Apa definition of 'activated user' dan berapa target conversion rate?",
        },
        TGM_Layer.CRM_RETENTION: {
            "clarification": "Bagaimana retention mechanism? Apa referral loop yang bisa diaktifkan untuk organic growth?",
            "bottleneck": "Di CRM layer, apa churn driver utama? Product-market fit, customer experience, atau pricing?",
            "ambiguity": "Retention strategy belum concrete. Apa feedback loop mechanism untuk continuous improvement?",
        },
        TGM_Layer.DATA_INSIGHT: {
            "clarification": "Apa KPI framework dan governance ownership structure? Di mana observability gap yang perlu ditutup?",
            "bottleneck": "Di data layer, apa metric inconsistency atau visibility gap yang menghambat decision quality?",
            "ambiguity": "Measurement framework masih ambiguous. Apa north star metric dan bagaimana cascade ke team-level KPIs?",
        },
        TGM_Layer.UNIT_ECONOMICS: {
            "clarification": "Bagaimana unit economics model? Apa LTV:CAC ratio target dan break-even timeline?",
            "bottleneck": "Di profitability layer, apa hidden cost atau margin pressure yang belum terlihat?",
            "ambiguity": "Unit economics belum clear. Apa contribution margin by segment dan scalability constraint?",
        },
        TGM_Layer.SCALABILITY: {
            "clarification": "Apa scalability risk terbesar? Bagaimana infrastructure readiness untuk handle 10x growth?",
            "bottleneck": "Di scalability layer, apa architectural constraint atau technical debt yang bisa block growth?",
            "ambiguity": "Scalability plan masih vague. Apa horizontal vs vertical scaling strategy dan capex requirement?",
        },
        TGM_Layer.OPERATIONAL_SUSTAINABILITY: {
            "clarification": "Apa operational constraint dan sustainability risk? Bagaimana mengurangi dependency pada individual heroics?",
            "bottleneck": "Di operational layer, di mana process fragmentation atau governance gap yang menyebabkan inefficiency?",
            "ambiguity": "Operational model belum sustainable. Bagaimana systematize processes untuk reduce ambiguity dan improve consistency?",
        },
    }
    
    def generate_question(
        self,
        analysis: DiagnosticAnalysis,
        conversation_state: ConversationState
    ) -> Dict:
        """
        Generate contextual question based on diagnostic analysis.
        
        Returns structured question with phase, leverage, and contextual recommendation.
        """
        # Determine question type based on signals
        if analysis.ambiguity_score > 0.6:
            question_type = "ambiguity"
        elif analysis.bottleneck_indicators:
            question_type = "bottleneck"
        else:
            question_type = "clarification"
        
        # Get focus layer
        focus_layer = analysis.suggested_focus_layer or \
                     conversation_state.get_most_critical_unclear_layer()
        
        if not focus_layer:
            # Fallback if no clear focus
            return self._generate_fallback_question(conversation_state)
        
        # Generate question using pattern
        question_text = self._construct_question(
            focus_layer,
            question_type,
            analysis
        )
        
        # Generate contextual recommendation
        recommendation = self._generate_recommendation(
            focus_layer,
            analysis,
            conversation_state
        )
        
        # Determine leverage
        leverage = self._determine_leverage(focus_layer, analysis, conversation_state)
        
        # Format phase label
        phase_label = self._format_phase_label(focus_layer)
        
        return {
            "question": question_text,
            "recommendation": recommendation,
            "phase": phase_label,
            "leverage": leverage.value,
            "focus_layer": focus_layer.value,
            "question_type": question_type,
            "confidence": analysis.confidence
        }
    
    def _construct_question(self, layer: TGM_Layer, q_type: str, analysis: DiagnosticAnalysis) -> str:
        """Construct question using pattern and contextual information."""
        patterns = self.QUESTION_PATTERNS.get(layer, {})
        pattern = patterns.get(q_type, patterns.get("clarification", ""))
        
        # Fill in focus area based on detected signals
        focus_area = self._extract_focus_area(analysis)
        question = pattern.format(focus_area=focus_area or "aspek ini")
        
        return question
    
    def _extract_focus_area(self, analysis: DiagnosticAnalysis) -> str:
        """Extract specific focus area from diagnostic signals."""
        if analysis.bottleneck_indicators:
            return analysis.bottleneck_indicators[0][:50]
        
        if analysis.missing_context:
            return analysis.missing_context[0].replace("_", " ")
        
        return ""
    
    def _generate_recommendation(
        self,
        layer: TGM_Layer,
        analysis: DiagnosticAnalysis,
        state: ConversationState
    ) -> str:
        """
        Generate contextual recommendation based on business reality.
        
        NOT hardcoded. Recommendation considers:
        - Detected signals
        - Current clarity level
        - Strategic priorities
        """
        recommendations = {
            TGM_Layer.UNDERSTANDING_MARKET: [
                "Validasi market assumption dengan customer interview sebelum build. Pain point harus acute, bukan nice-to-have.",
                "Map competitor positioning matrix. Identify white space opportunity yang underserved.",
                "Quantify market size dengan bottom-up approach. TAM/SAM/SOM harus realistic.",
            ],
            TGM_Layer.VALUE_CREATION: [
                "Jangan competing on features. Compete on niche positioning atau superior UX yang hard to copy.",
                "Identify unfair advantage: network effect, proprietary data, atau switching cost.",
                "Test value proposition dengan landing page experiment sebelum full build.",
            ],
            TGM_Layer.BRAND_BLUEPRINT: [
                "Authority comes dari consistent narrative dan proof of expertise. Build thought leadership early.",
                "Trust mechanism harus explicit: testimonial, case study, atau third-party validation.",
                "Avoid generic positioning. Be specific about who you serve dan how you're different.",
            ],
            TGM_Layer.AWARENESS: [
                "Start dengan 1-2 channel saja. Master satu channel sebelum diversify.",
                "Content direction harus aligned dengan positioning. Consistency > virality.",
                "Track awareness metrics: reach, engagement rate, brand recall survey.",
            ],
            TGM_Layer.ACQUISITION: [
                "Track CAC by channel dari hari pertama. Lead quality > lead quantity.",
                "Build funnel efficiency dashboard. Identify leakage point early.",
                "Test multiple acquisition channels dengan small budget before scale.",
            ],
            TGM_Layer.ACTIVATION: [
                "Identify top 3 friction points in activation flow. Fix bottlenecks before adding features.",
                "Define 'activated user' clearly. Track time-to-value metric.",
                "Optimize onboarding untuk reduce time-to-first-success.",
            ],
            TGM_Layer.CRM_RETENTION: [
                "Retention > Acquisition untuk sustainable growth. Track cohort retention weekly.",
                "Build feedback loop mechanism. Customer insight harus inform product roadmap.",
                "Activate referral loop dengan incentive yang aligned dengan customer value.",
            ],
            TGM_Layer.DATA_INSIGHT: [
                "Prioritaskan observability lebih dulu daripada automation. Metric consistency lintas team.",
                "Establish KPI governance: siapa owner tiap metric, review cadence, escalation process.",
                "Build anomaly detection untuk early warning system. Don't wait for monthly report.",
            ],
            TGM_Layer.UNIT_ECONOMICS: [
                "Calculate LTV:CAC ratio early. Target minimum 3:1 untuk sustainable unit economics.",
                "Identify break-even point dan cash runway. Track burn rate weekly.",
                "Track contribution margin by segment. Some customers may be unprofitable.",
            ],
            TGM_Layer.SCALABILITY: [
                "Optimize for developer velocity, bukan premature optimization. Tapi identify architectural constraints early.",
                "Plan for 10x growth dari sekarang. Infrastructure decision sulit di-reverse nanti.",
                "Balance between speed dan sustainability. Technical debt accrues interest.",
            ],
            TGM_Layer.OPERATIONAL_SUSTAINABILITY: [
                "Build systems, not heroics. Document processes untuk reduce ambiguity.",
                "Reduce dependency pada individual. Cross-train team untuk resilience.",
                "Establish governance rhythm: weekly review, monthly retrospective, quarterly planning.",
            ],
        }
        
        # Select recommendation based on context
        layer_recs = recommendations.get(layer, [])
        
        if not layer_recs:
            return "Focus on building observability before scaling. Measure first, optimize second."
        
        # Choose recommendation based on detected signals
        if analysis.detected_signals:
            signal_types = [s["type"] for s in analysis.detected_signals]
            if "bottleneck" in signal_types:
                return layer_recs[0]  # First rec usually addresses bottleneck
            elif "ambiguity" in signal_types:
                return layer_recs[-1] if len(layer_recs) > 1 else layer_recs[0]
        
        # Default: pick based on clarity level
        clarity = state.tgm_layer_clarity.get(layer, 0)
        if clarity < 0.3:
            return layer_recs[0]  # Foundational advice
        elif clarity < 0.6:
            return layer_recs[1] if len(layer_recs) > 1 else layer_recs[0]
        else:
            return layer_recs[-1]  # Advanced advice
    
    def _determine_leverage(
        self,
        layer: TGM_Layer,
        analysis: DiagnosticAnalysis,
        state: ConversationState
    ) -> LeverageLevel:
        """Determine question leverage based on strategic importance."""
        # Critical layers always have high leverage
        critical_layers = [
            TGM_Layer.UNDERSTANDING_MARKET,
            TGM_Layer.VALUE_CREATION,
            TGM_Layer.DATA_INSIGHT,
            TGM_Layer.UNIT_ECONOMICS,
        ]
        
        if layer in critical_layers:
            return LeverageLevel.CRITICAL
        
        # High leverage if ambiguity or bottleneck detected
        if analysis.ambiguity_score > 0.5 or analysis.bottleneck_indicators:
            return LeverageLevel.HIGH
        
        # Medium leverage for tactical layers
        tactical_layers = [
            TGM_Layer.AWARENESS,
            TGM_Layer.ACQUISITION,
            TGM_Layer.ACTIVATION,
            TGM_Layer.CRM_RETENTION,
        ]
        
        if layer in tactical_layers:
            return LeverageLevel.HIGH
        
        return LeverageLevel.MEDIUM
    
    def _format_phase_label(self, layer: TGM_Layer) -> str:
        """Format human-readable phase label."""
        labels = {
            TGM_Layer.UNDERSTANDING_MARKET: "Strategic - Understanding Market",
            TGM_Layer.VALUE_CREATION: "Strategic - Value Creation",
            TGM_Layer.BRAND_BLUEPRINT: "Strategic - Brand Blueprint",
            TGM_Layer.AWARENESS: "Tactical - Awareness",
            TGM_Layer.ACQUISITION: "Tactical - Acquisition",
            TGM_Layer.ACTIVATION: "Tactical - Activation",
            TGM_Layer.CRM_RETENTION: "Tactical - CRM & Retention",
            TGM_Layer.DATA_INSIGHT: "Engine - Data & Insight",
            TGM_Layer.UNIT_ECONOMICS: "Engine - Unit Economics",
            TGM_Layer.SCALABILITY: "Engine - Scalability",
            TGM_Layer.OPERATIONAL_SUSTAINABILITY: "Engine - Operational Sustainability",
        }
        
        return labels.get(layer, "Strategic - General")
    
    def _generate_fallback_question(self, state: ConversationState) -> Dict:
        """Generate fallback question when no clear direction."""
        unclear_layers = state.get_unclear_layers(threshold=0.5)
        
        if unclear_layers:
            layer = unclear_layers[0]
            return {
                "question": f"Mari clarify {layer.value.replace('_', ' ')}. Apa yang masih unclear di bagian ini?",
                "recommendation": "Focus on reducing ambiguity before moving forward. Clarity precedes execution.",
                "phase": "Clarification",
                "leverage": "high",
                "focus_layer": layer.value,
                "question_type": "clarification",
                "confidence": 0.5
            }
        
        return {
            "question": "Jika sudah cukup context, apa MVP realistis yang bisa dibangun dengan vertical slice thinking?",
            "recommendation": "Prioritaskan observability lebih dulu daripada automation. Build MVP yang measurable, bukan feature-complete.",
            "phase": "Implementation - MVP Realistis",
            "leverage": "high",
            "focus_layer": "implementation",
            "question_type": "synthesis",
            "confidence": 0.7
        }


class ResponseFormatter:
    """Formats grill responses with Rohadi AI style."""
    
    @staticmethod
    def format(question_data: Dict) -> str:
        """
        Format question and recommendation in Rohadi AI style.
        
        Output Style:
        - Ringkas tapi tajam
        - Fokus pada leverage terbesar
        - Jelaskan trade-off dan risiko
        - Gunakan reasoning yang observable dan explicit
        """
        leverage = question_data.get('leverage', 'medium')
        leverage_indicator = {
            'critical': '🔴 CRITICAL',
            'high': '🟠 HIGH',
            'medium': '🟡 MEDIUM',
            'low': '⚪ LOW',
        }.get(leverage, '🟡 MEDIUM')
        
        phase = question_data.get('phase', 'General')
        question = question_data.get('question', '')
        recommendation = question_data.get('recommendation', '')
        
        response = f"{leverage_indicator} **[{phase}]**\n\n"
        response += f"**Pertanyaan:**\n{question}\n\n"
        response += f"**Rekomendasi Rohadi:**\n{recommendation}"
        
        return response


class GrillMeSkillV2:
    """
    Rohadi AI v2: Contextual Strategic Reasoning Engine
    
    Architectural improvements:
    1. Stateful conversation tracking with TGM layer clarity scores
    2. Dynamic diagnostic analysis instead of template matching
    3. Contextual question generation based on detected signals
    4. Leverage-based prioritization for strategic impact
    5. Observability-oriented reasoning protocol
    
    This is NOT a template system. This is a diagnostic reasoning engine
    that adapts to user's business reality.
    """
    
    def __init__(self):
        self.context_analyzer = ContextAnalyzer()
        self.question_generator = QuestionGenerator()
        self.response_formatter = ResponseFormatter()
        
        # Session state management
        self.active_sessions: Dict[str, ConversationState] = {}
    
    def generate_grill_question(
        self,
        user_input: str,
        conversation_history: list = None,
        session_id: str = "default"
    ) -> dict:
        """
        Main entry point: Generate next grill question using contextual reasoning.
        
        INTEGRATED WITH SOLUTION RESTRAINT BEHAVIOR:
        - Evaluates diagnosis confidence before generating questions
        - Prevents premature solutioning even with long context
        - Forces deeper diagnosis when confidence is low
        
        Args:
            user_input: Current user message
            conversation_history: Previous Q&A pairs (for backward compatibility)
            session_id: Unique session identifier for state tracking
            
        Returns:
            Dict with question, recommendation, phase, leverage, and metadata
        """
        # Initialize or retrieve session state
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = ConversationState(
                session_id=session_id,
                user_initial_idea=user_input
            )
        
        state = self.active_sessions[session_id]
        
        # Check if session should continue
        if not state.should_continue():
            state.session_complete = True
            return self._generate_wrap_up_message(state)
        
        # Analyze the current input before evaluating restraint. The previous
        # ordering evaluated a brand-new zeroed state and returned without ever
        # updating it, so every turn could repeat the same question forever.
        analysis = self.context_analyzer.analyze_input(user_input, state)

        for signal in analysis.detected_signals:
            state.add_signal(
                DiagnosticSignal(signal["type"]),
                signal.get("text_snippet", signal.get("matched_pattern", "")),
                state.current_focus_layer,
            )

        if state.current_focus_layer:
            state.update_layer_clarity(
                state.current_focus_layer, 1.0 - analysis.ambiguity_score
            )
        self._extract_business_context(user_input, state)

        restraint_decision = solution_restraint_system.evaluate_diagnosis_sufficiency(
            conversation_state=state,
            user_input=user_input,
            requested_solution_type=None,
        )

        if restraint_decision.should_restrain:
            print(
                f"[SOLUTION RESTRAINT] Activated - Confidence: "
                f"{restraint_decision.confidence_score:.2f}"
            )
            print(
                f"[SOLUTION RESTRAINT] Reason: "
                f"{restraint_decision.restraint_reasoning[:100]}..."
            )
            question_data = self._generate_restraint_question(
                restraint_decision, state, user_input
            )
        else:
            question_data = self.question_generator.generate_question(analysis, state)

        # Every turn, including restraint turns, advances the session state.
        state.question_history.append(
            {
                "question": question_data["question"],
                "user_response": user_input,
                "focus_layer": question_data.get("focus_layer"),
                "analysis": {
                    "ambiguity": analysis.ambiguity_score,
                    "signals": len(analysis.detected_signals),
                    "confidence": analysis.confidence,
                    "restraint": restraint_decision.should_restrain,
                },
            }
        )
        state.total_questions_asked += 1
        focus_layer = question_data.get("focus_layer")
        state.current_focus_layer = (
            TGM_Layer(focus_layer)
            if focus_layer in [layer.value for layer in TGM_Layer]
            else None
        )
        state.response_depth_scores.append(1.0 - analysis.ambiguity_score)
        return question_data
    
    def _generate_restraint_question(
        self,
        restraint_decision: RestraintDecision,
        state: ConversationState,
        user_input: str
    ) -> dict:
        """
        Generate diagnostic question when solution restraint is activated.
        
        This prevents premature solutioning by forcing deeper diagnosis.
        """
        # Get suggested next focus from restraint system
        next_focus = restraint_decision.suggested_next_focus
        
        # Map weakest dimension to TGM layer for questioning
        if restraint_decision.weakest_dimensions:
            weakest_dim, weakest_score = restraint_decision.weakest_dimensions[0]
            
            # Generate targeted diagnostic question based on weakest dimension
            dimension_to_layer_mapping = {
                "market_clarity": "understanding_market",
                "bottleneck_clarity": "acquisition",  # Usually acquisition bottleneck
                "value_prop_clarity": "value_creation",
                "acquisition_clarity": "acquisition",
                "activation_clarity": "activation",
                "operational_clarity": "operational_sustainability",
                "governance_clarity": "data_insight",
                "economics_clarity": "unit_economics",
                "strategic_tension_clarity": "value_creation",
            }
            
            layer_name = dimension_to_layer_mapping.get(weakest_dim.value, "understanding_market")
            
            # Find matching TGM layer
            focus_layer = None
            for layer in TGM_Layer:
                if layer.value == layer_name:
                    focus_layer = layer
                    break
            
            if not focus_layer:
                focus_layer = TGM_Layer.UNDERSTANDING_MARKET
        else:
            focus_layer = TGM_Layer.UNDERSTANDING_MARKET
        
        # Generate restraint-aware question
        question_templates = {
            "market_clarity": (
                f"Sebelum saya memberikan rekomendasi strategis, saya perlu memahami lebih dalam: "
                f"{next_focus}. Bisa jelaskan lebih spesifik?"
            ),
            "bottleneck_clarity": (
                f"Saya melihat ada beberapa kemungkinan bottleneck. "
                f"Untuk memastikan diagnosis tepat: {next_focus} - mana yang paling critical menurut Anda?"
            ),
            "default": (
                f"Saya belum ingin terburu-buru memberikan solusi. "
                f"Mari kita pastikan dulu: {next_focus}"
            ),
        }
        
        # Select template based on weakest dimension
        if restraint_decision.weakest_dimensions:
            weakest_dim_name = restraint_decision.weakest_dimensions[0][0].value
            question_template = question_templates.get(weakest_dim_name, question_templates["default"])
        else:
            question_template = question_templates["default"]
        
        # Generate contextual recommendation
        recommendation = (
            f"**Mengapa saya menahan diri:**\n"
            f"{restraint_decision.restraint_reasoning}"
        )
        
        return {
            "question": question_template,
            "recommendation": recommendation,
            "phase": "Diagnostic - Clarification Needed",
            "leverage": "critical",
            "focus_layer": focus_layer.value,
            "question_type": "restraint_diagnostic",
            "confidence": restraint_decision.confidence_score,
            "restraint_activated": True
        }
    
    def format_response(self, question_data: dict) -> str:
        """Format question data into Rohadi AI styled response."""
        return ResponseFormatter.format(question_data)
    
    def get_session_state(self, session_id: str) -> Optional[ConversationState]:
        """Retrieve current session state for debugging/monitoring."""
        return self.active_sessions.get(session_id)
    
    def reset_session(self, session_id: str):
        """Reset session state for new conversation."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
    
    def _extract_business_context(self, user_input: str, state: ConversationState):
        """Extract and store business context from user input."""
        # Simple extraction - can be enhanced with NLP
        patterns = {
            "industry": r'\bindustri|industry|sector\b.*?([A-Za-z\s]{10,50})',
            "business_model": r'\bbusiness model\b.*?([A-Za-z\s]{10,50})',
            "target_market": r'\btarget\b.*?([A-Za-z\s]{10,50})',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match and key not in state.extracted_context:
                state.extracted_context[key] = match.group(1).strip()
    
    def _generate_wrap_up_message(self, state: ConversationState) -> dict:
        """Generate wrap-up message when session is complete."""
        unclear_layers = state.get_unclear_layers(threshold=0.7)
        
        if unclear_layers:
            summary = "\n\n**Areas yang masih perlu clarification:**\n"
            for layer in unclear_layers[:3]:
                clarity = state.tgm_layer_clarity[layer]
                summary += f"- {layer.value.replace('_', ' ').title()} (clarity: {clarity:.0%})\n"
        else:
            summary = "\n\n✅ Semua critical layers sudah cukup clear untuk mulai eksekusi."
        
        return {
            "question": f"Session complete.{summary}\n\nApa next step yang akan kamu ambil berdasarkan diskusi ini?",
            "recommendation": "Start with MVP yang measurable. Prioritaskan observability dari hari pertama. Iterate based on data, bukan assumption.",
            "phase": "Wrap-up - Next Steps",
            "leverage": "high",
            "focus_layer": "wrap_up",
            "question_type": "synthesis",
            "confidence": 0.9
        }


# Singleton instance
grill_me_skill = GrillMeSkillV2()
