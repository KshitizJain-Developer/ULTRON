# ULTRON

ULTRON is a personal AI desktop and CLI assistant for Windows. It provides a
graphical HUD, Gemini-powered conversation, optional voice input/output, local
conversation memory, long-term facts, and permission-aware desktop commands.

## Features

- Gemini chat through the `google-genai` SDK
- Streaming responses in the desktop HUD
- Optional speech input and text-to-speech output
- Local short-term and long-term memory
- Desktop actions for apps, URLs, files, screenshots, search, and volume
- Confirmation before restart and shutdown commands
- Offline startup with a clear status when no API key is configured

## Requirements

- Windows
- Python 3.10 or newer
- A Gemini API key
- A working microphone if voice input is used

## Setup

Create and activate a virtual environment, then install the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

Configure the API key in the environment. It is never stored in the source
code:

```powershell
$env:ULTRON_API_KEY = "replace-with-your-key"
```

The variable applies to the current PowerShell session. For a persistent
Windows user setting, use `setx ULTRON_API_KEY "replace-with-your-key"` and
open a new terminal afterward. Never commit the key or paste it into a tracked
file.

Start ULTRON:

```powershell
py main.py
```

## Local configuration

ULTRON creates `config/settings.json` on first startup. To begin with a
known-safe configuration, copy the example:

```powershell
Copy-Item config\settings.example.json config\settings.json
```

The model can also be overridden for the current session:

```powershell
$env:ULTRON_MODEL = "your-supported-gemini-model"
```

## Privacy and repository safety

The following files are intentionally local and ignored by Git:

- `memory\conversation.json` — recent conversation history
- `memory\long_term.json` — saved user/session facts
- `config\settings.json` — local settings
- `.env*` files, except a deliberately safe `.env.example`

Python caches, virtual environments, IDE metadata, Windows shortcuts, and
other generated files are ignored as well. The memory directory is created
automatically by ULTRON, so no private memory needs to be committed for a
fresh checkout.

Before publishing, scan the files that will be committed and verify that no
API key, credential, personal memory, or local configuration is included.

## Commands

Use `/help` inside ULTRON to see the available commands. Examples include:

```text
/search quantum computing
/url example.com
/open C:\path\to\file
/files C:\path\to\folder
/remember favorite_editor=VS Code
/recall
/clear
```

Sensitive power commands require `/confirm` after ULTRON displays the pending
action. Use `/cancel` to abort it.

## Project layout

```text
main.py              Application entry point
core/                Configuration, engine, Gemini, memory, and voice logic
ui/                  Desktop HUD
tools/               Permission-aware desktop actions
vision/              Vision package
config/              Safe settings template and ignored local settings
memory/              Ignored runtime memory
requirements.txt     Python dependencies
```

ULTRON's existing source code and runtime behavior are preserved; repository
preparation only documents setup and prevents local data from being published.
