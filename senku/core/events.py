"""
Senku Event System
Simple event bus for decoupled inter-module communication.
Enables modules to react to events without direct coupling.

v3.1 — Added events for reasoning, retry, feedback, scheduling.
"""

from typing import Callable
from collections import defaultdict


class EventBus:
    """
    Lightweight publish/subscribe event system.
    
    Usage:
        bus = EventBus()
        bus.on("action.completed", my_handler)
        bus.emit("action.completed", action=action, result=result)
    """

    def __init__(self):
        self._handlers: dict = defaultdict(list)

    def on(self, event: str, handler: Callable):
        """Subscribe to an event."""
        self._handlers[event].append(handler)

    def off(self, event: str, handler: Callable = None):
        """Unsubscribe from an event. If no handler specified, remove all."""
        if handler is None:
            self._handlers[event] = []
        else:
            self._handlers[event] = [
                h for h in self._handlers[event] if h != handler
            ]

    def emit(self, event: str, **kwargs):
        """Emit an event, notifying all subscribers."""
        for handler in self._handlers.get(event, []):
            try:
                handler(**kwargs)
            except Exception as e:
                # Event handlers should never crash the system
                print(f"[EventBus] Handler error for '{event}': {e}")

    def clear(self):
        """Remove all event subscriptions."""
        self._handlers.clear()


# ─── Event Names (Constants) ─────────────────────────────────────

class Events:
    """Standard event names used across the system."""
    
    # Brain events
    INPUT_RECEIVED = "input.received"
    INTENT_PARSED = "intent.parsed"
    CHAT_RESPONSE = "chat.response"
    
    # Action events
    ACTION_STARTED = "action.started"
    ACTION_COMPLETED = "action.completed"
    ACTION_FAILED = "action.failed"
    ACTION_RETRYING = "action.retrying"
    ACTION_RETRY_EXHAUSTED = "action.retry_exhausted"
    
    # Plan events
    PLAN_CREATED = "plan.created"
    PLAN_STEP_COMPLETED = "plan.step.completed"
    PLAN_STEP_FAILED = "plan.step.failed"
    PLAN_COMPLETED = "plan.completed"
    PLAN_FAILED = "plan.failed"
    
    # App events
    APP_LAUNCHED = "app.launched"
    APP_CLOSED = "app.closed"
    APP_RESOLVED = "app.resolved"
    
    # Memory events
    ALIAS_LEARNED = "alias.learned"
    MEMORY_UPDATED = "memory.updated"
    CONTEXT_UPDATED = "context.updated"
    PATTERN_LEARNED = "pattern.learned"
    
    # Feedback events
    FEEDBACK_COMPUTED = "feedback.computed"
    
    # Scheduling events
    TASK_SCHEDULED = "task.scheduled"
    TASK_TRIGGERED = "task.triggered"
    
    # Decision events
    CLARIFICATION_NEEDED = "clarification.needed"
    DECISION_MADE = "decision.made"
    
    # System events
    SESSION_STARTED = "session.started"
    SESSION_ENDED = "session.ended"
    ERROR_OCCURRED = "error.occurred"


# Global event bus instance
event_bus = EventBus()
