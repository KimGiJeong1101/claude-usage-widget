"""Detail window shown when the tray icon is clicked, and the settings window
reachable from the right-click menu."""

import tkinter as tk
from tkinter import ttk

from usage_widget.config import Config
from usage_widget.fetcher import UsageData


def _format_remaining(reset_at) -> str:
    from datetime import datetime

    delta = reset_at - datetime.now()
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes = remainder // 60
    return f"{hours}시간 {minutes}분 후"


def show_usage_popup(usage: UsageData) -> None:
    root = tk.Tk()
    root.title("Claude 사용량")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=16)
    frame.grid()

    ttk.Label(frame, text="세션 (5시간)", font=("", 10, "bold")).grid(column=0, row=0, sticky="w")
    ttk.Label(frame, text=f"{usage.session_percent}%").grid(column=1, row=0, sticky="e")
    ttk.Label(frame, text=f"리셋까지 {_format_remaining(usage.session_reset_at)}").grid(
        column=0, row=1, columnspan=2, sticky="w", pady=(0, 12)
    )

    ttk.Label(frame, text="주간", font=("", 10, "bold")).grid(column=0, row=2, sticky="w")
    ttk.Label(frame, text=f"{usage.week_percent}%").grid(column=1, row=2, sticky="e")
    ttk.Label(frame, text=f"리셋까지 {_format_remaining(usage.week_reset_at)}").grid(
        column=0, row=3, columnspan=2, sticky="w"
    )

    root.mainloop()


def show_settings_popup() -> None:
    config = Config.load()
    root = tk.Tk()
    root.title("설정")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=16)
    frame.grid()

    ttk.Label(frame, text="갱신 주기 (분)").grid(column=0, row=0, sticky="w")
    interval_var = tk.IntVar(value=config.refresh_minutes)
    ttk.Entry(frame, textvariable=interval_var, width=6).grid(column=1, row=0)

    def on_save():
        config.refresh_minutes = interval_var.get()
        config.save()
        # TODO: re-register the OS scheduler task (schtasks / launchd)
        # with the new interval -- see plan doc section 5.
        root.destroy()

    ttk.Button(frame, text="저장", command=on_save).grid(column=0, row=1, columnspan=2, pady=(12, 0))

    root.mainloop()
