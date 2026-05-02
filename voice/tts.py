# Converts text to speech

try:
    import pyttsx3
    engine = pyttsx3.init()
except:
    engine = None

def speak(text: str):
    if engine:
        engine.say(text)
        engine.runAndWait()
