"""
Senku Action Registry
Plugin-based action handler registration system.
Enables clean extension of action types without modifying the executor.
"""

from typing import Callable, Dict, Optional
from senku.core.types import Action, ActionResult, ActionStatus
from senku.core.exceptions import ActionNotFoundError


# Type for action handler functions
ActionHandler = Callable[[Action], ActionResult]


class ActionRegistry:
    """
    Central registry for action handlers.
    
    Handlers register themselves for specific action types.
    The executor queries the registry to find the right handler.
    
    Usage:
        registry = ActionRegistry()
        
        @registry.register("open_app")
        def handle_open_app(action: Action) -> ActionResult:
            ...
    """

    def __init__(self):
        self._handlers: Dict[str, ActionHandler] = {}
        self._descriptions: Dict[str, str] = {}

    def register(self, action_type: str, description: str = ""):
        """
        Decorator to register an action handler.
        
        Usage:
            @registry.register("open_app", "Opens an application")
            def handle_open_app(action: Action) -> ActionResult:
                ...
        """
        def decorator(func: ActionHandler) -> ActionHandler:
            self._handlers[action_type] = func
            self._descriptions[action_type] = description or action_type
            return func
        return decorator

    def register_handler(self, action_type: str, handler: ActionHandler,
                         description: str = ""):
        """Register a handler function directly (non-decorator style)."""
        self._handlers[action_type] = handler
        self._descriptions[action_type] = description or action_type

    def get_handler(self, action_type: str) -> Optional[ActionHandler]:
        """Get the handler for an action type."""
        return self._handlers.get(action_type)

    def has_handler(self, action_type: str) -> bool:
        """Check if a handler exists for an action type."""
        return action_type in self._handlers

    def execute(self, action: Action) -> ActionResult:
        """
        Execute an action using its registered handler.
        
        Raises:
            ActionNotFoundError if no handler registered.
        """
        handler = self.get_handler(action.action_type)
        if handler is None:
            raise ActionNotFoundError(action.action_type)
        return handler(action)

    def list_actions(self) -> list:
        """List all registered action types and descriptions."""
        return [
            {"type": t, "description": d}
            for t, d in sorted(self._descriptions.items())
        ]

    @property
    def action_count(self) -> int:
        return len(self._handlers)


# Global registry instance
registry = ActionRegistry()
