"""
Senku Planner v3.1
The central intelligence orchestrator.

Upgraded pipeline:
Input → Preprocess → Pattern Predict → Vocabulary Resolve → LLM Parse →
Decision Evaluate → Reasoning Plan → Schedule Detect → Output Intent

This is the main interface between user input and the action system.
All intelligence layers are wired here.
"""

from typing import List, Optional

from senku.core.types import Action, Intent, IntentType, ExecutionPlan
from senku.core.exceptions import LLMError, LLMParseError
from senku.brain.llm_client import LLMClient
from senku.brain.parser import ResponseParser
from senku.brain.preprocessor import Preprocessor
from senku.brain.prompts import build_action_prompt, build_chat_prompt
from senku.brain.reasoning import ReasoningEngine
from senku.brain.decision import DecisionLayer
from senku.brain.scheduler import parse_schedule_from_input
from senku.memory.conversation import ConversationMemory
from senku.memory.context import ContextManager
from senku.memory.pattern_learner import PatternLearner
from senku.config import DEBUG_MODE


class Planner:
    """
    The central intelligence engine — v3.1.
    
    Responsibilities (upgraded):
    1. Preprocess user input (normalization, shortcuts)
    2. Check learned patterns (bypass LLM for known commands)
    3. Resolve user vocabulary ("my editor" → "vscode")
    4. Classify intent (action vs chat vs schedule)
    5. Generate action plans via LLM
    6. Evaluate decisions (confidence, ambiguity, conflicts)
    7. Build execution plans (dependencies, retries, fallbacks)
    8. Detect scheduling intent
    9. Generate chat responses with full context
    """

    def __init__(self, llm: LLMClient = None, context: ContextManager = None,
                 conversation: ConversationMemory = None,
                 pattern_learner: PatternLearner = None):
        self.llm = llm or LLMClient()
        self.context = context or ContextManager()
        self.conversation = conversation or ConversationMemory()
        self.pattern_learner = pattern_learner or PatternLearner()
        self.preprocessor = Preprocessor()
        self.parser = ResponseParser()
        self.reasoning = ReasoningEngine()
        self.decision = DecisionLayer(pattern_learner=self.pattern_learner)

    def process_input(self, user_input: str) -> Intent:
        """
        Full intelligence pipeline — 9 steps.
        
        Args:
            user_input: Raw user text
            
        Returns:
            Intent object with classified type, actions, plan, and reasoning
        """
        # ─── Step 1: Preprocess ──────────────────────────────
        processed = self.preprocessor.process(user_input)

        if processed["is_exit"]:
            return Intent(
                intent_type=IntentType.ACTION,
                raw_input=user_input,
                actions=[],
                reasoning="Exit command detected",
            )

        # ─── Step 2: Resolve user vocabulary ─────────────────
        cleaned = self.pattern_learner.resolve_vocabulary(processed["cleaned"])

        # ─── Step 3: Check for scheduling intent ─────────────
        schedule_info = parse_schedule_from_input(user_input)

        # ─── Step 4: Check learned patterns (bypass LLM) ─────
        if not schedule_info["has_schedule"]:
            pattern_action = self.pattern_learner.predict_action(cleaned)
            if pattern_action:
                if DEBUG_MODE:
                    print(f"[Planner] Pattern match: {pattern_action.action_type} "
                          f"(confidence: {pattern_action.confidence:.2f})")
                intent = Intent(
                    intent_type=IntentType.ACTION,
                    raw_input=user_input,
                    actions=[pattern_action],
                    confidence=pattern_action.confidence,
                    reasoning=f"Pattern-based prediction "
                              f"(confidence: {pattern_action.confidence:.2f})",
                )
                # Still run through decision layer
                return self.decision.evaluate(intent, self.context.get_context_summary())

        # ─── Step 5: Check for shortcut actions ──────────────
        if processed["shortcut_action"]:
            action = processed["shortcut_action"]
            if DEBUG_MODE:
                print(f"[Planner] Shortcut detected: {action.action_type}")

            actions = [action]

            # If scheduled, wrap the action
            if schedule_info["has_schedule"]:
                return Intent(
                    intent_type=IntentType.SCHEDULE,
                    raw_input=user_input,
                    actions=actions,
                    confidence=0.95,
                    reasoning=f"Shortcut action, scheduled in "
                              f"{schedule_info['delay_seconds']}s",
                )

            intent = Intent(
                intent_type=IntentType.ACTION,
                raw_input=user_input,
                actions=actions,
                confidence=0.95,
                reasoning="Shortcut pattern match",
            )
            return self.decision.evaluate(intent, self.context.get_context_summary())

        # ─── Step 6: LLM-based action parsing ───────────────
        try:
            context_str = self.context.get_context_summary()
            prompt = build_action_prompt(cleaned, context_str)

            raw_response = self.llm.generate(prompt)

            if DEBUG_MODE:
                print(f"[Planner] LLM raw response: {raw_response[:200]}")

            actions = self.parser.parse_actions(raw_response)

            if DEBUG_MODE:
                print(f"[Planner] DEBUG ACTIONS: {[(a.action_type, a.params) for a in actions]}")

            if actions:
                # Validate: all items must be proper Action objects
                valid_actions = [
                    a for a in actions
                    if isinstance(a, Action) and a.action_type and a.action_type != "unknown"
                ]

                if not valid_actions:
                    if DEBUG_MODE:
                        print(f"[Planner] All parsed actions were invalid — chat mode")
                    # Fall through to chat
                else:
                    # ─── Step 7: Decision evaluation ─────────────
                    intent = Intent(
                        intent_type=IntentType.COMPOUND if len(valid_actions) > 1 else IntentType.ACTION,
                        raw_input=user_input,
                        actions=valid_actions,
                        confidence=0.85,
                        reasoning="LLM-parsed actions",
                    )

                    # If scheduled
                    if schedule_info["has_schedule"]:
                        intent.intent_type = IntentType.SCHEDULE
                        intent.reasoning += f", scheduled in {schedule_info['delay_seconds']}s"
                        return intent

                    evaluated = self.decision.evaluate(intent, context_str)

                    # ─── Step 8: Build execution plan ────────────
                    if evaluated.has_actions and not evaluated.needs_clarification:
                        try:
                            plan = self.reasoning.build_plan(
                                evaluated.actions, user_input, context_str
                            )
                            evaluated.plan = plan
                            evaluated.reasoning += f" → {plan.total_steps}-step plan"
                        except Exception as plan_err:
                            if DEBUG_MODE:
                                print(f"[Planner] Plan build failed: {plan_err}")
                            # Continue without plan — executor will use flat list

                    return evaluated

        except LLMError as e:
            if DEBUG_MODE:
                print(f"[Planner] LLM error: {e}")
            # Fall through to chat mode — don't crash
        except Exception as e:
            # Catch ALL exceptions — planner must never crash
            if DEBUG_MODE:
                import traceback
                print(f"[Planner] Unexpected error in pipeline: {e}")
                traceback.print_exc()
            # Fall through to chat mode

        # ─── Step 9: Chat mode (no actions found) ────────────
        return Intent(
            intent_type=IntentType.CHAT,
            raw_input=user_input,
            actions=[],
            reasoning="No actions detected — chat mode",
        )

    def generate_chat_response(self, user_input: str) -> str:
        """
        Generate a conversational response.
        Uses conversation history and context for coherent multi-turn chat.
        """
        try:
            context_str = self.context.get_context_summary()
            history_str = self.conversation.get_context_string(n=5)

            prompt = build_chat_prompt(user_input, context_str, history_str)
            response = self.llm.generate(prompt, temperature=0.7)

            return response.strip()

        except LLMError as e:
            return f"I'm having trouble connecting to my brain. Error: {e.message}"
        except Exception as e:
            return f"Something went wrong: {str(e)}"

    def check_health(self) -> dict:
        """Check the health of the intelligence system."""
        health = self.llm.check_connection()
        health["patterns_loaded"] = len(
            self.pattern_learner.get_top_patterns(limit=1)
        ) > 0
        return health
