"""Enhanced Tkinter-based autoclicker with advanced controls and UI."""
from __future__ import annotations

import contextlib
import tkinter as tk
from dataclasses import dataclass
from threading import Event, Thread
from typing import Callable, Iterable, List, Optional, Sequence, Set, Tuple

from tkinter import messagebox, ttk
from pynput.keyboard import Key, Listener
from pynput.mouse import Button, Controller

Position = Tuple[int, int]


THEMES = {
    "Windows Light": {
        "bg": "#f3f3f3",
        "fg": "#1b1b1b",
        "accent": "#0b6cfb",
        "accent_active": "#0a5ecf",
        "accent_hover": "#0d78ff",
        "button_fg": "#ffffff",
        "disabled_fg": "#8b8b8b",
        "tab_bg": "#e5e5e5",
        "tab_fg": "#1b1b1b",
        "selected_tab_fg": "#ffffff",
        "tree_bg": "#ffffff",
        "tree_alt_bg": "#f6f6f6",
        "tree_selected_fg": "#1b1b1b",
        "detail_fg": "#4f4f4f",
        "outline": "#c8c8c8",
        "input_bg": "#ffffff",
        "input_fg": "#1b1b1b",
        "control_bg": "#ffffff",
        "control_active_bg": "#e0efff",
        "selection": "#cfe5ff",
        "progress_trough": "#dfdfdf",
        "progress_fill": "#0b6cfb",
    },
    "Dark": {
        "bg": "#202124",
        "fg": "#f5f5f5",
        "accent": "#0b57d0",
        "accent_active": "#0844a4",
        "accent_hover": "#0c63eb",
        "button_fg": "#ffffff",
        "disabled_fg": "#6b7280",
        "tab_bg": "#2d2f33",
        "tab_fg": "#d1d5db",
        "selected_tab_fg": "#ffffff",
        "tree_bg": "#1f2124",
        "tree_alt_bg": "#232529",
        "tree_selected_fg": "#f5f5f5",
        "detail_fg": "#d1d5db",
        "outline": "#383b40",
        "input_bg": "#2a2c30",
        "input_fg": "#f5f5f5",
        "control_bg": "#2a2c30",
        "control_active_bg": "#1f3a5f",
        "selection": "#1d4ed8",
        "progress_trough": "#1a1c1f",
        "progress_fill": "#0b57d0",
    },
    "Hacker": {
        "bg": "#040a03",
        "fg": "#d9f99d",
        "accent": "#22c55e",
        "accent_active": "#16a34a",
        "accent_hover": "#38d876",
        "button_fg": "#041104",
        "disabled_fg": "#4d7c53",
        "tab_bg": "#06200a",
        "tab_fg": "#bbf7d0",
        "selected_tab_fg": "#041104",
        "tree_bg": "#071406",
        "tree_alt_bg": "#041004",
        "tree_selected_fg": "#d9f99d",
        "detail_fg": "#a7f3d0",
        "outline": "#14532d",
        "input_bg": "#041707",
        "input_fg": "#d9f99d",
        "control_bg": "#05210a",
        "control_active_bg": "#0f3d18",
        "selection": "#14532d",
        "progress_trough": "#041205",
        "progress_fill": "#22c55e",
    },
}


@dataclass
class AutoClickerConfig:
    """Configuration for a single autoclicker run."""

    interval: float
    count: int
    button: Button
    swipe_path: Optional[Tuple[Position, Position]] = None
    swipe_duration: float = 0.0
    swipe_steps: int = 0


class AutoClickerEngine:
    """Performs click automation on a background thread."""

    def __init__(self, mouse: Controller) -> None:
        self.mouse = mouse

    def run(
        self,
        config: AutoClickerConfig,
        positions: Sequence[Position],
        stop_event: Event,
        progress_callback: Callable[[int, Position], None],
    ) -> int:
        clicks_completed = 0
        targets: List[Position] = list(positions) or [self._safe_position()]

        while not stop_event.is_set() and (config.count == 0 or clicks_completed < config.count):
            for target in targets:
                if stop_event.is_set() or (config.count and clicks_completed >= config.count):
                    break

                self.mouse.position = target
                self.mouse.click(config.button)
                clicks_completed += 1
                progress_callback(clicks_completed, target)

                if config.swipe_path:
                    self._perform_swipe(config, stop_event)

                if config.count and clicks_completed >= config.count:
                    break

                if stop_event.wait(config.interval):
                    break
            else:
                continue
            break

        return clicks_completed

    def _perform_swipe(self, config: AutoClickerConfig, stop_event: Event) -> None:
        if not config.swipe_path:
            return

        start, end = config.swipe_path
        steps = max(2, config.swipe_steps)
        duration = max(0.0, config.swipe_duration)
        sleep_time = duration / steps if steps else 0.0

        self.mouse.position = start
        self.mouse.press(Button.left)

        for step in range(1, steps + 1):
            if stop_event.is_set():
                break

            x = int(round(start[0] + (end[0] - start[0]) * (step / steps)))
            y = int(round(start[1] + (end[1] - start[1]) * (step / steps)))
            self.mouse.position = (x, y)

            if sleep_time and stop_event.wait(sleep_time):
                break

        self.mouse.release(Button.left)

    def _safe_position(self) -> Position:
        try:
            x, y = self.mouse.position
            return int(x), int(y)
        except Exception:
            return 0, 0


class AdvancedAutoclicker:
    """Main application window and controller."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Advanced AutoClicker")
        self.root.geometry("540x640")
        self.root.minsize(520, 620)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.option_add("*Font", "Segoe UI 10")

        self.mouse = Controller()
        self.engine = AutoClickerEngine(self.mouse)

        self.stop_event = Event()
        self.click_thread: Optional[Thread] = None
        self.running = False
        self._stop_requested = False
        self._pressed_keys: Set[Key] = set()
        self.listener: Optional[Listener] = None

        self.positions: List[Position] = []
        self.swipe_start: Optional[Position] = None
        self.swipe_end: Optional[Position] = None

        self.total_clicks = 0
        self.active_config: Optional[AutoClickerConfig] = None
        self._current_theme = THEMES["Windows Light"]

        self.style = ttk.Style(self.root)
        for base_theme in ("vista", "xpnative", "clam", "default"):
            try:
                self.style.theme_use(base_theme)
                break
            except tk.TclError:
                continue

        self.theme_var = tk.StringVar(value="Windows Light")
        self.interval_var = tk.DoubleVar(value=0.5)
        self.count_var = tk.IntVar(value=0)
        self.button_var = tk.StringVar(value="Left")
        self.use_swipe_var = tk.BooleanVar(value=False)
        self.swipe_duration_var = tk.DoubleVar(value=0.35)
        self.swipe_steps_var = tk.IntVar(value=18)

        self.status_var = tk.StringVar(value="Status: Idle")
        self.detail_var = tk.StringVar(value="Ready to start clicking.")
        self.hotkey_var = tk.StringVar(
            value="Shortcuts: F6 start/stop, F7 stop, F8 add position."
        )

        self.create_widgets()
        self.apply_theme("Windows Light")
        self._start_keyboard_listener()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def create_widgets(self) -> None:
        self.container = ttk.Frame(self.root, padding=20, style="Background.TFrame")
        self.container.pack(fill="both", expand=True)

        options_frame = ttk.Frame(self.container, style="Background.TFrame")
        options_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(options_frame, text="Theme:").pack(side=tk.LEFT)
        self.theme_selector = ttk.Combobox(
            options_frame,
            textvariable=self.theme_var,
            values=list(THEMES.keys()),
            state="readonly",
            width=12,
        )
        self.theme_selector.pack(side=tk.LEFT, padx=(8, 0))
        self.theme_selector.bind("<<ComboboxSelected>>", self.change_theme)

        self.notebook = ttk.Notebook(self.container)
        self.notebook.pack(fill="both", expand=True)

        self.basic_tab = ttk.Frame(self.notebook, padding=12, style="Background.TFrame")
        self.advanced_tab = ttk.Frame(self.notebook, padding=12, style="Background.TFrame")
        self.notebook.add(self.basic_tab, text="Basic")
        self.notebook.add(self.advanced_tab, text="Advanced")

        self.create_basic_tab()
        self.create_advanced_tab()

        button_frame = ttk.Frame(self.container, padding=(0, 12, 0, 0), style="Background.TFrame")
        button_frame.pack(fill="x")
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        self.start_button = ttk.Button(
            button_frame, text="Start (F6)", command=self.start_clicking, style="Accent.TButton"
        )
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.stop_button = ttk.Button(
            button_frame,
            text="Stop (F7)",
            command=self.stop_clicking,
            state=tk.DISABLED,
            style="Accent.TButton",
        )
        self.stop_button.grid(row=0, column=1, sticky="ew")

        status_frame = ttk.Frame(self.container, padding=(0, 12, 0, 0), style="Background.TFrame")
        status_frame.pack(fill="x")

        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.pack(anchor="w")

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=1)
        self.progress.pack(fill="x", pady=(6, 6))

        self.detail_label = ttk.Label(status_frame, textvariable=self.detail_var, style="Detail.TLabel")
        self.detail_label.pack(anchor="w")

        self.shortcut_label = ttk.Label(status_frame, textvariable=self.hotkey_var, style="Detail.TLabel")
        self.shortcut_label.pack(anchor="w", pady=(6, 0))

    def create_basic_tab(self) -> None:
        self.basic_tab.columnconfigure(1, weight=1)

        ttk.Label(self.basic_tab, text="Click interval (seconds):").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 10)
        )
        self.interval_spin = ttk.Spinbox(
            self.basic_tab,
            from_=0.01,
            to=60.0,
            increment=0.05,
            textvariable=self.interval_var,
            format="%.2f",
            width=12,
        )
        self.interval_spin.grid(row=0, column=1, sticky="ew", pady=(0, 10))

        ttk.Label(self.basic_tab, text="Mouse button:").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(0, 10)
        )
        self.button_selector = ttk.Combobox(
            self.basic_tab,
            textvariable=self.button_var,
            values=["Left", "Right"],
            state="readonly",
            width=12,
        )
        self.button_selector.grid(row=1, column=1, sticky="ew", pady=(0, 10))

        ttk.Label(self.basic_tab, text="Number of clicks (0 = infinite):").grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=(0, 10)
        )
        self.count_spin = ttk.Spinbox(
            self.basic_tab,
            from_=0,
            to=100000,
            increment=10,
            textvariable=self.count_var,
            width=12,
        )
        self.count_spin.grid(row=2, column=1, sticky="ew", pady=(0, 10))

        ttk.Label(
            self.basic_tab,
            text="When no positions are recorded the current cursor location is used.",
            wraplength=360,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def create_advanced_tab(self) -> None:
        self.advanced_tab.columnconfigure(0, weight=1)

        ttk.Label(self.advanced_tab, text="Recorded click positions:").grid(
            row=0, column=0, sticky="w"
        )

        tree_frame = ttk.Frame(self.advanced_tab, style="Background.TFrame")
        tree_frame.grid(row=1, column=0, sticky="nsew", pady=(4, 6))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.position_tree = ttk.Treeview(
            tree_frame,
            columns=("index", "x", "y"),
            show="headings",
            height=6,
            selectmode="extended",
        )
        self.position_tree.heading("index", text="#")
        self.position_tree.heading("x", text="X")
        self.position_tree.heading("y", text="Y")
        self.position_tree.column("index", width=40, anchor="center")
        self.position_tree.column("x", width=80, anchor="center")
        self.position_tree.column("y", width=80, anchor="center")
        self.position_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.position_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.position_tree.configure(yscrollcommand=scrollbar.set)
        self.position_tree.bind("<Double-1>", lambda _event: self.remove_selected_position())
        self.position_tree.bind("<Delete>", lambda _event: self.remove_selected_position())

        self.positions_count_var = tk.StringVar(value="No positions recorded.")
        ttk.Label(self.advanced_tab, textvariable=self.positions_count_var).grid(
            row=2, column=0, sticky="w", pady=(0, 6)
        )

        position_buttons = ttk.Frame(self.advanced_tab, style="Background.TFrame")
        position_buttons.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        for col in range(3):
            position_buttons.columnconfigure(col, weight=1)

        self.add_position_button = ttk.Button(
            position_buttons, text="Add current (F8)", command=self.record_position
        )
        self.add_position_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.remove_position_button = ttk.Button(
            position_buttons, text="Remove selected", command=self.remove_selected_position
        )
        self.remove_position_button.grid(row=0, column=1, sticky="ew", padx=3)

        self.clear_position_button = ttk.Button(
            position_buttons, text="Clear all", command=self.clear_positions
        )
        self.clear_position_button.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        swipe_frame = ttk.LabelFrame(self.advanced_tab, text="Swipe automation", padding=12)
        swipe_frame.grid(row=4, column=0, sticky="ew")
        swipe_frame.columnconfigure(0, weight=1)

        self.swipe_toggle = ttk.Checkbutton(
            swipe_frame,
            text="Perform swipe after each click",
            variable=self.use_swipe_var,
            command=self.toggle_swipe_controls,
        )
        self.swipe_toggle.grid(row=0, column=0, columnspan=3, sticky="w")

        self.swipe_label_var = tk.StringVar(value="Start and end points not set.")
        ttk.Label(swipe_frame, textvariable=self.swipe_label_var).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(6, 8)
        )

        self.swipe_start_button = ttk.Button(
            swipe_frame, text="Record start", command=lambda: self.record_swipe_point("start")
        )
        self.swipe_start_button.grid(row=2, column=0, sticky="ew", pady=(0, 6), padx=(0, 6))

        self.swipe_end_button = ttk.Button(
            swipe_frame, text="Record end", command=lambda: self.record_swipe_point("end")
        )
        self.swipe_end_button.grid(row=2, column=1, sticky="ew", pady=(0, 6), padx=3)

        self.swipe_clear_button = ttk.Button(
            swipe_frame, text="Clear swipe", command=self.clear_swipe
        )
        self.swipe_clear_button.grid(row=2, column=2, sticky="ew", pady=(0, 6), padx=(6, 0))

        ttk.Label(swipe_frame, text="Duration (s):").grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.swipe_duration_entry = ttk.Entry(
            swipe_frame, textvariable=self.swipe_duration_var, width=8
        )
        self.swipe_duration_entry.grid(row=3, column=1, sticky="w", pady=(6, 0))

        ttk.Label(swipe_frame, text="Steps:").grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.swipe_steps_spin = ttk.Spinbox(
            swipe_frame, from_=2, to=200, increment=1, textvariable=self.swipe_steps_var, width=8
        )
        self.swipe_steps_spin.grid(row=4, column=1, sticky="w", pady=(6, 0))

        ttk.Label(
            self.advanced_tab,
            text="Tip: Use Delete or double-click to remove positions.",
        ).grid(row=5, column=0, sticky="w", pady=(12, 0))

        self.toggle_swipe_controls()

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------
    def record_position(self) -> None:
        position = self._current_mouse_position()
        self.positions.append(position)
        self.refresh_positions_tree()
        self.detail_var.set(f"Added position {position}.")

    def remove_selected_position(self) -> None:
        selection = self.position_tree.selection()
        if not selection:
            return

        indices = sorted((int(item) for item in selection if item.isdigit()), reverse=True)
        for index in indices:
            if 0 <= index < len(self.positions):
                self.positions.pop(index)
        self.refresh_positions_tree()
        self.detail_var.set("Selected positions removed.")

    def clear_positions(self) -> None:
        self.positions.clear()
        self.refresh_positions_tree()
        self.detail_var.set("All positions cleared.")

    def refresh_positions_tree(self) -> None:
        for item in self.position_tree.get_children():
            self.position_tree.delete(item)

        for idx, (x, y) in enumerate(self.positions):
            tag = "even" if idx % 2 == 0 else "odd"
            self.position_tree.insert("", tk.END, iid=str(idx), values=(idx + 1, x, y), tags=(tag,))

        count = len(self.positions)
        if count == 0:
            self.positions_count_var.set("No positions recorded.")
        elif count == 1:
            self.positions_count_var.set("1 position recorded.")
        else:
            self.positions_count_var.set(f"{count} positions recorded.")

    # ------------------------------------------------------------------
    # Swipe management
    # ------------------------------------------------------------------
    def record_swipe_point(self, which: str) -> None:
        position = self._current_mouse_position()
        if which == "start":
            self.swipe_start = position
        else:
            self.swipe_end = position
        self.update_swipe_label()

    def clear_swipe(self) -> None:
        self.swipe_start = None
        self.swipe_end = None
        self.update_swipe_label()

    def update_swipe_label(self) -> None:
        if self.swipe_start and self.swipe_end:
            self.swipe_label_var.set(
                f"Swipe from {self.swipe_start} to {self.swipe_end}."
            )
        elif self.swipe_start:
            self.swipe_label_var.set(f"Swipe start recorded at {self.swipe_start}.")
        elif self.swipe_end:
            self.swipe_label_var.set(f"Swipe end recorded at {self.swipe_end}.")
        else:
            self.swipe_label_var.set("Start and end points not set.")

    def toggle_swipe_controls(self) -> None:
        enabled = self.use_swipe_var.get() and not self.running
        state = tk.NORMAL if enabled else tk.DISABLED
        for widget in (
            self.swipe_start_button,
            self.swipe_end_button,
            self.swipe_clear_button,
            self.swipe_duration_entry,
            self.swipe_steps_spin,
        ):
            widget.configure(state=state)

    # ------------------------------------------------------------------
    # Autoclicker runtime logic
    # ------------------------------------------------------------------
    def start_clicking(self) -> None:
        if self.running:
            return

        try:
            config = self.build_config()
        except ValueError as exc:
            messagebox.showerror("Invalid configuration", str(exc))
            return

        self.stop_event.clear()
        self._stop_requested = False
        self.running = True
        self.total_clicks = 0
        self.active_config = config

        self.update_ui_state(True)
        self.update_status("Status: Running", "#16a34a")
        self.detail_var.set("Click automation started.")

        if config.count > 0:
            self.progress.configure(mode="determinate", maximum=config.count)
            self.progress_var.set(0)
        else:
            self.progress.configure(mode="indeterminate")
            self.progress.start(8)

        self.click_thread = Thread(target=self._click_worker, args=(config,), daemon=True)
        self.click_thread.start()

    def build_config(self) -> AutoClickerConfig:
        interval = self.interval_var.get()
        if interval <= 0:
            raise ValueError("Interval must be greater than zero.")

        count = self.count_var.get()
        if count < 0:
            raise ValueError("Number of clicks cannot be negative.")

        button = Button.left if self.button_var.get() == "Left" else Button.right

        swipe_path: Optional[Tuple[Position, Position]] = None
        if self.use_swipe_var.get():
            if not (self.swipe_start and self.swipe_end):
                raise ValueError("Record both swipe start and end points or disable swipe.")
            swipe_path = (self.swipe_start, self.swipe_end)

        swipe_duration = max(0.0, self.swipe_duration_var.get())
        swipe_steps = max(2, self.swipe_steps_var.get())

        return AutoClickerConfig(
            interval=interval,
            count=count,
            button=button,
            swipe_path=swipe_path,
            swipe_duration=swipe_duration,
            swipe_steps=swipe_steps,
        )

    def _click_worker(self, config: AutoClickerConfig) -> None:
        try:
            positions: Iterable[Position] = list(self.positions)
            self.engine.run(
                config,
                positions,
                self.stop_event,
                lambda clicks, pos: self.root.after(0, self.on_click_progress, clicks, pos),
            )
        except Exception as exc:  # pylint: disable=broad-except
            self.root.after(0, self._handle_worker_exception, exc)
        finally:
            self.root.after(0, self._on_worker_complete)

    def on_click_progress(self, clicks: int, position: Position) -> None:
        self.total_clicks = clicks
        self.detail_var.set(f"Clicks performed: {clicks} (last at {position}).")
        if self.active_config and self.active_config.count > 0:
            self.progress_var.set(clicks)

    def stop_clicking(self) -> None:
        if not self.running:
            return

        self._stop_requested = True
        self.update_status("Status: Stopping...", "#f59e0b")
        self.stop_event.set()

    def _on_worker_complete(self) -> None:
        if not self.running:
            return

        if self.active_config and self.active_config.count == 0:
            self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress_var.set(0)

        status_text = "Status: Completed" if not self._stop_requested else "Status: Stopped"
        color = "#2563eb" if not self._stop_requested else "#dc2626"
        self.update_status(status_text, color)

        if self._stop_requested:
            self.detail_var.set("Automation stopped by user.")
        else:
            self.detail_var.set(f"Automation finished after {self.total_clicks} click(s).")

        self.running = False
        self.active_config = None
        self.update_ui_state(False)
        self.stop_event.clear()
        self._stop_requested = False

    def _handle_worker_exception(self, exc: Exception) -> None:
        self.update_status("Status: Error", "#dc2626")
        self.detail_var.set("Automation stopped due to an error.")
        messagebox.showerror("AutoClicker error", str(exc))

    def update_ui_state(self, running: bool) -> None:
        start_state = tk.DISABLED if running else tk.NORMAL
        stop_state = tk.NORMAL if running else tk.DISABLED
        self.start_button.configure(state=start_state)
        self.stop_button.configure(state=stop_state)
        self.theme_selector.configure(state="disabled" if running else "readonly")
        self.position_tree.configure(selectmode="none" if running else "extended")

        tab_state = "disabled" if running else "normal"
        for tab_id in self.notebook.tabs():
            with contextlib.suppress(tk.TclError):
                self.notebook.tab(tab_id, state=tab_state)

        position_state = tk.DISABLED if running else tk.NORMAL
        for widget in (
            self.add_position_button,
            self.remove_position_button,
            self.clear_position_button,
        ):
            widget.configure(state=position_state)

        self.swipe_toggle.configure(state=position_state)
        self.toggle_swipe_controls()

    def update_status(self, text: str, color: Optional[str] = None) -> None:
        self.status_var.set(text)
        if color:
            self.status_label.configure(foreground=color)

    # ------------------------------------------------------------------
    # Theme management
    # ------------------------------------------------------------------
    def change_theme(self, _event: Optional[tk.Event] = None) -> None:  # type: ignore[override]
        self.apply_theme(self.theme_var.get())

    def apply_theme(self, theme_name: str) -> None:
        colors = THEMES.get(theme_name, THEMES["Windows Light"])
        self._current_theme = colors

        bg = colors["bg"]
        fg = colors["fg"]
        accent = colors["accent"]
        accent_active = colors.get("accent_active", accent)
        accent_hover = colors.get("accent_hover", accent_active)
        button_fg = colors["button_fg"]
        disabled_fg = colors["disabled_fg"]
        tab_bg = colors["tab_bg"]
        tab_fg = colors["tab_fg"]
        selected_tab_fg = colors["selected_tab_fg"]
        detail_fg = colors["detail_fg"]
        tree_bg = colors["tree_bg"]
        tree_alt_bg = colors["tree_alt_bg"]
        tree_selected_fg = colors.get("tree_selected_fg", button_fg)
        outline = colors.get("outline", tab_bg)
        input_bg = colors.get("input_bg", tree_bg)
        input_fg = colors.get("input_fg", fg)
        control_bg = colors.get("control_bg", input_bg)
        control_active_bg = colors.get("control_active_bg", accent)
        selection = colors.get("selection", accent)
        progress_trough = colors.get("progress_trough", bg)
        progress_fill = colors.get("progress_fill", accent)

        self.root.configure(bg=bg)
        for widget in (
            self.container,
            self.basic_tab,
            self.advanced_tab,
        ):
            widget.configure(style="Background.TFrame")

        self.style.configure("Background.TFrame", background=bg)
        self.style.configure("TFrame", background=bg)
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure(
            "Status.TLabel",
            background=bg,
            foreground=fg,
            font=("Segoe UI", 12, "bold"),
        )
        self.style.configure(
            "Detail.TLabel",
            background=bg,
            foreground=detail_fg,
            font=("Segoe UI", 9),
        )
        self.style.configure("TCheckbutton", background=bg, foreground=fg)
        self.style.configure("TLabelframe", background=bg, foreground=fg, borderwidth=1)
        self.style.configure("TLabelframe.Label", background=bg, foreground=fg)

        self.style.configure(
            "TNotebook",
            background=bg,
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )
        self.style.configure(
            "TNotebook.Tab",
            background=tab_bg,
            foreground=tab_fg,
            padding=(12, 6),
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", accent), ("active", control_bg)],
            foreground=[("selected", selected_tab_fg), ("disabled", disabled_fg)],
        )

        self.style.configure(
            "TButton",
            background=control_bg,
            foreground=fg,
            padding=(8, 6),
            borderwidth=1,
            relief="flat",
        )
        self.style.map(
            "TButton",
            background=[
                ("disabled", outline),
                ("pressed", control_active_bg),
                ("active", control_active_bg),
            ],
            foreground=[("disabled", disabled_fg)],
        )

        self.style.configure(
            "Accent.TButton",
            background=accent,
            foreground=button_fg,
            padding=(10, 6),
            borderwidth=0,
        )
        self.style.map(
            "Accent.TButton",
            background=[
                ("disabled", outline),
                ("pressed", accent_active),
                ("active", accent_hover),
            ],
            foreground=[("disabled", disabled_fg)],
        )

        for element in ("TEntry", "TCombobox", "TSpinbox"):
            self.style.configure(
                element,
                foreground=input_fg,
                fieldbackground=input_bg,
                background=input_bg,
            )
            self.style.map(
                element,
                fieldbackground=[("disabled", bg), ("readonly", bg)],
                foreground=[("disabled", disabled_fg)],
            )

        self.style.configure(
            "Treeview",
            background=tree_bg,
            fieldbackground=tree_bg,
            foreground=fg,
            borderwidth=0,
            rowheight=26,
        )
        self.style.configure(
            "Treeview.Heading",
            background=tab_bg,
            foreground=tab_fg,
        )
        self.style.map(
            "Treeview",
            background=[("selected", selection)],
            foreground=[("selected", tree_selected_fg)],
        )

        self.style.configure(
            "Horizontal.TProgressbar",
            background=progress_fill,
            troughcolor=progress_trough,
            borderwidth=0,
            lightcolor=progress_fill,
            darkcolor=progress_fill,
        )
        self.progress.configure(style="Horizontal.TProgressbar")

        self.position_tree.tag_configure("even", background=tree_bg)
        self.position_tree.tag_configure("odd", background=tree_alt_bg)
        self.refresh_positions_tree()

        self.update_status(self.status_var.get())
        if not self.running:
            self.status_label.configure(foreground=fg)

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------
    def _start_keyboard_listener(self) -> None:
        try:
            self.listener = Listener(
                on_press=self.on_key_press,
                on_release=self.on_key_release,
                suppress=False,
            )
            self.listener.start()
        except Exception:  # pylint: disable=broad-except
            self.listener = None
            self.hotkey_var.set("Shortcuts unavailable (listener could not start).")

    def on_key_press(self, key: Key) -> None:
        if key in self._pressed_keys:
            return
        self._pressed_keys.add(key)

        if key == Key.f6:
            self.root.after(0, self.toggle_start_stop)
        elif key == Key.f7:
            self.root.after(0, self.stop_clicking)
        elif key == Key.f8:
            self.root.after(0, self.record_position)

    def on_key_release(self, key: Key) -> None:
        with contextlib.suppress(KeyError):
            self._pressed_keys.remove(key)

    def toggle_start_stop(self) -> None:
        if self.running:
            self.stop_clicking()
        else:
            self.start_clicking()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _current_mouse_position(self) -> Position:
        try:
            x, y = self.mouse.position
            return int(round(x)), int(round(y))
        except Exception:
            return 0, 0

    def on_close(self) -> None:
        self.stop_event.set()
        if self.listener:
            with contextlib.suppress(RuntimeError):
                self.listener.stop()
        if self.click_thread and self.click_thread.is_alive():
            self.click_thread.join(timeout=0.5)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedAutoclicker(root)
    root.mainloop()
