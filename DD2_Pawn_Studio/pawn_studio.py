from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_VERSION = "1.0.0"
GAME_ROOT = Path(os.environ.get(
    "DD2_GAME_DIR",
    r"C:\Program Files (x86)\Steam\steamapps\common\Dragons Dogma 2",
))
DEFAULT_CONFIG = GAME_ROOT / "reframework" / "data" / "ThePawnController" / "config.json"
GAME_APP_ID = "2054970"

COLORS = {
    "bg": "#151411",
    "panel": "#211f1b",
    "panel_alt": "#292620",
    "input": "#302c25",
    "line": "#4a4337",
    "text": "#f0e8d8",
    "muted": "#a7a094",
    "accent": "#dfb66f",
    "accent_dark": "#806439",
    "green": "#8fce91",
    "blue": "#8fb7d9",
    "red": "#e1988e",
}

JOBS = [
    (0, "不覆盖 / No override"),
    (1, "剑士 / Fighter"),
    (2, "弓箭手 / Archer"),
    (3, "法师 / Mage"),
    (4, "盗贼 / Thief"),
    (5, "斗士 / Warrior"),
    (6, "巫师 / Sorcerer"),
    (7, "魔剑士 / Mystic Spearhand"),
    (8, "魔弓手 / Magick Archer"),
    (9, "幻术师 / Trickster"),
    (10, "龙选者 / Warfarer"),
]
PAWN_JOBS = JOBS[:7]
SPECIALIZATIONS = [
    (-1, "不覆盖 / No override"),
    (0, "无专长 / None"),
    (1, "林地语者 / Woodland Wordsmith"),
    (2, "外科医生 / Chirurgeon"),
    (3, "后勤专家 / Logistician"),
    (4, "商人 / Hawker"),
    (5, "采集者 / Forager"),
    (6, "阿波尼特 / Aphonite"),
]
CHATTER = [
    (0, "正常 / Normal"),
    (1, "较少 / Less"),
    (2, "极少 / Rare"),
    (3, "沉默 / Silent"),
]
KNOWLEDGE_MODES = [
    (0, "默认 / Default"),
    (1, "始终显示 / Always"),
    (2, "禁用 / Never"),
]
SLOTS = [
    ("Main", "主武器 / Main"),
    ("Sub", "副武器或盾 / Sub"),
    ("Head", "头部 / Head"),
    ("Upper", "上装 / Upper"),
    ("Lower", "下装 / Lower"),
    ("Mantle", "披风 / Mantle"),
    ("Jewelry_00", "首饰 1 / Jewelry 1"),
    ("Jewelry_01", "首饰 2 / Jewelry 2"),
    ("Visual", "外观装备 / Visual"),
]
ENHANCE_SLOTS = {"Main", "Sub", "Head", "Upper", "Lower", "Mantle"}
CATEGORY_TO_SLOTS = {
    "Weapon": {"Main"},
    "Shield": {"Sub"},
    "Head": {"Head"},
    "Chest": {"Upper"},
    "Legs": {"Lower"},
    "Mantle": {"Mantle"},
    "Jewelry": {"Jewelry_00", "Jewelry_01"},
    "Visual": {"Visual"},
}
CATEGORY_ZH = {
    "Weapon": "武器 / Weapon",
    "Shield": "盾牌 / Shield",
    "Head": "头部 / Head",
    "Chest": "上装 / Chest",
    "Legs": "下装 / Legs",
    "Mantle": "披风 / Mantle",
    "Jewelry": "首饰 / Jewelry",
    "Visual": "外观 / Visual",
}
SECTION_FIELDS = {
    "equipment": ["equipment", "enhance", "eq_skills"],
    "vocation": ["job", "job_rank", "level", "skills", "abilities", "core", "extra_aug"],
    "clone": ["clone"],
    "identity": ["name", "name_moniker", "personality", "specialization", "voice_gender", "voice_tone"],
    "behaviour": ["chatter", "plague_immune"],
    "knowledge": ["knowledge"],
    "knowledge_perm": ["knowledge_raw"],
}
SECTION_LABELS = {
    "equipment": "装备 / Equipment",
    "vocation": "职业与技能 / Vocation + Skills",
    "clone": "外观 / Appearance",
    "identity": "身份 / Identity",
    "behaviour": "行为 / Behaviour",
    "knowledge": "知识覆盖 / Knowledge Overrides",
    "knowledge_perm": "永久知识 / Permanent Knowledge",
}


def default_pawn_config() -> dict:
    return {
        "enabled": False,
        "equipment": {slot: 0 for slot, _ in SLOTS},
        "enhance": {
            slot: {"enabled": False, "steps": [0, 0, 0], "dragon": False}
            for slot in ENHANCE_SLOTS
        },
        "eq_skills": {
            slot: {"enabled": False, "ids": [0, 0, 0, 0]}
            for slot in ENHANCE_SLOTS
        },
        "job": 0,
        "job_rank": 0,
        "level": 0,
        "skills": [0] * 6,
        "abilities": [0] * 7,
        "core": {},
        "personality": 0,
        "specialization": -1,
        "voice_gender": 0,
        "voice_tone": -1,
        "name": "",
        "chatter": 1,
        "plague_immune": False,
        "knowledge": {"quest": 0, "way": 0, "shortcut": 0, "gimmick": 0},
        "qol": {
            "godmode": False,
            "inf_stamina": False,
            "cannot_die": False,
            "instant_revive": False,
            "damage_mult": 1.0,
            "light_load": False,
            "lantern": False,
            "scale": 1.0,
            "return_after_rest": False,
        },
    }


def deep_fill(target: dict, defaults: dict) -> dict:
    for key, value in defaults.items():
        if key not in target:
            target[key] = copy.deepcopy(value)
        elif isinstance(value, dict) and isinstance(target[key], dict):
            deep_fill(target[key], value)
    return target


def read_json(path: Path, fallback=None):
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return copy.deepcopy(fallback)


def write_json_atomic(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.stem + "_", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=4)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def safe_int(value, default=0) -> int:
    try:
        text = str(value).strip()
        if "(" in text and "ID:" in text:
            text = text.rsplit("ID:", 1)[1].split(")", 1)[0]
        return int(text)
    except (TypeError, ValueError):
        return default


def safe_float(value, default=0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def display_choice(choices, current):
    for value, label in choices:
        if value == current:
            return label
    return f"当前值 / Current ({current})"


def game_is_running() -> bool:
    if os.name != "nt":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq DD2.exe"],
            capture_output=True,
            text=True,
            timeout=4,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return "DD2.exe" in result.stdout
    except Exception:
        return False


class ScrollFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, style="Page.TFrame")
        self.canvas = tk.Canvas(
            self,
            bg=COLORS["bg"],
            highlightthickness=0,
            bd=0,
        )
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, style="Page.TFrame", padding=(26, 20))
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_inner_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.window, width=event.width)

class Catalog:
    def __init__(self, config_path: Path):
        data_dir = config_path.parent
        self.item_data = read_json(data_dir / "itemData.json", {})
        self.dynamic = read_json(data_dir / "pawn_studio_catalog.json", {})
        self.items = {}
        self.by_id = {}
        for raw_id, item in self.item_data.items():
            try:
                item_id = int(raw_id)
            except ValueError:
                continue
            category = item.get("category")
            entry = {
                "id": item_id,
                "name": item.get("name", f"Item {item_id}"),
                "category": category,
                "job_mask": int(item.get("job", 0) or 0),
                "stat": float(item.get("stat", 0) or 0),
                "level": int(item.get("level", 0) or 0),
            }
            self.by_id[item_id] = entry
            for slot in CATEGORY_TO_SLOTS.get(category, ()):
                self.items.setdefault(slot, []).append(entry)
        for entries in self.items.values():
            entries.sort(key=lambda item: item["name"].lower())

        self.jobs = self._dynamic_choices("jobs", JOBS)
        self.personalities = self._dynamic_choices(
            "personality",
            [(-1, "不覆盖 / No override"), (0, "不覆盖 / No override")],
        )
        self.specializations = self._dynamic_choices("spec", SPECIALIZATIONS)
        self.voice_genders = self._dynamic_choices("gender", [(-1, "不覆盖 / No override")])
        self.voice_tones = self._dynamic_choices("tone", [(-1, "不覆盖 / No override")])
        self.skills = self._dynamic_records("skills")
        self.abilities = self._dynamic_records("abilities")
        self.core = self._dynamic_records("core")
        self.equipment_abilities = self._dynamic_records("eq_skills")

    def _dynamic_choices(self, key, fallback):
        records = self.dynamic.get(key)
        if not isinstance(records, list):
            return copy.deepcopy(fallback)
        choices = []
        for record in records:
            try:
                choices.append((int(record["id"]), str(record.get("name", record["id"]))))
            except (KeyError, TypeError, ValueError):
                continue
        return choices or copy.deepcopy(fallback)

    def _dynamic_records(self, key):
        records = self.dynamic.get(key)
        if not isinstance(records, list):
            return []
        output = []
        for record in records:
            try:
                output.append(
                    {
                        "id": int(record["id"]),
                        "name": str(record.get("name", record["id"])),
                        "job": int(record.get("job", 0) or 0),
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue
        return output

    @staticmethod
    def choices_with_current(choices, current, zero_label="无 / No override"):
        result = [(0, zero_label), (-1, zero_label)]
        seen = set()
        for value, label in choices:
            if value in (0, -1) or value in seen:
                continue
            seen.add(value)
            result.append((value, label))
        if current not in seen and current not in (0, -1):
            result.append((current, f"当前值 / Current ({current})"))
        return result

    def item_choices(self, slot, job=0, show_all=False):
        result = [(0, "不覆盖 / No override")]
        bit = 1 << job if job > 0 else 0
        for item in self.items.get(slot, []):
            mask = item["job_mask"]
            if not show_all and bit and mask and not (mask & bit):
                continue
            result.append((item["id"], f'{item["name"]} (ID: {item["id"]})'))
        return result

    def skill_choices(self, job=0):
        result = [(0, "不覆盖 / No override")]
        for record in self.skills:
            if not job or record["job"] in (0, job):
                result.append((record["id"], f'{record["name"]} (ID: {record["id"]})'))
        return result

    def ability_choices(self, job=0):
        result = [(0, "不覆盖 / No override")]
        for record in self.abilities:
            if not job or record["job"] in (0, job):
                result.append((record["id"], f'{record["name"]} (ID: {record["id"]})'))
        return result

    def core_for_job(self, job):
        return [record for record in self.core if not job or record["job"] == job]

    @staticmethod
    def job_mask_labels(mask):
        if not mask:
            return "通用 / Any"
        labels = []
        for job_id, label in JOBS[1:]:
            if mask & (1 << job_id):
                labels.append(label.split(" / ", 1)[-1])
        return ", ".join(labels) if labels else f"掩码 / Mask {mask}"

    def equipment_ability_name(self, ability_id):
        for record in self.equipment_abilities:
            if record["id"] == ability_id:
                return record["name"]
        return f"ID {ability_id}"


class PawnStudio(tk.Tk):
    def __init__(self, config_path: Path = DEFAULT_CONFIG):
        super().__init__()
        self.title("龙之信条 2 · 追随者工作台 (Pawn Studio)")
        self.geometry("1420x920")
        self.minsize(1120, 720)
        self.configure(bg=COLORS["bg"])
        self._configure_style()
        self._enable_dpi_awareness()

        self.config_path = tk.StringVar(value=str(config_path))
        self.status = tk.StringVar(value="准备加载 / Ready")
        self.current_pawn = 0
        self.current_view = "pawn"
        self.config_data: dict = {}
        self.catalog: Catalog | None = None
        self.dirty = False
        self.pending_commits: list = []
        self.pawn_buttons: dict[int, tk.Button] = {}
        self.nav_buttons: dict[str, tk.Button] = {}

        self._build_shell()
        self.bind_all("<MouseWheel>", self._route_mousewheel, add="+")
        self.load_config()

    def _route_mousewheel(self, event):
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            if isinstance(widget, ScrollFrame):
                widget.canvas.yview_scroll(int(-event.delta / 120), "units")
                return "break"
            widget = getattr(widget, "master", None)

    def _enable_dpi_awareness(self):
        if os.name == "nt":
            try:
                import ctypes

                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass

    def _configure_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        self.option_add("*Font", ("Microsoft YaHei UI", 10))
        style.configure(".", background=COLORS["bg"], foreground=COLORS["text"])
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Page.TFrame", background=COLORS["bg"])
        style.configure("Panel.TFrame", background=COLORS["panel"])
        style.configure("Card.TFrame", background=COLORS["panel"], relief="solid", borderwidth=1)
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
        style.configure("Muted.TLabel", foreground=COLORS["muted"], background=COLORS["bg"])
        style.configure("Accent.TLabel", foreground=COLORS["accent"], background=COLORS["bg"])
        style.configure("Card.TLabel", background=COLORS["panel"], foreground=COLORS["text"])
        style.configure("CardMuted.TLabel", background=COLORS["panel"], foreground=COLORS["muted"])
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 22, "bold"), foreground=COLORS["text"])
        style.configure("Subtitle.TLabel", font=("Microsoft YaHei UI", 10), foreground=COLORS["muted"])
        style.configure("Section.TLabel", font=("Microsoft YaHei UI", 12, "bold"), foreground=COLORS["accent"])
        style.configure("Warning.TLabel", foreground=COLORS["red"], background=COLORS["bg"])
        style.configure("Success.TLabel", foreground=COLORS["green"], background=COLORS["bg"])
        style.configure(
            "TButton",
            background=COLORS["panel_alt"],
            foreground=COLORS["text"],
            borderwidth=0,
            padding=(12, 7),
        )
        style.map(
            "TButton",
            background=[("active", COLORS["line"]), ("pressed", COLORS["accent_dark"])],
            foreground=[("active", COLORS["text"])],
        )
        style.configure(
            "Accent.TButton",
            background=COLORS["accent"],
            foreground="#201b14",
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        style.map("Accent.TButton", background=[("active", "#efd093")])
        style.configure("Danger.TButton", background="#6d332f", foreground=COLORS["text"])
        style.map("Danger.TButton", background=[("active", "#8d433d")])
        style.configure("TEntry", fieldbackground=COLORS["input"], foreground=COLORS["text"], insertcolor=COLORS["text"])
        style.configure(
            "TCombobox",
            fieldbackground=COLORS["input"],
            background=COLORS["input"],
            foreground=COLORS["text"],
            readonlybackground=COLORS["input"],
            arrowcolor=COLORS["accent"],
            selectbackground=COLORS["accent_dark"],
            selectforeground=COLORS["text"],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", COLORS["input"]), ("active", COLORS["input"])],
            foreground=[("readonly", COLORS["text"]), ("disabled", COLORS["muted"])],
            background=[("readonly", COLORS["input"]), ("active", COLORS["panel_alt"])],
        )
        self.option_add("*TCombobox*Listbox.background", COLORS["panel_alt"])
        self.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
        self.option_add("*TCombobox*Listbox.selectBackground", COLORS["accent_dark"])
        self.option_add("*TCombobox*Listbox.selectForeground", COLORS["text"])
        style.configure(
            "TCheckbutton",
            background=COLORS["bg"],
            foreground=COLORS["text"],
            indicatorbackground=COLORS["input"],
            indicatorforeground=COLORS["accent"],
        )
        style.map("TCheckbutton", background=[("active", COLORS["bg"])])
        style.configure("TRadiobutton", background=COLORS["bg"], foreground=COLORS["text"])
        style.configure(
            "Treeview",
            background=COLORS["panel"],
            fieldbackground=COLORS["panel"],
            foreground=COLORS["text"],
            rowheight=26,
            borderwidth=0,
        )
        style.map(
            "Treeview",
            background=[("selected", COLORS["accent_dark"])],
            foreground=[("selected", COLORS["text"])],
        )
        style.configure(
            "Treeview.Heading",
            background=COLORS["panel_alt"],
            foreground=COLORS["accent"],
            borderwidth=0,
            padding=(6, 5),
        )
        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=COLORS["panel"], foreground=COLORS["muted"], padding=(16, 8))
        style.map(
            "TNotebook.Tab",
            background=[("selected", COLORS["panel_alt"])],
            foreground=[("selected", COLORS["accent"])],
        )
        style.configure("TSeparator", background=COLORS["line"])
        style.configure("Vertical.TScrollbar", background=COLORS["panel_alt"], troughcolor=COLORS["bg"])

    def _build_shell(self):
        header = ttk.Frame(self, padding=(22, 16, 22, 12))
        header.pack(fill="x")
        title_block = ttk.Frame(header)
        title_block.pack(side="left", fill="x", expand=True)
        ttk.Label(title_block, text="追随者工作台", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title_block,
            text="Pawn Studio · Standalone Python UI for The Pawn Controller",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        actions = ttk.Frame(header)
        actions.pack(side="right")
        ttk.Button(actions, text="重新载入 / Reload", command=self.load_config).pack(side="left", padx=4)
        ttk.Button(actions, text="立即备份 / Backup", command=self.backup_config).pack(side="left", padx=4)
        ttk.Button(actions, text="保存 / Save", style="Accent.TButton", command=self.save_config).pack(side="left", padx=4)
        ttk.Button(actions, text="启动游戏 / Launch", command=self.launch_game).pack(side="left", padx=(12, 0))

        path_row = ttk.Frame(self, padding=(22, 0, 22, 12))
        path_row.pack(fill="x")
        ttk.Label(path_row, text="MOD 配置 / Config", style="Muted.TLabel").pack(side="left", padx=(0, 10))
        ttk.Entry(path_row, textvariable=self.config_path).pack(side="left", fill="x", expand=True)
        ttk.Button(path_row, text="浏览 / Browse", command=self.choose_config).pack(side="left", padx=(8, 0))
        ttk.Button(path_row, text="打开目录 / Folder", command=self.open_config_folder).pack(side="left", padx=(8, 0))

        ttk.Separator(self).pack(fill="x")
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(body, bg=COLORS["panel"], width=262)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.content = ttk.Frame(body, padding=(18, 16))
        self.content.pack(side="left", fill="both", expand=True)

        footer = tk.Frame(self, bg=COLORS["panel"], height=38)
        footer.pack(fill="x", side="bottom")
        self.status_label = tk.Label(
            footer,
            textvariable=self.status,
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            anchor="w",
            padx=18,
            font=("Microsoft YaHei UI", 9),
        )
        self.status_label.pack(fill="both", expand=True)

        self._build_sidebar()

    def _build_sidebar(self):
        tk.Label(
            self.sidebar,
            text="队伍 / PARTY",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 9, "bold"),
            anchor="w",
            padx=18,
            pady=12,
        ).pack(fill="x")
        for index in range(3):
            button = tk.Button(
                self.sidebar,
                text="",
                command=lambda i=index: self.show_pawn(i),
                anchor="w",
                justify="left",
                bg=COLORS["panel"],
                activebackground=COLORS["panel_alt"],
                fg=COLORS["text"],
                activeforeground=COLORS["accent"],
                bd=0,
                padx=18,
                pady=9,
                font=("Microsoft YaHei UI", 10),
                cursor="hand2",
            )
            button.pack(fill="x")
            self.pawn_buttons[index] = button

        tk.Frame(self.sidebar, bg=COLORS["line"], height=1).pack(fill="x", pady=(14, 10), padx=16)
        tk.Label(
            self.sidebar,
            text="工具 / TOOLS",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 9, "bold"),
            anchor="w",
            padx=18,
            pady=6,
        ).pack(fill="x")
        for key, label in [
            ("global", "全局设置 / Global settings"),
            ("raw", "原始 JSON / Raw JSON"),
            ("about", "说明 / Help"),
        ]:
            button = tk.Button(
                self.sidebar,
                text=label,
                command=lambda k=key: self.show_tool(k),
                anchor="w",
                bg=COLORS["panel"],
                activebackground=COLORS["panel_alt"],
                fg=COLORS["muted"],
                activeforeground=COLORS["accent"],
                bd=0,
                padx=18,
                pady=9,
                font=("Microsoft YaHei UI", 10),
                cursor="hand2",
            )
            button.pack(fill="x")
            self.nav_buttons[key] = button

    def choose_config(self):
        path = filedialog.askopenfilename(
            title="选择 ThePawnController 的 config.json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
            initialdir=str(Path(self.config_path.get()).parent),
        )
        if path:
            self.config_path.set(path)
            self.load_config()

    def open_config_folder(self):
        path = Path(self.config_path.get()).parent
        self._open_path(path)

    def _open_path(self, path: Path):
        try:
            if os.name == "nt":
                os.startfile(str(path))
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror("无法打开 / Cannot open", str(exc))

    def launch_game(self):
        try:
            os.startfile(f"steam://rungameid/{GAME_APP_ID}")
            self.set_status("已请求启动游戏 / Steam launch requested", "ok")
        except Exception as exc:
            messagebox.showerror("启动失败 / Launch failed", str(exc))

    def set_status(self, text: str, kind: str = "muted"):
        self.status.set(text)
        colors = {"muted": COLORS["muted"], "ok": COLORS["green"], "warn": COLORS["red"], "accent": COLORS["accent"]}
        self.status_label.configure(fg=colors.get(kind, COLORS["muted"]))

    def mark_dirty(self, _event=None):
        self.dirty = True
        self.set_status("有未保存修改 / Unsaved changes", "warn")

    def commit_widgets(self):
        for commit in list(self.pending_commits):
            try:
                commit()
            except Exception:
                pass
        self.pending_commits.clear()

    def load_config(self):
        if self.dirty and not messagebox.askyesno(
            "放弃修改？ / Discard changes?",
            "当前修改尚未保存，重新载入会丢失。继续？\nUnsaved changes will be lost. Continue?",
        ):
            return
        path = Path(self.config_path.get())
        data = read_json(path)
        if not isinstance(data, dict):
            messagebox.showerror(
                "无法读取 / Cannot load",
                f"配置文件不存在或不是有效 JSON：\n{path}",
            )
            return
        self.config_data = data
        self._normalize_config()
        self.catalog = Catalog(path)
        self.dirty = False
        self.set_status(f"已载入 / Loaded: {path.name}", "ok")
        self.refresh_sidebar()
        self.show_pawn(self.current_pawn)

    def _normalize_config(self):
        for index in range(3):
            key = f"pawn{index}"
            if not isinstance(self.config_data.get(key), dict):
                self.config_data[key] = default_pawn_config()
            deep_fill(self.config_data[key], default_pawn_config())
        self.config_data.setdefault("allow_empty_slots", False)
        self.config_data.setdefault("show_all_items", False)
        self.config_data.setdefault("hire_levelup", False)
        self.config_data.setdefault("debug", {})
        self.config_data.setdefault("originals", {})
        self.config_data.setdefault(
            "player_qol",
            {
                "godmode": False,
                "inf_stamina": False,
                "cannot_die": False,
                "damage_mult": 1.0,
                "light_load": False,
                "lantern": False,
                "scale": 1.0,
            },
        )
        deep_fill(
            self.config_data["debug"],
            {
                "enable_startup_logs": False,
                "enable_search_logs": False,
                "enable_equipment_logs": False,
                "enable_attribute_logs": False,
            },
        )

    def refresh_sidebar(self):
        for index in range(3):
            label = self._pawn_sidebar_text(index)
            active = self.current_view == "pawn" and self.current_pawn == index
            self.pawn_buttons[index].configure(
                text=label,
                bg=COLORS["panel_alt"] if active else COLORS["panel"],
                fg=COLORS["accent"] if active else COLORS["text"],
            )
        for key, button in self.nav_buttons.items():
            active = self.current_view == key
            button.configure(
                bg=COLORS["panel_alt"] if active else COLORS["panel"],
                fg=COLORS["accent"] if active else COLORS["muted"],
            )

    def _pawn_sidebar_text(self, index):
        names = ["主追随者 / Main Pawn", "雇佣追随者 1 / Hired Pawn 1", "雇佣追随者 2 / Hired Pawn 2"]
        original = self.config_data.get("originals", {}).get(f"slot{index}", {}).get("data", {})
        name = original.get("name") or "空槽位 / Empty"
        level = original.get("status", {}).get("level", "?")
        enabled = self.config_data.get(f"pawn{index}", {}).get("enabled", False)
        mode = "编辑中 / ACTIVE" if enabled else "仅查看 / VIEW"
        return f"{names[index]}\n{name} · Lv.{level} · {mode}"

    def clear_content(self):
        self.commit_widgets()
        for child in self.content.winfo_children():
            child.destroy()
        self.pending_commits = []

    def show_pawn(self, index: int):
        self.clear_content()
        self.current_pawn = index
        self.current_view = "pawn"
        self.refresh_sidebar()
        pawn = self.config_data[f"pawn{index}"]
        original = self.config_data.get("originals", {}).get(f"slot{index}", {}).get("data", {})

        head = ttk.Frame(self.content)
        head.pack(fill="x", pady=(0, 10))
        ttk.Label(head, text=["主追随者", "雇佣追随者 1", "雇佣追随者 2"][index], style="Section.TLabel").pack(side="left")
        ttk.Label(
            head,
            text=f"  {original.get('name', '未记录 / Unknown')} · Level {original.get('status', {}).get('level', '?')}",
            style="Muted.TLabel",
        ).pack(side="left")
        enabled_var = tk.BooleanVar(value=bool(pawn.get("enabled")))

        def toggle_enabled():
            pawn["enabled"] = bool(enabled_var.get())
            self.mark_dirty()
            self.refresh_sidebar()

        ttk.Checkbutton(
            head,
            text="启用覆盖 / Enable overrides",
            variable=enabled_var,
            command=toggle_enabled,
        ).pack(side="right")

        notebook = ttk.Notebook(self.content)
        notebook.pack(fill="both", expand=True)
        builders = [
            ("概览 / Overview", self._build_overview),
            ("职业与技能 / Vocation", self._build_vocation),
            ("装备 / Equipment", self._build_equipment),
            ("装备资料 / Item Browser", self._build_item_browser),
            ("身份与行为 / Identity", self._build_identity),
            ("知识 / Knowledge + QoL", self._build_knowledge_qol),
            ("文件与预设 / Files + Presets", self._build_files_presets),
        ]
        for title, builder in builders:
            page = ScrollFrame(notebook)
            notebook.add(page, text=title)
            builder(page.inner, index)

    def show_tool(self, key):
        self.clear_content()
        self.current_view = key
        self.refresh_sidebar()
        if key == "global":
            self._build_global_settings(self.content)
        elif key == "raw":
            self._build_raw_json(self.content)
        else:
            self._build_about(self.content)

    @staticmethod
    def _section(parent, title, subtitle=None):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=(0, 14))
        ttk.Label(frame, text=title, style="Section.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(frame, text=subtitle, style="Muted.TLabel").pack(anchor="w", pady=(1, 8))
        else:
            ttk.Separator(frame).pack(fill="x", pady=(5, 10))
        return frame

    @staticmethod
    def _field_row(parent, label: str, hint: str = ""):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=5)
        label_frame = ttk.Frame(row)
        label_frame.pack(side="left", fill="x", expand=True)
        ttk.Label(label_frame, text=label).pack(anchor="w")
        if hint:
            ttk.Label(label_frame, text=hint, style="Muted.TLabel").pack(anchor="w")
        return row

    @staticmethod
    def _choice_widget(parent, choices, current, editable=False):
        by_value = {value: label for value, label in choices}
        values = [label for _, label in choices]
        selected = by_value.get(current)
        if selected is None:
            selected = f"当前值 / Current ({current})"
            values.append(selected)
        combo = ttk.Combobox(parent, values=values, state="normal" if editable else "readonly", width=36)
        combo.set(selected)
        return combo, by_value

    def _add_choice(self, parent, label, hint, choices, current, setter, editable=False):
        row = self._field_row(parent, label, hint)
        combo, value_map = self._choice_widget(row, choices, current, editable)
        combo.pack(side="right")

        def commit():
            setter(value_map.get(combo.get(), safe_int(combo.get(), current)))

        self.pending_commits.append(commit)
        return combo

    def _add_entry(self, parent, label, hint, current, setter, width=30, numeric=False, float_value=False):
        row = self._field_row(parent, label, hint)
        var = tk.StringVar(value=str(current))
        entry = ttk.Entry(row, textvariable=var, width=width)
        entry.pack(side="right")

        def commit():
            if float_value:
                setter(safe_float(var.get(), safe_float(current)))
            elif numeric:
                setter(safe_int(var.get(), safe_int(current)))
            else:
                setter(var.get())

        self.pending_commits.append(commit)
        return entry

    def _add_check(self, parent, label, hint, current, setter):
        var = tk.BooleanVar(value=bool(current))

        def changed():
            setter(bool(var.get()))
            self.mark_dirty()

        ttk.Checkbutton(parent, text=label, variable=var, command=changed).pack(anchor="w", pady=(4, 0))
        if hint:
            ttk.Label(parent, text=hint, style="Muted.TLabel").pack(anchor="w", padx=(24, 0), pady=(0, 5))
        return var

    def _original_equipment_names(self, index):
        original = self.config_data.get("originals", {}).get(f"slot{index}", {}).get("data", {})
        return original.get("names", {})

    def _build_overview(self, parent, index):
        pawn = self.config_data[f"pawn{index}"]
        original = self.config_data.get("originals", {}).get(f"slot{index}", {}).get("data", {})

        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.pack(fill="x", pady=(0, 16))
        ttk.Label(card, text="原始档案 / Original profile", style="Section.TLabel").pack(anchor="w")
        info = (
            f"姓名: {original.get('name', '?')}    昵称: {original.get('nickname', original.get('name', '?'))}\n"
            f"职业: {self._job_name(original.get('job', 0))}    职业等级: {original.get('job_rank', '?')}    "
            f"角色等级: {original.get('status', {}).get('level', '?')}"
        )
        ttk.Label(card, text=info, style="Card.TLabel", justify="left").pack(anchor="w", pady=(8, 0))

        ttk.Label(
            parent,
            text="覆盖模式 / Override mode",
            style="Section.TLabel",
        ).pack(anchor="w", pady=(4, 4))
        ttk.Label(
            parent,
            text="启用后，原版 MOD 会在载入角色时应用以下设置。修改配置文件后需要重新启动游戏。",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 8))
        enabled_var = tk.BooleanVar(value=bool(pawn.get("enabled")))
        ttk.Checkbutton(
            parent,
            text="启用这个追随者的全部覆盖 / Enable all overrides for this pawn",
            variable=enabled_var,
            command=lambda: self._set_and_dirty(pawn, "enabled", bool(enabled_var.get())),
        ).pack(anchor="w", pady=(0, 14))

        section = self._section(parent, "快速设置 / Quick settings", "这里的值会直接写入 MOD 配置。")
        jobs = self.catalog.jobs if self.catalog else PAWN_JOBS
        self._add_choice(
            section,
            "职业 / Vocation",
            "0 = 不覆盖。原版 Pawn Controller 只对追随者开放前 6 个职业。",
            [choice for choice in jobs if choice[0] <= 6],
            int(pawn.get("job", 0)),
            lambda value: self._set_and_dirty(pawn, "job", value),
        )
        self._add_entry(
            section,
            "职业等级 / Vocation rank",
            "0 = 不覆盖；有效范围通常为 1-9。",
            pawn.get("job_rank", 0),
            lambda value: self._set_and_dirty(pawn, "job_rank", value),
            width=12,
            numeric=True,
        )
        self._add_entry(
            section,
            "角色等级覆盖 / Level override",
            "0 = 不覆盖。设置一次后会由 MOD 应用。",
            pawn.get("level", 0),
            lambda value: self._set_and_dirty(pawn, "level", value),
            width=12,
            numeric=True,
        )
        self._add_entry(
            section,
            "覆盖姓名 / Name override",
            "留空 = 不修改姓名 / Blank = no name override",
            pawn.get("name", ""),
            lambda value: self._set_and_dirty(pawn, "name", value),
            width=34,
        )

        ttk.Label(
            parent,
            text=(
                "主追随者的修改会进入存档，并可能影响在线分享。\n"
                "Main Pawn edits are permanent and may affect online pawn sharing."
            ),
            style="Warning.TLabel",
            justify="left",
        ).pack(anchor="w", pady=(12, 0))

    def _set_and_dirty(self, target, key, value):
        target[key] = value
        self.mark_dirty()

    def _job_name(self, job_id):
        for value, label in JOBS:
            if value == job_id:
                return label
        return f"未知 / Unknown ({job_id})"

    def _build_vocation(self, parent, index):
        pawn = self.config_data[f"pawn{index}"]
        current_job = int(pawn.get("job", 0))
        section = self._section(
            parent,
            "职业与等级 / Vocation and level",
            "Vocation must match the selected skill set for predictable results.",
        )
        self._add_choice(
            section,
            "职业 / Vocation",
            "选择职业后再配置武器技能。",
            [choice for choice in (self.catalog.jobs if self.catalog else PAWN_JOBS) if choice[0] <= 6],
            current_job,
            lambda value: self._set_and_dirty(pawn, "job", value),
        )
        self._add_entry(
            section,
            "职业等级 / Vocation rank",
            "0 = 不覆盖。设为 9 可让大多数技能通过等级检查。",
            pawn.get("job_rank", 0),
            lambda value: self._set_and_dirty(pawn, "job_rank", value),
            width=12,
            numeric=True,
        )

        skill_section = self._section(
            parent,
            "武器技能 / Weapon skills",
            "最多 6 个。若数据目录包含 pawn_studio_catalog.json，会显示英文技能名称。",
        )
        skills = pawn.setdefault("skills", [0] * 6)
        skill_choices = self.catalog.skill_choices(current_job) if self.catalog else [(0, "不覆盖 / No override")]
        for slot_index in range(6):
            current = int(skills[slot_index] or 0) if slot_index < len(skills) else 0
            self._add_choice(
                skill_section,
                f"技能槽 {slot_index + 1} / Skill {slot_index + 1}",
                "No override (0) leaves the original slot untouched.",
                skill_choices,
                current,
                lambda value, pos=slot_index: self._set_list_value(skills, pos, value),
                editable=True,
            )

        aug_section = self._section(
            parent,
            "被动技能 / Augments",
            "原版 MOD 支持 7 个栏位；最后一个可能需要额外书槽。",
        )
        abilities = pawn.setdefault("abilities", [0] * 7)
        ability_choices = self.catalog.ability_choices(current_job) if self.catalog else [(0, "不覆盖 / No override")]
        for slot_index in range(7):
            current = int(abilities[slot_index] or 0) if slot_index < len(abilities) else 0
            self._add_choice(
                aug_section,
                f"被动槽 {slot_index + 1} / Augment {slot_index + 1}",
                "No override (0) leaves the original augment untouched.",
                ability_choices,
                current,
                lambda value, pos=slot_index: self._set_list_value(abilities, pos, value),
                editable=True,
            )

        core_section = self._section(
            parent,
            "核心技能 / Core skills",
            "这些是职业固有动作。需要先生成游戏技能目录后才会显示完整列表。",
        )
        core = pawn.setdefault("core", {})
        if not isinstance(core, dict):
            core = {}
            pawn["core"] = core
        core_records = self.catalog.core_for_job(current_job) if self.catalog else []
        if not core_records:
            ttk.Label(
                core_section,
                text="未找到核心技能目录。可用原始 JSON 页面编辑 core 字段。\nNo core-skill catalog found; edit the raw core object instead.",
                style="Muted.TLabel",
            ).pack(anchor="w")
        for record in core_records:
            key = str(record["id"])
            var = tk.BooleanVar(value=bool(core.get(key)))

            def toggle(record_id=key, variable=var):
                core[record_id] = bool(variable.get())
                self.mark_dirty()

            ttk.Checkbutton(
                core_section,
                text=f'{record["name"]} (ID: {record["id"]})',
                variable=var,
                command=toggle,
            ).pack(anchor="w", pady=2)

    def _set_list_value(self, values, index, value):
        while len(values) <= index:
            values.append(0)
        values[index] = value
        self.mark_dirty()

    def _original_item_record(self, index, slot, item_id):
        original = self.config_data.get("originals", {}).get(f"slot{index}", {}).get("data", {})
        records = original.get("eq_sid", {})
        if not isinstance(records, dict):
            return None
        for record in records.values():
            if not isinstance(record, dict):
                continue
            if record.get("slot") == slot and int(record.get("item", 0) or 0) == int(item_id or 0):
                return record
        return None

    def _original_record_by_item(self, index, item_id):
        original = self.config_data.get("originals", {}).get(f"slot{index}", {}).get("data", {})
        records = original.get("eq_sid", {})
        if not isinstance(records, dict):
            return None
        for record in records.values():
            if isinstance(record, dict) and int(record.get("item", 0) or 0) == int(item_id or 0):
                return record
        return None

    def _enhancement_text(self, index, slot):
        original = self.config_data.get("originals", {}).get(f"slot{index}", {}).get("data", {})
        data = (original.get("enhance") or {}).get(slot) or {}
        steps = data.get("steps") or []
        names = ["None", "Vernworth", "Battahl", "Elven"]
        applied = []
        for number, value in enumerate(steps, 1):
            value = int(value or 0)
            if value > 0:
                applied.append(f"{names[value] if value < len(names) else value} Lv{number}")
        if data.get("dragon"):
            applied.append("Dragonforged")
        return " → ".join(applied) if applied else "未强化 / None"

    def _record_traits(self, record):
        if not record:
            return "未记录 / No appraisal record"
        ids = [int(value or 0) for value in record.get("ids", []) if int(value or 0) > 0]
        if self.catalog:
            skill_text = ", ".join(self.catalog.equipment_ability_name(value) for value in ids)
        else:
            skill_text = ", ".join(str(value) for value in ids)
        stats = []
        for key, label in [("phys", "物理"), ("magic", "魔法"), ("blow", "击倒"), ("weight", "重量")]:
            value = record.get(key, 0)
            if value:
                stats.append(f"{label} {value:+g}")
        if record.get("bonus"):
            stats.append(f"Bonus {record['bonus']}")
        if record.get("appraised"):
            stats.append("已鉴定 / Appraised")
        left = skill_text or "无特殊技能 / No special skills"
        right = " | ".join(stats) if stats else "无词条数值 / No roll modifiers"
        return f"{left}; {right}"

    def _draw_current_gear_summary(self, parent, index):
        section = self._section(
            parent,
            "当前装备资料 / Recorded current gear",
            "Data captured by The Pawn Controller when this pawn was first edited.",
        )
        original = self.config_data.get("originals", {}).get(f"slot{index}", {}).get("data", {})
        equipment = original.get("equipment") or {}
        if not equipment:
            ttk.Label(
                section,
                text="尚未保存该追随者的装备快照。切换到装备编辑或重新进入游戏后可由原 MOD 记录。\nNo equipment snapshot is available.",
                style="Muted.TLabel",
            ).pack(anchor="w")
            return
        holder = ttk.Frame(section)
        holder.pack(fill="x")
        tree = ttk.Treeview(
            holder,
            columns=("slot", "name", "stat", "level", "enhance", "traits"),
            show="headings",
            height=8,
        )
        for key, title, width in [
            ("slot", "槽位 / Slot", 100),
            ("name", "装备 / Item", 170),
            ("stat", "基础数值 / Stat", 90),
            ("level", "物品等级 / Lv", 80),
            ("enhance", "强化 / Enhancement", 150),
            ("traits", "特性 / Traits", 340),
        ]:
            tree.heading(key, text=title)
            tree.column(key, width=width, minwidth=60, stretch=key in {"name", "traits"})
        yscroll = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(section, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.pack(side="left", fill="x", expand=True)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(fill="x", pady=(2, 0))
        for slot, label in SLOTS:
            item_id = int(equipment.get(slot, 0) or 0)
            if item_id <= 0:
                continue
            item = self.catalog.by_id.get(item_id) if self.catalog else None
            record = self._original_item_record(index, slot, item_id)
            tree.insert(
                "",
                "end",
                values=(
                    label,
                    item["name"] if item else f"Item {item_id}",
                    f'{item["stat"]:g}' if item else "?",
                    item["level"] if item else "?",
                    self._enhancement_text(index, slot),
                    self._record_traits(record),
                ),
            )

    def _build_item_browser(self, parent, index):
        ttk.Label(
            parent,
            text="装备数据库 / Equipment database",
            style="Section.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            parent,
            text=(
                "基础数值来自 itemData.json。当前装备的特殊技能、鉴定词条和强化来自 MOD 记录。\n"
                "Base stats come from itemData.json; current traits and enhancement come from MOD records."
            ),
            style="Muted.TLabel",
            justify="left",
        ).pack(anchor="w", pady=(2, 10))
        self._draw_current_gear_summary(parent, index)

        browser = self._section(
            parent,
            "全部装备 / All equipment",
            "Search by item name or ID. Values are the data shipped with The Pawn Controller.",
        )
        filters = ttk.Frame(browser)
        filters.pack(fill="x", pady=(3, 8))
        search_var = tk.StringVar()
        category_var = tk.StringVar(value="全部类别 / All categories")
        job_var = tk.StringVar(value="全部职业 / All vocations")
        ttk.Entry(filters, textvariable=search_var, width=28).pack(side="left")
        categories = ["全部类别 / All categories"] + [
            CATEGORY_ZH.get(key, key) for key in sorted({item["category"] for item in self.catalog.by_id.values()})
        ]
        category_combo = ttk.Combobox(filters, textvariable=category_var, values=categories, state="readonly", width=24)
        category_combo.pack(side="left", padx=8)
        jobs = ["全部职业 / All vocations"] + [label for value, label in JOBS[1:] if value <= 6]
        job_combo = ttk.Combobox(filters, textvariable=job_var, values=jobs, state="readonly", width=24)
        job_combo.pack(side="left")

        table_frame = ttk.Frame(browser)
        table_frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(
            table_frame,
            columns=("id", "name", "category", "stat", "level", "jobs"),
            show="headings",
            height=15,
        )
        for key, title, width in [
            ("id", "ID", 70),
            ("name", "名称 / Name", 210),
            ("category", "类别 / Category", 130),
            ("stat", "基础数值 / Stat", 105),
            ("level", "物品等级 / Level", 100),
            ("jobs", "可用职业 / Vocations", 300),
        ]:
            tree.heading(key, text=title)
            tree.column(key, width=width, minwidth=60, stretch=key in {"name", "jobs"})
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(browser, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(fill="x")

        details = tk.Text(
            browser,
            height=9,
            wrap="word",
            bg=COLORS["panel_alt"],
            fg=COLORS["text"],
            insertbackground=COLORS["accent"],
            relief="flat",
            padx=12,
            pady=10,
            font=("Microsoft YaHei UI", 10),
        )
        details.pack(fill="x", pady=(8, 0))
        details.configure(state="disabled")
        selected_id = tk.IntVar(value=0)

        def populate():
            tree.delete(*tree.get_children())
            query = search_var.get().strip().lower()
            selected_category = category_var.get()
            selected_job = job_var.get()
            job_value = 0
            for value, label in JOBS[1:]:
                if label == selected_job:
                    job_value = value
                    break
            for item in sorted(self.catalog.by_id.values(), key=lambda value: (value["category"], value["name"].lower())):
                if query and query not in item["name"].lower() and query != str(item["id"]):
                    continue
                if selected_category != "全部类别 / All categories" and CATEGORY_ZH.get(item["category"], item["category"]) != selected_category:
                    continue
                if job_value and item["job_mask"] and not (item["job_mask"] & (1 << job_value)):
                    continue
                tree.insert(
                    "",
                    "end",
                    iid=str(item["id"]),
                    values=(
                        item["id"],
                        item["name"],
                        CATEGORY_ZH.get(item["category"], item["category"]),
                        f'{item["stat"]:g}',
                        item["level"],
                        self.catalog.job_mask_labels(item["job_mask"]),
                    ),
                )
            children = tree.get_children()
            if children:
                tree.selection_set(children[0])
                tree.focus(children[0])
                show_details()

        def show_details(_event=None):
            selection = tree.selection()
            if not selection:
                return
            item_id = int(selection[0])
            selected_id.set(item_id)
            item = self.catalog.by_id.get(item_id)
            if not item:
                return
            usages = []
            for pawn_index in range(3):
                record = self._original_record_by_item(pawn_index, item_id)
                if record is not None:
                    usages.append(
                        f"追随者槽位 {pawn_index}: 强化 {self._enhancement_text(pawn_index, record['slot'])}; "
                        f"特性 {self._record_traits(record)}"
                    )
            if not usages:
                for pawn_index in range(3):
                    original = self.config_data.get("originals", {}).get(f"slot{pawn_index}", {}).get("data", {})
                    equipment = original.get("equipment") or {}
                    for slot, value in equipment.items():
                        if int(value or 0) == item_id:
                            usages.append(
                                f"追随者槽位 {pawn_index} / {slot}: 强化 {self._enhancement_text(pawn_index, slot)}"
                            )
            text = (
                f'{item["name"]}  (ID: {item["id"]})\n'
                f'类别 / Category: {CATEGORY_ZH.get(item["category"], item["category"])}\n'
                f'基础数值 / Base stat: {item["stat"]:g}\n'
                f'物品等级 / Item level: {item["level"]}\n'
                f'可用职业 / Vocations: {self.catalog.job_mask_labels(item["job_mask"])}\n'
            )
            if usages:
                text += "\n当前存档记录 / Current MOD records:\n" + "\n".join(usages)
            else:
                text += "\n当前队伍没有使用这件装备，或 MOD 尚未记录其鉴定特性。\n"
            details.configure(state="normal")
            details.delete("1.0", "end")
            details.insert("1.0", text)
            details.configure(state="disabled")

        def copy_selected():
            if selected_id.get() > 0:
                self.clipboard_clear()
                self.clipboard_append(str(selected_id.get()))
                self.set_status(f"已复制装备 ID / Copied item ID: {selected_id.get()}", "ok")

        search_var.trace_add("write", lambda *_: populate())
        category_combo.bind("<<ComboboxSelected>>", lambda _event: populate())
        job_combo.bind("<<ComboboxSelected>>", lambda _event: populate())
        tree.bind("<<TreeviewSelect>>", show_details)
        ttk.Button(browser, text="复制装备 ID / Copy item ID", command=copy_selected).pack(anchor="w", pady=(6, 0))
        populate()

    def _build_equipment(self, parent, index):
        pawn = self.config_data[f"pawn{index}"]
        job = int(pawn.get("job", 0) or 0)
        show_all = bool(self.config_data.get("show_all_items") or self.config_data.get("force_equip"))
        self._draw_current_gear_summary(parent, index)
        section = self._section(
            parent,
            "装备覆盖 / Equipment overrides",
            "The item list comes from itemData.json. No override keeps the pawn's current gear.",
        )
        equipment = pawn.setdefault("equipment", {})
        original_names = self._original_equipment_names(index)
        for slot, label in SLOTS:
            current = int(equipment.get(slot, 0) or 0)
            choices = self.catalog.item_choices(slot, job, show_all) if self.catalog else [(0, "不覆盖 / No override")]
            if current and current not in {value for value, _ in choices}:
                choices.append((current, f"{original_names.get(slot, '当前装备 / Current')} (ID: {current})"))
            self._add_choice(
                section,
                label,
                f"Original: {original_names.get(slot, 'None')}",
                choices,
                current,
                lambda value, slot_key=slot: self._set_and_dirty(equipment, slot_key, value),
            )

        enhance_section = self._section(
            parent,
            "强化等级 / Enhancement",
            "原版 MOD 支持 Vernworth、Battahl、Elven 三步强化以及 Dragonforged。",
        )
        enhance = pawn.setdefault("enhance", {})
        for slot in [slot for slot in ENHANCE_SLOTS]:
            data = enhance.setdefault(slot, {"enabled": False, "steps": [0, 0, 0], "dragon": False})
            label = dict(SLOTS)[slot]
            enabled_var = tk.BooleanVar(value=bool(data.get("enabled")))
            ttk.Checkbutton(
                enhance_section,
                text=f"覆盖 {label} 强化 / Override enhancement",
                variable=enabled_var,
                command=lambda target=data, var=enabled_var: self._set_and_dirty(target, "enabled", bool(var.get())),
            ).pack(anchor="w", pady=(7, 2))
            for step in range(3):
                current = int((data.get("steps") or [0, 0, 0])[step] or 0)
                self._add_choice(
                    enhance_section,
                    f"{label} · 强化阶段 {step + 1} / Step {step + 1}",
                    "0 = 无强化 / None; 1-3 = town smith tier.",
                    [(0, "无 / None"), (1, "Vernworth"), (2, "Battahl"), (3, "Elven")],
                    current,
                    lambda value, target=data, pos=step: self._set_list_value(
                        target.setdefault("steps", [0, 0, 0]), pos, value
                    ),
                )
            dragon_var = tk.BooleanVar(value=bool(data.get("dragon")))
            ttk.Checkbutton(
                enhance_section,
                text=f"{label} · Dragonforged",
                variable=dragon_var,
                command=lambda target=data, var=dragon_var: self._set_and_dirty(target, "dragon", bool(var.get())),
            ).pack(anchor="w", padx=(24, 0), pady=(0, 5))

        eq_skill_section = self._section(
            parent,
            "装备特殊技能 / Special skills on gear",
            "可输入原始技能 ID。高级功能；建议使用原版游戏内校验。",
        )
        eq_skills = pawn.setdefault("eq_skills", {})
        for slot in ENHANCE_SLOTS:
            data = eq_skills.setdefault(slot, {"enabled": False, "ids": [0, 0, 0, 0]})
            label = dict(SLOTS)[slot]
            enabled_var = tk.BooleanVar(value=bool(data.get("enabled")))
            ttk.Checkbutton(
                eq_skill_section,
                text=f"覆盖 {label} 特殊技能 / Override special skills",
                variable=enabled_var,
                command=lambda target=data, var=enabled_var: self._set_and_dirty(target, "enabled", bool(var.get())),
            ).pack(anchor="w", pady=(7, 2))
            for skill_index in range(4):
                current = int((data.get("ids") or [0, 0, 0, 0])[skill_index] or 0)
                self._add_entry(
                    eq_skill_section,
                    f"{label} · 特殊技能 {skill_index + 1} ID",
                    "0 = 空槽位 / Empty slot",
                    current,
                    lambda value, target=data, pos=skill_index: self._set_list_value(
                        target.setdefault("ids", [0, 0, 0, 0]), pos, value
                    ),
                    width=12,
                    numeric=True,
                )

    def _build_identity(self, parent, index):
        pawn = self.config_data[f"pawn{index}"]
        identity = self._section(
            parent,
            "身份 / Identity",
            "Voice and personality changes require saving and reloading the game.",
        )
        self._add_entry(
            identity,
            "姓名覆盖 / Name",
            "留空 = 不覆盖 / Blank = no override",
            pawn.get("name", ""),
            lambda value: self._set_and_dirty(pawn, "name", value),
            width=34,
        )
        moniker_var = tk.BooleanVar(value=bool(pawn.get("name_moniker")))
        ttk.Checkbutton(
            identity,
            text="姓名同时作为昵称 / Also use this name as moniker",
            variable=moniker_var,
            command=lambda: self._set_and_dirty(pawn, "name_moniker", bool(moniker_var.get())),
        ).pack(anchor="w", pady=6)

        current_personality = int(pawn.get("personality", 0) or 0)
        choices = self.catalog.personalities if self.catalog else []
        self._add_choice(
            identity,
            "性格 / Personality",
            "名称来自游戏枚举；若目录未生成则显示当前哈希值。",
            self.catalog.choices_with_current(choices, current_personality) if self.catalog else [
                (0, "不覆盖 / No override"),
                (current_personality, f"当前值 / Current ({current_personality})"),
            ],
            current_personality,
            lambda value: self._set_and_dirty(pawn, "personality", value),
            editable=True,
        )
        self._add_choice(
            identity,
            "专长 / Specialization",
            "Specialization controls pawn support behavior.",
            self.catalog.specializations if self.catalog else SPECIALIZATIONS,
            int(pawn.get("specialization", -1)),
            lambda value: self._set_and_dirty(pawn, "specialization", value),
        )

        voice = self._section(
            parent,
            "语音 / Voice",
            "保存并重新读取游戏后才能完整生效。",
        )
        self._add_choice(
            voice,
            "语音性别组 / Voice gender group",
            "Uses the game's numeric voice-group hash.",
            self.catalog.choices_with_current(self.catalog.voice_genders, int(pawn.get("voice_gender", 0)))
            if self.catalog
            else [(0, "不覆盖 / No override"), (int(pawn.get("voice_gender", 0)), f"当前值 / Current ({pawn.get('voice_gender', 0)})")],
            int(pawn.get("voice_gender", 0)),
            lambda value: self._set_and_dirty(pawn, "voice_gender", value),
            editable=True,
        )
        self._add_choice(
            voice,
            "语音音色 / Voice tone",
            "Tone selection is tied to the selected voice group.",
            self.catalog.choices_with_current(self.catalog.voice_tones, int(pawn.get("voice_tone", -1)))
            if self.catalog
            else [(-1, "不覆盖 / No override"), (int(pawn.get("voice_tone", -1)), f"当前值 / Current ({pawn.get('voice_tone', -1)})")],
            int(pawn.get("voice_tone", -1)),
            lambda value: self._set_and_dirty(pawn, "voice_tone", value),
            editable=True,
        )

        behaviour = self._section(
            parent,
            "行为 / Behaviour",
            "Chatter and Dragonsplague policy.",
        )
        self._add_choice(
            behaviour,
            "说话频率 / Chatter",
            "Silent prevents routine pawn voice lines.",
            CHATTER,
            int(pawn.get("chatter", 1)),
            lambda value: self._set_and_dirty(pawn, "chatter", value),
        )
        self._add_check(
            behaviour,
            "免疫龙瘟 / Immune to Dragonsplague",
            "Only changes the configured immunity flag; current infection requires the in-game tools.",
            bool(pawn.get("plague_immune")),
            lambda value: self._set_and_dirty(pawn, "plague_immune", value),
        )

    def _build_knowledge_qol(self, parent, index):
        pawn = self.config_data[f"pawn{index}"]
        knowledge = pawn.setdefault("knowledge", {})
        section = self._section(
            parent,
            "知识覆盖 / Knowledge overrides",
            "Default = game logic; Always = guide this topic; Never = suppress this topic.",
        )
        for key, label, hint in [
            ("quest", "任务指引 / Quest guidance", "Quest route hints."),
            ("way", "路线指引 / Route directions", "Key locations and route hints."),
            ("shortcut", "捷径 / Shortcuts", "Shortcut knowledge."),
            ("gimmick", "机关 / Gimmicks", "Chests, levers, doors and similar objects."),
        ]:
            self._add_choice(
                section,
                label,
                hint,
                KNOWLEDGE_MODES,
                int(knowledge.get(key, 0)),
                lambda value, field=key: self._set_and_dirty(knowledge, field, value),
            )

        qol = pawn.setdefault("qol", {})
        qsection = self._section(
            parent,
            "追随者 QoL / Pawn QoL",
            "These are live gameplay overrides handled by the original Lua MOD.",
        )
        for key, label, hint in [
            ("godmode", "无敌 / Godmode", "Ignore damage."),
            ("cannot_die", "不会死亡 / Cannot die", "Prevents lethal state."),
            ("instant_revive", "立即复活 / Instant revive", "Hired-pawn helper."),
            ("inf_stamina", "无限耐力 / Infinite stamina", "Stamina never drains."),
            ("light_load", "无限负重 / Infinite carry weight", "Menu also shows Light."),
            ("lantern", "提灯常亮 / Lantern always lit", "No oil consumption."),
            ("return_after_rest", "死亡后返回 / Respawn after death", "Revives instead of returning to the Rift."),
        ]:
            self._add_check(
                qsection,
                label,
                hint,
                bool(qol.get(key)),
                lambda value, field=key: self._set_and_dirty(qol, field, value),
            )
        self._add_entry(
            qsection,
            "伤害倍率 / Damage multiplier",
            "1.0 = normal. Supports fractional values.",
            qol.get("damage_mult", 1.0),
            lambda value: self._set_and_dirty(qol, "damage_mult", value),
            width=12,
            float_value=True,
        )
        self._add_entry(
            qsection,
            "体型倍率 / Size multiplier",
            "0.25-3.0 recommended. The Lua MOD applies the scale live.",
            qol.get("scale", 1.0),
            lambda value: self._set_and_dirty(qol, "scale", value),
            width=12,
            float_value=True,
        )
        ttk.Label(
            parent,
            text=(
                "Python 版本不能执行内存按钮：治疗、传送、杀死、立即感染。\n"
                "Live actions such as heal, teleport, kill and infect remain in the in-game MOD UI."
            ),
            style="Muted.TLabel",
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

    def _build_files_presets(self, parent, index):
        pawn = self.config_data[f"pawn{index}"]
        profile = self._section(
            parent,
            "追随者配置导入导出 / Pawn profile import-export",
            "Exports the editable Python profile, not a save file.",
        )
        buttons = ttk.Frame(profile)
        buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(
            buttons,
            text="导出当前追随者 / Export current pawn",
            command=lambda: self.export_pawn_profile(index),
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            buttons,
            text="导入追随者配置 / Import pawn profile",
            command=lambda: self.import_pawn_profile(index),
        ).pack(side="left")

        presets = self._section(
            parent,
            "预设 / Presets",
            "Stored in presets.json beside config.json and compatible with the original MOD.",
        )
        preset_row = ttk.Frame(presets)
        preset_row.pack(fill="x", pady=(4, 8))
        self.preset_name_var = tk.StringVar()
        ttk.Entry(preset_row, textvariable=self.preset_name_var, width=28).pack(side="left")
        ttk.Button(
            preset_row,
            text="保存为新预设 / Save preset",
            command=lambda: self.save_preset(index),
        ).pack(side="left", padx=8)
        self.preset_combo_var = tk.StringVar()
        presets_data = self._load_presets()
        self.preset_combo = ttk.Combobox(
            presets,
            textvariable=self.preset_combo_var,
            values=sorted(presets_data.keys()),
            state="readonly",
            width=40,
        )
        self.preset_combo.pack(fill="x", pady=(5, 5))
        row = ttk.Frame(presets)
        row.pack(fill="x")
        ttk.Button(row, text="载入预设 / Load", command=lambda: self.load_preset(index)).pack(side="left")
        ttk.Button(row, text="删除预设 / Delete", style="Danger.TButton", command=self.delete_preset).pack(
            side="left", padx=8
        )

        character_section = self._section(
            parent,
            "人物档案 / Character files",
            "Reads JSON files exported by the original MOD from the characters folder.",
        )
        files = self._character_files()
        self.character_file_var = tk.StringVar()
        if files:
            ttk.Combobox(
                character_section,
                textvariable=self.character_file_var,
                values=[path.name for path in files],
                state="readonly",
                width=48,
            ).pack(fill="x", pady=(4, 6))
            self.section_vars = {}
            for section_key, label in SECTION_LABELS.items():
                var = tk.BooleanVar(value=True)
                self.section_vars[section_key] = var
                ttk.Checkbutton(character_section, text=label, variable=var).pack(anchor="w")
            action_row = ttk.Frame(character_section)
            action_row.pack(fill="x", pady=(8, 0))
            ttk.Button(
                action_row,
                text="导入所选部分 / Import selected",
                command=lambda: self.import_character_sections(index),
            ).pack(side="left")
            ttk.Button(
                action_row,
                text="打开人物档案目录 / Open folder",
                command=lambda: self._open_path(Path(self.config_path.get()).parent / "characters"),
            ).pack(side="left", padx=8)
        else:
            ttk.Label(
                character_section,
                text="尚未找到人物档案。先在原版 MOD 的 Import / Export 页面导出一次。\nNo character files found.",
                style="Muted.TLabel",
            ).pack(anchor="w")

    def _build_global_settings(self, parent):
        ttk.Label(parent, text="全局设置 / Global settings", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        scroll = ScrollFrame(parent)
        scroll.pack(fill="both", expand=True)
        body = scroll.inner

        policy = self._section(body, "覆盖策略 / Override policy")
        options = [
            ("allow_empty_slots", "允许配置空槽位 / Configure empty slots", "Settings move to the next pawn hired there."),
            ("hire_levelup", "雇佣追随者随 EXP 升级 / Hired pawns level from EXP", "Previously earned EXP may cause a level jump."),
            ("force_equip", "忽略装备职业限制 / Ignore vocation restrictions", "Useful for fashion sets and mixed builds."),
            ("show_all_items", "显示全部职业装备 / Show all-vocation equipment", "Item lists will no longer filter by vocation."),
            ("log_uploads", "记录主追随者上传 / Log pawn uploads", "Writes upload results to the REFramework log."),
        ]
        for key, label, hint in options:
            self._add_check(
                policy,
                label,
                hint,
                bool(self.config_data.get(key)),
                lambda value, field=key: self._set_and_dirty(self.config_data, field, value),
            )

        debug = self._section(body, "诊断日志 / Diagnostics")
        for key, label in [
            ("enable_startup_logs", "启动数据加载 / Startup loading"),
            ("enable_search_logs", "搜索框 / Search boxes"),
            ("enable_equipment_logs", "装备与强化 / Equipment"),
            ("enable_attribute_logs", "技能与职业 / Skills and attributes"),
        ]:
            self._add_check(
                debug,
                label,
                "Writes additional REFramework log entries.",
                bool(self.config_data["debug"].get(key)),
                lambda value, field=key: self._set_and_dirty(self.config_data["debug"], field, value),
            )

        player = self.config_data.setdefault("player_qol", {})
        player_section = self._section(body, "玩家 QoL / Arisen QoL")
        for key, label in [
            ("godmode", "无敌 / Godmode"),
            ("cannot_die", "不会死亡 / Cannot die"),
            ("inf_stamina", "无限耐力 / Infinite stamina"),
            ("light_load", "无限负重 / Infinite carry weight"),
            ("lantern", "提灯常亮 / Lantern always lit"),
        ]:
            self._add_check(
                player_section,
                label,
                "",
                bool(player.get(key)),
                lambda value, field=key: self._set_and_dirty(player, field, value),
            )
        self._add_entry(
            player_section,
            "玩家伤害倍率 / Arisen damage multiplier",
            "1.0 = normal",
            player.get("damage_mult", 1.0),
            lambda value: self._set_and_dirty(player, "damage_mult", value),
            width=12,
            float_value=True,
        )
        self._add_entry(
            player_section,
            "玩家体型倍率 / Arisen size multiplier",
            "0.25-3.0 recommended",
            player.get("scale", 1.0),
            lambda value: self._set_and_dirty(player, "scale", value),
            width=12,
            float_value=True,
        )

    def _build_raw_json(self, parent):
        header = ttk.Frame(parent)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="原始配置 / Raw configuration JSON", style="Section.TLabel").pack(side="left")
        ttk.Button(header, text="应用 JSON / Apply JSON", style="Accent.TButton", command=self.apply_raw_json).pack(
            side="right"
        )
        ttk.Button(header, text="刷新自模型 / Reload model", command=lambda: self.show_tool("raw")).pack(
            side="right", padx=8
        )
        ttk.Label(
            parent,
            text="Advanced editor. Keep the JSON schema intact. Unknown fields are preserved by the normal editor.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 8))
        editor_frame = ttk.Frame(parent)
        editor_frame.pack(fill="both", expand=True)
        self.raw_text = tk.Text(
            editor_frame,
            wrap="none",
            undo=True,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            insertbackground=COLORS["accent"],
            selectbackground=COLORS["accent_dark"],
            font=("Cascadia Mono", 10),
            bd=0,
            padx=12,
            pady=10,
        )
        yscroll = ttk.Scrollbar(editor_frame, orient="vertical", command=self.raw_text.yview)
        xscroll = ttk.Scrollbar(editor_frame, orient="horizontal", command=self.raw_text.xview)
        self.raw_text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")
        self.raw_text.pack(side="left", fill="both", expand=True)
        self.raw_text.insert("1.0", json.dumps(self.config_data, ensure_ascii=False, indent=4))

    def _build_about(self, parent):
        ttk.Label(parent, text="关于 / About Pawn Studio", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            parent,
            text=(
                f"版本 / Version: {APP_VERSION}\n\n"
                "这是一个独立 Python 前端，不修改 The Pawn Controller 的 Lua 文件。\n"
                "它直接编辑 MOD 的 config.json；原版 MOD 在重新进入游戏后应用设置。\n\n"
                "This standalone Python frontend edits config.json. The original Lua MOD "
                "remains untouched and applies the saved settings after the game is restarted.\n\n"
                "限制 / Limitations:\n"
                "• 实时治疗、传送、杀死、感染等内存操作仍需使用游戏内原版 UI。\n"
                "• Python 程序不能直接验证在线追随者上传结果。\n"
                "• 修改主追随者后，建议先在原版 UI 中执行 Validate Pawn。\n"
            ),
            justify="left",
        ).pack(anchor="w", pady=(10, 0))
        if game_is_running():
            ttk.Label(
                parent,
                text="检测到游戏正在运行。保存配置后请重新启动游戏，否则本次修改不会载入。\n"
                "DD2.exe is running. Restart the game after saving so the original MOD reloads config.json.",
                style="Warning.TLabel",
                justify="left",
            ).pack(anchor="w", pady=(18, 0))

    def apply_raw_json(self):
        if not hasattr(self, "raw_text"):
            return
        try:
            data = json.loads(self.raw_text.get("1.0", "end-1c"))
        except json.JSONDecodeError as exc:
            messagebox.showerror("JSON 错误 / JSON error", f"第 {exc.lineno} 行第 {exc.colno} 列\n{exc.msg}")
            return
        if not isinstance(data, dict):
            messagebox.showerror("JSON 错误 / JSON error", "根节点必须是对象 / Root must be an object.")
            return
        if not messagebox.askyesno(
            "替换配置？ / Replace configuration?",
            "这会用编辑器中的 JSON 替换当前内存配置。\nReplace the in-memory configuration with this JSON?",
        ):
            return
        self.config_data = data
        self._normalize_config()
        self.dirty = True
        self.set_status("原始 JSON 已应用，尚未保存 / Raw JSON applied, not saved", "warn")
        self.refresh_sidebar()

    def save_config(self):
        self.commit_widgets()
        path = Path(self.config_path.get())
        if game_is_running():
            if not messagebox.askyesno(
                "游戏正在运行 / Game is running",
                "游戏正在运行。配置文件不会立即重新载入，退出游戏时原 MOD 也可能覆盖此文件。\n"
                "建议先关闭游戏再保存。仍然保存吗？\n\n"
                "The game is running. Changes will not reload until restart and may be overwritten on exit. Save anyway?",
            ):
                return
        try:
            self.backup_config(silent=True)
            write_json_atomic(path, self.config_data)
        except Exception as exc:
            messagebox.showerror("保存失败 / Save failed", str(exc))
            return
        self.dirty = False
        self.set_status(f"已保存 / Saved: {path}", "ok")
        self.refresh_sidebar()

    def backup_config(self, silent=False):
        path = Path(self.config_path.get())
        if not path.exists():
            if not silent:
                messagebox.showwarning("没有文件 / Missing file", f"配置文件不存在：\n{path}")
            return None
        backup_dir = Path(__file__).resolve().parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        target = backup_dir / f"config_{datetime.now():%Y-%m-%d_%H%M%S}.json"
        target.write_bytes(path.read_bytes())
        if not silent:
            self.set_status(f"备份完成 / Backup: {target.name}", "ok")
            messagebox.showinfo("备份完成 / Backup complete", str(target))
        return target

    def _load_presets(self):
        path = Path(self.config_path.get()).parent / "presets.json"
        data = read_json(path, {})
        return data if isinstance(data, dict) else {}

    def save_preset(self, index):
        self.commit_widgets()
        path = Path(self.config_path.get()).parent / "presets.json"
        presets = self._load_presets()
        name = self.preset_name_var.get().strip()
        if not name:
            original = self.config_data.get("originals", {}).get(f"slot{index}", {}).get("data", {})
            name = original.get("name") or f"Preset {index + 1}"
        base = name
        counter = 2
        while name in presets:
            name = f"{base} ({counter})"
            counter += 1
        preset = copy.deepcopy(self.config_data[f"pawn{index}"])
        preset["enabled"] = False
        for key in ("owner", "sid", "knowledge_raw", "possession", "status", "eq_sid", "eq_written", "names"):
            preset.pop(key, None)
        presets[name] = preset
        try:
            write_json_atomic(path, presets)
        except Exception as exc:
            messagebox.showerror("预设保存失败 / Preset save failed", str(exc))
            return
        self.set_status(f"预设已保存 / Preset saved: {name}", "ok")
        self.show_pawn(index)

    def load_preset(self, index):
        name = self.preset_combo_var.get()
        presets = self._load_presets()
        if not name or name not in presets:
            return
        if not messagebox.askyesno(
            "载入预设？ / Load preset?",
            f"用预设“{name}”覆盖当前追随者配置？\nReplace this pawn's configuration with '{name}'?",
        ):
            return
        old = self.config_data[f"pawn{index}"]
        for key in ("owner", "sid", "preconfigured"):
            if key in old:
                presets[name][key] = old[key]
        self.config_data[f"pawn{index}"] = copy.deepcopy(presets[name])
        self.config_data[f"pawn{index}"]["enabled"] = True
        self._normalize_config()
        self.mark_dirty()
        self.show_pawn(index)

    def delete_preset(self):
        name = self.preset_combo_var.get()
        if not name:
            return
        if not messagebox.askyesno("删除预设 / Delete preset", f"删除“{name}”？\nDelete '{name}'?"):
            return
        path = Path(self.config_path.get()).parent / "presets.json"
        presets = self._load_presets()
        presets.pop(name, None)
        write_json_atomic(path, presets)
        self.show_pawn(self.current_pawn)

    def export_pawn_profile(self, index):
        self.commit_widgets()
        path = filedialog.asksaveasfilename(
            title="导出追随者配置 / Export pawn profile",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile=f"pawn_{index}_profile.json",
        )
        if not path:
            return
        payload = {
            "format": "dd2-pawn-studio-profile",
            "version": APP_VERSION,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "slot": index,
            "pawn": self.config_data[f"pawn{index}"],
        }
        write_json_atomic(Path(path), payload)
        self.set_status(f"已导出 / Exported: {path}", "ok")

    def import_pawn_profile(self, index):
        path = filedialog.askopenfilename(
            title="导入追随者配置 / Import pawn profile",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        data = read_json(Path(path))
        pawn = data.get("pawn") if isinstance(data, dict) else None
        if not isinstance(pawn, dict):
            messagebox.showerror("导入失败 / Import failed", "文件中没有 pawn 配置。 / No pawn configuration found.")
            return
        if not messagebox.askyesno(
            "导入配置？ / Import profile?",
            "这会替换当前追随者的覆盖配置。\nReplace the current pawn overrides?",
        ):
            return
        old = self.config_data[f"pawn{index}"]
        for key in ("owner", "sid", "preconfigured"):
            if key in old:
                pawn[key] = old[key]
        self.config_data[f"pawn{index}"] = pawn
        self._normalize_config()
        self.mark_dirty()
        self.show_pawn(index)

    def _character_files(self):
        folder = Path(self.config_path.get()).parent / "characters"
        if not folder.exists():
            return []
        return sorted(folder.glob("*.json"))

    def import_character_sections(self, index):
        name = self.character_file_var.get()
        if not name:
            return
        path = Path(self.config_path.get()).parent / "characters" / name
        data = read_json(path)
        payload = data.get("data") if isinstance(data, dict) and isinstance(data.get("data"), dict) else data
        if not isinstance(payload, dict):
            messagebox.showerror("导入失败 / Import failed", "文件格式无效。 / Invalid character file.")
            return
        pawn = self.config_data[f"pawn{index}"]
        selected = [key for key, variable in self.section_vars.items() if variable.get()]
        if not selected:
            return
        for section_key in selected:
            for field in SECTION_FIELDS.get(section_key, []):
                if field in payload:
                    pawn[field] = copy.deepcopy(payload[field])
        pawn["enabled"] = True
        self._normalize_config()
        self.mark_dirty()
        self.show_pawn(index)
        self.set_status(f"已导入部分档案 / Imported sections: {', '.join(selected)}", "ok")

    def on_close(self):
        self.commit_widgets()
        if self.dirty and not messagebox.askyesno(
            "退出？ / Quit?",
            "仍有未保存修改。确定退出吗？\nThere are unsaved changes. Quit anyway?",
        ):
            return
        self.destroy()


def main():
    initial = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG
    app = PawnStudio(initial)
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
