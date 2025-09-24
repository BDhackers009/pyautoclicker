

    interval: float
    count: int
    button: Button


    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Advanced AutoClicker")

        self.notebook.add(self.advanced_tab, text="Advanced")

        self._create_basic_tab()
        self._create_advanced_tab()
        self._create_footer()


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
