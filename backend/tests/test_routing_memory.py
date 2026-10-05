from logic.cognitive_router import CognitiveRouter
from logic.memory_manager import MemoryManager
from logic.routing_policy import PolicyEngine
from tools.grill_me_skill_v2 import GrillMeSkillV2


def test_heuristic_profile_is_useful_when_provider_is_down():
    router = CognitiveRouter()
    features = router._heuristic_features("Bagaimana membuat microservice dengan kubernetes?")
    profile_data = router._coerce_profile_data(
        router._compute_derived_scores({**router._default_profile_data(), **features})
    )
    assert profile_data["domain"] == "architecture"
    assert profile_data["reasoning_complexity"] >= 0.7


def test_policy_keeps_factual_questions_on_fast_path():
    router = CognitiveRouter()
    data = router._coerce_profile_data(
        router._compute_derived_scores(
            {**router._default_profile_data(), **router._heuristic_features("Kapan Indonesia merdeka?")}
        )
    )
    from logic.cognitive_router import IntentProfile

    intent = IntentProfile(**data)
    policy = PolicyEngine().build_policy(intent, "Kapan Indonesia merdeka?")
    assert policy.reasoning_mode == "direct_factual_mode"
    assert policy.auto_grill_me is False


def test_grill_session_advances_after_restraint_turn():
    skill = GrillMeSkillV2()
    skill.generate_grill_question(
        "Saya ingin membangun bisnis kopi tetapi belum tahu target market.",
        session_id="progress-test",
    )
    state = skill.get_session_state("progress-test")
    assert state is not None
    assert state.total_questions_asked == 1
    assert len(state.question_history) == 1


def test_session_rooms_are_isolated_and_safe():
    manager = MemoryManager()
    assert manager.session_room("user/a") == "session_user_a"
    assert manager.session_room("one") != manager.session_room("two")
    manager._writer.shutdown(wait=True)
