from __future__ import annotations

"""An advanced, theme-aware desktop auto clicker application."""

import logging
import time
from dataclasses import dataclass
from threading import Event, Thread
from typing import Dict, List, Optional, Sequence, Tuple

import tkinter as tk
from tkinter import messagebox, ttk

from pynput.keyboard import Key, Listener
from pynput.mouse import Button, Controller


logging.basicConfig(level=logging.INFO)


# ---------------------------------------------------------------------------
# Theming and configuration helpers
# ---------------------------------------------------------------------------


THEMES: Dict[str, Dict[str, str]] = {
    "Dark": {
        "background": "#1f1f1f",
        "foreground": "#f5f5f5",
        "accent": "#4f9dff",
        "accent_hover": "#3177d6",
    },
    "Light": {
        "background": "#f7f7f7",
        "foreground": "#1c1c1c",
        "accent": "#3366cc",
        "accent_hover": "#274c99",
    },
    "Hacker": {
        "background": "#060b08",
        "foreground": "#33ff88",
        "accent": "#00cc66",
        "accent_hover": "#00994d",
    },
}


HOTKEY_CHOICES: Dict[str, Key] = {
    "F6": Key.f6,
    "F7": Key.f7,
    "F8": Key.f8,
    "F9": Key.f9,
    "F10": Key.f10,
    "F11": Key.f11,
    "F12": Key.f12,
    "Pause": Key.pause,
}


@dataclass(slots=True)
class ClickSettings:
    """Strongly typed container for a click run configuration."""

    interval: float
    count: int
    button: Button
    delay: float
    hold_duration: float
    positions: Sequence[Tuple[int, int]]
    swipe: Optional[Tuple[Tuple[int, int], Tuple[int, int]]]
    swipe_duration: float


class AdvancedAutoclicker:
    """Feature rich auto clicker with polished Tk themed interface."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Advanced AutoClicker")
        self.root.geometry("560x520")
        self.root.minsize(520, 480)

        self.mouse = Controller()
        self.click_thread: Optional[Thread] = None
        self.stop_event: Event = Event()
        self.running = False

        self.positions: List[Tuple[int, int]] = []
        self.swipe_positions: List[Tuple[int, int]] = []

        self.theme_var = tk.StringVar(value="Dark")
        self.interval_var = tk.DoubleVar(value=0.5)
        self.delay_var = tk.DoubleVar(value=0.0)
        self.hold_var = tk.DoubleVar(value=0.0)
        self.count_var = tk.IntVar(value=0)
        self.button_var = tk.StringVar(value="Left")
        self.swipe_duration_var = tk.DoubleVar(value=0.3)

        self.start_hotkey_var = tk.StringVar(value="F8")
        self.stop_hotkey_var = tk.StringVar(value="F9")

        self.status_var = tk.StringVar(value="Status: Stopped")
        self.progress_label_var = tk.StringVar(value="Progress: Idle")

        self.progress_infinite = False

        self._configure_style()
        self._create_widgets()
        self.apply_theme("Dark")

        self.keyboard_listener = Listener(on_press=self._on_key_press)
        self.keyboard_listener.daemon = True
        self.keyboard_listener.start()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _configure_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            # Fall back to default theme on platforms where clam is missing.
            logging.debug("'clam' ttk theme unavailable; using default theme.")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Card.TFrame", padding=16)

    def _create_widgets(self) -> None:
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", padx=12, pady=(12, 0))

        self.basic_tab = ttk.Frame(self.notebook, padding=12)
        self.advanced_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.basic_tab, text="Quick Setup")
        self.notebook.add(self.advanced_tab, text="Advanced")

        self._create_basic_tab()
        self._create_advanced_tab()
        self._create_footer()

    def _create_basic_tab(self) -> None:
        timing_card = ttk.LabelFrame(self.basic_tab, text="Timing")
        timing_card.pack(fill="x", pady=(0, 12))

        ttk.Label(timing_card, text="Click interval (seconds)").grid(
            row=0, column=0, sticky="w", padx=8, pady=(6, 3)
        )
        self.interval_spinbox = ttk.Spinbox(
            timing_card,
            from_=0.01,
            to=60.0,
            increment=0.01,
            textvariable=self.interval_var,
            width=8,
            format="%.2f",
        )
        self.interval_spinbox.grid(row=0, column=1, padx=8, pady=(6, 3))

        ttk.Label(timing_card, text="Initial delay (seconds)").grid(
            row=1, column=0, sticky="w", padx=8, pady=3
        )
        self.delay_spinbox = ttk.Spinbox(
            timing_card,
            from_=0.0,
            to=30.0,
            increment=0.5,
            textvariable=self.delay_var,
            width=8,
            format="%.1f",
        )
        self.delay_spinbox.grid(row=1, column=1, padx=8, pady=3)

        ttk.Label(timing_card, text="Hold duration (seconds)").grid(
            row=2, column=0, sticky="w", padx=8, pady=(3, 6)
        )
        self.hold_spinbox = ttk.Spinbox(
            timing_card,
            from_=0.0,
            to=5.0,
            increment=0.1,
            textvariable=self.hold_var,
            width=8,
            format="%.1f",
        )
        self.hold_spinbox.grid(row=2, column=1, padx=8, pady=(3, 6))

        timing_card.columnconfigure(0, weight=1)

        options_card = ttk.LabelFrame(self.basic_tab, text="Click options")
        options_card.pack(fill="x", pady=(0, 12))

        ttk.Label(options_card, text="Mouse button").grid(
            row=0, column=0, sticky="w", padx=8, pady=(6, 3)
        )
        self.button_selector = ttk.Combobox(
            options_card,
            textvariable=self.button_var,
            values=["Left", "Right", "Middle"],
            state="readonly",
            width=10,
        )
        self.button_selector.grid(row=0, column=1, padx=8, pady=(6, 3))

        ttk.Label(options_card, text="Number of clicks (0 = infinite)").grid(
            row=1, column=0, sticky="w", padx=8, pady=3
        )
        self.count_spinbox = ttk.Spinbox(
            options_card,
            from_=0,
            to=100000,
            increment=1,
            textvariable=self.count_var,
            width=12,
        )
        self.count_spinbox.grid(row=1, column=1, padx=8, pady=3)

        options_card.columnconfigure(0, weight=1)

        hotkey_card = ttk.LabelFrame(self.basic_tab, text="Global hotkeys")
        hotkey_card.pack(fill="x")

        ttk.Label(hotkey_card, text="Start").grid(
            row=0, column=0, sticky="w", padx=8, pady=(6, 3)
        )
        self.start_hotkey_combo = ttk.Combobox(
            hotkey_card,
            textvariable=self.start_hotkey_var,
            values=list(HOTKEY_CHOICES.keys()),
            state="readonly",
            width=10,
        )
        self.start_hotkey_combo.grid(row=0, column=1, padx=8, pady=(6, 3))

        ttk.Label(hotkey_card, text="Stop").grid(
            row=1, column=0, sticky="w", padx=8, pady=(3, 6)
        )
        self.stop_hotkey_combo = ttk.Combobox(
            hotkey_card,
            textvariable=self.stop_hotkey_var,
            values=list(HOTKEY_CHOICES.keys()),
            state="readonly",
            width=10,
        )
        self.stop_hotkey_combo.grid(row=1, column=1, padx=8, pady=(3, 6))

        hotkey_card.columnconfigure(0, weight=1)

    def _create_advanced_tab(self) -> None:
        positions_card = ttk.LabelFrame(self.advanced_tab, text="Click positions")
        positions_card.pack(fill="both", expand=True, pady=(0, 12))

        self.position_tree = ttk.Treeview(
            positions_card,
            columns=("x", "y"),
            show="headings",
            height=6,
            selectmode="extended",
        )
        self.position_tree.heading("x", text="X")
        self.position_tree.heading("y", text="Y")
        self.position_tree.column("x", width=80, anchor="center")
        self.position_tree.column("y", width=80, anchor="center")
        self.position_tree.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=8, pady=8)

        scrollbar = ttk.Scrollbar(
            positions_card, orient="vertical", command=self.position_tree.yview
        )
        self.position_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=3, sticky="ns", pady=8)

        ttk.Button(
            positions_card,
            text="Record current position",
            command=self.record_position,
            style="Accent.TButton",
        ).grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")

        ttk.Button(
            positions_card,
            text="Remove selected",
            command=self.remove_selected_position,
        ).grid(row=1, column=1, padx=8, pady=(0, 8), sticky="ew")

        ttk.Button(
            positions_card,
            text="Clear all",
            command=self.clear_positions,
        ).grid(row=1, column=2, padx=8, pady=(0, 8), sticky="ew")

        positions_card.columnconfigure(0, weight=1)
        positions_card.columnconfigure(1, weight=1)
        positions_card.columnconfigure(2, weight=1)
        positions_card.rowconfigure(0, weight=1)

        self.position_tree.bind("<Delete>", lambda _: self.remove_selected_position())

        ttk.Label(
            positions_card,
            text=(
                "Tip: use the record button at the spot you want clicked. "
                "If no positions are stored, the current cursor location will be used."
            ),
            wraplength=420,
            justify="left",
        ).grid(row=2, column=0, columnspan=3, padx=8, pady=(0, 8), sticky="w")

        swipe_card = ttk.LabelFrame(self.advanced_tab, text="Swipe gesture")
        swipe_card.pack(fill="x")

        ttk.Label(swipe_card, text="Swipe duration (seconds)").grid(
            row=0, column=0, sticky="w", padx=8, pady=(6, 3)
        )
        self.swipe_duration_spinbox = ttk.Spinbox(
            swipe_card,
            from_=0.1,
            to=10.0,
            increment=0.1,
            textvariable=self.swipe_duration_var,
            width=8,
            format="%.1f",
        )
        self.swipe_duration_spinbox.grid(row=0, column=1, padx=8, pady=(6, 3))

        self.swipe_status_var = tk.StringVar(value="Swipe: not recorded")
        self.swipe_status_label = ttk.Label(swipe_card, textvariable=self.swipe_status_var)
        self.swipe_status_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=3)

        ttk.Button(
            swipe_card,
            text="Record start/end",
            command=self.record_swipe,
            style="Accent.TButton",
        ).grid(row=2, column=0, padx=8, pady=(3, 6), sticky="ew")

        ttk.Button(
            swipe_card,
            text="Clear swipe",
            command=self.clear_swipe,
        ).grid(row=2, column=1, padx=8, pady=(3, 6), sticky="ew")

        swipe_card.columnconfigure(0, weight=1)
        swipe_card.columnconfigure(1, weight=1)

        ttk.Label(
            swipe_card,
            text="Swipe gestures are optional and trigger after each position cycle.",
            wraplength=420,
        ).grid(row=3, column=0, columnspan=2, padx=8, pady=(0, 6), sticky="w")

    def _create_footer(self) -> None:
        footer = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        footer.pack(fill="x")

        ttk.Label(footer, text="Theme:").grid(row=0, column=0, padx=(0, 6), pady=(0, 6))
        self.theme_selector = ttk.Combobox(
            footer,
            textvariable=self.theme_var,
            values=list(THEMES.keys()),
            state="readonly",
            width=10,
        )
        self.theme_selector.grid(row=0, column=1, pady=(0, 6))
        self.theme_selector.bind("<<ComboboxSelected>>", self.change_theme)

        footer.columnconfigure(2, weight=1)

        self.start_button = ttk.Button(
            footer,
            text="Start",
            command=self.start_clicking,
            style="Accent.TButton",
        )
        self.start_button.grid(row=0, column=2, sticky="e", padx=6)

        self.stop_button = ttk.Button(
            footer,
            text="Stop",
            command=self.stop_clicking,
            state=tk.DISABLED,
        )
        self.stop_button.grid(row=0, column=3, sticky="e")

        self.status_label = ttk.Label(
            footer,
            textvariable=self.status_var,
            style="Status.TLabel",
        )
        self.status_label.grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))

        self.progress = ttk.Progressbar(footer, mode="determinate")
        self.progress.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(8, 0))

        self.progress_label = ttk.Label(footer, textvariable=self.progress_label_var)
        self.progress_label.grid(row=3, column=0, columnspan=4, sticky="w", pady=(4, 0))

    # ------------------------------------------------------------------
    # UI callbacks
    # ------------------------------------------------------------------

    def record_position(self) -> None:
        x, y = map(int, self.mouse.position)
        self.positions.append((x, y))
        self.position_tree.insert("", tk.END, values=(x, y))
        logging.info("Recorded click position: (%s, %s)", x, y)

    def remove_selected_position(self) -> None:
        selection = self.position_tree.selection()
        if not selection:
            return

        for item in selection:
            index = self.position_tree.index(item)
            del self.positions[index]
            self.position_tree.delete(item)
        logging.info("Removed %d stored positions", len(selection))

    def clear_positions(self) -> None:
        if not self.positions:
            return
        self.positions.clear()
        for item in self.position_tree.get_children():
            self.position_tree.delete(item)
        logging.info("Cleared all stored positions")

    def record_swipe(self) -> None:
        x, y = map(int, self.mouse.position)
        if len(self.swipe_positions) == 2:
            self.swipe_positions.clear()
        self.swipe_positions.append((x, y))

        if len(self.swipe_positions) == 1:
            self.swipe_status_var.set(
                f"Swipe start recorded at: {x}, {y}. Move cursor and record again."
            )
        elif len(self.swipe_positions) == 2:
            start, end = self.swipe_positions
            self.swipe_status_var.set(
                f"Swipe from {start[0]}, {start[1]} to {end[0]}, {end[1]}"
            )
        logging.info("Updated swipe positions: %s", self.swipe_positions)

    def clear_swipe(self) -> None:
        self.swipe_positions.clear()
        self.swipe_status_var.set("Swipe: not recorded")
        logging.info("Cleared swipe configuration")

    # ------------------------------------------------------------------
    # Core functionality
    # ------------------------------------------------------------------

    def start_clicking(self) -> None:
        if self.running:
            return

        try:
            settings = self._build_settings()
        except ValueError as exc:
            messagebox.showerror("Invalid configuration", str(exc))
            return

        self.stop_event.clear()
        self.running = True

        self.update_ui_state(True)
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress["value"] = 0
        self.progress_infinite = False
        self._set_status("Status: Running")
        self._update_progress(0, settings.count)

        self.click_thread = Thread(target=self._autoclick_loop, args=(settings,), daemon=True)
        self.click_thread.start()

    def stop_clicking(self) -> None:
        if not self.running:
            return
        self.stop_event.set()
        self._set_status("Status: Stopping…")

    def _finalize_stop(self) -> None:
        if not self.running:
            return

        self.running = False
        self.stop_event.clear()
        self.update_ui_state(False)
        self.progress.stop()
        if not self.progress_infinite:
            self.progress["value"] = 0
        self.progress.configure(mode="determinate")
        self.progress_infinite = False
        self.progress_label_var.set("Progress: Idle")
        self._set_status("Status: Stopped")

    def _autoclick_loop(self, settings: ClickSettings) -> None:
        try:
            if settings.delay > 0 and self.stop_event.wait(settings.delay):
                self.root.after(0, self._finalize_stop)
                return

            positions: Sequence[Tuple[int, int]] = settings.positions

            executed_clicks = 0
            target = settings.count if settings.count > 0 else None

            while not self.stop_event.is_set():
                click_targets: Sequence[Optional[Tuple[int, int]]]
                if positions:
                    click_targets = positions
                else:
                    click_targets = [None]

                for pos in click_targets:
                    if self.stop_event.is_set():
                        break
                    if target is not None and executed_clicks >= target:
                        break

                    if pos is not None:
                        self.mouse.position = pos
                    self._perform_click(settings.button, settings.hold_duration)
                    executed_clicks += 1
                    self.root.after(0, self._update_progress, executed_clicks, settings.count)

                    if target is not None and executed_clicks >= target:
                        break

                    if self.stop_event.wait(settings.interval):
                        break

                if target is not None and executed_clicks >= target:
                    break

                if settings.swipe and not self.stop_event.is_set():
                    self._perform_swipe(settings)

        except Exception as exc:  # pragma: no cover - defensive logging
            logging.exception("Auto clicker encountered an error: %s", exc)
            self.root.after(0, messagebox.showerror, "AutoClicker Error", str(exc))
        finally:
            self.root.after(0, self._finalize_stop)

    def _perform_click(self, button: Button, hold_duration: float) -> None:
        if hold_duration > 0:
            self.mouse.press(button)
            waited = self.stop_event.wait(hold_duration)
            self.mouse.release(button)
            if waited:
                return
        else:
            self.mouse.click(button)

    def _perform_swipe(self, settings: ClickSettings) -> None:
        assert settings.swipe is not None
        start, end = settings.swipe
        self.mouse.position = start
        self.mouse.press(settings.button)
        steps = max(int(settings.swipe_duration / 0.02), 1)
        for step in range(steps):
            if self.stop_event.is_set():
                break
            ratio = (step + 1) / steps
            x = int(start[0] + (end[0] - start[0]) * ratio)
            y = int(start[1] + (end[1] - start[1]) * ratio)
            self.mouse.position = (x, y)
            time.sleep(settings.swipe_duration / steps)
        self.mouse.release(settings.button)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_settings(self) -> ClickSettings:
        interval = float(self.interval_var.get())
        if interval <= 0:
            raise ValueError("Click interval must be greater than zero.")

        delay = float(self.delay_var.get())
        if delay < 0:
            raise ValueError("Initial delay cannot be negative.")

        hold_duration = float(self.hold_var.get())
        if hold_duration < 0:
            raise ValueError("Hold duration cannot be negative.")

        count = int(self.count_var.get())
        if count < 0:
            raise ValueError("Number of clicks cannot be negative.")

        button_name = self.button_var.get().lower()
        button_map = {
            "left": Button.left,
            "right": Button.right,
            "middle": Button.middle,
        }
        try:
            button = button_map[button_name]
        except KeyError as exc:
            raise ValueError(f"Unsupported button selection: {self.button_var.get()}") from exc

        swipe_duration = float(self.swipe_duration_var.get())
        if swipe_duration <= 0:
            raise ValueError("Swipe duration must be greater than zero.")

        swipe: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None
        if len(self.swipe_positions) == 2:
            swipe = (self.swipe_positions[0], self.swipe_positions[1])

        return ClickSettings(
            interval=interval,
            count=count,
            button=button,
            delay=delay,
            hold_duration=hold_duration,
            positions=tuple(self.positions),
            swipe=swipe,
            swipe_duration=swipe_duration,
        )

    def _update_progress(self, clicks: int, count: int) -> None:
        if count == 0:
            if not self.progress_infinite:
                self.progress.configure(mode="indeterminate")
                self.progress.start(10)
                self.progress_infinite = True
            self.progress_label_var.set(f"Progress: {clicks} clicks")
            return

        if self.progress_infinite:
            self.progress.stop()
            self.progress_infinite = False
            self.progress.configure(mode="determinate")

        self.progress.configure(maximum=max(count, 1))
        self.progress["value"] = clicks
        self.progress_label_var.set(f"Progress: {clicks}/{count}")

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def change_theme(self, event: Optional[tk.Event] = None) -> None:  # noqa: ARG002
        self.apply_theme(self.theme_var.get())

    def apply_theme(self, theme_name: str) -> None:
        palette = THEMES.get(theme_name, THEMES["Dark"])
        bg = palette["background"]
        fg = palette["foreground"]
        accent = palette["accent"]
        accent_hover = palette["accent_hover"]

        self.root.configure(bg=bg)

        style = ttk.Style()
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TLabelFrame", background=bg, foreground=fg)
        style.configure("TLabelframe.Label", background=bg, foreground=fg)
        style.configure("TNotebook", background=bg)
        style.configure("TNotebook.Tab", background=bg, foreground=fg)
        style.map(
            "TNotebook.Tab",
            background=[("selected", accent)],
            foreground=[("selected", bg)],
        )
        style.configure("Status.TLabel", background=bg, foreground=accent)
        style.configure(
            "Accent.TButton",
            background=accent,
            foreground=bg,
            padding=(12, 6),
        )
        style.map(
            "Accent.TButton",
            background=[("active", accent_hover), ("disabled", "#767676")],
            foreground=[("disabled", "#d9d9d9")],
        )

        # Ensure regular buttons and combobox entries harmonize with the theme.
        style.configure("TButton", padding=(12, 6))
        style.configure("TCombobox", fieldbackground=bg, foreground=fg)
        style.map("TCombobox", fieldbackground=[("readonly", bg)])

    def update_ui_state(self, running: bool) -> None:
        self.start_button.config(state=tk.DISABLED if running else tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL if running else tk.DISABLED)
        self.notebook.configure(state=tk.DISABLED if running else tk.NORMAL)
        if running:
            self.theme_selector.config(state="disabled")
        else:
            self.theme_selector.config(state="readonly")

    # ------------------------------------------------------------------
    # Keyboard hooks & teardown
    # ------------------------------------------------------------------

    def _on_key_press(self, key: Key) -> None:
        try:
            if key == HOTKEY_CHOICES[self.start_hotkey_var.get()] and not self.running:
                self.root.after(0, self.start_clicking)
            elif key == HOTKEY_CHOICES[self.stop_hotkey_var.get()] and self.running:
                self.root.after(0, self.stop_clicking)
        except KeyError:
            logging.debug("Pressed key %s is not mapped to a hotkey", key)

    def _on_close(self) -> None:
        if self.running:
            self.stop_clicking()
            if self.click_thread and self.click_thread.is_alive():
                self.click_thread.join(timeout=1.0)
        if self.keyboard_listener.running:
            self.keyboard_listener.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedAutoclicker(root)
    root.mainloop()
