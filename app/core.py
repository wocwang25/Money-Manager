"""
core.py — Hằng số, config I/O, tiện ích CSV/date, và widgets dùng chung.
Gộp từ constants + config + utils + widgets để giảm file I/O khi khởi động.
"""

import csv
import json
import os
import sys
import calendar
from datetime import datetime

import customtkinter as ctk

# ══════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(APP_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "danh_muc_config.json")

DEFAULT_BUDGET = {
    "Ăn uống":  3_000_000,
    "Xăng xe":    500_000,
    "Lặt vặt":    500_000,
}
DEFAULT_DAILY_TRACK = {"Ăn uống", "Xăng xe"}
CSV_HEADERS = ["Ngày nhập", "Danh mục", "Số tiền chi", "Ghi chú"]

COL = {
    "bg":       "#1e1e2e",
    "card":     "#252538",
    "card2":    "#2e2e44",
    "input":    "#363652",
    "fg":       "#cdd6f4",
    "dim":      "#7f849c",
    "accent":   "#89b4fa",
    "green":    "#a6e3a1",
    "red":      "#f38ba8",
    "yellow":   "#f9e2af",
    "peach":    "#fab387",
    "mauve":    "#cba6f7",
    "teal":     "#94e2d5",
    "sidebar":  "#1a1a2e",
    "hover":    "#45457a",
    "white":    "#ffffff",
}

# ══════════════════════════════════════════════════════════════
#  CONFIG I/O
# ══════════════════════════════════════════════════════════════

def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        changed = False
        for cat, info in cfg.items():
            if "daily_track" not in info:
                info["daily_track"] = cat in DEFAULT_DAILY_TRACK
                changed = True
            if "daily_times" not in info:
                info["daily_times"] = 0
                changed = True
        if changed:
            save_config(cfg)
        return cfg
    cfg = {
        cat: {
            "budget": b,
            "enabled": True,
            "daily_track": cat in DEFAULT_DAILY_TRACK,
            "daily_times": 0,
        }
        for cat, b in DEFAULT_BUDGET.items()
    }
    save_config(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

# ══════════════════════════════════════════════════════════════
#  UTILS
# ══════════════════════════════════════════════════════════════

def fmt(amount: int) -> str:
    if amount < 0:
        return "-" + f"{abs(amount):,}đ".replace(",", ".")
    return f"{amount:,}đ".replace(",", ".")


def parse_amount(raw: str) -> int:
    s = (
        raw.strip()
        .replace(",", "")
        .replace(".", "")
        .replace("k", "000")
        .replace("tr", "000000")
    )
    return int(s)


def get_csv_path(month: int | None = None, year: int | None = None) -> str:
    now = datetime.now()
    return os.path.join(
        DATA_DIR,
        f"ChiTieu_Thang_{(month or now.month):02d}_{year or now.year}.csv",
    )


def init_csv(fp: str) -> None:
    if not os.path.exists(fp):
        with open(fp, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(CSV_HEADERS)


def read_all(fp: str) -> list[dict]:
    if not os.path.exists(fp):
        return []
    with open(fp, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["Số tiền chi"] = int(r["Số tiền chi"])
    return rows


def append_row(fp: str, date_str: str, cat: str, amount: int, note: str) -> None:
    with open(fp, "a", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerow([date_str, cat, amount, note])


def rewrite_csv(fp: str, rows: list[dict]) -> None:
    with open(fp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADERS)
        for r in rows:
            w.writerow([r["Ngày nhập"], r["Danh mục"], r["Số tiền chi"], r["Ghi chú"]])


def days_in_month(month: int | None = None, year: int | None = None) -> int:
    now = datetime.now()
    return calendar.monthrange(year or now.year, month or now.month)[1]


_date_cache: dict[str, datetime] = {}


def parse_date(d: str) -> datetime:
    r = _date_cache.get(d)
    if r is not None:
        return r
    for f in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            r = datetime.strptime(d, f)
            _date_cache[d] = r
            return r
        except ValueError:
            continue
    _date_cache[d] = datetime.min
    return datetime.min

# ══════════════════════════════════════════════════════════════
#  WIDGETS
# ══════════════════════════════════════════════════════════════

class StatCard(ctk.CTkFrame):
    """Summary card: label + big number + optional progress bar."""

    def __init__(self, master, title: str, value: str, color: str,
                 progress: float | None = None, **kw):
        super().__init__(master, fg_color=COL["card"], corner_radius=12, **kw)
        ctk.CTkLabel(self, text=title, font=("Segoe UI", 13),
                     text_color=COL["dim"]).pack(anchor="w", padx=14, pady=(10, 0))
        ctk.CTkLabel(self, text=value, font=("Segoe UI", 20, "bold"),
                     text_color=color).pack(anchor="w", padx=14, pady=(2, 4))
        if progress is not None:
            bar = ctk.CTkProgressBar(self, width=200, height=8,
                                      progress_color=color, fg_color=COL["input"],
                                      corner_radius=4)
            bar.set(max(0.0, min(1.0, progress)))
            bar.pack(fill="x", padx=14, pady=(0, 10))
        else:
            ctk.CTkFrame(self, height=8, fg_color="transparent").pack()


class SidebarBtn(ctk.CTkButton):
    """Sidebar navigation button."""

    def __init__(self, master, text: str, command, **kw):
        super().__init__(
            master, text=text, command=command,
            font=("Segoe UI", 13), anchor="w",
            fg_color="transparent", hover_color=COL["hover"],
            text_color=COL["fg"], height=38, corner_radius=8,
            **kw,
        )
