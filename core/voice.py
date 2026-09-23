class VoiceIO:
    """Optional speech input/output wrapper with graceful missing-package errors."""

    def __init__(self):
        self._tts = None

    def speak(self, text):
        try:
            import pyttsx3
        except Exception:
            return False, "Voice output needs pyttsx3: py -m pip install pyttsx3"

        try:
            if self._tts is None:
                self._tts = pyttsx3.init()
            self._tts.say(str(text))
            self._tts.runAndWait()
            return True, "Voice output complete."
        except Exception as error:
            return False, f"Voice output failed: {error}"

    def listen_once(self, timeout=5, phrase_time_limit=10):
        try:
            import speech_recognition as sr
        except Exception:
            return False, "Voice input needs SpeechRecognition: py -m pip install SpeechRecognition pyaudio"

        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )
            return True, recognizer.recognize_google(audio)
        except Exception as error:
            return False, f"Voice input failed: {error}"
