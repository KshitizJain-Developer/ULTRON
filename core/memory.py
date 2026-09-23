import json
from pathlib import Path


MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
MEMORY_FILE = MEMORY_DIR / "conversation.json"
LONG_TERM_FILE = MEMORY_DIR / "long_term.json"


class Memory:
    def __init__(self, max_messages=30):
        self.max_messages = max_messages
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

        self.messages = []
        self.long_term = {}
        self.load()
        self.load_long_term()

    def load(self):
        if not MEMORY_FILE.exists():
            return

        try:
            data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))

            if isinstance(data, list):
                self.messages = data[-self.max_messages:]

        except Exception:
            self.messages = []

    def save(self):
        try:
            MEMORY_FILE.write_text(
                json.dumps(
                    self.messages[-self.max_messages:],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    def load_long_term(self):
        if not LONG_TERM_FILE.exists():
            self.long_term = {}
            return

        try:
            data = json.loads(LONG_TERM_FILE.read_text(encoding="utf-8"))
            self.long_term = data if isinstance(data, dict) else {}
        except Exception:
            self.long_term = {}

    def save_long_term(self):
        try:
            LONG_TERM_FILE.write_text(
                json.dumps(self.long_term, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def remember_fact(self, key, value):
        key = str(key).strip().lower()
        value = str(value).strip()
        if not key or not value:
            raise ValueError("Memory facts need both a name and a value.")
        self.long_term[key] = value
        self.save_long_term()

    def forget_fact(self, key):
        key = str(key).strip().lower()
        removed = self.long_term.pop(key, None)
        self.save_long_term()
        return removed is not None

    def get_long_term(self):
        return dict(self.long_term)

    def long_term_prompt(self):
        if not self.long_term:
            return ""
        facts = "\n".join(f"- {key}: {value}" for key, value in self.long_term.items())
        return "Useful long-term memory about the user/session:\n" + facts

    def add_user(self, text):
        self.messages.append({
            "role": "user",
            "text": text,
        })
        self.save()

    def add_assistant(self, text):
        self.messages.append({
            "role": "assistant",
            "text": text,
        })
        self.save()

    def get_history(self):
        return self.messages[-self.max_messages:]

    def clear(self):
        self.messages = []
        self.save()
