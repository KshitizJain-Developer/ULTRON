import math
import queue
import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from core.engine import UltronEngine
from core.voice import VoiceIO


STATE_COLORS = {
    "IDLE": "#38bdf8",
    "LISTENING": "#22c55e",
    "THINKING": "#f59e0b",
    "SPEAKING": "#a78bfa",
    "ERROR": "#ef4444",
}


class ReactorCore(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            width=300,
            height=300,
            bg="#08090d",
            highlightthickness=0,
            **kwargs,
        )
        self.state = "IDLE"
        self.phase = 0
        self.after_id = None
        self.bind("<Configure>", lambda _event: self.draw())

    def set_state(self, state):
        self.state = state
        self.draw()

    def start(self):
        if self.after_id is None:
            self.animate()

    def stop(self):
        if self.after_id is not None:
            self.after_cancel(self.after_id)
            self.after_id = None

    def animate(self):
        self.phase = (self.phase + 4) % 360
        self.draw()
        self.after_id = self.after(50, self.animate)

    def draw(self):
        self.delete("all")

        width = max(self.winfo_width(), 260)
        height = max(self.winfo_height(), 260)
        cx = width / 2
        cy = height / 2
        size = min(width, height)
        color = STATE_COLORS.get(self.state, STATE_COLORS["IDLE"])
        pulse = math.sin(math.radians(self.phase)) * 6

        self.create_oval(
            cx - size * 0.34,
            cy - size * 0.34,
            cx + size * 0.34,
            cy + size * 0.34,
            outline="#1e293b",
            width=2,
        )
        self.create_oval(
            cx - size * 0.24 - pulse,
            cy - size * 0.24 - pulse,
            cx + size * 0.24 + pulse,
            cy + size * 0.24 + pulse,
            outline=color,
            width=3,
        )

        for index, radius in enumerate((0.38, 0.45)):
            start = (self.phase * (1 if index == 0 else -1)) % 360
            self.create_arc(
                cx - size * radius,
                cy - size * radius,
                cx + size * radius,
                cy + size * radius,
                start=start,
                extent=86,
                outline=color,
                width=2,
                style="arc",
            )
            self.create_arc(
                cx - size * radius,
                cy - size * radius,
                cx + size * radius,
                cy + size * radius,
                start=start + 180,
                extent=52,
                outline="#334155",
                width=2,
                style="arc",
            )

        for angle in range(0, 360, 45):
            radians = math.radians(angle + self.phase / 3)
            inner = size * 0.28
            outer = size * 0.32
            self.create_line(
                cx + math.cos(radians) * inner,
                cy + math.sin(radians) * inner,
                cx + math.cos(radians) * outer,
                cy + math.sin(radians) * outer,
                fill=color,
                width=2,
            )

        self.create_oval(
            cx - size * 0.11,
            cy - size * 0.11,
            cx + size * 0.11,
            cy + size * 0.11,
            fill="#0f172a",
            outline=color,
            width=3,
        )
        self.create_text(
            cx,
            cy,
            text=self.state,
            fill="#e5f6ff",
            font=("Segoe UI", 12, "bold"),
        )


class UltronHUD(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("ULTRON")
        self.geometry("1180x760")
        self.minsize(920, 620)
        self.configure(fg_color="#08090d")

        self.engine = UltronEngine()
        self.voice = VoiceIO()
        self.events = queue.Queue()
        self.busy = False
        self.thinking_ticks = 0
        self.current_response = ""

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_header()
        self.create_sidebar()
        self.create_main()
        self.create_input()

        self.refresh_status()
        self.reactor.start()
        self.after(80, self.process_events)
        self.after(240, self.animate_thinking)
        self.after(350, self.first_launch_check)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_header(self):
        header = ctk.CTkFrame(self, height=76, corner_radius=0, fg_color="#0b0f16")
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        header.grid_propagate(False)

        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.grid(row=0, column=0, sticky="w", padx=24)

        ctk.CTkLabel(
            title_block,
            text="ULTRON",
            font=("Segoe UI", 28, "bold"),
            text_color="#f8fafc",
        ).pack(anchor="w", pady=(12, 0))
        ctk.CTkLabel(
            title_block,
            text="TACTICAL DESKTOP INTELLIGENCE",
            font=("Segoe UI", 10, "bold"),
            text_color="#64748b",
        ).pack(anchor="w")

        self.model_status = ctk.CTkLabel(
            header,
            text="MODEL: CHECKING",
            font=("Segoe UI", 12, "bold"),
            text_color="#94a3b8",
        )
        self.model_status.grid(row=0, column=1, sticky="e", padx=(0, 24))

    def create_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#090d13")
        sidebar.grid(row=1, column=0, rowspan=2, sticky="nsew")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(
            sidebar,
            text="U",
            width=82,
            height=82,
            corner_radius=41,
            fg_color="#0f172a",
            font=("Segoe UI", 48, "bold"),
            text_color="#38bdf8",
        ).pack(pady=(34, 10))

        self.core_status = ctk.CTkLabel(
            sidebar,
            text="CORE: IDLE",
            font=("Segoe UI", 12, "bold"),
            text_color="#38bdf8",
        )
        self.core_status.pack(pady=(0, 28))

        commands = {
            "CHAT": lambda: self.entry.focus_set(),
            "MIC": self.listen_once,
            "VISION": lambda: self.quick_command("/screenshot"),
            "MEMORY": self.show_memory_status,
            "TOOLS": lambda: self.quick_command("/help"),
            "SETTINGS": self.show_settings_dialog,
        }

        for name, command in commands.items():
            button = ctk.CTkButton(
                sidebar,
                text=name,
                height=42,
                corner_radius=6,
                fg_color="#101722" if name == "CHAT" else "transparent",
                hover_color="#172033",
                text_color="#dbeafe",
                anchor="w",
                font=("Segoe UI", 13, "bold"),
                command=command,
            )
            button.pack(fill="x", padx=16, pady=5)

        ctk.CTkLabel(
            sidebar,
            text="SPIDEY IDENTITY\nPERMISSION GATED",
            justify="left",
            font=("Segoe UI", 10, "bold"),
            text_color="#475569",
        ).pack(side="bottom", anchor="w", padx=20, pady=22)

    def create_main(self):
        main = ctk.CTkFrame(self, corner_radius=0, fg_color="#08090d")
        main.grid(row=1, column=1, sticky="nsew", padx=22, pady=18)
        main.grid_columnconfigure(0, weight=0, minsize=330)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        reactor_panel = ctk.CTkFrame(
            main,
            width=330,
            corner_radius=8,
            fg_color="#0a0f18",
            border_width=1,
            border_color="#172033",
        )
        reactor_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        reactor_panel.grid_propagate(False)
        reactor_panel.grid_rowconfigure(1, weight=1)
        reactor_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            reactor_panel,
            text="ARC REACTOR",
            font=("Segoe UI", 12, "bold"),
            text_color="#94a3b8",
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 0))

        self.reactor = ReactorCore(reactor_panel)
        self.reactor.grid(row=1, column=0, sticky="nsew", padx=14, pady=10)

        self.status_text = ctk.CTkLabel(
            reactor_panel,
            text="Initializing core systems...",
            wraplength=280,
            justify="left",
            font=("Segoe UI", 12),
            text_color="#cbd5e1",
        )
        self.status_text.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))

        chat_panel = ctk.CTkFrame(
            main,
            corner_radius=8,
            fg_color="#0a0f18",
            border_width=1,
            border_color="#172033",
        )
        chat_panel.grid(row=0, column=1, sticky="nsew")
        chat_panel.grid_columnconfigure(0, weight=1)
        chat_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            chat_panel,
            text="MISSION CHANNEL",
            font=("Segoe UI", 12, "bold"),
            text_color="#94a3b8",
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 8))

        self.chat = ctk.CTkTextbox(
            chat_panel,
            corner_radius=0,
            fg_color="#070b11",
            border_width=0,
            text_color="#dbeafe",
            font=("Consolas", 13),
            wrap="word",
        )
        self.chat.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self.chat.configure(state="disabled")
        self.append_message(
            "SYSTEM",
            "ULTRON interface online. Use /help for desktop tools and memory commands.",
        )

    def create_input(self):
        bar = ctk.CTkFrame(self, height=86, corner_radius=0, fg_color="#090d13")
        bar.grid(row=2, column=1, sticky="ew", padx=22, pady=(0, 18))
        bar.grid_columnconfigure(0, weight=1)
        bar.grid_propagate(False)

        self.entry = ctk.CTkEntry(
            bar,
            height=48,
            placeholder_text="Transmit to ULTRON...",
            corner_radius=6,
            fg_color="#0f172a",
            border_color="#263244",
            text_color="#f8fafc",
            font=("Segoe UI", 14),
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=19)
        self.entry.bind("<Return>", self.send_message)

        self.mic_button = ctk.CTkButton(
            bar,
            text="MIC",
            width=66,
            height=48,
            corner_radius=6,
            fg_color="#111827",
            hover_color="#1f2937",
            command=self.listen_once,
        )
        self.mic_button.grid(row=0, column=1, padx=(0, 8), pady=19)

        self.vision_button = ctk.CTkButton(
            bar,
            text="VISION",
            width=82,
            height=48,
            corner_radius=6,
            fg_color="#111827",
            hover_color="#1f2937",
            command=lambda: self.quick_command("/screenshot"),
        )
        self.vision_button.grid(row=0, column=2, padx=(0, 8), pady=19)

        self.send_button = ctk.CTkButton(
            bar,
            text="SEND",
            width=86,
            height=48,
            corner_radius=6,
            fg_color="#0ea5e9",
            hover_color="#0284c7",
            font=("Segoe UI", 13, "bold"),
            command=self.send_message,
        )
        self.send_button.grid(row=0, column=3, pady=19)

    def first_launch_check(self):
        if not self.engine.api_key:
            self.show_settings_dialog(first_launch=True)

    def refresh_status(self):
        status = self.engine.status()
        if status.online:
            self.set_state("IDLE")
            self.model_status.configure(
                text=f"MODEL: {status.model} | API: CONFIGURED",
                text_color="#38bdf8",
            )
            self.status_text.configure(text="Gemini link online. Awaiting input.")
        else:
            self.set_state("ERROR")
            self.model_status.configure(
                text=f"MODEL: {status.model} | OFFLINE",
                text_color="#ef4444",
            )
            self.status_text.configure(text=status.message)

    def set_state(self, state):
        color = STATE_COLORS.get(state, STATE_COLORS["IDLE"])
        self.reactor.set_state(state)
        self.core_status.configure(text=f"CORE: {state}", text_color=color)

    def send_message(self, event=None):
        if self.busy:
            return

        message = self.entry.get().strip()
        if not message:
            return

        self.entry.delete(0, "end")
        self.dispatch_message(message)

    def quick_command(self, command):
        if not self.busy:
            self.dispatch_message(command)

    def dispatch_message(self, message):
        self.append_message("YOU", message)
        self.append_message("ULTRON", "")
        self.current_response = ""
        self.busy = True
        self.send_button.configure(state="disabled", text="BUSY")
        self.set_state("THINKING")
        self.status_text.configure(text="ULTRON is processing the transmission.")

        worker = threading.Thread(
            target=self.run_gemini_stream,
            args=(message,),
            daemon=True,
        )
        worker.start()

    def run_gemini_stream(self, message):
        try:
            self.engine.stream(
                message,
                lambda chunk: self.events.put(("chunk", chunk)),
            )
            self.events.put(("done", None))
        except Exception as error:
            self.events.put(("error", str(error)))

    def listen_once(self):
        if self.busy:
            return
        self.busy = True
        self.send_button.configure(state="disabled", text="BUSY")
        self.set_state("LISTENING")
        self.status_text.configure(text="Listening for voice input.")

        def worker():
            ok, payload = self.voice.listen_once()
            self.events.put(("voice", payload if ok else "[VOICE ERROR] " + payload))

        threading.Thread(target=worker, daemon=True).start()

    def process_events(self):
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if event == "chunk":
                if self.reactor.state != "SPEAKING":
                    self.set_state("SPEAKING")
                self.current_response += payload
                self.append_to_current_response(payload)
            elif event == "done":
                self.finish_response()
            elif event == "error":
                self.finish_response(error=payload)
            elif event == "voice":
                self.finish_listening(payload)

        self.after(80, self.process_events)

    def animate_thinking(self):
        if self.busy and self.reactor.state == "THINKING":
            self.thinking_ticks = (self.thinking_ticks + 1) % 4
            self.status_text.configure(
                text="ULTRON is thinking" + "." * self.thinking_ticks
            )
        self.after(240, self.animate_thinking)

    def finish_listening(self, payload):
        self.busy = False
        self.send_button.configure(state="normal", text="SEND")

        if payload.startswith("[VOICE ERROR]"):
            self.set_state("ERROR")
            self.append_message("SYSTEM", payload)
            self.status_text.configure(text=payload)
            return

        self.set_state("IDLE")
        self.status_text.configure(text="Voice input captured.")
        self.entry.delete(0, "end")
        self.entry.insert(0, payload)
        self.send_message()

    def finish_response(self, error=None):
        self.busy = False
        self.send_button.configure(state="normal", text="SEND")

        if error:
            cleaned = self.clean_error(error)
            self.set_state("ERROR")
            self.append_to_current_response(
                "\n[OFFLINE / API ERROR] " + cleaned
            )
            self.model_status.configure(
                text=f"MODEL: {self.engine.current_model()} | API ERROR",
                text_color="#ef4444",
            )
            self.status_text.configure(text=cleaned)
            return

        self.set_state("IDLE")
        self.status_text.configure(text="Response complete. Awaiting input.")
        self.refresh_status()
        if self.engine.settings.get("voice_output") and self.current_response.strip():
            threading.Thread(
                target=self.voice.speak,
                args=(self.current_response.strip(),),
                daemon=True,
            ).start()

    def append_message(self, speaker, message):
        self.chat.configure(state="normal")
        self.chat.insert("end", f"\n{speaker} > {message}\n")
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def append_to_current_response(self, text):
        self.chat.configure(state="normal")
        self.chat.insert("end-1c", text)
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def show_memory_status(self):
        count = len(self.engine.memory.get_history())
        facts = len(self.engine.memory.get_long_term())
        self.append_message(
            "SYSTEM",
            f"Short-term memory: {count} messages. Long-term memory: {facts} facts.",
        )
        self.quick_command("/recall")

    def show_settings_dialog(self, first_launch=False):
        dialog = ctk.CTkToplevel(self)
        dialog.title("ULTRON Settings")
        dialog.geometry("520x360")
        dialog.resizable(False, False)
        dialog.configure(fg_color="#0a0f18")
        dialog.transient(self)
        dialog.grab_set()

        title = "First Launch Setup" if first_launch else "Settings"
        ctk.CTkLabel(
            dialog,
            text=title,
            font=("Segoe UI", 22, "bold"),
            text_color="#f8fafc",
        ).pack(anchor="w", padx=24, pady=(22, 8))

        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=24, pady=8)
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            form,
            text="API key",
            text_color="#cbd5e1",
        ).grid(row=0, column=0, sticky="w", pady=8)
        ctk.CTkLabel(
            form,
            text="Read from ULTRON_API_KEY",
            text_color="#94a3b8",
        ).grid(row=0, column=1, sticky="w", padx=(14, 0), pady=8)

        ctk.CTkLabel(form, text="Model", text_color="#cbd5e1").grid(row=1, column=0, sticky="w", pady=8)
        model_entry = ctk.CTkEntry(form, height=38)
        model_entry.grid(row=1, column=1, sticky="ew", padx=(14, 0), pady=8)
        model_entry.insert(0, self.engine.current_model())

        ctk.CTkLabel(form, text="Wake word", text_color="#cbd5e1").grid(row=2, column=0, sticky="w", pady=8)
        wake_entry = ctk.CTkEntry(form, height=38)
        wake_entry.grid(row=2, column=1, sticky="ew", padx=(14, 0), pady=8)
        wake_entry.insert(0, self.engine.settings.get("wake_word", "ultron"))

        voice_var = tk.BooleanVar(value=bool(self.engine.settings.get("voice_output")))
        ctk.CTkCheckBox(
            form,
            text="Speak responses",
            variable=voice_var,
            text_color="#cbd5e1",
        ).grid(row=3, column=1, sticky="w", padx=(14, 0), pady=12)

        button_row = ctk.CTkFrame(dialog, fg_color="transparent")
        button_row.pack(fill="x", padx=24, pady=(0, 22))

        def save():
            self.engine.configure(
                model=model_entry.get(),
                voice_output=voice_var.get(),
                wake_word=wake_entry.get(),
            )
            self.refresh_status()
            self.append_message("SYSTEM", "Settings saved.")
            dialog.destroy()

        ctk.CTkButton(
            button_row,
            text="SAVE",
            height=40,
            fg_color="#0ea5e9",
            hover_color="#0284c7",
            command=save,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            button_row,
            text="CANCEL",
            height=40,
            fg_color="#1f2937",
            hover_color="#263244",
            command=dialog.destroy,
        ).pack(side="right")

    def on_close(self):
        if self.engine.pending_confirmation is not None:
            if not messagebox.askyesno("ULTRON", "A sensitive action is pending. Close anyway?"):
                return
        self.reactor.stop()
        self.destroy()

    @staticmethod
    def clean_error(error):
        text = str(error).strip()
        return text or "Gemini is unavailable."


def run():
    app = UltronHUD()
    app.mainloop()
