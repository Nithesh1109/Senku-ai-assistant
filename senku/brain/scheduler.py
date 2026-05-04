"""
Senku Task Scheduler
Handles deferred actions, reminders, and background tasks.

Supports:
- "remind me in 10 minutes to call John"
- "set a timer for 30 seconds"
- Background scheduled task execution
- Persistent task storage (survives restarts)
"""

import re
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable
import uuid

from senku.config import (
    SCHEDULE_FILE, MAX_SCHEDULED_TASKS, SCHEDULER_POLL_INTERVAL, DEBUG_MODE,
)
from senku.memory.store import MemoryStore
from senku.core.types import Action
from senku.core.events import event_bus, Events


class ScheduledTask:
    """Represents a task scheduled for future execution."""

    def __init__(self, action: Action, trigger_at: str, label: str = "",
                 task_id: str = ""):
        self.task_id = task_id or f"task_{uuid.uuid4().hex[:8]}"
        self.action = action
        self.trigger_at = trigger_at  # ISO format
        self.label = label or f"{action.action_type}"
        self.status = "pending"  # pending, triggered, completed, failed
        self.created_at = datetime.now().isoformat()

    def is_due(self) -> bool:
        """Check if this task is ready to trigger."""
        if self.status != "pending":
            return False
        try:
            trigger_time = datetime.fromisoformat(self.trigger_at)
            return datetime.now() >= trigger_time
        except (ValueError, TypeError):
            return False

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "action": self.action.to_dict(),
            "trigger_at": self.trigger_at,
            "label": self.label,
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduledTask":
        action = Action.from_dict(dict(data.get("action", {})))
        task = cls(
            action=action,
            trigger_at=data.get("trigger_at", ""),
            label=data.get("label", ""),
            task_id=data.get("task_id", ""),
        )
        task.status = data.get("status", "pending")
        task.created_at = data.get("created_at", "")
        return task


class TaskScheduler:
    """
    Background task scheduler with persistent storage.
    
    Architecture:
    - Tasks are stored in JSON and survive restarts
    - A background thread polls for due tasks
    - When a task is due, it's executed via a callback
    - Results are tracked and tasks are marked complete
    """

    def __init__(self, on_task_execute: Callable[[Action], None] = None):
        self._store = MemoryStore(SCHEDULE_FILE, default_data=[])
        self._on_execute = on_task_execute
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tasks: list = []  # In-memory task cache

    def start(self):
        """Start the background scheduler thread."""
        if self._running:
            return

        self._load_tasks()
        self._running = True
        self._thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
            name="senku-scheduler",
        )
        self._thread.start()

        if DEBUG_MODE:
            pending = sum(1 for t in self._tasks if t.status == "pending")
            print(f"[Scheduler] Started. {pending} pending tasks.")

    def stop(self):
        """Stop the scheduler."""
        self._running = False

    def schedule(self, action: Action, delay_seconds: float = 0,
                 trigger_at: str = "", label: str = "") -> ScheduledTask:
        """
        Schedule an action for future execution.
        
        Args:
            action: The action to execute
            delay_seconds: Seconds from now to trigger
            trigger_at: ISO datetime to trigger (overrides delay)
            label: Human-readable label
        """
        if trigger_at:
            trigger_time = trigger_at
        elif delay_seconds > 0:
            trigger_time = (
                datetime.now() + timedelta(seconds=delay_seconds)
            ).isoformat()
        else:
            trigger_time = datetime.now().isoformat()

        task = ScheduledTask(
            action=action,
            trigger_at=trigger_time,
            label=label,
        )

        self._tasks.append(task)
        self._save_tasks()

        event_bus.emit(Events.TASK_SCHEDULED, task=task)

        if DEBUG_MODE:
            print(f"[Scheduler] Task scheduled: {task.label} at {trigger_time}")

        return task

    def get_pending(self) -> list:
        """Get all pending tasks."""
        self._load_tasks()
        return [t for t in self._tasks if t.status == "pending"]

    def cancel(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        for task in self._tasks:
            if task.task_id == task_id and task.status == "pending":
                task.status = "cancelled"
                self._save_tasks()
                return True
        return False

    def _poll_loop(self):
        """Background loop that checks for due tasks."""
        while self._running:
            try:
                self._check_due_tasks()
            except Exception as e:
                if DEBUG_MODE:
                    print(f"[Scheduler] Poll error: {e}")
            time.sleep(SCHEDULER_POLL_INTERVAL)

    def _check_due_tasks(self):
        """Check and execute due tasks."""
        for task in self._tasks:
            if task.is_due():
                self._execute_task(task)

    def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        if DEBUG_MODE:
            print(f"[Scheduler] Triggering: {task.label}")

        task.status = "triggered"
        event_bus.emit(Events.TASK_TRIGGERED, task=task)

        try:
            if self._on_execute:
                self._on_execute(task.action)
                task.status = "completed"
            else:
                # No executor — just notify
                print(f"\n⏰ Scheduled task: {task.label}")
                task.status = "completed"
        except Exception as e:
            task.status = "failed"
            if DEBUG_MODE:
                print(f"[Scheduler] Task failed: {e}")

        self._save_tasks()

    def _load_tasks(self):
        """Load tasks from persistent storage."""
        data = self._store.all()
        if isinstance(data, list):
            self._tasks = [ScheduledTask.from_dict(d) for d in data]
        else:
            self._tasks = []

    def _save_tasks(self):
        """Save tasks to persistent storage."""
        # Only keep recent tasks (trim old completed/failed)
        active = [t for t in self._tasks if t.status == "pending"]
        recent = [
            t for t in self._tasks
            if t.status != "pending"
        ][-20:]  # Keep last 20 completed

        self._tasks = active + recent

        self._store._cache = [t.to_dict() for t in self._tasks]
        self._store.save()


# ─── Duration Parser ─────────────────────────────────────────────

def parse_schedule_from_input(text: str) -> dict:
    """
    Parse scheduling information from natural language.
    
    Returns:
        {
            "has_schedule": bool,
            "delay_seconds": int,
            "label": str,
            "remaining_text": str,  # Text after removing schedule info
        }
    """
    result = {
        "has_schedule": False,
        "delay_seconds": 0,
        "label": "",
        "remaining_text": text,
    }

    # Pattern: "in X minutes/seconds/hours"
    match = re.search(
        r"(?:in|after)\s+(\d+)\s*(s|sec|seconds?|m|min|minutes?|h|hr|hours?)",
        text, re.IGNORECASE
    )
    if match:
        value = int(match.group(1))
        unit = match.group(2)[0].lower()
        multiplier = {"s": 1, "m": 60, "h": 3600}
        result["delay_seconds"] = value * multiplier.get(unit, 60)
        result["has_schedule"] = True
        result["remaining_text"] = text[:match.start()].strip()
        result["label"] = result["remaining_text"] or f"Scheduled task"

    # Pattern: "remind me to X"
    remind_match = re.match(
        r"remind\s+(?:me\s+)?(?:to\s+)?(.+?)(?:\s+in\s+.+)?$",
        text, re.IGNORECASE,
    )
    if remind_match and result["has_schedule"]:
        result["label"] = remind_match.group(1).strip()

    return result
