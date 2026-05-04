"""
Senku Custom Exceptions
Structured error hierarchy for clear error handling and recovery.
"""


class SenkuError(Exception):
    """Base exception for all Senku errors."""

    def __init__(self, message: str, recoverable: bool = True):
        super().__init__(message)
        self.message = message
        self.recoverable = recoverable


# ─── Brain / LLM Errors ──────────────────────────────────────────

class LLMError(SenkuError):
    """Base class for LLM-related errors."""
    pass


class LLMConnectionError(LLMError):
    """Failed to connect to the LLM service (Ollama)."""

    def __init__(self, url: str = "", detail: str = ""):
        msg = f"Cannot connect to Ollama at {url}"
        if detail:
            msg += f": {detail}"
        msg += ". Ensure Ollama is running (run: ollama serve)"
        super().__init__(msg, recoverable=True)


class LLMTimeoutError(LLMError):
    """LLM request timed out."""

    def __init__(self, timeout: int = 0):
        msg = f"LLM request timed out after {timeout}s"
        super().__init__(msg, recoverable=True)


class LLMParseError(LLMError):
    """Failed to parse LLM response into structured actions."""

    def __init__(self, raw_response: str = ""):
        preview = raw_response[:100] if raw_response else "(empty)"
        msg = f"Failed to parse LLM response: {preview}"
        super().__init__(msg, recoverable=True)
        self.raw_response = raw_response


class LLMModelError(LLMError):
    """Requested model is not available."""

    def __init__(self, model: str = ""):
        msg = f"Model '{model}' not found. Run: ollama pull {model}"
        super().__init__(msg, recoverable=False)


# ─── Action / Execution Errors ───────────────────────────────────

class ActionError(SenkuError):
    """Base class for action execution errors."""
    pass


class ActionNotFoundError(ActionError):
    """Unknown action type."""

    def __init__(self, action_type: str = ""):
        msg = f"Unknown action type: '{action_type}'"
        super().__init__(msg, recoverable=True)


class ActionValidationError(ActionError):
    """Action parameters failed validation."""

    def __init__(self, action_type: str = "", missing_params: list = None):
        params = ", ".join(missing_params or [])
        msg = f"Action '{action_type}' missing required parameters: {params}"
        super().__init__(msg, recoverable=True)


class ActionExecutionError(ActionError):
    """Error during action execution."""

    def __init__(self, action_type: str = "", detail: str = ""):
        msg = f"Failed to execute '{action_type}'"
        if detail:
            msg += f": {detail}"
        super().__init__(msg, recoverable=True)


# ─── Resolver Errors ─────────────────────────────────────────────

class ResolverError(SenkuError):
    """Base class for app resolution errors."""
    pass


class AppNotFoundError(ResolverError):
    """Could not find the requested application."""

    def __init__(self, app_name: str = ""):
        msg = f"Application '{app_name}' not found on this system"
        super().__init__(msg, recoverable=True)


class AppLaunchError(ResolverError):
    """Failed to launch an application."""

    def __init__(self, app_name: str = "", detail: str = ""):
        msg = f"Failed to launch '{app_name}'"
        if detail:
            msg += f": {detail}"
        super().__init__(msg, recoverable=True)


# ─── Memory Errors ───────────────────────────────────────────────

class MemoryError(SenkuError):
    """Base class for memory system errors."""
    pass


class MemoryCorruptionError(MemoryError):
    """Memory data file is corrupted or invalid."""

    def __init__(self, filepath: str = ""):
        msg = f"Memory file corrupted: {filepath}. Will reset."
        super().__init__(msg, recoverable=True)


# ─── Voice Errors ────────────────────────────────────────────────

class VoiceError(SenkuError):
    """Base class for voice I/O errors."""
    pass


class STTError(VoiceError):
    """Speech-to-text error."""

    def __init__(self, detail: str = ""):
        msg = f"Speech recognition failed"
        if detail:
            msg += f": {detail}"
        super().__init__(msg, recoverable=True)


class TTSError(VoiceError):
    """Text-to-speech error."""

    def __init__(self, detail: str = ""):
        msg = f"Text-to-speech failed"
        if detail:
            msg += f": {detail}"
        super().__init__(msg, recoverable=True)
