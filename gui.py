"""Tk desktop case board styled after Griductive's warm dark-noir interface.

All cards, portraits, icons, and pill buttons are drawn on Canvas using only
the Python standard library (tkinter / ttk).
"""
import tkinter as tk
from tkinter import font, ttk

from engine import GameEngine, clue_groups, load_puzzle
from logic_agent import DeductiveAgent
from models import Status, Verdict
from puzzle_generator import CASES, PUZZLES, generate

# ── Warm Dark-Noir Palette (inspired by original Griductive) ─────────────────
BG = "#1A1715"
TOPBAR = "#151210"
SURFACE = "#221E1B"
SURFACE_ALT = "#2A2521"
SURFACE_HOVER = "#36302B"
BORDER_SUBTLE = "#2F2A26"
BORDER_MID = "#4F4740"

CARD_BG = "#26221F"
CARD_HOVER = "#302B27"
CARD_BORDER = "#4E463F"
CARD_HOVER_BORDER = "#786D63"
CARD_SHADOW = "#110F0D"

CRIMINAL_BG = "#5C2B26"
CRIMINAL_BORDER = "#D96C62"
CRIMINAL_DIV = "#783B35"
CRIMINAL_TEXT = "#FAF3EC"
CRIMINAL_SUB = "#E2B5AF"

INNOCENT_BG = "#1F4438"
INNOCENT_BORDER = "#4FA884"
INNOCENT_DIV = "#2E6050"
INNOCENT_TEXT = "#F1FAF6"
INNOCENT_SUB = "#A1D1BE"

HIGHLIGHT = "#E6A94D"
FOCUS_RING = "#F4C970"

TEXT = "#F2ECE4"
TEXT_SOFT = "#BFB5AA"
MUTED = "#847A70"

BTN_INNOCENT = "#2E6F56"
BTN_INNOCENT_HOVER = "#3A8769"
BTN_CRIMINAL = "#A93F36"
BTN_CRIMINAL_HOVER = "#C44C42"
BTN_PRIMARY = "#D5953F"
BTN_PRIMARY_HOVER = "#E5A752"
BTN_PRIMARY_BORDER = "#ECB86A"
BTN_PAUSE = "#B5483E"
BTN_PAUSE_HOVER = "#CC564B"

DIFFICULTY_LEVELS = {
    "Easy": 2,
    "Normal": 4,
    "Medium": 5,
    "Hard": 6,
    "Stress": 7,
}

FEMININE_NAMES = {
    "Bea", "Clara", "Dana", "Eliza", "Emma", "Fern", "Hannah", "Iris", "Ivy",
    "Mara", "Mona", "Priya", "Quilla", "Ruby", "Sophia", "Uma", "Wendy", "Yara",
}
MASCULINE_NAMES = {
    "Abel", "Bruno", "Derek", "Franz", "Grant", "Gus", "Jonas", "Karl",
    "Leo", "Liam", "Noah", "Owen", "Roy", "Seth", "Tom", "Victor", "Xavier",
}

SANS = "Helvetica"
SERIF = "Georgia"
MONO = "Courier"


def rounded(canvas, box, radius=11, **style):
    """Draw a smooth rounded rectangle on a Tk Canvas."""
    x, y, right, bottom = box
    if right <= x or bottom <= y:
        return None
    r = min(radius, (right - x) / 2, (bottom - y) / 2)
    coords = (
        x + r, y, right - r, y, right, y, right, y + r,
        right, bottom - r, right, bottom, right - r, bottom,
        x + r, bottom, x, bottom, x, bottom - r, x, y + r, x, y,
    )
    return canvas.create_polygon(coords, smooth=True, splinesteps=12, **style)


def draw_vector_icon(canvas, kind, cx, cy, color, bg=SURFACE_ALT):
    """Draw crisp 14x14 minimalist vector icons with zero Unicode glyph reliance."""
    if kind == "pencil":
        canvas.create_line(cx - 4, cy + 4, cx + 3, cy - 3, fill=color, width=2, capstyle="round")
        canvas.create_polygon(cx - 5, cy + 5, cx - 5, cy + 2, cx - 2, cy + 5, fill=color, outline="")
        canvas.create_line(cx + 2, cy - 4, cx + 4, cy - 2, fill=color, width=1.6)
    elif kind == "bulb":
        canvas.create_oval(cx - 4, cy - 5, cx + 4, cy + 2, outline=color, width=1.5)
        canvas.create_line(cx - 2, cy + 3, cx + 2, cy + 3, fill=color, width=1.5)
        canvas.create_line(cx - 1.5, cy + 5, cx + 1.5, cy + 5, fill=color, width=1.4)
    elif kind == "step":
        canvas.create_polygon(cx - 3.5, cy - 4.5, cx + 4.5, cy, cx - 3.5, cy + 4.5, fill=color, outline="")
    elif kind == "play":
        canvas.create_polygon(cx - 5.5, cy - 4, cx + 0.5, cy, cx - 5.5, cy + 4, fill=color, outline="")
        canvas.create_polygon(cx + 0.5, cy - 4, cx + 6, cy, cx + 0.5, cy + 4, fill=color, outline="")
    elif kind == "pause":
        canvas.create_rectangle(cx - 4, cy - 4.5, cx - 1.5, cy + 4.5, fill=color, outline="")
        canvas.create_rectangle(cx + 1.5, cy - 4.5, cx + 4, cy + 4.5, fill=color, outline="")
    elif kind == "restart":
        canvas.create_arc(cx - 4.5, cy - 4.5, cx + 4.5, cy + 4.5, start=35, extent=290, style="arc", outline=color, width=1.6)
        canvas.create_polygon(cx + 2, cy - 5.5, cx + 5.5, cy - 2.5, cx + 1.5, cy - 1.5, fill=color, outline="")
    elif kind == "dice":
        canvas.create_rectangle(cx - 5, cy - 5, cx + 5, cy + 5, outline=color, width=1.4)
        for dx, dy in ((-2.2, -2.2), (2.2, -2.2), (0, 0), (-2.2, 2.2), (2.2, 2.2)):
            canvas.create_oval(cx + dx - 1, cy + dy - 1, cx + dx + 1, cy + dy + 1, fill=color, outline="")
    elif kind == "dot":
        canvas.create_oval(cx - 2.6, cy - 2.6, cx + 2.6, cy + 2.6, fill=color, outline="")
    elif kind == "shield":
        canvas.create_polygon(cx, cy - 5, cx + 4.5, cy - 2.5, cx + 3.5, cy + 2.5, cx, cy + 5, cx - 3.5, cy + 2.5, cx - 4.5, cy - 2.5, outline=color, fill="", width=1.4)
    elif kind == "spark":
        canvas.create_line(cx, cy - 4.5, cx, cy + 4.5, fill=color, width=1.5)
        canvas.create_line(cx - 4.5, cy, cx + 4.5, cy, fill=color, width=1.5)
        canvas.create_oval(cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5, fill=color, outline="")
    elif kind == "tap":
        canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, outline=color, width=1.4)
        canvas.create_oval(cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5, fill=color, outline="")


class PillButton(tk.Canvas):
    """Smooth rounded-pill Canvas button with crisp vector icon and hover state."""

    def __init__(self, parent, text, command, *, icon=None, bg=SURFACE_ALT, fg=TEXT,
                 hover=SURFACE_HOVER, border=BORDER_MID, parent_bg=BG, width=96, height=32):
        super().__init__(parent, width=width, height=height, bg=parent_bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._text = text
        self._command = command
        self._icon = icon
        self._bg = bg
        self._fg = fg
        self._hover_bg = hover
        self._border = border
        self._hovered = False
        self._bw = width
        self._bh = height

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self._render()

    def set_style(self, *, text=None, icon=None, bg=None, fg=None, hover=None, border=None):
        if text is not None:
            self._text = text
        if icon is not None:
            self._icon = icon
        if bg is not None:
            self._bg = bg
        if fg is not None:
            self._fg = fg
        if hover is not None:
            self._hover_bg = hover
        if border is not None:
            self._border = border
        self._render()

    def _render(self):
        self.delete("all")
        fill = self._hover_bg if self._hovered else self._bg
        rounded(self, (1, 1, self._bw - 1, self._bh - 1), radius=9, fill=fill, outline=self._border, width=1.2)
        cy = self._bh / 2
        if self._icon:
            # Measure text to center icon + text cleanly as a unit
            fnt = font.Font(family=SANS, size=9, weight="bold")
            tw = fnt.measure(self._text)
            total = 16 + tw
            start_x = (self._bw - total) / 2
            draw_vector_icon(self, self._icon, start_x + 6, cy, self._fg, fill)
            self.create_text(start_x + 17, cy, anchor="w", text=self._text, fill=self._fg, font=(SANS, 9, "bold"))
        else:
            self.create_text(self._bw / 2, cy, text=self._text, fill=self._fg, font=(SANS, 9, "bold"))

    def _on_enter(self, _e):
        self._hovered = True
        self._render()

    def _on_leave(self, _e):
        self._hovered = False
        self._render()

    def _on_click(self, _e):
        if callable(self._command):
            self._command()


def draw_detective_icon(canvas, cx, cy, size=26, fg=TEXT, accent=BG):
    """Minimal vector detective hat + silhouette icon (matching Griductive header)."""
    s = size / 28.0

    def pt(*vals):
        return [v * s + (cx if i % 2 == 0 else cy) for i, v in enumerate(vals)]

    canvas.create_polygon(
        pt(-12, 13, -9, 5, -4, 3, 4, 3, 9, 5, 12, 13),
        fill=fg, outline="", smooth=True,
    )
    canvas.create_polygon(pt(-3, 3, 0, 8, 3, 3), fill=accent, outline="")
    canvas.create_oval(pt(-5.5, -5, 5.5, 4.5), fill=fg, outline="")
    canvas.create_oval(pt(-12, -7.5, 12, -3.5), fill=fg, outline="")
    canvas.create_polygon(
        pt(-7, -5.5, -5.5, -13, -1, -11.5, 1, -11.5, 5.5, -13, 7, -5.5),
        fill=fg, outline="",
    )
    canvas.create_line(pt(-6.6, -6.5, 6.6, -6.5), fill=accent, width=max(1, round(1.5 * s)))


def portrait(canvas, x, y, size, person, tags, compact=False):
    """Clean flat-vector character bust with distinct hair, skin tone, and outfit."""
    seed = sum((n + 1) * ord(c) for n, c in enumerate(person.name))
    skins = ("#F3C8A0", "#E3AE82", "#C98B5E", "#9E6743", "#73462C")
    skin_shadows = ("#DDA97D", "#CA9166", "#AF7147", "#845232", "#5A351F")
    hairs = ("#2A201B", "#5B3B26", "#9E5329", "#D7A352", "#47342B", "#C57C44", "#231E24")
    skin_idx = seed % len(skins)
    skin = skins[skin_idx]
    skin_sh = skin_shadows[skin_idx]
    hair = hairs[(seed // 2) % len(hairs)]

    outfits = {
        "Astronaut": ("#D8DCD9", "#D87C4A"),
        "Cook": ("#EFEAE1", "#C45746"),
        "Chef": ("#EFEAE1", "#C45746"),
        "Guard": ("#3D546B", "#D9A74A"),
        "Detective": ("#8C7458", "#4A3A2C"),
        "Clerk": ("#597A73", "#D8CFC2"),
        "Farmer": ("#B87A3E", "#4A647B"),
        "Painter": ("#8E6288", "#E3C26B"),
        "Pilot": ("#435A75", "#E0B65C"),
        "Doctor": ("#E8ECEA", "#4A8B7C"),
    }
    coat, trim = outfits.get(person.profession, ("#6D7F76", "#D2C5B4"))
    scale = size / 60.0
    if person.name in FEMININE_NAMES:
        is_fem = True
    elif person.name in MASCULINE_NAMES:
        is_fem = False
    else:
        is_fem = (seed % 2 == 0)

    def shape(method, points, **kw):
        coords = [p * scale + (x if j % 2 == 0 else y) for j, p in enumerate(points)]
        return method(*coords, tags=tags, **kw)

    def oval(points, fill, **kw):
        return shape(canvas.create_oval, points, fill=fill, outline="", **kw)

    def poly(points, fill, **kw):
        return shape(canvas.create_polygon, points, fill=fill, outline="", **kw)

    def line(points, color, width=1.4):
        return shape(
            canvas.create_line, points, fill=color,
            width=max(1, round(width * scale)), smooth=True, capstyle="round",
        )

    style_id = (seed // 3) % 4
    if is_fem:
        if style_id == 0:
            oval((-7, -30, 7, -18), hair)
            oval((-14, -22, 14, 4), hair)
        elif style_id == 1:
            poly((-15, -14, -17, 10, -10, 15, 10, 15, 17, 10, 15, -14), hair, smooth=True)
            oval((-15, -24, 15, 4), hair)
        elif style_id == 2:
            oval((-17, -22, 17, 12), hair)
            oval((-14, -26, 14, -4), hair)
        else:
            poly((-15, -16, -16, 16, -9, 18, 9, 18, 16, 16, 15, -16), hair)
            oval((-15, -24, 15, 2), hair)
    elif style_id == 2:
        oval((-15.5, -25, 15.5, 1), hair)

    # Shoulders & torso (clean rounded bust floating directly on dark card)
    poly((-20, 26, -18, 15, -10, 11, 10, 11, 18, 15, 20, 26), coat, smooth=True)
    poly((-6, 11, 0, 19, 6, 11), trim)

    if person.profession == "Farmer":
        poly((-11, 12, -7, 12, -7, 25, -11, 25), trim)
        poly((7, 12, 11, 12, 11, 25, 7, 25), trim)
    elif person.profession == "Doctor" and not compact:
        line((-7, 12, -9, 19, -4, 23), trim, 1.8)
        line((7, 12, 9, 19, 4, 23), trim, 1.8)
        oval((-6, 21, -2, 25), trim)
    elif person.profession in ("Guard", "Pilot") and not compact:
        oval((6, 17, 11, 21), trim)
    elif person.profession == "Astronaut":
        line((-14, 15, 14, 15), trim, 2.2)

    # Neck & chin shadow
    oval((-4.5, 5, 4.5, 15), skin)
    oval((-4, 5, 4, 10), skin_sh)

    # Ears
    oval((-14.5, -7, -10.5, 0), skin)
    oval((10.5, -7, 14.5, 0), skin)

    # Face
    oval((-12.5, -20, 12.5, 8.5), skin)

    # Front hair / bangs
    if is_fem:
        if style_id in (0, 3):
            poly((-13, -10, -13, -19, -5, -24, 6, -24, 13, -18, 13, -10, 6, -15, -2, -16, -9, -12), hair, smooth=True)
        elif style_id == 1:
            poly((-13, -11, -13, -20, -4, -24, 5, -24, 13, -19, 13, -11, 4, -16, 0, -13, -6, -16), hair, smooth=True)
        else:
            for dx, dy, rad in ((-8, -19, 5), (-2, -21, 5.5), (5, -20, 5), (10, -16, 4)):
                oval((dx - rad, dy - rad, dx + rad, dy + rad), hair)
    else:
        if style_id == 0:
            poly((-13, -10, -13, -19, -6, -24, 6, -24, 13, -18, 13, -10, 7, -16, -4, -15, -10, -13), hair)
        elif style_id == 1:
            poly((-13, -10, -13, -18, -9, -24, -4, -21, 0, -25, 5, -21, 10, -24, 13, -17, 13, -10, 8, -15, -8, -15), hair)
        elif style_id == 2:
            for dx, dy, rad in ((-8, -18, 5), (-2, -21, 5.5), (5, -20, 5.2), (10, -16, 4.2)):
                oval((dx - rad, dy - rad, dx + rad, dy + rad), hair)
        else:
            poly((-13, -9, -13, -18, -7, -23, 5, -24, 13, -19, 13, -10, 5, -16, -6, -15), hair, smooth=True)

    # Eyes & brows
    eye_col = "#241D1A"
    for dx in (-5.2, 5.2):
        oval((dx - 1.7, -7.2, dx + 1.7, -3.5), eye_col)
        if not compact:
            oval((dx - 0.7, -6.7, dx + 0.4, -5.6), "#F8F3EC")
            line((dx - 2.6, -9.8, dx + 2.4, -9.8), hair, 1.3)

    # Cheeks & smile
    if not compact:
        blush = "#D98A7A" if skin_idx < 3 else "#A8624D"
        oval((-9.5, -2.5, -6.2, -0.3), blush)
        oval((6.2, -2.5, 9.5, -0.3), blush)
        line((-2.8, 1.8, 0, 3.6, 2.8, 1.8), skin_sh, 1.5)
    else:
        line((-2.2, 1.5, 0, 3.0, 2.2, 1.5), skin_sh, 1.2)

    # Profession headwear / glasses (positioned cleanly above eyebrows)
    if person.profession == "Detective":
        poly((-16, -17.5, 16, -17.5, 12, -20.5, -12, -20.5), coat)
        poly((-10.5, -19.5, -8, -28.5, 8, -28.5, 10.5, -19.5), coat)
        line((-10, -20, 10, -20), trim, 2.2)
    elif person.profession in ("Cook", "Chef"):
        for dx in (-6, 0, 6):
            oval((dx - 5.5, -29.5, dx + 5.5, -20.5), "#F6F2EA")
        poly((-10, -23.5, 10, -23.5, 9, -17.5, -9, -17.5), "#F6F2EA")
    elif person.profession == "Painter":
        oval((-13.5, -27, 12, -17), coat)
        line((-1, -27, 1, -29.5), coat, 2.0)
    elif person.profession in ("Guard", "Pilot"):
        poly((-13, -18, -10, -25, 10, -25, 13, -18), coat)
        line((-13, -18, 13, -18), "#1D242C", 2.4)
        if not compact:
            oval((-2, -23, 2, -20), trim)
    elif person.profession == "Clerk" or (seed % 5 == 0 and not compact):
        frame_col = "#3B312B"
        for dx in (-5.2, 5.2):
            shape(canvas.create_oval, (dx - 3.6, -8.5, dx + 3.6, -2.3), outline=frame_col, width=max(1, round(1.3 * scale)))
        line((-1.6, -5.6, 1.6, -5.6), frame_col, 1.2)


class GriductiveApp:
    """Dark-noir Griductive desktop interface with SAT/DPLL solver tools."""

    def __init__(self, root):
        global SANS, SERIF, MONO
        available = {f.casefold(): f for f in font.families(root)}
        SANS = next(
            (available[f] for f in (
                "inter", "segoe ui", "ubuntu", "noto sans", "dejavu sans",
                "liberation sans", "helvetica neue", "helvetica", "arial", "nimbus sans l",
            ) if f in available),
            "TkDefaultFont",
        )
        SERIF = next(
            (available[f] for f in (
                "playfair display", "georgia", "merriweather", "noto serif",
                "dejavu serif", "liberation serif", "bitstream charter",
                "palatino", "new century schoolbook", "times",
            ) if f in available),
            SANS,
        )
        MONO = next(
            (available[f] for f in (
                "jetbrains mono", "cascadia code", "ubuntu mono", "dejavu sans mono",
                "consolas", "courier new", "nimbus mono l", "courier",
            ) if f in available),
            "TkFixedFont",
        )

        self.root = root
        root.title("Griductive")
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{min(1380, sw - 40)}x{min(880, sh - 60)}")
        root.minsize(880, 620)
        root.configure(bg=BG)

        self.timer = self.animation = self.clock_job = None
        self.current = None
        self.highlights = set()
        self.overlay = self.focus = None
        self.hover_cell = None
        self.hover_btn = None
        self.flip = None
        self.flip_phase = 0
        self.boxes = {}
        self.metrics = {}
        self.marks = {}           # cell_id -> Status (pencil notes)
        self.mark_mode = False
        self.elapsed_sec = 0
        self.clock_paused = False
        self.active_tab = "guide"
        self.case_pills = []
        self.case_names = [f"{r}×{c}   {title}" for _, r, c, title, _, _ in CASES]
        self.case_var = tk.StringVar(value=self.case_names[0])

        self._configure_styles()
        self.build_layout()
        self.select_case()

    def _configure_styles(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Dark.TCombobox",
            fieldbackground=SURFACE_ALT,
            background=SURFACE_ALT,
            foreground=TEXT,
            arrowcolor=TEXT_SOFT,
            bordercolor=BORDER_MID,
            lightcolor=SURFACE_ALT,
            darkcolor=SURFACE_ALT,
            padding=(8, 4),
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", SURFACE_ALT)],
            foreground=[("readonly", TEXT)],
            selectbackground=[("readonly", SURFACE_ALT)],
            selectforeground=[("readonly", TEXT)],
            bordercolor=[("focus", HIGHLIGHT)],
        )
        style.configure(
            "Dark.Vertical.TScrollbar",
            background=SURFACE_ALT,
            troughcolor=BG,
            bordercolor=BG,
            arrowcolor=MUTED,
            relief="flat",
        )
        style.configure(
            "Dark.Horizontal.TScrollbar",
            background=SURFACE_ALT,
            troughcolor=BG,
            bordercolor=BG,
            arrowcolor=MUTED,
            relief="flat",
        )
        self.root.option_add("*TCombobox*Listbox.background", SURFACE_ALT)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#3E3630")
        self.root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
        self.root.option_add("*TCombobox*Listbox.font", (SANS, 9))

    def label(self, parent, text, *, font=None, fg=TEXT, bg=BG, **kw):
        return tk.Label(parent, text=text, font=font or (SANS, 10), fg=fg, bg=bg, **kw)

    def build_layout(self):
        # ── 1. Top Navigation Bar (Griductive chrome) ────────────────────────
        topbar = tk.Frame(self.root, bg=TOPBAR, height=46, padx=18)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        tk.Frame(self.root, bg=BORDER_SUBTLE, height=1).pack(fill="x")

        # Left wordmark
        left_nav = tk.Frame(topbar, bg=TOPBAR)
        left_nav.pack(side="left", fill="y")
        self.label(left_nav, "<  Griductive", font=(SERIF, 13, "bold"), fg=TEXT, bg=TOPBAR).pack(side="left", pady=10)

        # Center case stepper pill (1 .. 8 like MON EASY 1..7 SUN HARD)
        center_nav = tk.Frame(topbar, bg=TOPBAR)
        center_nav.place(relx=0.5, rely=0.5, anchor="center")
        pill_outer = tk.Frame(center_nav, bg=BORDER_SUBTLE, padx=1, pady=1)
        pill_outer.pack()
        pill_inner = tk.Frame(pill_outer, bg=SURFACE, padx=10, pady=3)
        pill_inner.pack()
        self.label(pill_inner, "EASY", font=(SANS, 7, "bold"), fg=MUTED, bg=SURFACE).pack(side="left", padx=(2, 8))
        self.case_pills = []
        for idx in range(len(CASES)):
            c = tk.Canvas(pill_inner, width=24, height=24, bg=SURFACE, highlightthickness=0, cursor="hand2")
            c.pack(side="left", padx=2)
            c.bind("<Button-1>", lambda _e, i=idx: self._pick_case_index(i))
            self.case_pills.append(c)
        self.label(pill_inner, "STRESS", font=(SANS, 7, "bold"), fg=MUTED, bg=SURFACE).pack(side="left", padx=(8, 2))

        # Right status cluster: timer + pause icon + solved count
        right_nav = tk.Frame(topbar, bg=TOPBAR)
        right_nav.pack(side="right", fill="y")
        self.progress = self.label(right_nav, "", font=(MONO, 9, "bold"), fg=HIGHLIGHT, bg=TOPBAR)
        self.progress.pack(side="right", padx=(14, 0))

        self.clock_icon = tk.Canvas(right_nav, width=20, height=20, bg=TOPBAR, highlightthickness=0, cursor="hand2")
        self.clock_icon.pack(side="right", padx=(6, 0), pady=13)
        self.clock_icon.bind("<Button-1>", lambda _e: self._toggle_clock())
        self._draw_clock_icon()

        self.clock_lbl = self.label(right_nav, "00:00", font=(MONO, 10, "bold"), fg=TEXT_SOFT, bg=TOPBAR)
        self.clock_lbl.pack(side="right")

        # ── 2. Main Split Body (Editorial Left Panel + Centered Board Right) ─
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)

        # Left Editorial Info & Solver Panel
        left_shell = tk.Frame(body, bg=BG, width=360)
        left_shell.pack(side="left", fill="y", padx=(30, 12), pady=(26, 16))
        left_shell.pack_propagate(False)

        # Brand hero (detective icon + serif Griductive title)
        hero = tk.Frame(left_shell, bg=BG)
        hero.pack(fill="x", anchor="w")
        icon_cv = tk.Canvas(hero, width=34, height=34, bg=BG, highlightthickness=0)
        icon_cv.pack(side="left", padx=(0, 8), pady=(4, 0))
        draw_detective_icon(icon_cv, 17, 18, size=28, fg=TEXT, accent=BG)
        self.label(hero, "Griductive", font=(SERIF, 24, "bold"), fg=TEXT, bg=BG).pack(side="left")

        # Meta badge row: [5x4 · CASE 01]   LEVEL ●●●●○○○
        meta = tk.Frame(left_shell, bg=BG)
        meta.pack(fill="x", pady=(8, 4))
        badge_border = tk.Frame(meta, bg=BORDER_MID, padx=1, pady=1)
        badge_border.pack(side="left")
        self.case_badge = self.label(badge_border, "5x4 · CASE 01", font=(SANS, 8, "bold"), fg=TEXT_SOFT, bg=SURFACE, padx=8, pady=2)
        self.case_badge.pack()
        self.label(meta, "LEVEL", font=(SANS, 8, "bold"), fg=MUTED, bg=BG).pack(side="left", padx=(12, 5))
        self.level_dots = tk.Canvas(meta, width=78, height=14, bg=BG, highlightthickness=0)
        self.level_dots.pack(side="left")

        # Case title & subtitle
        self.title = self.label(left_shell, "", font=(SERIF, 12), fg=TEXT_SOFT, bg=BG, anchor="w")
        self.title.pack(fill="x", pady=(4, 10))

        # Case selector dropdown (dark-styled, preserves tests/test_gui.py contract)
        combo_row = tk.Frame(left_shell, bg=BG)
        combo_row.pack(fill="x", pady=(0, 10))
        self.combo = ttk.Combobox(
            combo_row, textvariable=self.case_var, values=self.case_names,
            state="readonly", style="Dark.TCombobox", font=(SANS, 9),
        )
        self.combo.pack(fill="x")
        self.combo.bind("<<ComboboxSelected>>", lambda _e: self.select_case())

        tk.Frame(left_shell, bg=BORDER_SUBTLE, height=1).pack(fill="x", pady=(2, 10))

        # Active Evidence Card (warm amber left stripe)
        ev_head = tk.Frame(left_shell, bg=BG)
        ev_head.pack(fill="x", pady=(0, 5))
        self.label(ev_head, "EVIDENCE", font=(SANS, 8, "bold"), fg=MUTED, bg=BG).pack(side="left")
        self.ev_cell_badge = self.label(ev_head, "", font=(MONO, 8, "bold"), fg=HIGHLIGHT, bg=BG)
        self.ev_cell_badge.pack(side="right")

        ev_outer = tk.Frame(left_shell, bg=BORDER_SUBTLE, padx=1, pady=1)
        ev_outer.pack(fill="x")
        ev_inner = tk.Frame(ev_outer, bg=SURFACE)
        ev_inner.pack(fill="x")
        tk.Frame(ev_inner, bg=HIGHLIGHT, width=3).pack(side="left", fill="y")
        self.evidence = self.label(
            ev_inner, "", anchor="nw", justify="left", wraplength=318,
            font=(SANS, 10), fg=TEXT, bg=SURFACE, padx=11, pady=9,
        )
        self.evidence.pack(side="left", fill="x", expand=True)

        # Feedback line (verdicts / hint / solved banner)
        self.feedback = self.label(
            left_shell, "", bg=BG, fg=MUTED, anchor="w", justify="left",
            wraplength=348, font=(SANS, 9),
        )
        self.feedback.pack(fill="x", pady=(8, 10))

        # Segmented Tabs: How to Play | Solver Stats | Trace
        tab_bar = tk.Frame(left_shell, bg=SURFACE, padx=3, pady=3)
        tab_bar.pack(fill="x", pady=(0, 8))
        tab_bar.columnconfigure((0, 1, 2), weight=1, uniform="tabs")
        self.tab_btns = {}
        for col, (key, title) in enumerate((("guide", "How to Play"), ("solver", "Solver Stats"), ("trace", "Trace (0)"))):
            btn = tk.Button(
                tab_bar, text=title, command=lambda k=key: self._switch_tab(k),
                bg=SURFACE, fg=MUTED, activebackground=SURFACE_HOVER, activeforeground=TEXT,
                font=(SANS, 8, "bold"), relief="flat", bd=0, pady=5, cursor="hand2", highlightthickness=0,
            )
            btn.grid(row=0, column=col, sticky="ew", padx=1)
            self.tab_btns[key] = btn

        self.tab_host = tk.Frame(left_shell, bg=BG)
        self.tab_host.pack(fill="both", expand=True)

        # Tab 1: How to Play (crisp Canvas icons, matching original Griductive left column)
        self.tab_frames = {}
        guide = tk.Frame(self.tab_host, bg=BG, padx=2, pady=4)
        self.label(
            guide, "Every person is criminal or innocent, and every clue is true.",
            font=(SANS, 10), fg=TEXT_SOFT, bg=BG, wraplength=340, justify="left", anchor="w",
        ).pack(fill="x", pady=(0, 10))
        tips = (
            ("tap", "Tap a suspect to call them Innocent or Criminal."),
            ("spark", "A provable call flips the card and reveals a new clue."),
            ("shield", "Only call what the clues logically prove — no guessing."),
            ("pencil", "Use Mark (or right-click) for notes; Hint spotlights next step."),
            ("step", "Step / Auto Solve runs your CNF + DPLL agent live."),
        )
        for icon_kind, line in tips:
            row = tk.Frame(guide, bg=BG)
            row.pack(fill="x", pady=4)
            ic = tk.Canvas(row, width=18, height=18, bg=BG, highlightthickness=0)
            ic.pack(side="left", anchor="n", padx=(0, 6))
            draw_vector_icon(ic, icon_kind, 9, 9, HIGHLIGHT, BG)
            self.label(row, line, font=(SANS, 9), fg=MUTED, bg=BG, wraplength=318, justify="left", anchor="w").pack(side="left", fill="x")
        self.tab_frames["guide"] = guide

        # Tab 2: Solver Statistics
        solver = tk.Frame(self.tab_host, bg=BORDER_SUBTLE, padx=1, pady=1)
        solver_in = tk.Frame(solver, bg=SURFACE, padx=12, pady=10)
        solver_in.pack(fill="both", expand=True)
        for j, key in enumerate((
            "Solver Mode", "Primary Vars", "Aux Vars", "CNF Clauses", "SAT Calls",
            "Decisions", "Propagations", "Backtracks", "Runtime (ms)",
        )):
            self.label(solver_in, key, font=(SANS, 9), fg=MUTED, bg=SURFACE).grid(row=j, column=0, sticky="w", pady=2)
            lbl = self.label(solver_in, "--", font=(MONO, 9, "bold"), fg=TEXT, bg=SURFACE)
            lbl.grid(row=j, column=1, sticky="e", pady=2)
            self.metrics[key] = lbl
        solver_in.columnconfigure(0, weight=1)
        self.tab_frames["solver"] = solver

        # Tab 3: Deduction Trace
        trace = tk.Frame(self.tab_host, bg=BORDER_SUBTLE, padx=1, pady=1)
        trace_in = tk.Frame(trace, bg=SURFACE)
        trace_in.pack(fill="both", expand=True)
        log_scroll = ttk.Scrollbar(trace_in, style="Dark.Vertical.TScrollbar")
        log_scroll.pack(side="right", fill="y")
        self.log = tk.Text(
            trace_in, height=8, wrap="word", font=(SANS, 9),
            bg=SURFACE, fg=TEXT_SOFT, insertbackground=TEXT,
            padx=10, pady=8, relief="flat", state="disabled",
            yscrollcommand=log_scroll.set, highlightthickness=0,
        )
        self.log.pack(fill="both", expand=True)
        log_scroll.config(command=self.log.yview)
        self.tab_frames["trace"] = trace

        self._switch_tab("guide")

        # ── 3. Right / Center Board + Rounded Pill Toolbar ───────────────────
        right_shell = tk.Frame(body, bg=BG)
        right_shell.pack(side="right", fill="both", expand=True, padx=(4, 24), pady=(8, 12))

        area = tk.Frame(right_shell, bg=BG)
        area.pack(fill="both", expand=True)
        self.board = tk.Canvas(area, bg=BG, highlightthickness=0)
        self.vbar = ttk.Scrollbar(area, orient="vertical", command=self.board.yview, style="Dark.Vertical.TScrollbar")
        self.hbar = ttk.Scrollbar(area, orient="horizontal", command=self.board.xview, style="Dark.Horizontal.TScrollbar")
        self.board.configure(yscrollcommand=self.vbar.set, xscrollcommand=self.hbar.set)
        self.board.grid(row=0, column=0, sticky="nsew")
        area.rowconfigure(0, weight=1)
        area.columnconfigure(0, weight=1)

        # Bottom Pill Toolbar (smooth rounded pills with crisp vector icons)
        toolbar_host = tk.Frame(right_shell, bg=BG)
        toolbar_host.pack(fill="x", pady=(6, 0))
        toolbar = tk.Frame(toolbar_host, bg=BG)
        toolbar.pack(anchor="center")

        self.mark_btn = PillButton(toolbar, "Mark", self.toggle_mark, icon="pencil", width=82)
        self.mark_btn.pack(side="left", padx=4)
        PillButton(toolbar, "Hint", self.hint, icon="bulb", width=78).pack(side="left", padx=4)
        PillButton(toolbar, "Step", self.step, icon="step", width=78).pack(side="left", padx=4)
        self.auto_btn = PillButton(
            toolbar, "Auto Solve", self.toggle_auto, icon="play",
            bg=BTN_PRIMARY, fg="#171412", hover=BTN_PRIMARY_HOVER,
            border=BTN_PRIMARY_BORDER, width=116,
        )
        self.auto_btn.pack(side="left", padx=4)
        PillButton(toolbar, "Restart", self.restart, icon="restart", width=92).pack(side="left", padx=4)
        PillButton(toolbar, "New Case", self.generate_new, icon="dice", width=106).pack(side="left", padx=4)

        # Bind canvas & global shortcuts
        self.board.bind("<Configure>", lambda _e: self.draw())
        self.board.bind("<Button-1>", self.board_click)
        self.board.bind("<Button-3>", self.board_right_click)
        self.board.bind("<Motion>", self.board_motion)
        self.board.bind("<Leave>", self.board_leave)
        self.board.bind("<MouseWheel>", lambda e: self.board.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        for event, delta in (("<Button-4>", -1), ("<Button-5>", 1)):
            self.board.bind(event, lambda _e, d=delta: self.board.yview_scroll(d, "units"))
        self.root.bind("<Escape>", lambda _e: self.dismiss())
        self.root.bind("<Key-m>", lambda _e: self.toggle_mark())
        self.root.bind("<Key-h>", lambda _e: self.hint())

    # ── UI Helpers ───────────────────────────────────────────────────────────
    def _switch_tab(self, key):
        self.active_tab = key
        for k, frame in self.tab_frames.items():
            frame.pack_forget()
        self.tab_frames[key].pack(fill="both", expand=True)
        for k, btn in self.tab_btns.items():
            btn.config(bg=SURFACE_HOVER if k == key else SURFACE, fg=TEXT if k == key else MUTED)

    def _draw_case_pills(self, active_idx=None):
        for idx, cv in enumerate(self.case_pills):
            cv.delete("all")
            if idx == active_idx:
                cv.create_oval(2, 2, 22, 22, fill=SURFACE_HOVER, outline=TEXT, width=1.5)
                cv.create_text(12, 12, text=str(idx + 1), fill=TEXT, font=(SANS, 8, "bold"))
            else:
                cv.create_text(12, 12, text=str(idx + 1), fill=MUTED, font=(SANS, 8, "bold"))

    def _draw_level_dots(self, difficulty):
        cv = self.level_dots
        cv.delete("all")
        filled = DIFFICULTY_LEVELS.get(difficulty, 4)
        for i in range(7):
            cx = 6 + i * 11
            col = CRIMINAL_BORDER if i < filled else "#3A342F"
            cv.create_oval(cx - 3.5, 3.5, cx + 3.5, 10.5, fill=col, outline="")

    def _draw_clock_icon(self):
        self.clock_icon.delete("all")
        draw_vector_icon(self.clock_icon, "step" if self.clock_paused else "pause", 10, 10, TEXT_SOFT, TOPBAR)

    def _pick_case_index(self, idx):
        self.combo.current(idx)
        self.select_case()

    def _start_clock(self):
        if self.clock_job is not None:
            self.root.after_cancel(self.clock_job)
        self.elapsed_sec = 0
        self.clock_paused = False
        self._draw_clock_icon()
        self._update_clock_label()
        self.clock_job = self.root.after(1000, self._tick_clock)

    def _tick_clock(self):
        self.clock_job = None
        if self.current is None:
            return
        state = self.engine.public_state()
        if not self.clock_paused and len(state.known) < len(state.people):
            self.elapsed_sec += 1
            self._update_clock_label()
        self.clock_job = self.root.after(1000, self._tick_clock)

    def _toggle_clock(self):
        self.clock_paused = not self.clock_paused
        self._draw_clock_icon()

    def _update_clock_label(self):
        mins, secs = divmod(self.elapsed_sec, 60)
        self.clock_lbl.config(text=f"{mins:02d}:{secs:02d}")

    def toggle_mark(self):
        self.mark_mode = not self.mark_mode
        if self.mark_mode:
            self.overlay = None
            self.mark_btn.set_style(bg="#493822", fg=HIGHLIGHT, hover="#5C472B", border=HIGHLIGHT)
            self.feedback.config(text="Mark mode ON · Click thẻ úp để đánh dấu nghi vấn (I? / C?).", fg=HIGHLIGHT)
        else:
            self.mark_btn.set_style(bg=SURFACE_ALT, fg=TEXT, hover=SURFACE_HOVER, border=BORDER_MID)
            self.feedback.config(text="Chọn thẻ đã mở để xem manh mối, hoặc thẻ úp để đưa ra phán quyết.", fg=MUTED)
        self.draw()

    def _cycle_mark(self, cell_id):
        cur = self.marks.get(cell_id)
        if cur is None:
            self.marks[cell_id] = Status.INNOCENT
        elif cur == Status.INNOCENT:
            self.marks[cell_id] = Status.CRIMINAL
        else:
            self.marks.pop(cell_id, None)
        self.draw()

    # ── Case Loading & Lifecycle ─────────────────────────────────────────────
    def select_case(self):
        index = self.case_names.index(self.case_var.get())
        self.base_index = index
        self._draw_case_pills(index)
        self.load(load_puzzle(PUZZLES / (CASES[index][0] + ".json")), case_num=index + 1)

    def generate_new(self):
        _, r, c, _, difficulty, ext = CASES[self.base_index]
        self._draw_case_pills(None)
        self.load(generate(r, c, extensions=ext, title="New Inquiry", difficulty=difficulty), case_num=None)
        self.case_var.set(f"{r}×{c}   Generated case")

    def load(self, puzzle, case_num=None):
        self.stop()
        self.current = puzzle
        self.engine = GameEngine(puzzle)
        self.agent = DeductiveAgent(self.engine)
        self.overlay = self.focus = None
        self.hover_cell = self.hover_btn = None
        self.highlights.clear()
        self.marks.clear()

        tag = f"CASE {case_num:02d}" if case_num is not None else "GENERATED"
        self.case_badge.config(text=f"{puzzle.num_rows}x{puzzle.num_cols} · {tag}")
        self._draw_level_dots(puzzle.difficulty)
        self.title.config(text=f"{puzzle.title}  ·  {puzzle.difficulty}")
        self.feedback.config(text="Chọn thẻ đã mở để xem manh mối, hoặc thẻ úp để đưa ra phán quyết.", fg=MUTED)

        state = self.engine.public_state()
        first = state.clues[0]
        self.evidence.config(text=f"{first.owner_cell}   {first.text}")
        self.ev_cell_badge.config(text=first.owner_cell)
        self.highlights = self.references(first)
        self.focus = first.owner_cell
        # Probe on public data so the displayed backend is the one that actually ran.
        self.agent.classify(state, first.owner_cell)
        self.board.xview_moveto(0)
        self.board.yview_moveto(0)
        self._start_clock()
        self.refresh()

    def references(self, clue):
        return {i for group in clue_groups(clue, self.current.num_rows, self.current.num_cols) for i in group}

    def restart(self):
        self.load(self.current, case_num=self.base_index + 1 if "Generated" not in self.case_var.get() else None)

    def stop(self):
        for attr in ("timer", "animation"):
            handle = getattr(self, attr)
            if handle is not None:
                self.root.after_cancel(handle)
                setattr(self, attr, None)
        self.flip = None
        self.auto_btn.set_style(
            text="Auto Solve", icon="play",
            bg=BTN_PRIMARY, fg="#171412", hover=BTN_PRIMARY_HOVER, border=BTN_PRIMARY_BORDER,
        )

    def dismiss(self):
        self.overlay = None
        if self.mark_mode:
            self.toggle_mark()
        else:
            self.draw()

    def refresh(self):
        state = self.engine.public_state()
        self.progress.config(text=f"{len(state.known)} / {len(state.people)} OPEN")
        stats = self.agent.stats
        vals = [
            stats.mode, stats.primary_vars, stats.aux_vars, stats.cnf_clauses, stats.sat_calls,
            stats.decisions, stats.propagations, stats.backtracks, f"{stats.runtime_sec * 1000:.2f}",
        ]
        for key, (label, value) in zip(self.metrics.keys(), zip(self.metrics.values(), vals)):
            label.config(text=str(value))
            if key == "Solver Mode":
                label.config(fg=INNOCENT_BORDER if str(value).upper() == "DPLL" else HIGHLIGHT)

        entries = self.agent.trace.entries
        self.tab_btns["trace"].config(text=f"Trace ({len(entries)})")
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.insert("end", "\n".join(entries) if entries else "Chưa có bước suy diễn nào được ghi nhận.")
        self.log.see("end")
        self.log.config(state="disabled")

        if len(state.known) == len(state.people):
            self.feedback.config(text="Đã phá án! Mọi phán quyết đều có đủ bằng chứng logic.", fg=INNOCENT_BORDER)
        self.draw()

    # ── Canvas Board Rendering ───────────────────────────────────────────────
    def draw(self):
        if self.current is None:
            return
        canvas = self.board
        canvas.delete("all")
        state = self.engine.public_state()
        rows, cols = state.num_rows, state.num_cols

        view_w = max(canvas.winfo_width(), 520)
        view_h = max(canvas.winfo_height(), 500)
        pad_x, pad_y = 20, 10
        gap = 9

        # Crisp near-square cards that fit 5x4 cleanly without scrollbars on standard displays
        avail_w = view_w - 2 * pad_x - (cols - 1) * gap
        avail_h = view_h - 2 * pad_y - (rows - 1) * gap
        max_ch = avail_h / rows
        max_cw = avail_w / cols

        ch = max(120.0, min(150.0, max_ch))
        cw = max(122.0, min(148.0, max_cw, ch * 1.05))
        ch = max(120.0, min(ch, cw * 1.12))

        grid_w = cols * cw + (cols - 1) * gap
        grid_h = rows * ch + (rows - 1) * gap
        total_w = max(view_w, grid_w + 2 * pad_x)
        total_h = max(view_h, grid_h + 2 * pad_y)

        if grid_h + 2 * pad_y > view_h + 4:
            self.vbar.grid(row=0, column=1, sticky="ns")
        else:
            self.vbar.grid_remove()
        if grid_w + 2 * pad_x > view_w + 4:
            self.hbar.grid(row=1, column=0, sticky="ew")
        else:
            self.hbar.grid_remove()

        canvas.config(scrollregion=(0, 0, total_w, total_h))

        ox = max(pad_x, (total_w - grid_w) / 2)
        oy = max(pad_y, (total_h - grid_h) / 2)

        clues = {c.owner_cell: c for c in state.clues}
        self.boxes.clear()
        for person in state.people:
            x = ox + (person.col - 1) * (cw + gap)
            y = oy + (person.row - 1) * (ch + gap)
            box = (x, y, x + cw, y + ch)
            self.boxes[person.cell_id] = box
            self.card(person, box, state.known.get(person.cell_id), clues.get(person.cell_id))

    def card(self, p, box, status, clue):
        cv = self.board
        x, y, r, b = box
        tags = (p.cell_id,)

        if p.cell_id == self.flip:
            shrink = (r - x) * (0.36, 0.18, 0.06, 0.0)[self.flip_phase]
            x, r = x + shrink, r - shrink

        w, h = r - x, b - y
        cx = (x + r) / 2
        is_hover = (self.hover_cell == p.cell_id)
        is_focus = (p.cell_id == self.focus)
        is_ref = (p.cell_id in self.highlights)

        # Soft shadow
        rounded(cv, (x, y + 3, r, b + 3), radius=11, fill=CARD_SHADOW, outline="")

        # Card surface & border
        if self.overlay == p.cell_id:
            fill, edge, lw = "#2D2824", "#8A7E72", 2
        elif status == Status.INNOCENT:
            fill, edge, lw = INNOCENT_BG, INNOCENT_BORDER, 2
        elif status == Status.CRIMINAL:
            fill, edge, lw = CRIMINAL_BG, CRIMINAL_BORDER, 2
        else:
            fill = CARD_HOVER if is_hover else CARD_BG
            edge = CARD_HOVER_BORDER if is_hover else CARD_BORDER
            lw = 1.5

        rounded(cv, (x, y, r, b), radius=11, fill=fill, outline=edge, width=lw)

        # Highlight glow ring for focused / referenced / hint cards
        if is_focus or is_ref:
            ring_col = FOCUS_RING if is_focus else HIGHLIGHT
            ring_w = 2.6 if is_focus else 2.0
            rounded(cv, (x - 2, y - 2, r + 2, b + 2), radius=13, fill="", outline=ring_col, width=ring_w)

        if p.cell_id == self.flip and self.flip_phase < 2:
            return

        # Coordinate top-left
        coord_col = INNOCENT_SUB if status == Status.INNOCENT else CRIMINAL_SUB if status == Status.CRIMINAL else MUTED
        cv.create_text(x + 9, y + 7, anchor="nw", text=p.cell_id, font=(SANS, 8, "bold"), fill=coord_col)

        # ── Verdict Overlay Mode (y+60 -> Innocent, y+95 -> Criminal) ────────
        if self.overlay == p.cell_id:
            cv.create_text(r - 10, y + 8, anchor="ne", text="x", font=(SANS, 9, "bold"), fill=MUTED)
            portrait(cv, x + 28, y + 25, 21, p, tags, compact=True)
            cv.create_text(x + 43, y + 20, anchor="w", text=p.name, fill=TEXT, font=(SERIF, 10, "bold"))
            cv.create_text(x + 43, y + 34, anchor="w", text=p.profession, fill=MUTED, font=(SANS, 8))

            btn_specs = (
                (0, "Innocent", BTN_INNOCENT, BTN_INNOCENT_HOVER, "#D8F6E8"),
                (1, "Criminal", BTN_CRIMINAL, BTN_CRIMINAL_HOVER, "#FFE1DD"),
            )
            for j, label, col, col_h, txt_col in btn_specs:
                top = y + 48 + j * 34
                active = self.hover_btn == (p.cell_id, j)
                rounded(cv, (x + 10, top, r - 10, top + 28), radius=8, fill=col_h if active else col, outline="")
                cv.create_text(cx, top + 14, text=label, fill=txt_col, font=(SANS, 9, "bold"))
            return

        # ── Revealed Card Layout (modeled on B3 Jonas in original screenshot) ─
        if status is not None:
            txt_col = INNOCENT_TEXT if status == Status.INNOCENT else CRIMINAL_TEXT
            sub_col = INNOCENT_SUB if status == Status.INNOCENT else CRIMINAL_SUB
            div_col = INNOCENT_DIV if status == Status.INNOCENT else CRIMINAL_DIV

            dot_col = INNOCENT_BORDER if status == Status.INNOCENT else CRIMINAL_BORDER
            cv.create_oval(r - 14, y + 9, r - 8, y + 15, fill=dot_col, outline="")

            portrait(cv, cx - 25, y + 23, 21, p, tags, compact=True)
            cv.create_text(cx - 10, y + 17, anchor="w", text=p.name, font=(SANS, 9, "bold"), fill=txt_col)
            cv.create_text(cx - 10, y + 30, anchor="w", text=p.profession, font=(SANS, 8), fill=sub_col)

            cv.create_line(x + 12, y + 41, r - 12, y + 41, fill=div_col, width=1)

            body_top = y + 46
            body_cy = (body_top + b - 6) / 2
            max_w = max(60, w - 18)
            item = cv.create_text(
                cx, body_cy, text=clue.text, anchor="center", width=max_w,
                font=(SANS, 9), fill=txt_col, justify="center",
            )
            bb = cv.bbox(item)
            if bb and (bb[1] < body_top or bb[3] > b - 4):
                cv.itemconfigure(item, font=(SANS, 8))
                bb = cv.bbox(item)
            if bb and (bb[1] < body_top or bb[3] > b - 4):
                words = clue.text.split()
                while len(words) > 2:
                    words.pop()
                    cv.itemconfigure(item, text=" ".join(words) + "...")
                    bb = cv.bbox(item)
                    if bb and bb[1] >= body_top and bb[3] <= b - 4:
                        break
            return

        # ── Unrevealed Suspect Card (floating avatar + Name + Profession) ────
        mark = self.marks.get(p.cell_id)
        if mark is not None:
            m_bg = INNOCENT_BG if mark == Status.INNOCENT else CRIMINAL_BG
            m_fg = INNOCENT_BORDER if mark == Status.INNOCENT else CRIMINAL_BORDER
            m_txt = "I?" if mark == Status.INNOCENT else "C?"
            rounded(cv, (r - 27, y + 6, r - 7, y + 21), radius=6, fill=m_bg, outline=m_fg, width=1)
            cv.create_text(r - 17, y + 13.5, text=m_txt, font=(SANS, 7, "bold"), fill=m_fg)

        avatar_size = max(42, min(56, h * 0.41))
        portrait(cv, cx, y + h * 0.40, avatar_size, p, tags, compact=False)
        cv.create_text(cx, b - 29, text=p.name, font=(SANS, 10, "bold"), fill=TEXT)
        cv.create_text(cx, b - 14, text=p.profession, font=(SANS, 8), fill=MUTED)

    # ── Mouse Interactions ───────────────────────────────────────────────────
    def board_motion(self, event):
        px, py = self.board.canvasx(event.x), self.board.canvasy(event.y)
        new_hover = None
        new_btn = None
        for i, (x, y, r, b) in self.boxes.items():
            if x <= px <= r and y <= py <= b:
                new_hover = i
                if self.overlay == i and x + 9 <= px <= r - 9:
                    for j in (0, 1):
                        if y + 48 + j * 34 <= py <= y + 76 + j * 34:
                            new_btn = (i, j)
                            break
                break
        if new_hover != self.hover_cell or new_btn != self.hover_btn:
            self.hover_cell, self.hover_btn = new_hover, new_btn
            self.board.config(cursor="hand2" if new_hover else "")
            self.draw()

    def board_leave(self, _event):
        if self.hover_cell is not None or self.hover_btn is not None:
            self.hover_cell = self.hover_btn = None
            self.board.config(cursor="")
            self.draw()

    def board_right_click(self, event):
        px, py = self.board.canvasx(event.x), self.board.canvasy(event.y)
        state = self.engine.public_state()
        for i, (x, y, r, b) in self.boxes.items():
            if x <= px <= r and y <= py <= b:
                if i not in state.known:
                    self._cycle_mark(i)
                return

    def board_click(self, event):
        px, py = self.board.canvasx(event.x), self.board.canvasy(event.y)
        for i, (x, y, r, b) in self.boxes.items():
            if x <= px <= r and y <= py <= b:
                state = self.engine.public_state()
                self.stop()
                if i in state.known:
                    clue = next(c for c in state.clues if c.owner_cell == i)
                    self.overlay = None
                    self.focus = i
                    self.highlights = self.references(clue)
                    self.evidence.config(text=f"{i}   {clue.text}")
                    self.ev_cell_badge.config(text=i)
                elif self.mark_mode:
                    self._cycle_mark(i)
                    return
                elif self.overlay == i and x + 9 <= px <= r - 9:
                    for j, s in enumerate((Status.INNOCENT, Status.CRIMINAL)):
                        if y + 48 + j * 34 <= py <= y + 76 + j * 34:
                            self.submit(i, s)
                            return
                    self.overlay = None
                else:
                    self.overlay = i
                self.draw()
                return
        self.overlay = None
        self.draw()

    # ── Gameplay & AI Solver Actions ─────────────────────────────────────────
    def hint(self):
        self.stop()
        self.overlay = None
        hint = self.agent.get_hint()
        if hint:
            self.focus, self.highlights = hint.cell_id, set(hint.related)
            related = [c for c in self.engine.public_state().clues if c.owner_cell in self.highlights]
            self.evidence.config(text="\n".join(f"{c.owner_cell}   {c.text}" for c in related))
            self.ev_cell_badge.config(text=f"HINT -> {hint.cell_id}")
            self.feedback.config(text=f"Hint · {hint.cell_id} có thể kết luận. Xem các manh mối được đánh dấu.", fg=HIGHLIGHT)
        self.refresh()
        if hint:
            self.show_card(hint.cell_id)

    def show_card(self, i):
        x, y, r, b = self.boxes[i]
        cv = self.board
        region = cv.cget("scrollregion")
        if not region:
            return
        _, _, w, h = map(float, region.split())
        if h > 0 and (y < cv.canvasy(0) or b > cv.canvasy(cv.winfo_height())):
            cv.yview_moveto(max(0, (y - 10) / h))
        if w > 0 and (x < cv.canvasx(0) or r > cv.canvasx(cv.winfo_width())):
            cv.xview_moveto(max(0, (x - 10) / w))

    def submit(self, i, status):
        result = self.agent.submit(i, status)
        self.overlay = None
        if result == Verdict.ACCEPTED:
            self.marks.pop(i, None)
            self.reveal(i)
        else:
            msg = {
                Verdict.NOT_PROVABLE: "Chưa đủ cơ sở logic bắt buộc để kết luận nhân vật này! Không được đoán mò.",
                Verdict.CONTRADICTED: "Phán quyết này MÂU THUẪN với kết quả suy diễn bắt buộc từ các manh mối hiện tại!",
            }
            self.feedback.config(text=f"{result.value}: {msg.get(result, 'Kiểm tra lại trạng thái bàn.')}", fg=CRIMINAL_BORDER)
            self.refresh()

    def reveal(self, i):
        self.focus = i
        self.marks.pop(i, None)
        clue = next(c for c in self.engine.public_state().clues if c.owner_cell == i)
        self.highlights = self.references(clue)
        self.evidence.config(text=f"{i}   {clue.text}")
        self.ev_cell_badge.config(text=i)
        self.feedback.config(text=f"ACCEPTED · Đã mở {i}.", fg=INNOCENT_BORDER)
        if self.animation is not None:
            self.root.after_cancel(self.animation)
        self.flip, self.flip_phase = i, 0
        self.refresh()
        self.show_card(i)

        def advance():
            self.flip_phase += 1
            if self.flip_phase == 3:
                self.flip = self.animation = None
            else:
                self.animation = self.root.after(42, advance)
            self.draw()

        self.animation = self.root.after(42, advance)

    def step(self):
        self.stop()
        self.advance_one()

    def advance_one(self):
        self.overlay = None
        hint = self.agent.step()
        if hint:
            self.reveal(hint.cell_id)
        else:
            self.refresh()
        return bool(hint)

    def toggle_auto(self):
        if self.timer is not None:
            self.stop()
            self.draw()
            return
        self.auto_btn.set_style(
            text="Pause", icon="pause",
            bg=BTN_PAUSE, fg=TEXT, hover=BTN_PAUSE_HOVER, border=CRIMINAL_BORDER,
        )

        def tick():
            self.timer = None
            if self.advance_one():
                self.timer = self.root.after(390, tick)
            else:
                self.stop()

        tick()
