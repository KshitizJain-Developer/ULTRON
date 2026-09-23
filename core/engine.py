from threading import Lock

from .config import (
    API_KEY_ENV_NAME,
    SYSTEM_PROMPT,
    get_api_key,
    get_model_name,
    load_settings,
    update_settings,
)
from .gemini import GeminiClient, GeminiStatus
from .memory import Memory
from tools.desktop import DesktopTools


class UltronEngine:
    """
    ULTRON's AI engine.

    The engine owns API configuration, Gemini chat access, local memory, and
    permission-aware desktop tools. It has no GUI dependencies.
    """

    def __init__(self):
        self.settings = load_settings()
        self.api_key = get_api_key()
        self.model = get_model_name()
        self.memory = Memory(max_messages=30)
        self.tools = DesktopTools()
        self.pending_confirmation = None
        self._lock = Lock()
        self._gemini = None
        self._last_error = ""

        if self.api_key:
            self._connect()
        else:
            self._last_error = (
                f"{API_KEY_ENV_NAME} is missing. Gemini is offline until the "
                "ULTRON API key is configured."
            )

    def status(self) -> GeminiStatus:
        online = self._gemini is not None and not self._last_error
        if online:
            message = "ONLINE"
        else:
            message = self._last_error or "OFFLINE"
        return GeminiStatus(online=online, model=self.model, message=message)

    def current_model(self) -> str:
        return self.model

    def configure(self, model=None, voice_output=None, wake_word=None):
        changes = {}
        if model is not None and model.strip():
            changes["model"] = model.strip()
        if voice_output is not None:
            changes["voice_output"] = bool(voice_output)
        if wake_word is not None and wake_word.strip():
            changes["wake_word"] = wake_word.strip()

        self.settings = update_settings(**changes)
        self.api_key = get_api_key()
        self.model = get_model_name()
        self._gemini = None

        if self.api_key:
            self._connect()
        else:
            self._last_error = f"{API_KEY_ENV_NAME} is missing."

    def send(self, user_text: str) -> str:
        """Return a complete response for a single user message."""
        user_text = user_text.strip()
        if not user_text:
            return ""

        local = self._handle_local_command(user_text)
        if local is not None:
            return local

        with self._lock:
            self._ensure_online()
            history = self.memory.get_history()
            prompt = self._with_long_term_context(user_text)
            try:
                answer = self._gemini.send(prompt, history=history).strip()
            except Exception as error:
                self._handle_api_error(error)
                raise RuntimeError(self._last_error) from error

            if not answer:
                answer = "I received an empty response."

            self._remember(user_text, answer)
            return answer

    def stream(self, user_text: str, on_chunk) -> str:
        """
        Stream a response through on_chunk and return the final text.

        Local slash commands are executed immediately and emitted as one chunk.
        Gemini streaming remains synchronous so the GUI can run it in a thread.
        """
        user_text = user_text.strip()
        if not user_text:
            return ""

        local = self._handle_local_command(user_text)
        if local is not None:
            on_chunk(local)
            return local

        with self._lock:
            self._ensure_online()
            history = self.memory.get_history()
            prompt = self._with_long_term_context(user_text)
            chunks = []

            try:
                for chunk in self._gemini.stream(prompt, history=history):
                    chunks.append(chunk)
                    on_chunk(chunk)
            except Exception as error:
                self._handle_api_error(error)
                raise RuntimeError(self._last_error) from error

            answer = "".join(chunks).strip()
            if not answer:
                answer = "I received an empty response."
                on_chunk(answer)

            self._remember(user_text, answer)
            return answer

    def clear_memory(self):
        """Clear ULTRON's local conversation memory and reset the chat."""
        with self._lock:
            self.memory.clear()
            if self._gemini is not None:
                self._gemini.reset([])
            self._last_error = ""

    def _connect(self):
        try:
            self._gemini = GeminiClient(
                api_key=self.api_key,
                model=self.model,
                system_prompt=SYSTEM_PROMPT,
            )
            self._gemini.reset(self.memory.get_history())
            self._last_error = ""
        except Exception as error:
            self._gemini = None
            self._last_error = self._friendly_error(error)

    def _ensure_online(self):
        if self._gemini is None and self.api_key:
            self._connect()

        if self._gemini is None:
            raise RuntimeError(self._last_error or "Gemini is offline.")

    def _remember(self, user_text: str, answer: str):
        self.memory.add_user(user_text)
        self.memory.add_assistant(answer)

    def _with_long_term_context(self, user_text):
        long_term = self.memory.long_term_prompt()
        if not long_term:
            return user_text
        return f"{long_term}\n\nCurrent user message:\n{user_text}"

    def _handle_local_command(self, text):
        if not text.startswith("/"):
            return None

        command, _, rest = text[1:].partition(" ")
        command = command.lower().strip()
        rest = rest.strip()

        if command in {"help", "commands"}:
            return self._command_help()
        if command == "app":
            return self._tool_message(self.tools.open_app(rest))
        if command in {"url", "browser"}:
            return self._tool_message(self.tools.open_url(rest))
        if command in {"search", "web"}:
            return self._tool_message(self.tools.web_search(rest))
        if command == "open":
            return self._tool_message(self.tools.open_path(rest))
        if command in {"files", "ls"}:
            return self._tool_message(self.tools.list_files(rest or "."))
        if command in {"screen", "screenshot", "vision"}:
            return self._tool_message(self.tools.screenshot())
        if command == "volume":
            return self._tool_message(self.tools.volume(rest))
        if command in {"restart", "shutdown"}:
            return self._tool_message(self.tools.request_power(command))
        if command == "confirm":
            return self._confirm_pending()
        if command == "cancel":
            self.pending_confirmation = None
            return "Pending action cancelled."
        if command == "remember":
            return self._remember_fact(rest)
        if command == "recall":
            return self._recall_facts()
        if command == "forget":
            return self._forget_fact(rest)
        if command == "clear":
            self.clear_memory()
            return "Short-term conversation memory cleared."

        return f"Unknown command: /{command}. Try /help."

    def _tool_message(self, result):
        if result.needs_confirmation:
            self.pending_confirmation = result
            return result.message + " Type /confirm to proceed or /cancel to abort."
        prefix = "OK" if result.ok else "ERROR"
        return f"[{prefix}] {result.message}"

    def _confirm_pending(self):
        if self.pending_confirmation is None:
            return "No pending action to confirm."
        result = self.tools.confirm(self.pending_confirmation)
        self.pending_confirmation = None
        return self._tool_message(result)

    def _remember_fact(self, rest):
        if "=" in rest:
            key, value = rest.split("=", 1)
        elif ":" in rest:
            key, value = rest.split(":", 1)
        else:
            return "Use /remember key=value. Example: /remember favorite_editor=VS Code"

        try:
            self.memory.remember_fact(key, value)
        except ValueError as error:
            return str(error)
        return f"Remembered: {key.strip().lower()} = {value.strip()}"

    def _recall_facts(self):
        facts = self.memory.get_long_term()
        if not facts:
            return "Long-term memory is empty."
        return "Long-term memory:\n" + "\n".join(
            f"- {key}: {value}" for key, value in facts.items()
        )

    def _forget_fact(self, rest):
        if not rest:
            return "Use /forget key."
        if self.memory.forget_fact(rest):
            return f"Forgot: {rest.strip().lower()}"
        return f"No long-term memory found for: {rest.strip().lower()}"

    @staticmethod
    def _command_help():
        return (
            "ULTRON commands:\n"
            "/app notepad - launch an app\n"
            "/search quantum computing - web search in browser\n"
            "/url example.com - open a website\n"
            "/open C:\\path - open a file or folder\n"
            "/files C:\\path - list folder contents\n"
            "/screenshot - save the current screen\n"
            "/volume up|down|mute - system volume keys\n"
            "/remember key=value - save long-term memory\n"
            "/recall - show long-term memory\n"
            "/restart or /shutdown - ask for confirmation first\n"
            "/confirm, /cancel, /clear"
        )

    def _handle_api_error(self, error: Exception):
        self._last_error = self._friendly_error(error)

    def _friendly_error(self, error: Exception) -> str:
        error_text = self._error_text(error)
        lowered = error_text.lower()
        status_code = getattr(error, "code", None)

        if (
            status_code == 401
            or "401" in error_text
            or "invalid api key" in lowered
            or "api key" in lowered
        ):
            return (
                f"Gemini authentication failed: {error_text}. "
                f"Check {API_KEY_ENV_NAME}."
            )

        if status_code == 403 or "403" in error_text or "permission" in lowered:
            return f"Gemini permission denied: {error_text}"

        if status_code == 404 or "404" in error_text or "not found" in lowered:
            return (
                f"Gemini model '{self.model}' is unavailable: {error_text}"
            )

        if (
            status_code == 429
            or "429" in error_text
            or "resource_exhausted" in lowered
            or "quota" in lowered
            or "rate limit" in lowered
        ):
            return f"Gemini quota or rate limit reached: {error_text}"

        if (
            status_code in {500, 502, 503, 504}
            or any(code in error_text for code in ("500", "502", "503", "504"))
            or "service unavailable" in lowered
            or "overloaded" in lowered
            or "busy" in lowered
        ):
            return f"Gemini temporary server error: {error_text}"

        if (
            isinstance(error, (TimeoutError, ConnectionError, OSError))
            or error.__class__.__module__.startswith("httpx")
        ):
            return f"Gemini network error: {error_text}"

        if error_text:
            return f"Gemini error: {error_text}"

        return "Gemini returned an unknown error."

    @staticmethod
    def _error_text(error: Exception) -> str:
        response_json = getattr(error, "response_json", None)
        if isinstance(response_json, dict):
            api_error = response_json.get("error")
            if isinstance(api_error, dict):
                message = api_error.get("message")
                if message:
                    return str(message).strip()

        return str(error).strip()
