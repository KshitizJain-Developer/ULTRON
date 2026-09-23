from dataclasses import dataclass
from typing import Iterable, List, Optional

try:
    from google import genai
    from google.genai import types
except Exception as import_error:  # pragma: no cover - depends on local install
    genai = None
    types = None
    GENAI_IMPORT_ERROR = import_error
else:
    GENAI_IMPORT_ERROR = None


@dataclass
class GeminiStatus:
    online: bool
    model: str
    message: str


class GeminiClient:
    """Small adapter around the google-genai Chat API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        max_output_tokens: int = 1200,
    ):
        if GENAI_IMPORT_ERROR is not None:
            raise RuntimeError(
                "google-genai is not available. Install or repair the package "
                "before connecting ULTRON to Gemini."
            ) from GENAI_IMPORT_ERROR

        if not api_key:
            raise ValueError(
                "ULTRON_API_KEY is missing. Configure ULTRON_API_KEY to enable Gemini."
            )

        self.model = model
        self.client = genai.Client(api_key=api_key)
        self.config = types.GenerateContentConfig(
            system_instruction=system_prompt.strip(),
            max_output_tokens=max_output_tokens,
        )
        self.chat = None

    def start_chat(self, history: Optional[List[dict]] = None):
        self.chat = self.client.chats.create(
            model=self.model,
            config=self.config,
            history=self._to_sdk_history(history or []),
        )
        return self.chat

    def send(self, message: str, history: Optional[List[dict]] = None) -> str:
        chat = self._chat(history)
        response = chat.send_message(message=message)
        return self._response_text(response)

    def stream(
        self,
        message: str,
        history: Optional[List[dict]] = None,
    ) -> Iterable[str]:
        chat = self._chat(history)
        for chunk in chat.send_message_stream(message=message):
            text = getattr(chunk, "text", None)
            if text:
                yield text

    def reset(self, history: Optional[List[dict]] = None):
        self.start_chat(history)

    def _chat(self, history: Optional[List[dict]] = None):
        if self.chat is None:
            return self.start_chat(history)
        return self.chat

    def _to_sdk_history(self, history: List[dict]):
        sdk_history = []

        for item in history:
            text = str(item.get("text", "")).strip()
            if not text:
                continue

            role = item.get("role")
            if role == "assistant":
                role = "model"
            elif role != "user":
                continue

            sdk_history.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=text)],
                )
            )

        return sdk_history

    @staticmethod
    def _response_text(response) -> str:
        text = getattr(response, "text", None)
        if text:
            return text.strip()
        return "I received an empty response."
