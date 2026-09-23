import json
import os
from pathlib import Path

APP_NAME = "ULTRON"
APP_VERSION = "0.2.0"

# ULTRON has its own API environment variable.
API_KEY_ENV_NAME = "ULTRON_API_KEY"
MODEL_ENV_NAME = "ULTRON_MODEL"

# Keep model configuration local and explicit.
# Do not add guessed fallback names here. If Google changes model availability,
# set ULTRON_MODEL locally or update this single default after verification.
DEFAULT_MODEL_NAME = "gemini-3.6-flash"
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "model": DEFAULT_MODEL_NAME,
    "wake_word": "ultron",
    "voice_output": False,
    "confirm_sensitive_actions": True,
    "camera_enabled": False,
}

SYSTEM_PROMPT = """
You are ULTRON, a personal desktop AI assistant.

You are intelligent, calm, confident, natural and helpful.

Your responsibilities include:
- answering questions
- explaining concepts
- helping with coding
- understanding user instructions
- assisting with computer tasks
- remembering useful conversation context
- working with tools such as vision, files, browser/app launching and system controls

Rules:
- Never pretend an action was completed if it was not.
- Never claim to have accessed something you cannot access.
- Ask for confirmation before sensitive or irreversible computer actions.
- Be concise for simple questions.
- Give detailed answers when the task requires it.
- Stay honest about limitations.

You are running as ULTRON User Edition.
"""


def load_settings():
    """Load user settings, repairing missing or invalid values."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    settings = DEFAULT_SETTINGS.copy()

    if SETTINGS_FILE.exists() and SETTINGS_FILE.stat().st_size > 0:
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                settings.update(
                    {key: data.get(key, value) for key, value in settings.items()}
                )
        except Exception:
            pass

    save_settings(settings)
    return settings


def save_settings(settings):
    """Persist settings to config/settings.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    clean = DEFAULT_SETTINGS.copy()
    clean.update(
        {key: settings.get(key, value) for key, value in DEFAULT_SETTINGS.items()}
    )
    SETTINGS_FILE.write_text(
        json.dumps(clean, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return clean


def update_settings(**changes):
    settings = load_settings()
    settings.update(changes)
    return save_settings(settings)


def get_api_key():
    """
    Return ULTRON's API key from the environment only.
    """
    return os.environ.get(API_KEY_ENV_NAME, "").strip()


def has_api_key():
    """Return True when an ULTRON API key is configured."""
    return bool(get_api_key())


def get_model_name():
    """Return the configured Gemini model for ULTRON."""
    return os.environ.get(MODEL_ENV_NAME, "").strip() or load_settings().get(
        "model", DEFAULT_MODEL_NAME
    ).strip()
