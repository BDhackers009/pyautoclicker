import tkinter as tk
from tkinter import ttk, messagebox
from pynput.mouse import Controller, Button
from pynput.keyboard import Listener, Key, KeyCode
from threading import Thread, Event
import time

class AdvancedAutoclicker:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced AutoClicker")
        self.root.geometry("400x400")
        self.mouse = Controller()
        self.click_thread = None
        self.stop_event = Event()
        self.running = False
        self.positions = []  # List for multiple click positions
        self.swipe_positions = []  # Start and end positions for swipe
        self.theme_var = tk.StringVar(value="Dark")  # Default theme

        self.create_widgets()
        self.apply_theme("Dark")

    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.basic_tab = ttk.Frame(self.notebook)
        self.advanced_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.basic_tab, text="Basic")
        self.notebook.add(self.advanced_tab, text="Advanced")
        self.notebook.pack(expand=True, fill="both")

        self.create_basic_tab()
        self.create_advanced_tab()

        # Theme Selection
        ttk.Label(self.root, text="Theme:").pack(pady=5)
        self.theme_selector = ttk.Combobox(self.root, textvariable=self.theme_var, values=["Dark", "Light", "Hacker"])
        self.theme_selector.pack()
        self.theme_selector.bind("<<ComboboxSelected>>", self.change_theme)

        # Control Buttons
        self.start_button = ttk.Button(self.root, text="Start", command=self.start_clicking)
        self.start_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.stop_button = ttk.Button(self.root, text="Stop", command=self.stop_clicking, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=10, pady=10)

        # Status Label
        self.status_label = ttk.Label(self.root, text="Status: Stopped", foreground="red")
        self.status_label.pack(side=tk.BOTTOM, pady=5)

    def create_basic_tab(self):
        ttk.Label(self.basic_tab, text="Click Interval (seconds):").grid(row=0, column=0, padx=10, pady=5)
        self.interval_entry = ttk.Entry(self.basic_tab)
        self.interval_entry.grid(row=0, column=1, padx=10, pady=5)
        self.interval_entry.insert(0, "0.5")

        ttk.Label(self.basic_tab, text="Mouse Button:").grid(row=1, column=0, padx=10, pady=5)
        self.button_var = tk.StringVar()
        self.button_selector = ttk.Combobox(self.basic_tab, textvariable=self.button_var, values=["Left", "Right"])
        self.button_selector.grid(row=1, column=1, padx=10, pady=5)
        self.button_selector.current(0)

        ttk.Label(self.basic_tab, text="Number of Clicks (0=infinite):").grid(row=2, column=0, padx=10, pady=5)
        self.count_entry = ttk.Entry(self.basic_tab)
        self.count_entry.grid(row=2, column=1, padx=10, pady=5)
        self.count_entry.insert(0, "0")

    def create_advanced_tab(self):
        ttk.Label(self.advanced_tab, text="Click Positions (x,y):").grid(row=0, column=0, padx=10, pady=5)
        self.position_listbox = tk.Listbox(self.advanced_tab, height=5)
        self.position_listbox.grid(row=0, column=1, padx=10, pady=5)

        ttk.Button(self.advanced_tab, text="Add Position", command=self.record_position).grid(row=0, column=2, padx=5)

        ttk.Label(self.advanced_tab, text="Swipe (Start-End):").grid(row=1, column=0, padx=10, pady=5)
        self.swipe_entry = ttk.Entry(self.advanced_tab)
        self.swipe_entry.grid(row=1, column=1, padx=10, pady=5)

        ttk.Button(self.advanced_tab, text="Record Swipe", command=self.record_swipe).grid(row=1, column=2, padx=5)

    def record_position(self):
        x, y = self.mouse.position
        self.positions.append((x, y))
        self.position_listbox.insert(tk.END, f"{x},{y}")

    def record_swipe(self):
        if len(self.swipe_positions) < 2:
            x, y = self.mouse.position
            self.swipe_positions.append((x, y))
            self.swipe_entry.insert(tk.END, f"{x},{y} ")

    def start_clicking(self):
        if self.running:
            return

        try:
            interval = float(self.interval_entry.get())
            count = int(self.count_entry.get())
            button = Button.left if self.button_var.get() == "Left" else Button.right
        except ValueError:
            messagebox.showerror("Error", "Invalid input values")
            return

        self.stop_event.clear()
        self.running = True
        self.update_ui_state(True)

        self.click_thread = Thread(target=self.autoclick_loop, args=(interval, count, button))
        self.click_thread.start()

    def autoclick_loop(self, interval, count, button):
        clicks = 0

        while not self.stop_event.is_set() and (count == 0 or clicks < count):
            for pos in self.positions:
                if self.stop_event.is_set():
                    return

                self.mouse.position = pos
                self.mouse.click(button)
                clicks += 1
                self.root.after(int(interval * 1000))  # Use after() for responsiveness

            time.sleep(interval)

        self.stop_clicking()

    def stop_clicking(self):
        self.running = False
        self.stop_event.set()
        self.update_ui_state(False)

    def change_theme(self, event=None):
        theme = self.theme_var.get()
        self.apply_theme(theme)

    def apply_theme(self, theme):
        if theme == "Dark":
            self.root.configure(bg="#333")
            self.status_label.configure(fg="white")
        elif theme == "Light":
            self.root.configure(bg="white")
            self.status_label.configure(fg="black")
        elif theme == "Hacker":
            self.root.configure(bg="black")
            self.status_label.configure(fg="lime")

    def update_ui_state(self, running):
        state = tk.NORMAL if not running else tk.DISABLED
        self.start_button.config(state=state)
        self.stop_button.config(state=tk.NORMAL if running else tk.DISABLED)
        self.status_label.config(
            text=f"Status: {'Running' if running else 'Stopped'}",
            foreground="green" if running else "red"
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedAutoclicker(root)
    root.mainloop()
