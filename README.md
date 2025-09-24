# pyautoclicker

An advanced, theme-aware desktop auto clicker with a modern Tkinter interface.

## Features

- **Quick setup panel** – configure click interval, initial delay, hold duration and mouse button in seconds.
- **Progress-aware execution** – see live progress for finite runs or an indeterminate indicator for infinite clicking.
- **Global hotkeys** – start and stop from anywhere using configurable function-key shortcuts.
- **Position playlists** – record, manage and remove exact screen coordinates to replay complex click paths.
- **Optional swipe gestures** – capture start and end points for drag-based automation with configurable duration.
- **Polished theming** – switch instantly between Dark, Light and Hacker themes with accent styling.

## Requirements

- Python 3.9 or newer.
- [`pynput`](https://pypi.org/project/pynput/) (install with `pip install pynput`).

## Usage

```bash
python pyautoclicker.py
```

1. Configure the **Quick Setup** tab with the desired click cadence and button.
2. (Optional) Record multiple click targets or swipe gestures from the **Advanced** tab.
3. Choose a UI theme and press **Start** (or the configured start hotkey).
4. Stop the automation with the **Stop** button or the stop hotkey.

> Tip: If no positions are recorded the app will click wherever your cursor currently sits, making it ideal for rapid-fire tasks.
