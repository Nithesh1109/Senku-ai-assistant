"""
Senku 3.1 — Main Orchestrator
The central entry point that wires together all subsystems.

v3.1 — Intelligence upgrade:
- Pattern learning from every action outcome
- Feedback scoring after every execution
- Plan-based execution with dependency awareness
- Scheduling with background thread
- Clarification flow for ambiguous commands
- Self-healing retry logic
"""

import sys
import os

# Ensure the project root is in Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from senku.core.types import IntentType, ActionStatus, Intent
from senku.core.events import event_bus, Events
from senku.core.exceptions import SenkuError, LLMConnectionError
from senku.brain.planner import Planner
from senku.brain.llm_client import LLMClient
from senku.brain.feedback import FeedbackLoop
from senku.brain.scheduler import TaskScheduler
from senku.actions.executor import Executor
from senku.memory.conversation import ConversationMemory
from senku.memory.action_log import ActionLog
from senku.memory.context import ContextManager
from senku.memory.pattern_learner import PatternLearner
from senku.actions.handlers.app_handler import get_resolver
from senku.config import VOICE_ENABLED, DEBUG_MODE


class Senku:
    """
    The Senku AI Agent — v3.1.
    
    Wires together:
    - Brain (Planner + LLM + Parser + Reasoning + Decision)
    - Hands (Executor + Handlers + Launcher + Retry)
    - Memory (Conversation + Action Log + Context + Patterns)
    - Intelligence (Feedback Loop + Scheduler + Pattern Learning)
    - Voice (STT + TTS)
    """

    def __init__(self):
        # ─── Core Systems ────────────────────────────────────
        self.llm = LLMClient()
        self.context = ContextManager()
        self.conversation = ConversationMemory()
        self.action_log = ActionLog()
        self.pattern_learner = PatternLearner()
        self.feedback = FeedbackLoop(pattern_learner=self.pattern_learner)

        self.planner = Planner(
            llm=self.llm,
            context=self.context,
            conversation=self.conversation,
            pattern_learner=self.pattern_learner,
        )
        self.executor = Executor()
        self.resolver = get_resolver()

        # ─── Scheduler ───────────────────────────────────────
        self.scheduler = TaskScheduler(
            on_task_execute=self._execute_scheduled_task,
        )

        # ─── Voice (optional) ────────────────────────────────
        self.voice_enabled = VOICE_ENABLED
        self.stt = None
        self.tts = None

        # ─── Event Wiring ────────────────────────────────────
        self._wire_events()

    def _wire_events(self):
        """Connect event handlers for learning."""
        event_bus.on(Events.ACTION_COMPLETED, self._on_action_completed)
        event_bus.on(Events.ACTION_FAILED, self._on_action_failed)

    def _on_action_completed(self, action=None, result=None):
        """Learning hook: record successful actions + learn patterns."""
        if action and result:
            # Log the raw result
            self.action_log.record(result)
            # Update session context
            self.context.update_after_action(action, result)
            # Learn pattern from this success
            self.pattern_learner.learn_from_result(
                self.context.last_query or action.action_type,
                action, result,
            )
            # Compute and record feedback
            score = self.feedback.evaluate_action(result)
            self.feedback.record_feedback(action.action_type, score)

    def _on_action_failed(self, action=None, result=None):
        """Learning hook: record failed actions for pattern analysis."""
        if action and result:
            self.action_log.record(result)
            self.pattern_learner.learn_from_result(
                self.context.last_query or action.action_type,
                action, result,
            )
            score = self.feedback.evaluate_action(result)
            self.feedback.record_feedback(action.action_type, score)

    def _execute_scheduled_task(self, action):
        """Callback for the scheduler to execute a deferred action."""
        result = self.executor.execute_one(action)
        icon = "✅" if result.success else "❌"
        print(f"\n⏰ Scheduled: {icon} {result.message}")

    def process(self, user_input: str) -> str:
        """
        Process a single user input and return a response string.
        This is the main API for the Senku agent.
        NEVER raises — always returns a string.
        """
        if not user_input or not user_input.strip():
            return ""

        try:
            # Record user input
            self.conversation.add_user_input(user_input)
            self.context.update_last_input(user_input)
        except Exception:
            pass  # Don't crash on memory failures

        try:
            # Get intent from planner (full intelligence pipeline)
            intent = self.planner.process_input(user_input)
        except Exception as e:
            if DEBUG_MODE:
                import traceback
                print(f"[Senku] Planner crashed: {e}")
                traceback.print_exc()
            # Fallback: treat as chat
            intent = Intent(
                intent_type=IntentType.CHAT,
                raw_input=user_input,
                actions=[],
                reasoning="Planner error — fallback to chat",
            )

        try:
            # ─── Clarification Flow ──────────────────────────────
            if intent.needs_clarification:
                response = f"I need some clarification: {intent.clarification_needed}"
                self.conversation.add_assistant_response(response)
                return response

            # ─── Scheduled Actions ───────────────────────────────
            if intent.is_scheduled and intent.has_actions:
                from senku.brain.scheduler import parse_schedule_from_input
                schedule_info = parse_schedule_from_input(user_input)
                delay = schedule_info.get("delay_seconds", 0)
                label = schedule_info.get("label", "Scheduled task")

                for action in intent.actions:
                    self.scheduler.schedule(
                        action, delay_seconds=delay, label=label,
                    )

                if delay >= 60:
                    time_str = f"{delay // 60} minute(s)"
                else:
                    time_str = f"{delay} second(s)"

                response = f"Scheduled: {label} (in {time_str})"
                self.conversation.add_assistant_response(response)
                return response

            # ─── Execute Actions ─────────────────────────────────
            if intent.has_actions:
                try:
                    # Use plan-based execution if a plan was built
                    if intent.plan:
                        results = self.executor.execute_plan(intent.plan)

                        # Compute plan-level feedback
                        try:
                            plan_score = self.feedback.evaluate_plan(intent.plan, results)
                            if DEBUG_MODE and plan_score.suggestions:
                                print(f"[Feedback] Plan score: {plan_score.overall:.2f}")
                                for s in plan_score.suggestions:
                                    print(f"  > {s}")
                        except Exception:
                            pass  # Feedback failure is non-critical
                    else:
                        results = self.executor.execute_all(intent.actions)

                    # Format response
                    response_parts = []
                    for result in results:
                        try:
                            # Skip fallback actions that weren't needed
                            if (result.action.fallback_for
                                    and result.status == ActionStatus.SKIPPED):
                                continue

                            icon = "[OK]" if result.success else "[FAIL]"
                            msg = result.message or result.action.action_type

                            # Show retry info
                            if result.attempt > 1:
                                msg += f" (attempt {result.attempt})"

                            response_parts.append(f"{icon} {msg}")

                            # Auto-learn alias for fuzzy matches
                            if (result.success
                                    and result.action.action_type == "open_app"
                                    and result.metadata.get("source", "").startswith("fuzzy")):
                                raw_app = result.action.get_param("app", "")
                                resolved = result.metadata.get("resolved_to", "")
                                if raw_app and resolved and raw_app != resolved:
                                    response_parts.append(
                                        f"   Learned: '{raw_app}' -> '{resolved}'"
                                    )
                                    try:
                                        self.resolver.learn_alias(raw_app, resolved)
                                        self.pattern_learner.learn_vocabulary(raw_app, resolved)
                                    except Exception:
                                        pass
                        except Exception as fmt_err:
                            if DEBUG_MODE:
                                print(f"[Senku] Error formatting result: {fmt_err}")
                            response_parts.append("[FAIL] Action completed with unknown result")

                    response = "\n".join(response_parts) if response_parts else "Actions processed."

                except Exception as exec_err:
                    if DEBUG_MODE:
                        import traceback
                        print(f"[Senku] Executor crashed: {exec_err}")
                        traceback.print_exc()
                    response = f"Error executing action: {str(exec_err)}"

            else:
                # ─── Chat Mode ───────────────────────────────────
                response = self.planner.generate_chat_response(user_input)

        except Exception as e:
            if DEBUG_MODE:
                import traceback
                print(f"[Senku] Process error: {e}")
                traceback.print_exc()
            response = f"Something went wrong: {str(e)}"

        # Record response (non-critical)
        try:
            self.conversation.add_assistant_response(
                response,
                actions=intent.actions if intent.has_actions else None,
            )
        except Exception:
            pass

        return response

    def health_check(self) -> dict:
        """Check the health of all subsystems."""
        llm_status = self.planner.check_health()
        pending_tasks = len(self.scheduler.get_pending())

        # Get top action trends
        top_actions = self.pattern_learner.get_top_patterns(5)

        return {
            "llm": llm_status,
            "actions_registered": len(Executor.list_available_actions()),
            "conversation_turns": self.conversation.turn_count,
            "patterns_learned": len(self.pattern_learner.get_top_patterns(100)),
            "scheduled_tasks": pending_tasks,
            "debug_mode": DEBUG_MODE,
            "voice_enabled": self.voice_enabled,
        }

    def run_interactive(self):
        """Run the interactive CLI loop."""
        self._print_banner()

        # Start scheduler
        self.scheduler.start()

        # Health check
        health = self.health_check()
        if not health["llm"]["ollama_running"]:
            print(f"⚠️  {health['llm'].get('error', 'Ollama not running')}")
            print("   Senku will work in limited mode (shortcuts + patterns)")
            print()

        if health["patterns_learned"] > 0:
            print(f"   🧠 {health['patterns_learned']} learned patterns loaded")

        if health["scheduled_tasks"] > 0:
            print(f"   ⏰ {health['scheduled_tasks']} pending scheduled tasks")

        while True:
            try:
                user_input = input("\n🧪 >> ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ("exit", "/bye", "quit", "/quit"):
                    print("\n👋 Senku shutting down. See you!")
                    self.scheduler.stop()
                    break

                if user_input.lower() == "/health":
                    self._show_health()
                    continue

                if user_input.lower() == "/actions":
                    self._show_actions()
                    continue

                if user_input.lower() == "/history":
                    self._show_history()
                    continue

                if user_input.lower() == "/patterns":
                    self._show_patterns()
                    continue

                if user_input.lower() == "/schedule":
                    self._show_schedule()
                    continue

                if user_input.lower() == "/feedback":
                    self._show_feedback()
                    continue

                if user_input.lower() == "/help":
                    self._show_help()
                    continue

                # Process input
                response = self.process(user_input)
                if response:
                    print(f"\n{response}")

            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Bye!")
                self.scheduler.stop()
                break
            except EOFError:
                self.scheduler.stop()
                break
            except SenkuError as e:
                print(f"\n⚠️  {e.message}")
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                if DEBUG_MODE:
                    import traceback
                    traceback.print_exc()

    def _print_banner(self):
        """Print the startup banner."""
        print()
        print("╔══════════════════════════════════════════════╗")
        print("║     🧪 SENKU 3.1 — Intelligent AI Agent      ║")
        print("║  Reasoning · Learning · Self-Healing · Goals  ║")
        print("╠══════════════════════════════════════════════╣")
        print("║  /help  /health  /patterns  /schedule  /bye  ║")
        print("╚══════════════════════════════════════════════╝")
        print()

    def _show_health(self):
        """Display system health."""
        health = self.health_check()
        print("\n📊 System Health:")
        llm = health["llm"]
        print(f"   Ollama: {'✅ Running' if llm['ollama_running'] else '❌ Not running'}")
        print(f"   Model: {llm['model_name']} "
              f"{'✅' if llm['model_available'] else '❌'}")
        print(f"   Actions: {health['actions_registered']} registered")
        print(f"   History: {health['conversation_turns']} turns")
        print(f"   Patterns: {health['patterns_learned']} learned")
        print(f"   Scheduled: {health['scheduled_tasks']} pending")
        if llm.get("error"):
            print(f"   ⚠️  {llm['error']}")

    def _show_actions(self):
        """Display available actions."""
        actions = Executor.list_available_actions()
        print("\n📋 Available Actions:")
        for a in actions:
            print(f"   • {a['type']}: {a['description']}")

    def _show_history(self):
        """Display recent conversation history."""
        recent = self.conversation.get_recent(10)
        print("\n💬 Recent History:")
        for turn in recent:
            role = "You" if turn.get("role") == "user" else "Senku"
            content = turn.get("content", "")[:100]
            print(f"   {role}: {content}")

    def _show_patterns(self):
        """Display learned patterns."""
        patterns = self.pattern_learner.get_top_patterns(15)
        if not patterns:
            print("\n🧠 No patterns learned yet. Keep using Senku!")
            return

        print("\n🧠 Learned Patterns (top 15):")
        for p in patterns:
            total = p["success_count"] + p["fail_count"]
            rate = p["success_count"] / total * 100 if total > 0 else 0
            print(f"   '{p['input']}' → {p['action_type']} "
                  f"({total}x, {rate:.0f}% success)")

    def _show_schedule(self):
        """Display scheduled tasks."""
        pending = self.scheduler.get_pending()
        if not pending:
            print("\n⏰ No pending scheduled tasks.")
            return

        print(f"\n⏰ Scheduled Tasks ({len(pending)}):")
        for task in pending:
            print(f"   • {task.label} — triggers at {task.trigger_at}")

    def _show_feedback(self):
        """Display performance feedback for common actions."""
        print("\n📈 Action Performance:")
        for action_type in ["open_app", "search_web", "play_youtube", "screenshot"]:
            trend = self.feedback.get_trend(action_type)
            if trend["count"] > 0:
                emoji = {"improving": "📈", "declining": "📉",
                         "stable": "➡️"}.get(trend["trend"], "❓")
                print(f"   {emoji} {action_type}: "
                      f"score {trend['avg_overall']:.2f} "
                      f"({trend['trend']}, {trend['count']} samples)")

    def _show_help(self):
        """Display help information."""
        print("\n📖 Senku Help:")
        print("   Just type naturally! Examples:")
        print("   • 'open chrome'")
        print("   • 'play lofi music'")
        print("   • 'search for python tutorials'")
        print("   • 'take a screenshot'")
        print("   • 'what's the weather in Tokyo?'")
        print("   • 'create a file called notes.txt'")
        print("   • 'remind me in 5 minutes to check email'")
        print("   • 'close notepad'")
        print()
        print("   System commands:")
        print("   • /help     — Show this help")
        print("   • /health   — System status")
        print("   • /actions  — Available actions")
        print("   • /history  — Recent conversation")
        print("   • /patterns — Learned behaviors")
        print("   • /schedule — Pending tasks")
        print("   • /feedback — Performance metrics")
        print("   • /bye      — Exit Senku")


# ─── Entry Point ─────────────────────────────────────────────────

def main():
    """Start the Senku agent."""
    senku = Senku()
    senku.run_interactive()


if __name__ == "__main__":
    main()
