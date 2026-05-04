"""
Senku Text-to-Speech
Converts text responses to speech output.
"""

from senku.config import TTS_RATE, TTS_VOLUME
from senku.core.exceptions import TTSError


class TextToSpeech:
    """
    Text-to-speech engine using pyttsx3.
    """

    def __init__(self):
        self._engine = None
        self._initialized = False

    def _init_engine(self):
        """Lazy initialization of TTS engine."""
        if self._initialized:
            return

        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", TTS_RATE)
            self._engine.setProperty("volume", TTS_VOLUME)

            # Try to use a female voice if available
            voices = self._engine.getProperty("voices")
            if len(voices) > 1:
                self._engine.setProperty("voice", voices[1].id)

            self._initialized = True

        except ImportError:
            raise TTSError(
                "pyttsx3 library not installed. "
                "Run: pip install pyttsx3"
            )
        except Exception as e:
            raise TTSError(f"Failed to initialize TTS engine: {e}")

    def speak(self, text: str):
        """
        Speak the given text aloud.
        
        Args:
            text: Text to speak
            
        Raises:
            TTSError on failure
        """
        if not text:
            return

        self._init_engine()

        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as e:
            raise TTSError(f"Speech output failed: {e}")

    def speak_async(self, text: str):
        """Speak text in a background thread (non-blocking)."""
        import threading
        thread = threading.Thread(
            target=self.speak,
            args=(text,),
            daemon=True,
        )
        thread.start()

    @property
    def is_available(self) -> bool:
        """Check if TTS is available."""
        try:
            self._init_engine()
            return True
        except TTSError:
            return False
