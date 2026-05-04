"""
Senku Speech-to-Text
Captures audio from microphone and converts to text.
"""

from senku.config import STT_TIMEOUT, STT_PHRASE_LIMIT
from senku.core.exceptions import STTError


class SpeechToText:
    """
    Microphone-based speech recognition.
    Uses Google Speech Recognition via the SpeechRecognition library.
    """

    def __init__(self):
        self._recognizer = None
        self._microphone = None
        self._initialized = False

    def _init_engine(self):
        """Lazy initialization of speech recognition engine."""
        if self._initialized:
            return

        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._microphone = sr.Microphone()
            self._initialized = True

            # Adjust for ambient noise
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)

        except ImportError:
            raise STTError(
                "SpeechRecognition library not installed. "
                "Run: pip install SpeechRecognition pyaudio"
            )
        except Exception as e:
            raise STTError(f"Failed to initialize microphone: {e}")

    def listen(self) -> str:
        """
        Listen for speech and return text.
        
        Returns:
            Recognized text string
            
        Raises:
            STTError on failure
        """
        self._init_engine()
        import speech_recognition as sr

        try:
            print("🎤 Listening...")
            with self._microphone as source:
                audio = self._recognizer.listen(
                    source,
                    timeout=STT_TIMEOUT,
                    phrase_time_limit=STT_PHRASE_LIMIT,
                )

            print("🧠 Recognizing...")
            text = self._recognizer.recognize_google(audio)
            return text.strip()

        except sr.WaitTimeoutError:
            raise STTError("No speech detected (timeout)")
        except sr.UnknownValueError:
            raise STTError("Could not understand audio")
        except sr.RequestError as e:
            raise STTError(f"Speech recognition service error: {e}")
        except Exception as e:
            raise STTError(str(e))

    @property
    def is_available(self) -> bool:
        """Check if speech recognition is available."""
        try:
            self._init_engine()
            return True
        except STTError:
            return False
