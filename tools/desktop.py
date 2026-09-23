from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
import urllib.parse
import webbrowser


@dataclass
class ToolResult:
    ok: bool
    message: str
    needs_confirmation: bool = False
    action: str = ""
    payload: str = ""


class DesktopTools:
    """Small permission-aware desktop actions used by the ULTRON engine/UI."""

    def open_app(self, app_name):
        app_name = str(app_name).strip()
        if not app_name:
            return ToolResult(False, "Tell me which app to launch.")

        try:
            subprocess.Popen(app_name, shell=True)
            return ToolResult(True, f"Launching app: {app_name}")
        except Exception as error:
            return ToolResult(False, f"Could not launch {app_name}: {error}")

    def open_url(self, url):
        url = str(url).strip()
        if not url:
            return ToolResult(False, "Tell me which URL to open.")
        if "://" not in url:
            url = "https://" + url

        try:
            webbrowser.open(url)
            return ToolResult(True, f"Opening browser: {url}")
        except Exception as error:
            return ToolResult(False, f"Could not open browser: {error}")

    def web_search(self, query):
        query = str(query).strip()
        if not query:
            return ToolResult(False, "Tell me what to search for.")
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
        return self.open_url(url)

    def open_path(self, raw_path):
        raw_path = str(raw_path).strip().strip('"')
        if not raw_path:
            return ToolResult(False, "Tell me which file or folder to open.")

        path = Path(raw_path).expanduser()
        if not path.exists():
            return ToolResult(False, f"Path not found: {path}")

        try:
            os.startfile(path)  # type: ignore[attr-defined]
            return ToolResult(True, f"Opening: {path}")
        except Exception as error:
            return ToolResult(False, f"Could not open {path}: {error}")

    def list_files(self, raw_path="."):
        raw_path = str(raw_path or ".").strip().strip('"')
        path = Path(raw_path).expanduser()
        if not path.exists():
            return ToolResult(False, f"Folder not found: {path}")
        if not path.is_dir():
            return ToolResult(False, f"Not a folder: {path}")

        try:
            entries = sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
            preview = []
            for item in entries[:40]:
                prefix = "[DIR]" if item.is_dir() else "[FILE]"
                preview.append(f"{prefix} {item.name}")
            more = "" if len(entries) <= 40 else f"\n...and {len(entries) - 40} more"
            return ToolResult(True, "\n".join(preview) + more)
        except Exception as error:
            return ToolResult(False, f"Could not list files: {error}")

    def screenshot(self):
        try:
            from PIL import ImageGrab
        except Exception:
            return ToolResult(
                False,
                "Screenshot support needs Pillow installed: py -m pip install pillow",
            )

        target_dir = Path.home() / "Pictures" / "Ultron"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "latest_screenshot.png"

        try:
            image = ImageGrab.grab()
            image.save(target)
            return ToolResult(True, f"Screenshot saved: {target}")
        except Exception as error:
            return ToolResult(False, f"Could not capture screenshot: {error}")

    def volume(self, direction):
        direction = str(direction).strip().lower()
        key_map = {
            "up": "{VOLUME_UP}",
            "down": "{VOLUME_DOWN}",
            "mute": "{VOLUME_MUTE}",
        }
        key = key_map.get(direction)
        if not key:
            return ToolResult(False, "Use volume up, volume down, or volume mute.")

        command = (
            "$shell = New-Object -ComObject WScript.Shell; "
            f"$shell.SendKeys('{key}')"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                check=True,
                capture_output=True,
                text=True,
            )
            return ToolResult(True, f"Volume command sent: {direction}")
        except Exception as error:
            return ToolResult(False, f"Could not change volume: {error}")

    def request_power(self, action):
        action = str(action).strip().lower()
        if action not in {"restart", "shutdown"}:
            return ToolResult(False, "Power action must be restart or shutdown.")
        return ToolResult(
            False,
            f"Confirm {action}? This will affect the whole computer.",
            needs_confirmation=True,
            action="power",
            payload=action,
        )

    def confirm(self, result):
        if result.action == "power":
            flag = "/r" if result.payload == "restart" else "/s"
            try:
                subprocess.Popen(["shutdown", flag, "/t", "5"])
                return ToolResult(True, f"{result.payload.title()} scheduled in 5 seconds.")
            except Exception as error:
                return ToolResult(False, f"Could not start {result.payload}: {error}")
        return ToolResult(False, "No confirmable action is pending.")
