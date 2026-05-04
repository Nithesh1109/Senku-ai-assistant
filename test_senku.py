"""Comprehensive verification for Senku 3.1 Intelligence Upgrade"""
import sys
sys.path.insert(0, ".")

try:
    # ═══════════════════════════════════════════════════════
    # 1. CORE IMPORTS
    # ═══════════════════════════════════════════════════════
    from senku.core.types import (
        Action, ActionResult, ActionStatus, ErrorClass,
        Intent, IntentType, ExecutionPlan, FeedbackScore,
        RetryPolicy, SessionContext, ConversationTurn,
    )
    from senku.core.exceptions import SenkuError, LLMConnectionError
    from senku.core.events import EventBus, event_bus, Events
    print("✅ Core: OK (types, exceptions, events)")

    from senku.config import (
        OLLAMA_BASE_URL, ACTION_SCHEMA, RETRY_STRATEGIES,
        PATTERN_FILE, SCHEDULE_FILE, FEEDBACK_FILE,
        MIN_CONFIDENCE_THRESHOLD, AMBIGUITY_THRESHOLD,
        FEEDBACK_WEIGHTS, SPEED_BASELINE_MS,
    )
    print("✅ Config: OK (all new settings)")

    # ═══════════════════════════════════════════════════════
    # 2. MEMORY IMPORTS
    # ═══════════════════════════════════════════════════════
    from senku.memory.store import MemoryStore
    from senku.memory.conversation import ConversationMemory
    from senku.memory.action_log import ActionLog
    from senku.memory.context import ContextManager
    from senku.memory.pattern_learner import PatternLearner
    print("✅ Memory: OK (store, conversation, action_log, context, pattern_learner)")

    # ═══════════════════════════════════════════════════════
    # 3. BRAIN IMPORTS
    # ═══════════════════════════════════════════════════════
    from senku.brain.prompts import build_action_prompt, build_chat_prompt
    from senku.brain.preprocessor import Preprocessor
    from senku.brain.llm_client import LLMClient
    from senku.brain.parser import ResponseParser
    from senku.brain.reasoning import ReasoningEngine
    from senku.brain.decision import DecisionLayer
    from senku.brain.feedback import FeedbackLoop
    from senku.brain.scheduler import TaskScheduler, parse_schedule_from_input
    from senku.brain.planner import Planner
    print("✅ Brain: OK (prompts, preprocessor, llm, parser, reasoning, "
          "decision, feedback, scheduler, planner)")

    # ═══════════════════════════════════════════════════════
    # 4. ACTION IMPORTS
    # ═══════════════════════════════════════════════════════
    from senku.actions.registry import registry
    from senku.actions.launcher import AppLauncher
    from senku.actions.executor import Executor
    print(f"✅ Actions: OK ({registry.action_count} handlers registered)")

    # ═══════════════════════════════════════════════════════
    # 5. MAIN IMPORT
    # ═══════════════════════════════════════════════════════
    from senku.main import Senku
    print("✅ Main: OK")

    print()
    print("═" * 50)
    print("  ALL IMPORTS SUCCESSFUL")
    print("═" * 50)

    # ═══════════════════════════════════════════════════════
    # 6. TEST: ExecutionPlan dependency graph
    # ═══════════════════════════════════════════════════════
    print("\n--- Test: ExecutionPlan dependency graph ---")
    a1 = Action("open_app", {"app": "chrome"}, id="a1")
    a2 = Action("search_web", {"query": "python"}, id="a2",
                depends_on="a1", condition="previous_success")
    a3 = Action("search_web", {"query": "chrome download"}, id="a3",
                depends_on="a1", condition="previous_failed")

    plan = ExecutionPlan(goal="open chrome and search", steps=[a1, a2, a3])

    # a1 not done yet → should return a1
    next_step = plan.get_next_executable(set(), set())
    assert next_step.id == "a1", f"Expected a1, got {next_step.id}"

    # a1 completed → should return a2 (condition: previous_success)
    next_step = plan.get_next_executable({"a1"}, set())
    assert next_step.id == "a2", f"Expected a2, got {next_step.id}"

    # a1 failed → should return a3 (condition: previous_failed)
    next_step = plan.get_next_executable(set(), {"a1"})
    assert next_step.id == "a3", f"Expected a3, got {next_step.id}"
    print("  ✅ Dependency graph works correctly")

    # ═══════════════════════════════════════════════════════
    # 7. TEST: Reasoning Engine
    # ═══════════════════════════════════════════════════════
    print("\n--- Test: Reasoning Engine ---")
    reasoning = ReasoningEngine()

    actions = [
        Action("open_app", {"app": "chrome"}),
        Action("search_web", {"query": "python tutorials"}),
    ]
    plan = reasoning.build_plan(actions, "open chrome and search python")

    assert plan.total_steps >= 2, f"Expected >=2 steps, got {plan.total_steps}"
    assert plan.is_sequential, "Expected sequential plan"

    # Check that search depends on chrome open
    search_step = [s for s in plan.steps
                   if s.action_type == "search_web" and s.condition != "previous_failed"][0]
    assert search_step.depends_on, "Search should depend on app open"
    print(f"  ✅ Built {plan.total_steps}-step plan with dependencies")

    # Check that retry policies were assigned
    for step in plan.steps:
        assert step.retry_policy is not None, f"Missing retry policy for {step.action_type}"
    print("  ✅ Retry policies assigned to all steps")

    # ═══════════════════════════════════════════════════════
    # 8. TEST: Decision Layer
    # ═══════════════════════════════════════════════════════
    print("\n--- Test: Decision Layer ---")
    decision = DecisionLayer()

    # Test: low confidence filtering
    intent = Intent(
        intent_type=IntentType.ACTION,
        raw_input="do something",
        actions=[
            Action("open_app", {"app": "test"}, confidence=0.9),
            Action("search_web", {"query": "x"}, confidence=0.1),
        ],
    )
    evaluated = decision.evaluate(intent)
    assert len(evaluated.actions) == 1, "Low confidence action should be filtered"
    print("  ✅ Low confidence filtering works")

    # Test: conflict resolution
    intent2 = Intent(
        intent_type=IntentType.ACTION,
        raw_input="open and close chrome",
        actions=[
            Action("open_app", {"app": "chrome"}, confidence=0.9),
            Action("close_app", {"app": "chrome"}, confidence=0.9),
        ],
    )
    evaluated2 = decision.evaluate(intent2)
    assert len(evaluated2.actions) == 1, "Conflicting actions should be resolved"
    print("  ✅ Conflict resolution works")

    # ═══════════════════════════════════════════════════════
    # 9. TEST: Error Classification
    # ═══════════════════════════════════════════════════════
    print("\n--- Test: Error Classification ---")
    executor = Executor()

    assert executor._classify_error("open_app", "file not found") == ErrorClass.RECOVERABLE_ALT
    assert executor._classify_error("open_app", "permission denied") == ErrorClass.FATAL
    assert executor._classify_error("search_web", "connection timeout") == ErrorClass.TRANSIENT
    assert executor._classify_error("open_app", "something weird") == ErrorClass.RECOVERABLE
    print("  ✅ Error classification: 4/4 correct")

    # ═══════════════════════════════════════════════════════
    # 10. TEST: Feedback Scoring
    # ═══════════════════════════════════════════════════════
    print("\n--- Test: Feedback Scoring ---")
    feedback = FeedbackLoop()

    mock_action = Action("open_app", {"app": "chrome"})
    mock_result = ActionResult(
        action=mock_action,
        status=ActionStatus.SUCCESS,
        message="Opened chrome",
        duration_ms=400,
    )
    score = feedback.evaluate_action(mock_result)
    assert score.success_score == 1.0
    assert score.speed_score > 0
    assert 0 <= score.overall <= 1.0
    print(f"  ✅ Feedback score: {score.overall:.3f} "
          f"(success={score.success_score}, speed={score.speed_score:.2f})")

    # ═══════════════════════════════════════════════════════
    # 11. TEST: Schedule Parsing
    # ═══════════════════════════════════════════════════════
    print("\n--- Test: Schedule Parsing ---")
    tests = [
        ("remind me in 5 minutes to check email", True, 300),
        ("open chrome in 30 seconds", True, 30),
        ("open chrome", False, 0),
        ("play music after 1 hour", True, 3600),
    ]
    for text, expected_sched, expected_delay in tests:
        result = parse_schedule_from_input(text)
        assert result["has_schedule"] == expected_sched, \
            f"'{text}': expected has_schedule={expected_sched}"
        if expected_sched:
            assert result["delay_seconds"] == expected_delay, \
                f"'{text}': expected {expected_delay}s, got {result['delay_seconds']}s"
    print("  ✅ Schedule parsing: 4/4 correct")

    # ═══════════════════════════════════════════════════════
    # 12. TEST: Pattern Learning
    # ═══════════════════════════════════════════════════════
    print("\n--- Test: Pattern Learning ---")
    learner = PatternLearner()

    # Simulate learning
    test_action = Action("open_app", {"app": "chrome"})
    test_result = ActionResult(
        action=test_action,
        status=ActionStatus.SUCCESS,
        message="ok",
        duration_ms=300,
    )
    for _ in range(5):
        learner.learn_from_result("open chrome", test_action, test_result)

    confidence = learner.get_confidence("open chrome", "open_app")
    assert confidence > 0, "Pattern should have positive confidence"
    print(f"  ✅ Pattern confidence after 5 successes: {confidence:.3f}")

    predicted = learner.predict_action("open chrome")
    assert predicted is not None, "Should predict from strong pattern"
    assert predicted.action_type == "open_app"
    print(f"  ✅ Pattern prediction works: {predicted.action_type}")

    # Vocabulary learning
    learner.learn_vocabulary("my browser", "chrome")
    resolved = learner.resolve_vocabulary("open my browser")
    assert "chrome" in resolved, "Vocabulary should resolve"
    print(f"  ✅ Vocabulary: 'open my browser' → '{resolved}'")

    # ═══════════════════════════════════════════════════════
    # 13. TEST: RetryPolicy
    # ═══════════════════════════════════════════════════════
    print("\n--- Test: RetryPolicy ---")
    policy = RetryPolicy(max_attempts=3, delay_seconds=0.5, backoff_multiplier=2.0)
    assert policy.get_delay(0) == 0.5
    assert policy.get_delay(1) == 1.0
    assert policy.get_delay(2) == 2.0
    print("  ✅ Exponential backoff: 0.5s → 1.0s → 2.0s")

    # ═══════════════════════════════════════════════════════
    # 14. TEST: FeedbackScore
    # ═══════════════════════════════════════════════════════
    print("\n--- Test: FeedbackScore ---")
    fs = FeedbackScore(success_score=1.0, speed_score=0.8, reliability_score=0.9)
    fs.compute_overall()
    assert 0.5 < fs.overall < 1.0, f"Expected 0.5-1.0, got {fs.overall}"
    print(f"  ✅ Overall score: {fs.overall:.3f}")

    print()
    print("═" * 50)
    print("  ALL 14 TESTS PASSED")
    print("  SENKU 3.1 INTELLIGENCE UPGRADE VERIFIED")
    print("═" * 50)

except Exception as e:
    import traceback
    print(f"\n❌ FAILED: {e}")
    traceback.print_exc()
