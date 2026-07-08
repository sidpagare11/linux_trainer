#!/usr/bin/env python3
"""
Linux Trainer Modern V3
A safe, self-contained Tkinter Linux trainer with a more modern dashboard UI.
"""

from __future__ import annotations

import os
import shlex
import shutil
import stat
import tempfile
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


APP_TITLE = "Linux Trainer Modern V16"
TRAINING_HOST = "linuxtraining22"
USERNAME = "trainee"

# Palette
BG = "#08111F"
SURFACE = "#0F1B2D"
SURFACE_2 = "#13243B"
SURFACE_3 = "#0C1626"
PANEL_BORDER = "#203754"
TEXT = "#E6EEF8"
TEXT_SOFT = "#A9BCD4"
TEXT_MUTED = "#7E94AF"
ACCENT = "#41C7FF"
ACCENT_2 = "#69F0D0"
SUCCESS = "#38D981"
WARNING = "#FFCB52"
ERROR = "#FF8B8B"
TERMINAL_BG = "#050B14"
TERMINAL_FG = "#D9E7F5"
BTN_BG = "#17304F"
BTN_BG_ACTIVE = "#214269"


@dataclass
class CommandResult:
    name: str
    args: List[str]
    raw: str
    output: str = ""
    success: bool = True


@dataclass
class Objective:
    title: str
    lesson: str
    hint: str
    checker: Callable[["LinuxTrainerApp", Optional[CommandResult]], bool]
    completed: bool = False


class PureVirtualPath:
    def __init__(self, path: str) -> None:
        if not path.startswith("/"):
            path = "/" + path
        self.path = self._norm(path)

    def _norm(self, path: str) -> str:
        parts = []
        for p in path.split("/"):
            if p in ("", "."):
                continue
            if p == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(p)
        return "/" + "/".join(parts)

    def __str__(self) -> str:
        return self.path


class SafeVirtualLinux:
    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="linux_trainer_lab_"))
        self.cwd = PureVirtualPath("/home/trainee")
        self._build_lab()

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def prompt_path(self) -> str:
        return str(self.cwd)

    def _build_lab(self) -> None:
        for d in [
            "home/trainee",
            "home/trainee/training",
            "home/trainee/logs",
            "home/trainee/configs",
            "home/trainee/intel",
            "home/trainee/archive",
        ]:
            (self.root / d).mkdir(parents=True, exist_ok=True)

        self.write_virtual(
            "/home/trainee/training/readme.txt",
            """
Linux Training Lab README
=========================
This file is safe training content.

You will practice:
- listing files with ls and ll
- changing folders with cd and cd ..
- copying files with cp
- searching text with grep
- editing files with vi/gvim
- removing files with rm

Security reminder: never paste unknown commands into a production terminal.
""",
        )
        self.write_virtual(
            "/home/trainee/training/commands.txt",
            """
Common Linux Commands
---------------------
pwd                  print current directory
ls                   list files
ll                   long listing, similar to ls -l
cd folder            enter a folder
cd ..                go up one folder
mkdir name           create a folder
cp source dest       copy a file
rm file              remove a file
grep PATTERN file    search for matching text
vi file              edit a file
""",
        )
        self.write_virtual(
            "/home/trainee/logs/system.log",
            """
2026-07-07 08:31:15 INFO  Boot sequence started
2026-07-07 08:31:21 INFO  Network interface eth0 online
2026-07-07 08:32:02 WARN  Disk usage at 74 percent
2026-07-07 08:33:44 ERROR Failed authentication attempt for service account
2026-07-07 08:34:10 INFO  User trainee session created
2026-07-07 08:35:52 ERROR Package checksum mismatch in staging cache
2026-07-07 08:37:01 INFO  Health check completed
""",
        )
        self.write_virtual(
            "/home/trainee/configs/template.conf",
            """
# Training service configuration
service_name=linux_training_demo
enabled=false
owner=unset
log_level=INFO
""",
        )
        self.write_virtual(
            "/home/trainee/intel/brief.txt",
            """
Mission Brief - Training Only
=============================
This exercise uses fictional training data.

Find the target system and record it in your answer file.
TARGET: SERVER_ALPHA
PORT: 2222
ACTION: VERIFY_CONFIG

Remember: use grep to search faster than reading every line manually.
""",
        )
        self.write_virtual("/home/trainee/archive/old.tmp", "temporary scratch file - safe to remove\n")
        self.write_virtual("/home/trainee/notes.txt", "Training notes:\n")

    def write_virtual(self, vpath: str, content: str) -> None:
        real = self.real_path(vpath)
        real.parent.mkdir(parents=True, exist_ok=True)
        real.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")

    def read_virtual(self, vpath: str) -> str:
        return self.real_path(vpath).read_text(encoding="utf-8")

    def exists(self, vpath: str) -> bool:
        return self.real_path(vpath).exists()

    def is_file(self, vpath: str) -> bool:
        return self.real_path(vpath).is_file()

    def is_dir(self, vpath: str) -> bool:
        return self.real_path(vpath).is_dir()

    def _normalize_virtual_path(self, path: str) -> str:
        parts: List[str] = []
        for part in path.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(part)
        return "/" + "/".join(parts)

    def _expand_user_path(self, path_text: str) -> str:
        if path_text == "~":
            return "/home/trainee"
        if path_text.startswith("~/"):
            return "/home/trainee/" + path_text[2:]
        return path_text

    def resolve_virtual(self, path_text: str) -> str:
        """Resolve a path using normal shell-like relative/absolute rules."""
        path_text = self._expand_user_path(path_text)
        if not path_text or path_text == ".":
            path = str(self.cwd)
        elif path_text.startswith("/"):
            path = path_text
        else:
            path = f"{self.cwd}/{path_text}"
        return self._normalize_virtual_path(path)

    def _real_from_virtual(self, vpath: str) -> Path:
        real = (self.root / vpath.lstrip("/")).resolve()
        root_resolved = self.root.resolve()
        if os.path.commonpath([str(root_resolved), str(real)]) != str(root_resolved):
            raise ValueError("Path escapes training sandbox")
        return real

    def real_path(self, path_text: str) -> Path:
        return self._real_from_virtual(self.resolve_virtual(path_text))

    def _smart_candidate_virtuals(self, path_text: str) -> List[str]:
        """Return normal path first, then trainer-friendly fallbacks.

        This keeps the terminal forgiving for training. For example:
        - cd home works like cd /home
        - cd trainee works like cd /home/trainee
        - cd training works from anywhere if /home/trainee/training exists
        """
        raw = self._expand_user_path(path_text.strip())
        candidates = [self.resolve_virtual(raw)]

        if raw and not raw.startswith("/"):
            stripped = raw.rstrip("/")
            if stripped:
                top, _, rest = stripped.partition("/")
                home_level = {"home"}
                trainee_level = {"trainee"}
                trainee_dirs = {
                    "training",
                    "workspace",
                    "logs",
                    "configs",
                    "intel",
                    "archive",
                    "mission",
                    "notes.txt",
                }

                if top in home_level:
                    candidates.append(self._normalize_virtual_path("/" + stripped))
                if top in trainee_level:
                    candidates.append(self._normalize_virtual_path("/home/" + stripped))
                if top in trainee_dirs:
                    candidates.append(self._normalize_virtual_path("/home/trainee/" + stripped))

        deduped: List[str] = []
        for c in candidates:
            if c not in deduped:
                deduped.append(c)
        return deduped

    def smart_resolve_existing(self, path_text: str) -> str:
        for candidate in self._smart_candidate_virtuals(path_text):
            if self._real_from_virtual(candidate).exists():
                return candidate
        return self.resolve_virtual(path_text)

    def smart_real_path_existing(self, path_text: str) -> Path:
        return self._real_from_virtual(self.smart_resolve_existing(path_text))

    def output_virtual_path(self, path_text: str) -> str:
        """Resolve a path for commands that create/write a file.

        If the target exists, use the smart existing path. If only the parent
        exists through a trainer-friendly fallback, use that parent. This lets
        commands like `cp training/readme.txt workspace/` still work after a
        trainee has wandered into another folder.
        """
        raw = self._expand_user_path(path_text.strip())

        existing = self.smart_resolve_existing(raw)
        if self._real_from_virtual(existing).exists():
            return existing

        clean = raw.rstrip("/\\")
        parent_text, sep, filename = clean.rpartition("/")
        if not sep:
            return self.resolve_virtual(raw)

        if parent_text:
            parent_v = self.smart_resolve_existing(parent_text)
            parent_real = self._real_from_virtual(parent_v)
            if parent_real.exists() and parent_real.is_dir():
                return self._normalize_virtual_path(parent_v + "/" + filename)

        return self.resolve_virtual(raw)

    def output_real_path(self, path_text: str) -> Path:
        return self._real_from_virtual(self.output_virtual_path(path_text))

    def cd(self, target: str) -> Tuple[bool, str]:
        vpath = self.smart_resolve_existing(target)
        real = self._real_from_virtual(vpath)
        if not real.exists():
            return False, f"cd: {target}: No such file or directory\n"
        if not real.is_dir():
            return False, f"cd: {target}: Not a directory\n"
        self.cwd = PureVirtualPath(vpath)
        return True, ""

class RoundedFrame(tk.Canvas):
    """Canvas-backed rounded container with a clean, artifact-free border."""

    def __init__(
        self,
        master,
        *,
        outer_bg: str,
        fill: str,
        radius: int = 18,
        border_color: str = PANEL_BORDER,
        border_width: int = 1,
        padding: int = 2,
        width: int = 120,
        height: int = 120,
    ) -> None:
        super().__init__(
            master,
            bg=outer_bg,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        self.outer_bg = outer_bg
        self.fill = fill
        self.radius = radius
        self.border_color = border_color
        self.border_width = border_width
        self.padding = padding
        self.content = tk.Frame(self, bg=fill, highlightthickness=0, bd=0)
        self._window_id = self.create_window(0, 0, anchor="nw", window=self.content)
        self.bind("<Configure>", self._redraw)

    def _draw_rounded_fill(self, x1: int, y1: int, x2: int, y2: int, r: int) -> None:
        """Draw a rounded rectangle using real arcs, not smoothed polygons."""
        r = max(0, min(r, (x2 - x1) // 2, (y2 - y1) // 2))
        self.create_rectangle(x1 + r, y1, x2 - r, y2, fill=self.fill, outline=self.fill, tags="shape")
        self.create_rectangle(x1, y1 + r, x2, y2 - r, fill=self.fill, outline=self.fill, tags="shape")

        self.create_arc(x1, y1, x1 + 2 * r, y1 + 2 * r, start=90, extent=90, style="pieslice",
                        fill=self.fill, outline=self.fill, tags="shape")
        self.create_arc(x2 - 2 * r, y1, x2, y1 + 2 * r, start=0, extent=90, style="pieslice",
                        fill=self.fill, outline=self.fill, tags="shape")
        self.create_arc(x2 - 2 * r, y2 - 2 * r, x2, y2, start=270, extent=90, style="pieslice",
                        fill=self.fill, outline=self.fill, tags="shape")
        self.create_arc(x1, y2 - 2 * r, x1 + 2 * r, y2, start=180, extent=90, style="pieslice",
                        fill=self.fill, outline=self.fill, tags="shape")

    def _draw_rounded_border(self, x1: int, y1: int, x2: int, y2: int, r: int) -> None:
        if self.border_width <= 0:
            return
        r = max(0, min(r, (x2 - x1) // 2, (y2 - y1) // 2))
        color = self.border_color
        width = self.border_width
        self.create_line(x1 + r, y1, x2 - r, y1, fill=color, width=width, tags="border")
        self.create_line(x2, y1 + r, x2, y2 - r, fill=color, width=width, tags="border")
        self.create_line(x1 + r, y2, x2 - r, y2, fill=color, width=width, tags="border")
        self.create_line(x1, y1 + r, x1, y2 - r, fill=color, width=width, tags="border")
        self.create_arc(x1, y1, x1 + 2 * r, y1 + 2 * r, start=90, extent=90, style="arc",
                        outline=color, width=width, tags="border")
        self.create_arc(x2 - 2 * r, y1, x2, y1 + 2 * r, start=0, extent=90, style="arc",
                        outline=color, width=width, tags="border")
        self.create_arc(x2 - 2 * r, y2 - 2 * r, x2, y2, start=270, extent=90, style="arc",
                        outline=color, width=width, tags="border")
        self.create_arc(x1, y2 - 2 * r, x1 + 2 * r, y2, start=180, extent=90, style="arc",
                        outline=color, width=width, tags="border")

    def _redraw(self, event=None) -> None:
        self.delete("shape")
        self.delete("border")
        w = max(2, self.winfo_width())
        h = max(2, self.winfo_height())

        # Slight inset prevents clipped arcs on macOS.
        x1 = y1 = max(1, self.border_width)
        x2 = w - max(1, self.border_width)
        y2 = h - max(1, self.border_width)

        self._draw_rounded_fill(x1, y1, x2, y2, self.radius)
        self._draw_rounded_border(x1, y1, x2, y2, self.radius)

        # Keep child widgets inside the rounded shape so the corners do not show square artifacts.
        content_inset = max(self.border_width + self.padding, min(8, max(2, self.radius // 3)))
        self.coords(self._window_id, content_inset, content_inset)
        self.itemconfigure(
            self._window_id,
            width=max(1, w - content_inset * 2),
            height=max(1, h - content_inset * 2),
        )
        self.tag_lower("shape")
        self.tag_raise("border")


class ThemedScrollbar(tk.Canvas):
    """Small custom vertical scrollbar so macOS does not force a white native scrollbar."""

    def __init__(
        self,
        master,
        *,
        command,
        track_color: str,
        thumb_color: str = "#254666",
        active_color: str = "#356A94",
        width: int = 12,
    ) -> None:
        super().__init__(
            master,
            width=width,
            bg=track_color,
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        self.command = command
        self.track_color = track_color
        self.thumb_color = thumb_color
        self.active_color = active_color
        self.first = 0.0
        self.last = 1.0
        self.dragging = False
        self.drag_offset = 0
        self.bind("<Configure>", lambda e: self._redraw())
        self.bind("<Button-1>", self._mouse_down)
        self.bind("<B1-Motion>", self._mouse_drag)
        self.bind("<ButtonRelease-1>", self._mouse_up)
        self.bind("<Enter>", lambda e: self._redraw(active=True))
        self.bind("<Leave>", lambda e: self._redraw(active=False))

    def set(self, first, last) -> None:
        self.first = max(0.0, min(1.0, float(first)))
        self.last = max(0.0, min(1.0, float(last)))
        self._redraw()

    def _thumb_bounds(self):
        h = max(1, self.winfo_height())
        fraction = max(0.08, self.last - self.first)
        top = self.first * h
        bottom = top + fraction * h
        if bottom - top < 28:
            bottom = top + 28
        if bottom > h:
            bottom = h
            top = max(0, h - (bottom - top))
        return top, bottom

    def _redraw(self, active: bool = False) -> None:
        self.delete("all")
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        self.create_rectangle(0, 0, w, h, fill=self.track_color, outline=self.track_color)
        top, bottom = self._thumb_bounds()
        color = self.active_color if active or self.dragging else self.thumb_color
        # Rounded thumb.
        radius = min(w // 2, 5)
        self.create_rectangle(3, top + radius, w - 3, bottom - radius, fill=color, outline=color)
        self.create_oval(3, top, w - 3, top + 2 * radius, fill=color, outline=color)
        self.create_oval(3, bottom - 2 * radius, w - 3, bottom, fill=color, outline=color)

    def _mouse_down(self, event) -> None:
        top, bottom = self._thumb_bounds()
        if top <= event.y <= bottom:
            self.dragging = True
            self.drag_offset = event.y - top
        else:
            self.dragging = True
            self.drag_offset = 14
            self._move_to_event(event)
        self._redraw(active=True)

    def _mouse_drag(self, event) -> None:
        if self.dragging:
            self._move_to_event(event)
            self._redraw(active=True)

    def _mouse_up(self, event) -> None:
        self.dragging = False
        self._redraw(active=False)

    def _move_to_event(self, event) -> None:
        h = max(1, self.winfo_height())
        fraction = max(0.08, self.last - self.first)
        thumb_h = max(28, fraction * h)
        available = max(1, h - thumb_h)
        new_top = min(max(0, event.y - self.drag_offset), available)
        self.command("moveto", new_top / available)


class LinuxTrainerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1560x940")
        self.minsize(1320, 780)
        self.configure(bg=BG)

        self.fs = SafeVirtualLinux()
        self.connected = False
        self.phase = "education"
        self.history: List[str] = []
        self.history_index: Optional[int] = None
        self.last_result: Optional[CommandResult] = None

        self.education_objectives = self._make_education_objectives()
        self.challenge_objectives = self._make_challenge_objectives()
        self.current_index = 0
        self.objectives = self.education_objectives

        self._style_setup()
        self._build_ui()
        self._welcome()
        self._new_prompt()
        self._refresh_sidebar()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _style_setup(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Action.TButton", background=BTN_BG, foreground=TEXT, borderwidth=0, focusthickness=0, padding=(16, 12), font=("Segoe UI", 10, "bold"))
        style.map("Action.TButton", background=[("active", BTN_BG_ACTIVE), ("pressed", BTN_BG_ACTIVE)])

    def _card(
        self,
        parent,
        *,
        fill: str = SURFACE,
        radius: int = 18,
        border_color: str = PANEL_BORDER,
        border_width: int = 1,
        width: int = 160,
        height: int = 120,
        **grid_kwargs,
    ):
        outer_bg = parent.cget("bg") if hasattr(parent, "cget") else BG
        wrapper = RoundedFrame(
            parent,
            outer_bg=outer_bg,
            fill=fill,
            radius=radius,
            border_color=border_color,
            border_width=border_width,
            width=width,
            height=height,
        )
        wrapper.grid(**grid_kwargs)
        return wrapper.content


    def _build_ui(self) -> None:
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        topbar = tk.Frame(self, bg="#07111F", height=64, highlightthickness=0, bd=0)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        topbar.columnconfigure(1, weight=1)

        tk.Label(
            topbar,
            text="LOCKHEED MARTIN • LINUX TRAINER",
            bg="#07111F",
            fg=TEXT,
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=17)

        tk.Label(
            topbar,
            text="MODERN V16",
            bg="#123B63",
            fg=ACCENT,
            font=("Segoe UI", 11, "bold"),
            padx=14,
            pady=7,
        ).grid(row=0, column=1, sticky="e", padx=(0, 22), pady=12)

        body = tk.Frame(self, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=5)
        body.columnconfigure(1, weight=3)

        # LEFT: terminal card
        left = self._card(body, row=0, column=0, sticky="nsew", padx=(0, 10), radius=16)
        left.rowconfigure(2, weight=1)
        left.columnconfigure(0, weight=1)

        left_head = tk.Frame(left, bg=SURFACE_2, height=88, highlightthickness=0, bd=0)
        left_head.grid(row=0, column=0, sticky="ew")
        left_head.grid_propagate(False)
        left_head.columnconfigure(0, weight=1)

        tk.Label(
            left_head,
            text="Linux Training Lab",
            bg=SURFACE_2,
            fg=TEXT,
            font=("Segoe UI", 22, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(16, 0))

        tk.Label(
            left_head,
            text="Sandbox terminal with guided education and challenge mode",
            bg=SURFACE_2,
            fg=TEXT_SOFT,
            font=("Segoe UI", 11),
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(4, 0))

        status_shell = tk.Frame(left, bg=SURFACE, height=58, highlightthickness=0, bd=0)
        status_shell.grid(row=1, column=0, sticky="ew", padx=20, pady=(14, 10))
        status_shell.grid_propagate(False)
        status_shell.columnconfigure(0, weight=1)
        status_shell.columnconfigure(1, weight=1)

        self.connection_chip = tk.Label(
            status_shell,
            text="LOCAL",
            bg="#331C22",
            fg="#FFD3DC",
            font=("Segoe UI", 10, "bold"),
            padx=16,
            pady=9,
        )
        self.connection_chip.grid(row=0, column=0, sticky="w", pady=8)

        self.phase_chip = tk.Label(
            status_shell,
            text="EDUCATION",
            bg="#14304A",
            fg="#BEE5FF",
            font=("Segoe UI", 10, "bold"),
            padx=16,
            pady=9,
        )
        self.phase_chip.grid(row=0, column=1, sticky="e", pady=8)

        term_area = tk.Frame(left, bg=SURFACE, padx=20, pady=0, highlightthickness=0, bd=0)
        term_area.grid(row=2, column=0, sticky="nsew")
        term_area.rowconfigure(0, weight=1)
        term_area.columnconfigure(0, weight=1)

        term_shell = RoundedFrame(
            term_area,
            outer_bg=SURFACE,
            fill=TERMINAL_BG,
            radius=14,
            border_color=TERMINAL_BG,
            border_width=0,
            width=700,
            height=520,
        )
        term_shell.grid(row=0, column=0, sticky="nsew")
        term_shell.content.rowconfigure(0, weight=1)
        term_shell.content.columnconfigure(0, weight=1)

        self.terminal = tk.Text(
            term_shell.content,
            wrap="word",
            font=("Cascadia Mono", 14),
            bg=TERMINAL_BG,
            fg=TERMINAL_FG,
            insertbackground=ACCENT_2,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=20,
            pady=20,
            selectbackground="#163558",
        )
        self.terminal.grid(row=0, column=0, sticky="nsew")

        term_scroll = ThemedScrollbar(
            term_shell.content,
            command=self.terminal.yview,
            track_color=TERMINAL_BG,
            thumb_color="#1D3B5B",
            active_color="#2E6D9A",
            width=12,
        )
        term_scroll.grid(row=0, column=1, sticky="ns", padx=(2, 8), pady=14)
        self.terminal.configure(yscrollcommand=term_scroll.set)

        self.terminal.tag_configure("banner", foreground=TEXT_SOFT)
        self.terminal.tag_configure("system", foreground="#8BB7FF")
        self.terminal.tag_configure("error", foreground=ERROR)
        self.terminal.tag_configure("success", foreground=SUCCESS)
        self.terminal.tag_configure("prompt", foreground=ACCENT_2)
        self.terminal.bind("<Return>", self._on_enter)
        self.terminal.bind("<BackSpace>", self._on_backspace)
        self.terminal.bind("<Left>", self._guard_cursor)
        self.terminal.bind("<Home>", self._home_key)
        self.terminal.bind("<Up>", self._history_up)
        self.terminal.bind("<Down>", self._history_down)
        self.terminal.bind("<Tab>", self._tab_complete)
        self.terminal.bind("<Button-1>", self._click_guard)

        bottom_shell = tk.Frame(left, bg=SURFACE, padx=20, pady=0, highlightthickness=0, bd=0)
        bottom_shell.grid(row=3, column=0, sticky="ew", pady=(12, 18))
        bottom_card = RoundedFrame(
            bottom_shell,
            outer_bg=SURFACE,
            fill=SURFACE_3,
            radius=14,
            border_color=SURFACE_3,
            border_width=0,
            width=500,
            height=46,
        )
        bottom_card.grid(row=0, column=0, sticky="ew")
        bottom_shell.columnconfigure(0, weight=1)
        bottom_card.content.columnconfigure(0, weight=1)
        self.bottom_message = tk.Label(
            bottom_card.content,
            text="Begin by connecting with: ssh -X linuxtraining22",
            bg=SURFACE_3,
            fg=TEXT_MUTED,
            font=("Segoe UI", 10),
            anchor="w",
        )
        self.bottom_message.grid(row=0, column=0, sticky="ew", padx=16, pady=12)

        # RIGHT: control cards
        right = tk.Frame(body, bg=BG, highlightthickness=0, bd=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1, uniform="right_cards")
        right.rowconfigure(2, weight=1, uniform="right_cards")
        right.columnconfigure(0, weight=1)

        ctrl = self._card(right, row=0, column=0, sticky="ew", height=170, radius=16)
        ctrl.columnconfigure(0, weight=1)
        tk.Label(
            ctrl,
            text="Training Control",
            bg=SURFACE,
            fg=TEXT,
            font=("Segoe UI", 21, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(18, 0))
        tk.Label(
            ctrl,
            text="Clear step-by-step objectives • relative and absolute paths supported",
            bg=SURFACE,
            fg=TEXT_SOFT,
            font=("Segoe UI", 11),
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(6, 0))

        progress_wrap = tk.Frame(ctrl, bg=SURFACE, highlightthickness=0, bd=0)
        progress_wrap.grid(row=2, column=0, sticky="ew", padx=22, pady=(16, 18))
        progress_wrap.columnconfigure(0, weight=1)
        self.progress_text = tk.Label(
            progress_wrap,
            text="0 / 0 complete",
            bg=SURFACE,
            fg=ACCENT,
            font=("Segoe UI", 11, "bold"),
        )
        self.progress_text.grid(row=0, column=0, sticky="w")
        self.progress_canvas = tk.Canvas(progress_wrap, height=11, bg=SURFACE, highlightthickness=0, bd=0)
        self.progress_canvas.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        lesson_card = self._card(right, row=1, column=0, sticky="nsew", pady=(10, 10), height=300, radius=16)
        lesson_card.rowconfigure(2, weight=1)
        lesson_card.columnconfigure(0, weight=1)
        tk.Label(
            lesson_card,
            text="Current Objective",
            bg=SURFACE,
            fg=TEXT,
            font=("Segoe UI", 14, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(16, 0))
        self.phase_label = tk.Label(
            lesson_card,
            text="Education Section",
            bg=SURFACE,
            fg=ACCENT_2,
            font=("Segoe UI", 11, "bold"),
        )
        self.phase_label.grid(row=1, column=0, sticky="w", padx=22, pady=(4, 8))

        lesson_shell = RoundedFrame(
            lesson_card,
            outer_bg=SURFACE,
            fill=SURFACE_3,
            radius=14,
            border_color="#203754",
            border_width=1,
            width=420,
            height=210,
        )
        lesson_shell.grid(row=2, column=0, sticky="nsew", padx=22, pady=(0, 16))
        lesson_shell.content.rowconfigure(0, weight=1)
        lesson_shell.content.columnconfigure(0, weight=1)
        self.lesson = tk.Text(
            lesson_shell.content,
            height=7,
            wrap="word",
            bg=SURFACE_3,
            fg=TEXT,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 12),
            padx=14,
            pady=12,
            spacing1=1,
            spacing2=0,
            spacing3=3,
        )
        self.lesson.grid(row=0, column=0, sticky="nsew")
        self.lesson.configure(state="disabled")

        lesson_scroll = ThemedScrollbar(
            lesson_shell.content,
            command=self.lesson.yview,
            track_color=SURFACE_3,
            thumb_color="#244564",
            active_color="#2E6D9A",
            width=12,
        )
        lesson_scroll.grid(row=0, column=1, sticky="ns", padx=(2, 8), pady=10)
        self.lesson.configure(yscrollcommand=lesson_scroll.set)

        tracker_card = self._card(right, row=2, column=0, sticky="nsew", radius=16)
        tracker_card.rowconfigure(1, weight=1)
        tracker_card.columnconfigure(0, weight=1)
        tk.Label(
            tracker_card,
            text="Mission Tracker",
            bg=SURFACE,
            fg=TEXT,
            font=("Segoe UI", 14, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(16, 0))

        tracker_shell = RoundedFrame(
            tracker_card,
            outer_bg=SURFACE,
            fill=SURFACE_3,
            radius=14,
            border_color="#203754",
            border_width=1,
            width=420,
            height=360,
        )
        tracker_shell.grid(row=1, column=0, sticky="nsew", padx=22, pady=(12, 18))
        tracker_shell.content.rowconfigure(0, weight=1)
        tracker_shell.content.columnconfigure(0, weight=1)

        self.objective_box = tk.Text(
            tracker_shell.content,
            wrap="word",
            bg=SURFACE_3,
            fg=TEXT_SOFT,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 12),
            padx=14,
            pady=12,
            spacing1=7,
            spacing3=7,
        )
        self.objective_box.grid(row=0, column=0, sticky="nsew")
        self.objective_box.tag_configure("done", foreground=SUCCESS, font=("Segoe UI", 12, "bold"))
        self.objective_box.tag_configure("current", foreground=TEXT, font=("Segoe UI", 12, "bold"))
        self.objective_box.tag_configure("upcoming", foreground=TEXT_SOFT, font=("Segoe UI", 12))
        self.objective_box.configure(state="disabled")

        tracker_scroll = ThemedScrollbar(
            tracker_shell.content,
            command=self.objective_box.yview,
            track_color=SURFACE_3,
            thumb_color="#244564",
            active_color="#2E6D9A",
            width=12,
        )
        tracker_scroll.grid(row=0, column=1, sticky="ns", padx=(2, 8), pady=10)
        self.objective_box.configure(yscrollcommand=tracker_scroll.set)

        btns = tk.Frame(right, bg=BG, highlightthickness=0, bd=0)
        btns.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        ttk.Button(btns, text="Need a Hint?", style="Action.TButton", command=self._show_hint).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(btns, text="Reset Lab", style="Action.TButton", command=self._reset_lab).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )


    def _write(self, text: str, tag: Optional[str] = None) -> None:
        if tag:
            self.terminal.insert("end", text, tag)
        else:
            self.terminal.insert("end", text)
        self.terminal.see("end")

    def _welcome(self) -> None:
        welcome = (
            "Linux Training Lab\n"
            "──────────────────\n\n"
            "This lab simulates a Linux workstation inside a safe sandbox.\n"
            "Start by connecting to the remote training environment exactly as shown.\n\n"
            f"    ssh -X {TRAINING_HOST}\n\n"
            "Path rules match Linux basics:\n"
            "  • /home/trainee/training is an absolute path.\n"
            "  • training/readme.txt is relative to your current directory.\n"
            "  • Press Tab to autocomplete file and folder paths.\n"
            "  • vi/gvim can create a new file when you save, but the folder must already exist.\n\n"
        )
        self._write(welcome, "banner")

    def _prompt_text(self) -> str:
        host = TRAINING_HOST if self.connected else "local"
        return f"{USERNAME}@{host}:{self.fs.prompt_path()}$ "

    def _new_prompt(self) -> None:
        start = self.terminal.index("end-1c")
        self.terminal.insert("end", self._prompt_text())
        end = self.terminal.index("end-1c")
        self.terminal.tag_add("prompt", start, end)
        self.terminal.mark_set("input_start", "insert")
        self.terminal.mark_gravity("input_start", "left")
        self.terminal.focus_set()

    def _get_current_input(self) -> str:
        return self.terminal.get("input_start", "end-1c")

    def _replace_current_input(self, text: str) -> None:
        self.terminal.delete("input_start", "end-1c")
        self.terminal.insert("end", text)

    def _on_enter(self, event) -> str:
        command = self._get_current_input().strip()
        self._write("\n")
        if command:
            self.history.append(command)
        self.history_index = None
        result = self.execute_command(command)
        self.last_result = result
        if result.output:
            tag = "error" if (not result.success and result.name) else None
            self._write(result.output, tag)
        self._evaluate_objective(result)
        self._new_prompt()
        return "break"

    def _on_backspace(self, event):
        if self.terminal.compare("insert", "<=", "input_start"):
            return "break"
        return None

    def _guard_cursor(self, event):
        if self.terminal.compare("insert", "<=", "input_start"):
            return "break"
        return None

    def _home_key(self, event):
        self.terminal.mark_set("insert", "input_start")
        return "break"

    def _click_guard(self, event) -> None:
        self.after(1, self._ensure_cursor_in_input)

    def _ensure_cursor_in_input(self) -> None:
        if self.terminal.compare("insert", "<", "input_start"):
            self.terminal.mark_set("insert", "end-1c")

    def _history_up(self, event):
        if not self.history:
            return "break"
        if self.history_index is None:
            self.history_index = len(self.history) - 1
        else:
            self.history_index = max(0, self.history_index - 1)
        self._replace_current_input(self.history[self.history_index])
        return "break"

    def _history_down(self, event):
        if self.history_index is None:
            return "break"
        self.history_index += 1
        if self.history_index >= len(self.history):
            self.history_index = None
            self._replace_current_input("")
        else:
            self._replace_current_input(self.history[self.history_index])
        return "break"

    def _tab_complete(self, event):
        current = self._get_current_input()
        prefix, token = self._split_completion_token(current)
        matches = self._path_completions(token)

        if not matches:
            return "break"

        if len(matches) == 1:
            completed = matches[0]
            self._replace_current_input(prefix + completed)
            return "break"

        common = os.path.commonprefix(matches)
        if common and common != token:
            self._replace_current_input(prefix + common)
            return "break"

        # Multiple possible completions: show them, then redraw the same prompt/input.
        self._write("\n" + "  ".join(matches) + "\n", "system")
        start = self.terminal.index("end-1c")
        self.terminal.insert("end", self._prompt_text())
        end = self.terminal.index("end-1c")
        self.terminal.tag_add("prompt", start, end)
        self.terminal.mark_set("input_start", "insert")
        self.terminal.mark_gravity("input_start", "left")
        self.terminal.insert("end", current)
        return "break"

    def _split_completion_token(self, command_text: str) -> Tuple[str, str]:
        if not command_text:
            return "", ""
        if command_text[-1].isspace():
            return command_text, ""

        last_space = max(command_text.rfind(" "), command_text.rfind("\t"))
        if last_space == -1:
            return "", command_text
        return command_text[: last_space + 1], command_text[last_space + 1 :]

    def _path_completions(self, token: str) -> List[str]:
        token = token or ""
        expanded_token = self.fs._expand_user_path(token)

        if "/" in expanded_token:
            base_text, _, partial = expanded_token.rpartition("/")
            if base_text == "":
                base_text = "/"
            display_base = token.rpartition("/")[0]
        else:
            base_text = "."
            partial = expanded_token
            display_base = ""

        base_v = self.fs.smart_resolve_existing(base_text)
        base_real = self.fs._real_from_virtual(base_v)
        if not base_real.exists() or not base_real.is_dir():
            return []

        matches: List[str] = []
        for entry in sorted(base_real.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if not entry.name.startswith(partial):
                continue

            suffix = "/" if entry.is_dir() else " "
            if display_base:
                matches.append(display_base + "/" + entry.name + suffix)
            elif token.startswith("/"):
                matches.append(base_v.rstrip("/") + "/" + entry.name + suffix)
            else:
                matches.append(entry.name + suffix)

        return matches

    def _draw_progress(self, complete: int, total: int) -> None:
        self.progress_canvas.delete("all")
        self.progress_canvas.update_idletasks()
        width = max(self.progress_canvas.winfo_width(), 50)
        height = 10
        self.progress_canvas.create_rectangle(0, 0, width, height, fill="#16263C", outline="#16263C")
        pct = 0 if total == 0 else complete / total
        fill_w = width * pct
        self.progress_canvas.create_rectangle(0, 0, fill_w, height, fill=ACCENT, outline=ACCENT)

    def _refresh_sidebar(self) -> None:
        phase_name = "Education Section" if self.phase == "education" else "Challenge Section"
        self.phase_label.configure(text=phase_name)
        self.phase_chip.configure(text="EDUCATION" if self.phase == "education" else "CHALLENGE")

        if self.connected:
            self.connection_chip.configure(text=TRAINING_HOST.upper(), bg="#113728", fg="#D4FFE7")
            self.bottom_message.configure(text="Connected. Follow the active objective shown in the control panel.")
        else:
            self.connection_chip.configure(text="LOCAL", bg="#331C22", fg="#FFD3DC")
            self.bottom_message.configure(text=f"Begin by connecting with: ssh -X {TRAINING_HOST}")

        current = self._current_objective()
        self.lesson.configure(state="normal")
        self.lesson.delete("1.0", "end")
        if current:
            self.lesson.insert("end", self._format_objective_panel_text(current))
            self.lesson.see("1.0")
        else:
            self.lesson.insert("end", "All objectives complete.")
        self.lesson.configure(state="disabled")

        complete = sum(1 for o in self.objectives if o.completed)
        total = len(self.objectives)
        self.progress_text.configure(text=f"{complete} / {total} complete")
        self.after(10, lambda: self._draw_progress(complete, total))

        self.objective_box.configure(state="normal")
        self.objective_box.delete("1.0", "end")
        for idx, obj in enumerate(self.objectives):
            if obj.completed:
                self.objective_box.insert("end", f"✓  {obj.title}\n", "done")
            elif idx == self.current_index:
                self.objective_box.insert("end", f"▶  {obj.title}\n", "current")
            else:
                self.objective_box.insert("end", f"○  {obj.title}\n", "upcoming")
        self.objective_box.configure(state="disabled")

        # Keep the active objective visible as the user progresses.
        if self.current_index < len(self.objectives):
            target_line = f"{self.current_index + 1}.0"
        else:
            target_line = "end"
        self.after_idle(lambda line=target_line: self.objective_box.see(line))

    def _show_popup(self, title: str, message: str) -> None:
        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=BG)
        win.geometry("520x250")
        win.minsize(420, 220)
        card = tk.Frame(win, bg=SURFACE, highlightthickness=1, highlightbackground=PANEL_BORDER)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(card, text=title, bg=SURFACE, fg=TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=18, pady=(16, 8))
        tk.Label(card, text=message, bg=SURFACE, fg=TEXT_SOFT, wraplength=450, justify="left", font=("Segoe UI", 12)).pack(anchor="w", padx=18, pady=(0, 16))
        ttk.Button(card, text="Close", style="Action.TButton", command=win.destroy).pack(anchor="e", padx=18, pady=(0, 18))
        win.transient(self)
        win.grab_set()

    def _show_hint(self) -> None:
        obj = self._current_objective()
        if obj is None:
            self._show_popup("Hint", "You completed all objectives.")
        else:
            self._show_popup("Hint", obj.hint)

    def _current_objective(self) -> Optional[Objective]:
        if self.current_index < len(self.objectives):
            return self.objectives[self.current_index]
        return None

    def _format_objective_panel_text(self, obj: Objective) -> str:
        """Create compact, readable objective text for the right-side panel."""
        lines = [line.strip() for line in obj.lesson.splitlines()]
        lines = [line for line in lines if line]

        # Convert common verbose labels to shorter labels.
        compact = []
        i = 0
        label_map = {
            "Goal:": "Goal:",
            "Type exactly:": "Command:",
            "Expected result:": "Expected:",
            "Expected output:": "Expected:",
            "Source file:": "Source:",
            "Destination file:": "Destination:",
            "Destination folder:": "Destination:",
            "Required folder:": "Required:",
            "File to search:": "File:",
            "File to remove:": "File:",
            "Open this file with either editor:": "Open:",
            "Add this exact phrase:": "Add:",
            "Add this exact line:": "Add:",
        }

        while i < len(lines):
            line = lines[i]

            # Labels that should absorb the next line into the same compact line.
            if line in label_map and i + 1 < len(lines):
                compact.append(f"{label_map[line]} {lines[i + 1]}")
                i += 2
                continue

            # Keep short standalone reminders, but simplify wording.
            line = line.replace("Type one of these:", "Command options:")
            line = line.replace("Use one of these:", "Command options:")
            line = line.replace("Because you should now be inside /home/trainee/mission, type:", "From /home/trainee/mission:")
            line = line.replace("Because you should be in /home/trainee/mission, type one of these:", "From /home/trainee/mission, use:")
            line = line.replace("The absolute path works too.", "Full path also works.")
            line = line.replace("Absolute path also works:", "Full path also works:")
            compact.append(line)
            i += 1

        # Hard cap very long panel text by keeping it useful and scroll-free.
        # The Hint button still has the full hint if the user needs more.
        useful = []
        for line in compact:
            if line not in useful:
                useful.append(line)

        return "Task: " + obj.title + "\n" + "\n".join(useful)

    def _any_file_contains_phrase(self, paths: List[str], phrase: str, *, case_sensitive: bool = False) -> bool:
        """Return True when any sandbox file contains the required phrase.

        This is used by editor objectives so either vi or gvim can complete the
        task after a save. It also prevents users from getting stuck if an older
        instruction pointed them to /home/trainee/notes.txt instead of the newer
        workspace notes file.
        """
        expected = phrase if case_sensitive else phrase.lower()
        for path in paths:
            try:
                if not self.fs.is_file(path):
                    continue
                content = self.fs.read_virtual(path)
            except Exception:
                continue

            haystack = content if case_sensitive else content.lower()
            if expected in haystack:
                return True
        return False

    def _evaluate_objective(self, result: Optional[CommandResult]) -> None:
        obj = self._current_objective()
        if obj and obj.checker(self, result):
            obj.completed = True
            self.current_index += 1
            if self.current_index >= len(self.objectives):
                if self.phase == "education":
                    self._start_challenge()
                else:
                    self._write(
                        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "Challenge complete. You passed the Linux trainer.\n"
                        "You practiced navigation, file management, grep, editing,\n"
                        "and cleanup in a safe training sandbox.\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
                        "success",
                    )
            self._refresh_sidebar()

    def _start_challenge(self) -> None:
        self.phase = "challenge"
        self.objectives = self.challenge_objectives
        self.current_index = 0
        self._write(
            "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Education complete. Starting cumulative challenge mode.\n\n"
            "Scenario: prepare a small mission package.\n"
            "Important paths:\n"
            "  mission folder:  /home/trainee/mission\n"
            "  mission brief:   /home/trainee/intel/brief.txt\n"
            "  config template: /home/trainee/configs/template.conf\n"
            "  archive cleanup: /home/trainee/archive/old.tmp\n\n"
            "Use the exact command shown in the objective panel, or use the\n"
            "relative version when you are already in the correct folder.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
            "system",
        )
        self._refresh_sidebar()

    def _reset_lab(self) -> None:
        self.fs.cleanup()
        self.fs = SafeVirtualLinux()
        self.connected = False
        self.phase = "education"
        self.history = []
        self.history_index = None
        self.education_objectives = self._make_education_objectives()
        self.challenge_objectives = self._make_challenge_objectives()
        self.objectives = self.education_objectives
        self.current_index = 0
        self.terminal.delete("1.0", "end")
        self._welcome()
        self._new_prompt()
        self._refresh_sidebar()

    def _on_close(self) -> None:
        self.fs.cleanup()
        self.destroy()

    def _make_education_objectives(self) -> List[Objective]:
        return [
            Objective(
                "Remote connect to the Linux training host",
                "Goal: connect to the simulated Linux host.\n\nType exactly:\nssh -X linuxtraining22\n\nExpected result: the prompt changes from trainee@local to trainee@linuxtraining22.",
                "Type exactly: ssh -X linuxtraining22",
                lambda app, r: app.connected and r is not None and r.raw == "ssh -X linuxtraining22",
            ),
            Objective(
                "Print your current directory with pwd",
                "Goal: confirm where you are in the filesystem.\n\nType exactly:\npwd\n\nExpected output: /home/trainee",
                "Type: pwd",
                lambda app, r: r is not None and r.name == "pwd" and r.success,
            ),
            Objective(
                "List files with ls",
                "Goal: see what is inside /home/trainee.\n\nType exactly:\nls\n\nExpected result: you should see folders such as training, logs, configs, intel, and archive.",
                "Type: ls",
                lambda app, r: r is not None and r.name == "ls" and r.success,
            ),
            Objective(
                "Use ll for a long listing",
                "Goal: see the same folder with details like permissions, owner, size, and modified time.\n\nType exactly:\nll\n\nExpected result: a long listing of /home/trainee.",
                "Type: ll",
                lambda app, r: r is not None and r.name == "ll" and r.success,
            ),
            Objective(
                "Change into the training folder",
                "Goal: enter the folder that contains training files.\n\nType exactly:\ncd /home/trainee/training\n\nExpected result: the prompt ends with /home/trainee/training.",
                "Type: cd /home/trainee/training. You can press Tab while typing the path.",
                lambda app, r: r is not None and r.name == "cd" and app.fs.prompt_path() == "/home/trainee/training",
            ),
            Objective(
                "Return to your home folder with cd ..",
                "Goal: move one directory up from /home/trainee/training back to /home/trainee.\n\nType exactly:\ncd ..\n\nExpected result: the prompt ends with /home/trainee.",
                "Type: cd ..",
                lambda app, r: r is not None and r.name == "cd" and app.fs.prompt_path() == "/home/trainee",
            ),
            Objective(
                "Create a workspace folder with mkdir",
                "Goal: create a folder where your copied files and notes will go.\n\nType exactly:\nmkdir /home/trainee/workspace\n\nExpected result: /home/trainee/workspace exists. You can confirm with ls /home/trainee.",
                "Type: mkdir /home/trainee/workspace",
                lambda app, r: app.fs.is_dir("/home/trainee/workspace"),
            ),
            Objective(
                "Copy the README into workspace with cp",
                "Goal: copy the README file into your workspace folder.\n\nSource file:\n/home/trainee/training/readme.txt\n\nDestination folder:\n/home/trainee/workspace/\n\nType exactly:\ncp /home/trainee/training/readme.txt /home/trainee/workspace/\n\nExpected result: /home/trainee/workspace/readme.txt exists.",
                "Type: cp /home/trainee/training/readme.txt /home/trainee/workspace/",
                lambda app, r: r is not None
                and r.name == "cp"
                and r.success
                and (
                    app.fs.is_file("/home/trainee/workspace/readme.txt")
                    or app.fs.is_file("/home/trainee/workspace/readme_copy.txt")
                ),
            ),
            Objective(
                "Search logs with grep",
                "Goal: search a log file for ERROR lines.\n\nFile to search:\n/home/trainee/logs/system.log\n\nType exactly:\ngrep ERROR /home/trainee/logs/system.log\n\nExpected result: lines containing ERROR appear in the terminal.",
                "Type: grep ERROR /home/trainee/logs/system.log",
                lambda app, r: r is not None and r.name == "grep" and "ERROR" in r.output,
            ),
            Objective(
                "Open and save a notes file using vi OR gvim",
                "Goal: edit a file and save it.\n\nOpen this file with either editor:\n/home/trainee/workspace/notes.txt\n\nType one of these:\nvi /home/trainee/workspace/notes.txt\ngvim /home/trainee/workspace/notes.txt\n\nAdd this exact phrase:\nLinux training complete\n\nSave with Ctrl+S, Save, Save & Close, or :wq.",
                "Use either vi or gvim, not both. Add the exact phrase Linux training complete, then save.",
                lambda app, r: app._any_file_contains_phrase(
                    [
                        "/home/trainee/workspace/notes.txt",
                        "/home/trainee/notes.txt",
                    ],
                    "Linux training complete",
                ),
            ),
            Objective(
                "Remove the copied README with rm",
                "Goal: remove only the README copy from workspace.\n\nIf your copied file is readme.txt, type:\nrm /home/trainee/workspace/readme.txt\n\nIf you named it readme_copy.txt, type:\nrm /home/trainee/workspace/readme_copy.txt\n\nExpected result: the copied README is gone.",
                "Remove the copied README in /home/trainee/workspace. Do not remove the original file in /home/trainee/training.",
                lambda app, r: r is not None
                and r.name == "rm"
                and r.success
                and not app.fs.exists("/home/trainee/workspace/readme.txt")
                and not app.fs.exists("/home/trainee/workspace/readme_copy.txt"),
            ),
        ]

    def _make_challenge_objectives(self) -> List[Objective]:
        return [
            Objective(
                "Create the mission directory",
                "Goal: create the folder where the challenge package will be built.\n\nRequired folder:\n/home/trainee/mission\n\nType exactly:\nmkdir /home/trainee/mission\n\nExpected result: the mission folder exists.",
                "Type: mkdir /home/trainee/mission",
                lambda app, r: app.fs.is_dir("/home/trainee/mission"),
            ),
            Objective(
                "Copy the mission brief into mission",
                "Goal: copy the brief into the mission folder.\n\nSource file:\n/home/trainee/intel/brief.txt\n\nDestination file:\n/home/trainee/mission/brief.txt\n\nType exactly:\ncp /home/trainee/intel/brief.txt /home/trainee/mission/brief.txt\n\nExpected result: brief.txt appears inside /home/trainee/mission.",
                "Type: cp /home/trainee/intel/brief.txt /home/trainee/mission/brief.txt",
                lambda app, r: app.fs.is_file("/home/trainee/mission/brief.txt"),
            ),
            Objective(
                "Enter the mission directory",
                "Goal: move into the mission folder so relative file commands work.\n\nType exactly:\ncd /home/trainee/mission\n\nExpected result: the prompt ends with /home/trainee/mission.",
                "Type: cd /home/trainee/mission",
                lambda app, r: app.fs.prompt_path() == "/home/trainee/mission",
            ),
            Objective(
                "Use grep to identify the target",
                "Goal: search the copied mission brief for the TARGET line.\n\nBecause you should now be inside /home/trainee/mission, type:\ngrep TARGET brief.txt\n\nAbsolute path also works:\ngrep TARGET /home/trainee/mission/brief.txt\n\nExpected output:\nTARGET: SERVER_ALPHA",
                "Type: grep TARGET brief.txt. Full path also works.",
                lambda app, r: r is not None and r.name == "grep" and r.success and "TARGET: SERVER_ALPHA" in r.output,
            ),
            Objective(
                "Create answer.txt with vi OR gvim",
                "Goal: create /home/trainee/mission/answer.txt and record the target.\n\nBecause you should be in /home/trainee/mission, type one of these:\nvi answer.txt\ngvim answer.txt\n\nAdd this exact line:\nTARGET=SERVER_ALPHA\n\nSave the file. In real Linux, vi/gvim can create a new file when you save, as long as the parent folder already exists.",
                "Use either vi answer.txt or gvim answer.txt. Add TARGET=SERVER_ALPHA, then save.",
                lambda app, r: app.fs.is_file("/home/trainee/mission/answer.txt")
                and "TARGET=SERVER_ALPHA" in app.fs.read_virtual("/home/trainee/mission/answer.txt"),
            ),
            Objective(
                "Copy the config template into mission",
                "Goal: place a config file into the mission package.\n\nSource file:\n/home/trainee/configs/template.conf\n\nDestination file:\n/home/trainee/mission/final.conf\n\nType exactly:\ncp /home/trainee/configs/template.conf /home/trainee/mission/final.conf\n\nExpected result: final.conf exists in /home/trainee/mission.",
                "Type: cp /home/trainee/configs/template.conf /home/trainee/mission/final.conf",
                lambda app, r: app.fs.is_file("/home/trainee/mission/final.conf"),
            ),
            Objective(
                "Edit final.conf so the service is enabled and owned",
                "Goal: update the mission config.\n\nBecause you should be in /home/trainee/mission, type one of these:\nvi final.conf\ngvim final.conf\n\nChange this line:\nenabled=false\n\nto:\nenabled=true\n\nChange this line:\nowner=unset\n\nto:\nowner=trainee\n\nSave the file.",
                "Open final.conf with vi or gvim. Change enabled=false to enabled=true and owner=unset to owner=trainee, then save.",
                lambda app, r: app.fs.is_file("/home/trainee/mission/final.conf")
                and "enabled=true" in app.fs.read_virtual("/home/trainee/mission/final.conf")
                and "owner=trainee" in app.fs.read_virtual("/home/trainee/mission/final.conf"),
            ),
            Objective(
                "Remove the stale archive temp file",
                "Goal: clean up the old temporary file.\n\nFile to remove:\n/home/trainee/archive/old.tmp\n\nFrom /home/trainee/mission, this relative command works:\nrm ../archive/old.tmp\n\nThe absolute path also works:\nrm /home/trainee/archive/old.tmp\n\nExpected result: old.tmp is removed.",
                "Use rm ../archive/old.tmp from /home/trainee/mission, or use rm /home/trainee/archive/old.tmp.",
                lambda app, r: not app.fs.exists("/home/trainee/archive/old.tmp"),
            ),
            Objective(
                "Verify the mission package with ll",
                "Goal: verify that the mission package contains answer.txt, brief.txt, and final.conf.\n\nBecause you should be in /home/trainee/mission, type:\nll\n\nAbsolute path also works:\nll /home/trainee/mission\n\nExpected result: the listing shows answer.txt, brief.txt, and final.conf.",
                "Type: ll from /home/trainee/mission. Full path also works.",
                lambda app, r: r is not None
                and r.name == "ll"
                and r.success
                and app.fs.is_file("/home/trainee/mission/answer.txt")
                and app.fs.is_file("/home/trainee/mission/brief.txt")
                and app.fs.is_file("/home/trainee/mission/final.conf"),
            ),
        ]

    def execute_command(self, command: str) -> CommandResult:
        if not command:
            return CommandResult("", [], "", "", True)
        try:
            parts = shlex.split(command)
        except ValueError as exc:
            return CommandResult("parse_error", [], command, f"shell: {exc}\n", False)
        if not parts:
            return CommandResult("", [], command, "", True)

        name = parts[0]
        args = parts[1:]

        if name == "ssh":
            return self._cmd_ssh(args, command)
        if not self.connected:
            return CommandResult(name, args, command, f"Not connected. Start with: ssh -X {TRAINING_HOST}\n", False)

        dispatch = {
            "pwd": self._cmd_pwd,
            "ls": self._cmd_ls,
            "ll": self._cmd_ll,
            "cd": self._cmd_cd,
            "mkdir": self._cmd_mkdir,
            "cp": self._cmd_cp,
            "rm": self._cmd_rm,
            "grep": self._cmd_grep,
            "cat": self._cmd_cat,
            "touch": self._cmd_touch,
            "vi": self._cmd_editor,
            "vim": self._cmd_editor,
            "gvim": self._cmd_editor,
            "clear": self._cmd_clear,
            "help": self._cmd_help,
        }
        func = dispatch.get(name)
        if not func:
            return CommandResult(name, args, command, f"{name}: command not found in trainer\nType help to see supported commands.\n", False)
        return func(args, command, name)

    def _cmd_ssh(self, args, raw):
        if args == ["-X", TRAINING_HOST]:
            self.connected = True
            self._refresh_sidebar()
            return CommandResult("ssh", args, raw, f"Connecting to {TRAINING_HOST} with X11 forwarding...\nWelcome to {TRAINING_HOST}.\n", True)
        return CommandResult("ssh", args, raw, "ssh: training target not recognized. Use: ssh -X linuxtraining22\n", False)

    def _cmd_pwd(self, args, raw, name):
        if args:
            return CommandResult(name, args, raw, "pwd: too many arguments\n", False)
        return CommandResult(name, args, raw, self.fs.prompt_path() + "\n", True)

    def _cmd_cd(self, args, raw, name):
        target = args[0] if args else "/home/trainee"
        ok, out = self.fs.cd(target)
        return CommandResult(name, args, raw, out, ok)

    def _cmd_ls(self, args, raw, name):
        long_format = False
        show_all = False
        paths = []
        for a in args:
            if a.startswith("-"):
                if "l" in a:
                    long_format = True
                if "a" in a:
                    show_all = True
            else:
                paths.append(a)
        if not paths:
            paths = ["."]
        out_parts = []
        success = True
        for idx, p in enumerate(paths):
            real = self.fs.smart_real_path_existing(p)
            if not real.exists():
                out_parts.append(f"ls: cannot access '{p}': No such file or directory\n")
                success = False
                continue
            if len(paths) > 1:
                out_parts.append(f"{p}:\n")
            if real.is_file():
                out_parts.append(self._format_ls_item(real, long_format) + "\n")
            else:
                entries = sorted(real.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                if show_all:
                    entries = [real / ".", real / ".."] + entries
                if long_format:
                    for e in entries:
                        out_parts.append(self._format_ls_item(e, True) + "\n")
                else:
                    visible = [e.name + ("/" if e.is_dir() else "") for e in entries if show_all or not e.name.startswith(".")]
                    out_parts.append("  ".join(visible) + ("\n" if visible else ""))
            if idx != len(paths) - 1:
                out_parts.append("\n")
        return CommandResult(name, args, raw, "".join(out_parts), success)

    def _cmd_ll(self, args, raw, name):
        result = self._cmd_ls(["-l"] + args, raw, "ll")
        result.name = "ll"
        return result

    def _format_ls_item(self, path: Path, long_format: bool) -> str:
        if not long_format:
            return path.name
        st = path.stat()
        perms = stat.filemode(st.st_mode)
        size = st.st_size
        mtime = time.strftime("%b %d %H:%M", time.localtime(st.st_mtime))
        suffix = "/" if path.is_dir() else ""
        return f"{perms} 1 {USERNAME} training {size:>6} {mtime} {path.name}{suffix}"

    def _cmd_mkdir(self, args, raw, name):
        if not args:
            return CommandResult(name, args, raw, "mkdir: missing operand\n", False)
        out = []
        success = True
        parents = False
        dirs = []
        for a in args:
            if a == "-p":
                parents = True
            else:
                dirs.append(a)
        for d in dirs:
            real = self.fs.real_path(d)
            try:
                real.mkdir(parents=parents, exist_ok=parents)
            except FileExistsError:
                out.append(f"mkdir: cannot create directory '{d}': File exists\n")
                success = False
            except FileNotFoundError:
                out.append(f"mkdir: cannot create directory '{d}': No such file or directory\n")
                success = False
        return CommandResult(name, args, raw, "".join(out), success)

    def _cmd_cp(self, args, raw, name):
        if len(args) != 2:
            return CommandResult(name, args, raw, "cp: expected source and destination\n", False)

        src, dest = args
        src_real = self.fs.smart_real_path_existing(src)
        dest_real = self.fs.output_real_path(dest)

        if not src_real.exists():
            return CommandResult(name, args, raw, f"cp: cannot stat '{src}': No such file or directory\n", False)
        if src_real.is_dir():
            return CommandResult(name, args, raw, "cp: -r not enabled in this trainer for directories\n", False)

        if dest_real.exists() and dest_real.is_dir():
            dest_real = dest_real / src_real.name
        else:
            if dest.endswith("/") or dest.endswith("\\"):
                return CommandResult(name, args, raw, f"cp: cannot create regular file '{dest}': No such directory\n", False)
            if not dest_real.parent.exists():
                return CommandResult(name, args, raw, f"cp: cannot create regular file '{dest}': No such file or directory\n", False)
            if not dest_real.parent.is_dir():
                return CommandResult(name, args, raw, f"cp: cannot create regular file '{dest}': Not a directory\n", False)

        shutil.copy2(src_real, dest_real)
        return CommandResult(name, args, raw, "", True)

    def _cmd_rm(self, args, raw, name):
        if not args:
            return CommandResult(name, args, raw, "rm: missing operand\n", False)
        recursive = False
        force = False
        targets = []
        for a in args:
            if a.startswith("-"):
                recursive = recursive or "r" in a or "R" in a
                force = force or "f" in a
            else:
                targets.append(a)
        out = []
        success = True
        for t in targets:
            real = self.fs.smart_real_path_existing(t)
            if not real.exists():
                if not force:
                    out.append(f"rm: cannot remove '{t}': No such file or directory\n")
                    success = False
                continue
            if real.is_dir():
                if recursive:
                    shutil.rmtree(real)
                else:
                    out.append(f"rm: cannot remove '{t}': Is a directory\n")
                    success = False
            else:
                real.unlink()
        return CommandResult(name, args, raw, "".join(out), success)

    def _cmd_grep(self, args, raw, name):
        if len(args) < 2:
            return CommandResult(name, args, raw, "grep: expected PATTERN and FILE\n", False)
        show_numbers = False
        clean_args = []
        for a in args:
            if a == "-n":
                show_numbers = True
            else:
                clean_args.append(a)
        if len(clean_args) < 2:
            return CommandResult(name, args, raw, "grep: expected PATTERN and FILE\n", False)
        pattern = clean_args[0]
        files = clean_args[1:]
        out = []
        success = True
        matched_any = False
        for f in files:
            real = self.fs.smart_real_path_existing(f)
            if not real.exists() or not real.is_file():
                out.append(f"grep: {f}: No such file\n")
                success = False
                continue
            lines = real.read_text(encoding="utf-8", errors="replace").splitlines()
            for n, line in enumerate(lines, start=1):
                if pattern in line:
                    matched_any = True
                    prefix = ""
                    if len(files) > 1:
                        prefix += f"{f}:"
                    if show_numbers:
                        prefix += f"{n}:"
                    out.append(prefix + line + "\n")
        if not matched_any and success:
            success = False
        return CommandResult(name, args, raw, "".join(out), success)

    def _cmd_cat(self, args, raw, name):
        if not args:
            return CommandResult(name, args, raw, "cat: missing file operand\n", False)
        out = []
        success = True
        for f in args:
            real = self.fs.smart_real_path_existing(f)
            if not real.exists() or not real.is_file():
                out.append(f"cat: {f}: No such file\n")
                success = False
            else:
                out.append(real.read_text(encoding="utf-8", errors="replace"))
                if not out[-1].endswith("\n"):
                    out.append("\n")
        return CommandResult(name, args, raw, "".join(out), success)

    def _cmd_touch(self, args, raw, name):
        if not args:
            return CommandResult(name, args, raw, "touch: missing file operand\n", False)
        out = []
        success = True
        for f in args:
            real = self.fs.output_real_path(f)
            if not real.parent.exists():
                out.append(f"touch: cannot touch '{f}': No such file or directory\n")
                success = False
                continue
            if not real.parent.is_dir():
                out.append(f"touch: cannot touch '{f}': Not a directory\n")
                success = False
                continue
            real.touch()
        return CommandResult(name, args, raw, "".join(out), success)

    def _cmd_editor(self, args, raw, name):
        if len(args) != 1:
            return CommandResult(name, args, raw, f"{name}: expected one file path\n", False)
        vpath = self.fs.output_virtual_path(args[0])
        real = self.fs._real_from_virtual(vpath)
        if real.exists() and real.is_dir():
            return CommandResult(name, args, raw, f"{name}: {args[0]} is a directory\n", False)
        if not real.parent.exists():
            return CommandResult(name, args, raw, f"{name}: {args[0]}: No such file or directory\n", False)
        if not real.parent.is_dir():
            return CommandResult(name, args, raw, f"{name}: {args[0]}: Not a directory\n", False)
        self._open_editor(vpath, real, name)
        return CommandResult(name, args, raw, f"Opening {name} editor for {vpath}\n", True)

    def _cmd_clear(self, args, raw, name):
        self.terminal.delete("1.0", "end")
        return CommandResult(name, args, raw, "", True)

    def _cmd_help(self, args, raw, name):
        return CommandResult(name, args, raw, """
Supported trainer commands:
  ssh -X linuxtraining22       connect to the training host
  pwd                          print current directory
  ls [path]                    list files
  ll [path]                    long listing
  cd [path]                    change directory
  cd ..                        move to parent directory
  mkdir [-p] name              create directory
  cp source dest               copy a file
  rm [-f] file                 remove a file
  grep [-n] PATTERN file       search file text
  cat file                     print file contents
  touch file                   create an empty file if parent folder exists
  vi file | gvim file          edit a file; new files are created on save
  clear                        clear terminal

Path tips:
  /home/trainee/training       absolute path
  training/readme.txt          relative path from /home/trainee
  brief.txt                    relative path from /home/trainee/mission
  Tab                          autocomplete paths
""".lstrip("\n"), True)

    def _open_editor(self, vpath: str, real: Path, editor_name: str) -> None:
        win = tk.Toplevel(self)
        win.title(f"{editor_name} - {vpath}")
        win.geometry("900x650")
        win.minsize(760, 540)
        win.configure(bg=BG)
        win.rowconfigure(1, weight=1)
        win.columnconfigure(0, weight=1)

        head = tk.Frame(win, bg=SURFACE_2, height=70)
        head.grid(row=0, column=0, sticky="ew")
        head.grid_propagate(False)
        head.columnconfigure(0, weight=1)
        tk.Label(head, text=f"{editor_name.upper()}  •  {vpath}", bg=SURFACE_2, fg=TEXT, font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w", padx=18, pady=(12, 0))
        tk.Label(head, text="Save with Ctrl+S, Save, Save & Close, or type :w / :wq in the bottom command box", bg=SURFACE_2, fg=TEXT_SOFT, font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", padx=18, pady=(4, 0))

        wrap = tk.Frame(win, bg=SURFACE, padx=14, pady=14)
        wrap.grid(row=1, column=0, sticky="nsew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        text = ScrolledText(wrap, wrap="word", font=("Cascadia Mono", 12), undo=True, bg=TERMINAL_BG, fg=TERMINAL_FG, insertbackground=ACCENT_2, relief="flat", borderwidth=0, padx=14, pady=14)
        text.grid(row=0, column=0, sticky="nsew")
        if real.exists():
            text.insert("1.0", real.read_text(encoding="utf-8", errors="replace"))
        else:
            text.insert("1.0", "")

        bottom = tk.Frame(win, bg=SURFACE_3, height=60)
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.grid_propagate(False)
        bottom.columnconfigure(0, weight=1)
        cmd_entry = tk.Entry(bottom, font=("Cascadia Mono", 11), bg="#12203A", fg=TEXT, insertbackground=TEXT, relief="flat", borderwidth=0)
        cmd_entry.grid(row=0, column=0, sticky="ew", padx=(16, 10), pady=12, ipady=8)
        cmd_entry.insert(0, ":")

        def save() -> None:
            real.write_text(text.get("1.0", "end-1c"), encoding="utf-8")

            # Treat Save, Ctrl+S, :w, and :wq as a successful vi/gvim action.
            # This makes either editor complete the objective after one saved edit.
            result = CommandResult(
                name=editor_name,
                args=[vpath],
                raw=f"{editor_name} {vpath}",
                output="",
                success=True,
            )
            self.last_result = result
            self._evaluate_objective(result)
            self._refresh_sidebar()

        def save_close() -> None:
            save()
            win.destroy()

        def command_submit(event=None):
            cmd = cmd_entry.get().strip()
            if cmd == ":wq":
                save_close()
            elif cmd == ":w":
                save()
            elif cmd == ":q!":
                win.destroy()
            else:
                self._show_popup("Editor Command", "Supported editor commands: :w, :wq, :q!")
            return "break"

        def text_area_command_submit(event=None):
            """Forgiving shortcut: allow :w, :wq, or :q! typed in the editor body.

            The preferred place is still the bottom command box, but this prevents
            users from getting stuck if they naturally type the vi command inside
            the editor body and press Enter.
            """
            current_line = text.get("insert linestart", "insert lineend").strip()
            if current_line not in {":w", ":wq", ":q!"}:
                return None

            # Remove the editor command from the file contents before saving.
            text.delete("insert linestart", "insert lineend")
            if current_line == ":wq":
                save_close()
            elif current_line == ":w":
                save()
            elif current_line == ":q!":
                win.destroy()
            return "break"

        ttk.Button(bottom, text="Save", style="Action.TButton", command=save).grid(row=0, column=1, padx=(0, 8), pady=10)
        ttk.Button(bottom, text="Save & Close", style="Action.TButton", command=save_close).grid(row=0, column=2, padx=(0, 16), pady=10)
        cmd_entry.bind("<Return>", command_submit)
        text.bind("<Return>", text_area_command_submit)
        text.bind("<Control-s>", lambda e: (save(), "break")[-1])
        text.focus_set()


if __name__ == "__main__":
    app = LinuxTrainerApp()
    app.mainloop()
