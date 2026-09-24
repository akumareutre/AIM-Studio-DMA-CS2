#!/usr/bin/env python3
"""Menu Tk léger : profils, point de visée et contrôle du moteur DMA."""

import json
import math
import os
from pathlib import Path
import queue
import signal
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, filedialog

from aim_profiles import PROFILES, BODY_PARTS
from aim_control import HOTKEYS
from aim_illustration import draw_operator
import aim_i18n as i18n

ROOT = Path(__file__).resolve().parent
PREFERENCES = ROOT / "aim-preferences.json"
# Palette graphite : surfaces bleu ardoise et accent menthe/cyan.
BG, CARD, INNER, BORDER = "#0b1017", "#121b25", "#1a2734", "#293b4a"
TEXT, MUTED = "#e8f0f5", "#8c9eae"
ACCENT, ACCENT_HOVER = "#58e0d0", "#a0f5e9"
BLUE, RED, GREEN, YELLOW = "#7ca2fa", "#f87171", "#7ce8a8", "#fbbf24"


def auto_map():
    """Libellé du mode automatique du sélecteur de carte (traduit)."""
    return i18n.t("auto.map")


class AccentScale(tk.Canvas):
    def __init__(self, parent, variable, low, high, step, changed):
        super().__init__(parent, height=23, bg=CARD, highlightthickness=0, takefocus=True)
        self.variable, self.low, self.high, self.step = variable, low, high, step
        self.changed = changed
        variable.trace_add("write", lambda *_: self.paint())
        self.bind("<Configure>", lambda _: self.paint())
        self.bind("<Button-1>", self.drag)
        self.bind("<B1-Motion>", self.drag)
        self.bind("<Left>", lambda _: self.set_value(variable.get() - step))
        self.bind("<Right>", lambda _: self.set_value(variable.get() + step))

    def configure(self, cnf=None, **kwargs):
        result = super().configure(cnf, **kwargs)
        if "state" in kwargs and hasattr(self, "variable"):
            self.paint()
        return result

    def set_value(self, value):
        if self.cget("state") == "disabled":
            return
        self.variable.set(max(self.low, min(self.high, self.low + round((value-self.low)/self.step)*self.step)))
        self.changed()

    def drag(self, event):
        self.focus_set()
        self.set_value(self.low + (event.x-8)/max(1, self.winfo_width()-16)*(self.high-self.low))

    def paint(self):
        self.delete("all")
        width = max(20, self.winfo_width())
        x = 8 + (width-16)*(self.variable.get()-self.low)/(self.high-self.low)
        color = MUTED if self.cget("state") == "disabled" else ACCENT
        self.create_line(8, 12, width-8, 12, fill=BORDER, width=4, capstyle="round")
        self.create_line(8, 12, max(8, x), 12, fill=color, width=4, capstyle="round")
        self.create_oval(x-5, 7, x+5, 17, fill=color, outline=CARD, width=2)


class AimMenu(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AIM Studio DMA · CS2 / KMBox")
        self.geometry("1120x980")
        self.minsize(1050, 940)
        self.configure(bg=BG)
        self.option_add("*Font", ("DejaVu Sans", 10))
        self.process = None
        self.offset_process = None
        self.events = queue.Queue(maxsize=1000)
        self.closing = False
        self.stopping = False
        self.controls = []
        self.static_texts = []
        self.mappick = None
        self.map_box = None
        self.mode = "magnetic"
        self.body = "head"
        self.visibility = tk.BooleanVar(value=True)
        self.recoil_enabled = tk.BooleanVar(value=True)
        self.recoil_strength = tk.DoubleVar(value=100)
        self.fov = tk.DoubleVar(value=5)
        self.head_z_offset = tk.DoubleVar(value=-1.0)
        self.prediction_ms = tk.DoubleVar(value=0)
        self.toggle_key = tk.StringVar(value="F6")
        self.collision_path = tk.StringVar(value="")
        self.enabled = True
        self.values = {key: tk.DoubleVar(value=PROFILES[self.mode][key])
                       for key in ("radius", "smooth_ms", "max_step", "hz")}
        self.load_preferences()
        self.lang_var = tk.StringVar(value=i18n.language_name(i18n.current()))
        self.build()
        self.paint_mode()
        self.paint_body()
        self.figure.bind("<Configure>", lambda _: self.paint_body())
        self.protocol("WM_DELETE_WINDOW", self.request_close)
        self.bind("<Escape>", lambda _: self.stop())
        for key in ('F6', 'F7', 'F8', 'F9'):
            self.bind(f'<{key}>', lambda _, k=key: self.toggle_assist() if k == self.toggle_key.get() else None)
        self.after(100, self.poll)

    def label(self, parent, text, size=10, color=TEXT, bold=False, **kwargs):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("DejaVu Sans", size, "bold" if bold else "normal"), **kwargs)

    def _l(self, parent, text_key, size=10, color=TEXT, bold=False, **kwargs):
        """Label statique lié à une clé de traduction (rafraîchi au changement de langue)."""
        widget = self.label(parent, i18n.t(text_key), size, color, bold, **kwargs)
        self.static_texts.append((widget, text_key))
        return widget

    def button(self, parent, text, command, color=INNER, fg=TEXT, **kwargs):
        b = tk.Button(parent, text=text, command=command, bg=color, fg=fg,
                      activebackground=BORDER, activeforeground=TEXT,
                      relief="flat", bd=0, cursor="hand2", padx=14, pady=kwargs.pop("pady", 9),
                      highlightthickness=1, highlightbackground=BORDER,
                      disabledforeground="#566178", **kwargs)
        b.bind("<Enter>", lambda _: b.configure(highlightbackground=ACCENT)
               if b.cget("state") != "disabled" else None)
        b.bind("<Leave>", lambda _: b.configure(highlightbackground=BORDER))
        return b

    def panel(self, parent):
        return tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)

    def build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        shell = tk.Frame(self, bg=BG, padx=24, pady=20)
        shell.grid(sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(3, weight=1)

        header = tk.Frame(shell, bg=BG)
        header.grid(row=0, sticky="ew", pady=(0, 18))
        self.label(header, "◈", 36, ACCENT).pack(side="left", padx=(0, 16))
        title = tk.Frame(header, bg=BG)
        title.pack(side="left")
        self.label(title, "AIM Studio DMA", 27, bold=True).pack(anchor="w")
        self.label(title, "By Akumaprog", 9, ACCENT).pack(anchor="w", pady=(3, 0))
        actions = tk.Frame(header, bg=BG)
        actions.pack(side="right")
        lang_row = tk.Frame(actions, bg=BG)
        lang_row.pack(anchor="e", pady=(0, 6))
        self._l(lang_row, "app.lang", 8, MUTED).pack(side="left", padx=(0, 6))
        lang_menu = tk.OptionMenu(lang_row, self.lang_var, *i18n.LANGUAGES.values(),
                                  command=self.change_language)
        lang_menu.configure(bg=INNER, fg=TEXT, highlightthickness=0, activebackground=BORDER, bd=0)
        lang_menu['menu'].configure(bg=INNER, fg=TEXT, activebackground=BORDER)
        lang_menu.pack(side="left")
        self.controls.append(lang_menu)
        self.offset_button = self.button(actions, i18n.t("offset.update"), self.update_offsets)
        self.offset_button.pack(anchor="e")
        self.offset_label = self.label(actions, i18n.t("offset.hint"), 8, MUTED)
        self.offset_label.pack(anchor="e", pady=(5, 0))

        modes = tk.Frame(shell, bg=BG)
        modes.grid(row=1, sticky="ew")
        self._l(modes, "modes.title", 9, MUTED, True).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 9))
        self.mode_buttons = {}
        symbols = {"soft": "≈", "magnetic": "◎", "rage": "↯"}
        for column, key in enumerate(PROFILES):
            modes.columnconfigure(column, weight=1, uniform="modes")
            b = self.button(modes,
                            f"{symbols[key]}   {i18n.t('mode.' + key)}\n{i18n.t('mode.' + key + '.sub')}",
                            lambda k=key: self.choose_mode(k), height=3,
                            font=("DejaVu Sans", 11), justify="left", anchor="w")
            b.grid(row=1, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0))
            self.mode_buttons[key] = b
            self.controls.append(b)

        self.description = self.label(shell, "", 10, ACCENT, anchor="w")
        self.description.grid(row=2, sticky="ew", pady=(10, 15))

        middle = tk.Frame(shell, bg=BG)
        middle.grid(row=3, sticky="nsew")
        middle.columnconfigure(0, weight=1, uniform="middle")
        middle.columnconfigure(1, weight=1, uniform="middle")
        middle.rowconfigure(0, weight=1)
        body_panel = self.panel(middle)
        body_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._l(body_panel, "body.title", 10, TEXT, True).pack(
            anchor="w", padx=17, pady=(15, 10))
        body_inner = tk.Frame(body_panel, bg=CARD)
        body_inner.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.figure = tk.Canvas(body_inner, width=300, height=375, bg=CARD,
                                highlightthickness=0)
        self.figure.pack(side="left", expand=True, fill="both")
        body_buttons = tk.Frame(body_inner, bg=CARD)
        body_buttons.pack(side="right", fill="y", padx=(5, 8))
        self.body_buttons = {}
        for key in BODY_PARTS:
            b = self.button(body_buttons, i18n.t("body." + key), lambda k=key: self.choose_body(k),
                            anchor="w", width=11, pady=7)
            b.pack(fill="x", pady=3)
            self.body_buttons[key] = b
            self.controls.append(b)

        tuning = self.panel(middle)
        tuning.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._l(tuning, "tuning.title", 10, TEXT, True).pack(
            anchor="w", padx=17, pady=(15, 8))
        self.scales = {}
        self.value_labels = {}
        for key, label, low, high, step, unit in (
            ("radius", "tune.radius", 20, 600, 5, "px"),
            ("smooth_ms", "tune.smooth", 0, 400, 5, "ms"),
            ("max_step", "tune.maxstep", 1, 1000, 1, "units"),
            ("hz", "tune.hz", 10, 120, 5, "hz"),
            ("fov", "tune.fov", 0, 89, 1, "deg"),
            ("head_z_offset", "tune.headz", -3, 0, 0.25, "u"),
            ("prediction_ms", "tune.prediction", 0, 200, 5, "ms"),
        ):
            row = tk.Frame(tuning, bg=CARD)
            row.pack(fill="x", padx=17, pady=(3, 0))
            self._l(row, label, 9, MUTED).pack(side="left")
            value_label = self.label(row, "", 9, ACCENT, True)
            value_label.pack(side="right")
            self.value_labels[key] = (value_label, unit)
            if key in ("fov", "head_z_offset", "prediction_ms"):
                scale = AccentScale(tuning, getattr(self, key), low, high, step,
                                    lambda k=key: self.show_value(k))
            else:
                scale = AccentScale(tuning, self.values[key], low, high, step,
                                    lambda k=key: self.show_value(k))
            scale.pack(fill="x", padx=17, pady=(0, 3))
            self.scales[key] = scale
            self.controls.append(scale)
            self.show_value(key)

        activation = self.panel(shell)
        activation.grid(row=4, sticky="ew", pady=(15, 10))
        banner = tk.Frame(activation, bg=CARD)
        banner.pack(fill="x")
        self._l(banner, "act.title", 10, ACCENT, True).pack(
            side="left", padx=15, pady=11)
        self._l(banner, "act.release", 9, MUTED).pack(
            side="right", padx=15)

        options = tk.Frame(activation, bg=CARD)
        options.pack(fill="x", padx=12)
        self.check_texts = []
        for text_key, variable in (("opt.strict", self.visibility),
                                   ("opt.recoil", self.recoil_enabled)):
            check = tk.Checkbutton(options, text=i18n.t(text_key), variable=variable, bg=CARD, fg=TEXT,
                                   selectcolor=INNER, activebackground=CARD, activeforeground=ACCENT,
                                   highlightthickness=0, disabledforeground=MUTED)
            check.pack(side="left", padx=(0, 15))
            self.check_texts.append((check, text_key))
            self.controls.append(check)
        strength_label = self.label(options, "100 %", 9, ACCENT)
        strength_label.pack(side="right", padx=(8, 0))
        strength = AccentScale(options, self.recoil_strength, 0, 100, 5,
                               lambda: strength_label.configure(text=f'{self.recoil_strength.get():.0f} %'))
        strength.configure(width=125)
        strength.pack(side="right")
        strength_label.configure(text=f'{self.recoil_strength.get():.0f} %')
        self.controls.append(strength)

        extra = tk.Frame(activation, bg=CARD)
        extra.pack(fill="x", padx=15, pady=(8, 10))
        self._l(extra, "hotkey.label", 9, MUTED).pack(side="left", padx=(0, 8))
        hotkey = tk.OptionMenu(extra, self.toggle_key, *HOTKEYS)
        hotkey.configure(bg=INNER, fg=TEXT, highlightthickness=0, activebackground=BORDER, bd=0)
        hotkey['menu'].configure(bg=INNER, fg=TEXT, activebackground=BORDER)
        hotkey.pack(side="left")
        self.controls.append(hotkey)
        self._l(extra, "hotkey.hint", 8, MUTED).pack(side="left", padx=10)
        maps_dir = Path(__file__).resolve().parent / 'maps'
        # Les caches BVH (<carte>.bvh) ne sont pas des géométries : exclus.
        self.available_maps = sorted({p.stem for p in maps_dir.glob('*')
                                      if p.is_file() and not p.name.endswith('.bvh')}) if maps_dir.is_dir() else []
        self.maps_dir = maps_dir
        map_var = tk.StringVar(value=auto_map())
        self.map_var = map_var
        self.map_box = tk.Frame(extra, bg=CARD)
        self.map_box.pack(side="left")
        self.rebuild_map_picker()
        self.geometry_button = self.button(extra, i18n.t("geometry.load"), self.choose_collision, pady=5)
        self.geometry_button.pack(side="right")
        self.controls.append(self.geometry_button)
        self.geometry_label = self.label(activation, "", 8, MUTED, anchor="w")
        self.geometry_label.pack(fill="x", padx=15, pady=(0, 10))
        self.update_geometry_label()

        status = tk.Frame(shell, bg=BG)
        status.grid(row=5, sticky="ew", pady=(0, 10))
        status.columnconfigure(0, weight=1)
        self.status_label = self.label(status, i18n.t("status.ready"), 11, MUTED, True)
        self.status_label.grid(row=0, column=0, sticky="w")
        self.metric_label = self.label(status, i18n.t("metrics.empty"), 9, MUTED)
        self.metric_label.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.start_button = self.button(status, i18n.t("btn.start"), self.start,
                                        color=ACCENT, fg=BG, font=("DejaVu Sans", 11, "bold"))
        self.start_button.grid(row=0, column=1, rowspan=2, padx=(8, 8))
        self.stop_button = self.button(status, i18n.t("btn.stop"), self.stop, fg=RED)
        self.stop_button.grid(row=0, column=3, rowspan=2)
        self.stop_button.configure(state="disabled")
        self.pause_button = self.button(status, i18n.t("btn.pause"), self.toggle_assist, fg=BLUE)
        self.pause_button.grid(row=0, column=2, rowspan=2, padx=(0, 8))
        self.pause_button.configure(state="disabled")

        self.log = tk.Text(shell, height=3, bg="#080d13", fg=MUTED, relief="flat",
                           padx=10, pady=8, font=("DejaVu Sans Mono", 8),
                           state="disabled", wrap="word", highlightthickness=1,
                           highlightbackground=BORDER)
        self.log.grid(row=6, sticky="ew")
        self._l(shell, "footer.hint", 8, MUTED).grid(row=7, sticky="w", pady=(9, 0))

    def show_value(self, key):
        label, unit_key = self.value_labels[key]
        variable = self.values[key] if key in self.values else getattr(self, key)
        unit = i18n.t("unit." + unit_key)
        text = f"{variable.get():.0f} {unit}" if abs(variable.get()) >= 10 or unit_key in ("deg", "u") else f"{variable.get():.2f} {unit}"
        label.configure(text=text)

    def choose_mode(self, mode):
        if self.process is not None or mode == self.mode:
            return
        self.mode = mode
        for key, value in self.values.items():
            value.set(PROFILES[mode][key])
            self.show_value(key)
        self.paint_mode()

    def paint_mode(self):
        selected_bg = "#193b40"
        symbols = {"soft": "≈", "magnetic": "◎", "rage": "↯"}
        for key, b in self.mode_buttons.items():
            b.configure(text=f"{symbols[key]}   {i18n.t('mode.' + key)}\n{i18n.t('mode.' + key + '.sub')}",
                        bg=selected_bg if key == self.mode else CARD,
                        fg=ACCENT_HOVER if key == self.mode else TEXT,
                        highlightbackground=ACCENT if key == self.mode else BORDER)
        self.description.configure(text=i18n.t("mode." + self.mode + ".desc"))
        self.scales["radius"].configure(state="normal" if self.mode == "soft" and self.process is None else "disabled")

    def choose_body(self, body):
        if self.process is not None:
            return
        self.body = body
        self.paint_body()

    def paint_body(self):
        draw_operator(self.figure, self.body, self.choose_body)
        for key, b in self.body_buttons.items():
            b.configure(text=i18n.t("body." + key),
                        bg="#193b40" if key == self.body else INNER,
                        fg=ACCENT_HOVER if key == self.body else TEXT)

    def load_preferences(self):
        try:
            data = json.loads(PREFERENCES.read_text())
            lang = data.get("lang")
            if isinstance(lang, str) and lang in i18n.LANGUAGES:
                i18n.set_lang(lang)
            if data.get("mode") in PROFILES:
                self.mode = data["mode"]
            if data.get("body") in BODY_PARTS:
                self.body = data["body"]
            if data.get('toggle_key') in HOTKEYS:
                self.toggle_key.set(data['toggle_key'])
            for name in ('visibility', 'recoil_enabled'):
                if type(data.get(name)) is bool:
                    getattr(self, name).set(data[name])
            strength = data.get('recoil_strength', 100)
            if isinstance(strength, (int, float)) and math.isfinite(strength) and 0 <= strength <= 100:
                self.recoil_strength.set(strength)
            for name, low, high in (('fov', 0, 89), ('head_z_offset', -3, 0),
                                    ('prediction_ms', 0, 200)):
                value = data.get(name)
                if isinstance(value, (int, float)) and math.isfinite(value) and low <= value <= high:
                    getattr(self, name).set(value)
            if isinstance(data.get('collision_path'), str):
                self.collision_path.set(data['collision_path'])
            # Restaure le sélecteur de carte : une géométrie chargée manuellement
            # redevient la carte choisie, sinon le mode automatique.
            if hasattr(self, "map_var") and self.available_maps:
                chosen = self.collision_path.get()
                if chosen:
                    try:
                        name = Path(chosen).stem
                    except ValueError:
                        name = ""
                    self.map_var.set(name if name in self.available_maps else auto_map())
                else:
                    self.map_var.set(auto_map())
            bounds = {"radius": (20, 600), "smooth_ms": (0, 400), "max_step": (1, 1000), "hz": (10, 120)}
            for key, variable in self.values.items():
                value = float(data.get(key, PROFILES[self.mode][key]))
                if math.isfinite(value) and bounds[key][0] <= value <= bounds[key][1]:
                    variable.set(value)
        except (OSError, ValueError, TypeError, AttributeError):
            return

    def save_preferences(self):
        data = {"mode": self.mode, "body": self.body, "lang": i18n.current(),
                "visibility": self.visibility.get(), "recoil_enabled": self.recoil_enabled.get(),
                "recoil_strength": self.recoil_strength.get(), "toggle_key": self.toggle_key.get(),
                "collision_path": self.collision_path.get(), "fov": self.fov.get(),
                "head_z_offset": self.head_z_offset.get(), "prediction_ms": self.prediction_ms.get(),
                **{k: int(v.get()) for k, v in self.values.items()}}
        tmp = PREFERENCES.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n")
        tmp.replace(PREFERENCES)

    def set_running(self, running):
        for widget in self.controls:
            widget.configure(state="disabled" if running else "normal")
        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")
        self.pause_button.configure(state="normal" if running else "disabled")
        self.offset_button.configure(state="disabled" if running else "normal")
        if not running:
            self.paint_mode()

    def start(self):
        if self.process is not None or self.offset_process is not None:
            return
        try:
            self.save_preferences()
            command = ["bash", str(ROOT / "start-aim.sh"), "--mode", self.mode,
                       "--body", self.body, "--status-json", "--toggle-key", self.toggle_key.get(),
                       "--visibility", "strict" if self.visibility.get() else "off",
                       "--recoil", str(self.recoil_strength.get() if self.recoil_enabled.get() else 0),
                       "--fov", str(self.fov.get()), "--head-z-offset", str(self.head_z_offset.get()),
                       "--prediction-ms", str(self.prediction_ms.get()), "--lang", i18n.current()]
            if self.collision_path.get() and self.visibility.get():
                command += ['--collision', self.collision_path.get()]
            for key, value in self.values.items():
                command += ["--" + key.replace("_", "-"), str(int(value.get()))]
            self.process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, text=True, bufsize=1,
                                            start_new_session=True)
        except OSError as error:
            self.process = None
            messagebox.showerror(i18n.t("error.start.title"), str(error), parent=self)
            return
        self.stopping = False
        self.set_running(True)
        self.status_label.configure(text=i18n.t("status.connect"), fg=BLUE)
        self.append_log(i18n.t("log.start", profile=i18n.t("mode." + self.mode),
                               body=i18n.t("body." + self.body)))
        threading.Thread(target=self.read_output, args=(self.process,), daemon=True).start()

    def update_offsets(self):
        if self.process is not None or self.offset_process is not None:
            return
        try:
            self.offset_process = subprocess.Popen(
                ["bash", str(ROOT / "update-aim-offsets.sh"), "--lang", i18n.current()], cwd=ROOT,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                bufsize=1, start_new_session=True)
        except OSError as error:
            messagebox.showerror(i18n.t("error.update.title"), str(error), parent=self)
            return
        self.set_running(True)
        self.stop_button.configure(state="disabled")
        self.pause_button.configure(state="disabled")
        self.offset_button.configure(text=i18n.t("offset.busy"))
        self.offset_label.configure(text=i18n.t("offset.busy.hint"), fg=BLUE)
        self.append_log(i18n.t("log.offsets"))
        threading.Thread(target=self.read_output, args=(self.offset_process, "offsets_exit"), daemon=True).start()

    def read_output(self, process, exit_event="exit"):
        try:
            for line in process.stdout:
                self.events.put(line.rstrip())
        finally:
            process.stdout.close()
            code = process.wait()
            self.events.put((exit_event, code))

    def append_log(self, line):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        if int(self.log.index("end-1c").split(".")[0]) > 160:
            self.log.delete("1.0", "40.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def display_status(self, data):
        if "map_name" in data:
            name = data.get("map_name")
            loaded = bool(name and data.get("geometry_map") == name)
            self.map_var.set(name or auto_map())
            state = i18n.t("geo.state.loaded") if loaded else (
                i18n.t("geo.state.loading") if data.get("geometry_pending") else i18n.t("geo.state.missing"))
            self.geometry_label.configure(
                text=i18n.t("geo.line.auto", name=name, state=state) if name else i18n.t("geo.auto.wait"),
                fg=ACCENT if loaded else '#edc478')
        phases = {"kmbox": i18n.t("phase.kmbox"), "dma": i18n.t("phase.dma"),
                  "idle": i18n.t("phase.idle"), "ready": i18n.t("phase.ready"),
                  "tracking": i18n.t("phase.tracking"), "waiting": i18n.t("phase.waiting"),
                  "error": i18n.t("phase.error"), "paused": i18n.t("phase.paused"),
                  "geometry": i18n.t("phase.geometry"),
                  "geometry_missing": i18n.t("phase.geometry_missing")}
        self.enabled = data.get('enabled', True)
        self.pause_button.configure(text=i18n.t("btn.pause" if self.enabled else "btn.resume"))
        phase = data.get("phase")
        if not self.stopping:
            self.status_label.configure(text="●  " + phases.get(phase, phase or i18n.t("phase.wait")),
                                        fg=ACCENT if phase in ("idle", "tracking") else BLUE)
        button = i18n.t("button.held") if data.get("pressed") else i18n.t("button.released")
        target = i18n.t("target.yes") if data.get("target") else i18n.t("target.no")
        elapsed = f"{data['ms']:.0f} ms" if "ms" in data else "—"
        self.metric_label.configure(text=i18n.t("metrics.line", b=button, t=target, e=elapsed))

    def choose_collision(self):
        default = str(Path(__file__).resolve().parent / 'maps')
        path = filedialog.askopenfilename(parent=self, title=i18n.t("dialog.geometry.title"),
                                         initialdir=default,
                                         filetypes=[(i18n.t("file.cs2geo"), '*'),
                                                    (i18n.t("file.collision"), '*.aimcoll')])
        if path:
            self.collision_path.set(path)
            self.update_geometry_label()

    def pick_map(self, name):
        if name == auto_map() or not self.available_maps:
            self.collision_path.set("")
        else:
            path = self.maps_dir / name
            if not path.is_file():
                matches = [p for p in self.maps_dir.glob(f'{name}.*')
                           if p.is_file() and not p.name.endswith('.bvh')]
                if matches:
                    path = matches[0]
            if path.is_file():
                self.collision_path.set(str(path))
        self.update_geometry_label()

    def update_geometry_label(self):
        path = str(self.collision_path.get() or "")
        if path and os.path.isfile(path):
            size = os.path.getsize(path)
            text = i18n.t("geo.loaded", name=Path(path).name,
                          size=size // 1024 // 1024, triangles=f"{size // 36:,}")
            self.geometry_label.configure(text=text, fg=ACCENT)
        else:
            n = len(self.available_maps)
            self.geometry_label.configure(
                text=i18n.t("geo.auto.byline", n=n),
                fg='#edc478')

    def rebuild_map_picker(self):
        """(Re)construit le sélecteur de carte avec le libellé « auto » traduit."""
        if self.map_box is None:
            return
        for widget in self.map_box.winfo_children():
            widget.destroy()
        if self.mappick is not None and self.mappick in self.controls:
            self.controls.remove(self.mappick)
        self.mappick = None
        if not self.available_maps:
            return
        if self.map_var.get() not in self.available_maps and self.map_var.get() != auto_map():
            self.map_var.set(auto_map())
        self.label(self.map_box, i18n.t("map.label"), 9, MUTED).pack(side="left", padx=(0, 4))
        mappick = tk.OptionMenu(self.map_box, self.map_var, auto_map(), *self.available_maps,
                                command=self.pick_map)
        mappick.configure(bg=INNER, fg=TEXT, highlightthickness=0, activebackground=BORDER, bd=0)
        mappick['menu'].configure(bg=INNER, fg=TEXT, activebackground=BORDER)
        mappick.pack(side="left")
        self.mappick = mappick
        self.controls.append(mappick)

    def change_language(self, name):
        code = i18n.code_by_name(name)
        self.lang_var.set(i18n.language_name(code))
        if code == i18n.current():
            return
        i18n.set_lang(code)
        self.refresh_texts()
        try:
            self.save_preferences()
        except OSError:
            pass

    def refresh_texts(self):
        for widget, key in self.static_texts:
            try:
                widget.configure(text=i18n.t(key))
            except tk.TclError:
                pass
        for check, key in self.check_texts:
            try:
                check.configure(text=i18n.t(key))
            except tk.TclError:
                pass
        self.offset_button.configure(text=i18n.t("offset.update"))
        self.offset_label.configure(text=i18n.t("offset.hint"))
        self.geometry_button.configure(text=i18n.t("geometry.load"))
        if self.process is None:
            self.status_label.configure(text=i18n.t("status.ready"))
            self.metric_label.configure(text=i18n.t("metrics.empty"))
        self.pause_button.configure(text=i18n.t("btn.pause" if self.enabled else "btn.resume"))
        self.rebuild_map_picker()
        self.update_geometry_label()
        self.paint_mode()
        self.paint_body()

    def toggle_assist(self):
        if self.process is not None and not self.stopping:
            try:
                os.kill(self.process.pid, signal.SIGUSR1)
            except ProcessLookupError:
                return

    def poll(self):
        for _ in range(200):
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if isinstance(event, tuple):
                if event[0] == "offsets_exit":
                    self.offset_process = None
                    self.set_running(False)
                    self.offset_button.configure(text=i18n.t("offset.update"))
                    self.offset_label.configure(
                        text=i18n.t("offset.ok") if event[1] == 0 else i18n.t("offset.fail"),
                        fg=GREEN if event[1] == 0 else RED)
                    if self.closing:
                        self.destroy()
                        return
                    continue
                self.process = None
                self.set_running(False)
                code = event[1]
                self.status_label.configure(
                    text=i18n.t("status.stopped") if code == 0 else i18n.t("status.stopped.code", code=code),
                    fg=MUTED if code == 0 else RED)
                self.metric_label.configure(text=i18n.t("metrics.empty"))
                if self.closing:
                    self.destroy()
                    return
            elif event.startswith("@status "):
                try:
                    self.display_status(json.loads(event[8:]))
                except (ValueError, TypeError, KeyError):
                    self.append_log(event)
            else:
                self.append_log(event)
        self.after(100, self.poll)

    def stop(self):
        if self.process is None or self.stopping:
            return
        self.stopping = True
        self.stop_button.configure(state="disabled")
        self.status_label.configure(text=i18n.t("status.stopping"), fg=BLUE)
        try:
            os.killpg(self.process.pid, signal.SIGINT)
        except ProcessLookupError:
            return

    def request_close(self):
        try:
            self.save_preferences()
        except OSError:
            pass
        if self.offset_process is not None:
            self.closing = True
            try:
                os.killpg(self.offset_process.pid, signal.SIGINT)
            except ProcessLookupError:
                pass
        elif self.process is not None:
            self.closing = True
            self.stop()
        else:
            self.destroy()


if __name__ == "__main__":
    AimMenu().mainloop()
