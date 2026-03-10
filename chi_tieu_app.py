"""
╔══════════════════════════════════════════════════════════════╗
║       QUẢN LÝ CHI TIÊU CÁ NHÂN — PHIÊN BẢN WINDOWS GUI   ║
║         Personal Expense Tracker  (customtkinter)            ║
╠══════════════════════════════════════════════════════════════╣
║  Chạy:  python chi_tieu_app.py                               ║
╚══════════════════════════════════════════════════════════════╝
"""

import csv
import json
import os
import calendar
import customtkinter as ctk
from tkinter import ttk, messagebox, Canvas
from datetime import datetime
from collections import defaultdict, OrderedDict
from functools import lru_cache

# ======================================================================
# CẤU HÌNH
# ======================================================================
DEFAULT_BUDGET = {
    "Ăn uống":    3_000_000,
    "Xăng xe":      500_000,
    # "Người yêu":  1_000_000,
    "Lặt vặt":      500_000,
    # "Trọ":        2_500_000,
}
DEFAULT_DAILY_TRACK = {"Ăn uống", "Xăng xe"}  # danh mục mặc định theo dõi dư/âm
CSV_HEADERS = ["Ngày nhập", "Danh mục", "Số tiền chi", "Ghi chú"]

# Khi đóng gói bằng PyInstaller --onefile, __file__ trỏ vào thư mục tạm.
# Dùng sys.executable để lấy đúng thư mục chứa .exe
import sys
if getattr(sys, 'frozen', False):
    _APP_DIR = os.path.dirname(sys.executable)
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Data & config sống trong thư mục con "data/"
DATA_DIR = os.path.join(_APP_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "danh_muc_config.json")

# ── Palette (Catppuccin Mocha-inspired) ──
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

# ======================================================================
# CONFIG I/O
# ======================================================================

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # Migrate: ensure every entry has daily_track and daily_times fields
        changed = False
        for cat, info in cfg.items():
            if "daily_track" not in info:
                info["daily_track"] = cat in DEFAULT_DAILY_TRACK
                changed = True
            if "daily_times" not in info:
                info["daily_times"] = 0  # 0 = chia theo ngày trong tháng
                changed = True
        if changed:
            save_config(cfg)
        return cfg
    cfg = {cat: {"budget": b, "enabled": True, "daily_track": cat in DEFAULT_DAILY_TRACK, "daily_times": 0}
           for cat, b in DEFAULT_BUDGET.items()}
    save_config(cfg)
    return cfg

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

# ======================================================================
# TIỆN ÍCH
# ======================================================================

def fmt(amount: int) -> str:
    if amount < 0:
        return "-" + f"{abs(amount):,}đ".replace(",", ".")
    return f"{amount:,}đ".replace(",", ".")

def get_csv_path(month=None, year=None):
    now = datetime.now()
    return os.path.join(DATA_DIR,
        f"ChiTieu_Thang_{(month or now.month):02d}_{year or now.year}.csv")

def init_csv(fp):
    if not os.path.exists(fp):
        with open(fp, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(CSV_HEADERS)

def read_all(fp):
    if not os.path.exists(fp):
        return []
    with open(fp, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["Số tiền chi"] = int(r["Số tiền chi"])
    return rows

def append_row(fp, date_str, cat, amount, note):
    with open(fp, "a", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerow([date_str, cat, amount, note])

def rewrite_csv(fp, rows):
    with open(fp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADERS)
        for r in rows:
            w.writerow([r["Ngày nhập"], r["Danh mục"], r["Số tiền chi"], r["Ghi chú"]])

def days_in_month(month=None, year=None):
    now = datetime.now()
    return calendar.monthrange(year or now.year, month or now.month)[1]

_date_cache: dict[str, datetime] = {}
def parse_date(d):
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

def parse_amount(raw: str) -> int:
    s = raw.strip().replace(",","").replace(".","").replace("k","000").replace("tr","000000")
    return int(s)


# ======================================================================
# CUSTOM WIDGETS
# ======================================================================

class StatCard(ctk.CTkFrame):
    """Summary card: label + big number + optional progress bar."""
    def __init__(self, master, title, value, color, progress=None, **kw):
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
    def __init__(self, master, text, command, **kw):
        super().__init__(master, text=text, command=command,
                         font=("Segoe UI", 13), anchor="w",
                         fg_color="transparent", hover_color=COL["hover"],
                         text_color=COL["fg"], height=38, corner_radius=8,
                         **kw)


# ======================================================================
# APP
# ======================================================================

class ExpenseApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("💸 Quản lý Chi tiêu")
        self.configure(fg_color=COL["bg"])

        # Set window/taskbar icon
        icon_path = os.path.join(_APP_DIR, "app_icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
            self.after(200, lambda: self.iconbitmap(icon_path))

        self.minsize(900, 620)
        w, h = 1000, 680
        sx = (self.winfo_screenwidth() - w) // 2
        sy = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{sx}+{sy}")

        now = datetime.now()
        self.view_month = now.month
        self.view_year = now.year
        self.filepath = get_csv_path(self.view_month, self.view_year)
        init_csv(self.filepath)
        self._csv_cache = {}   # filepath -> (mtime, rows)
        self._config_mtime = 0
        self._reload_config()

        self._setup_tree_style()
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()
        self.show_thong_ke()

    # ─── helpers ───
    def _read_all_cached(self, fp=None):
        """Read CSV with mtime-based cache to avoid re-parsing unchanged files."""
        fp = fp or self.filepath
        try:
            mt = os.path.getmtime(fp)
        except OSError:
            return []
        cached = self._csv_cache.get(fp)
        if cached and cached[0] == mt:
            return cached[1]
        rows = read_all(fp)
        self._csv_cache[fp] = (mt, rows)
        return rows

    def _invalidate_cache(self, fp=None):
        """Clear cache for a file after writing."""
        fp = fp or self.filepath
        self._csv_cache.pop(fp, None)

    def _reload_config(self):
        try:
            mt = os.path.getmtime(CONFIG_PATH)
        except OSError:
            mt = 0
        if mt != self._config_mtime or not hasattr(self, 'config'):
            self.config = load_config()
            self._config_mtime = mt
        self.active_budget = {c: i["budget"] for c, i in self.config.items() if i["enabled"]}
        self.active_cats = list(self.active_budget.keys())
        self.total_budget = sum(self.active_budget.values())
        if hasattr(self, "lbl_budget"):
            self.lbl_budget.configure(text=f"💰 {fmt(self.total_budget)}")

    def _setup_tree_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Dark.Treeview", background=COL["card"], foreground=COL["fg"],
                     fieldbackground=COL["card"], font=("Segoe UI", 20),
                     rowheight=52, borderwidth=0)
        s.configure("Dark.Treeview.Heading", background=COL["card2"],
                     foreground=COL["accent"], font=("Segoe UI", 20, "bold"),
                     borderwidth=0, relief="flat")
        s.map("Dark.Treeview",
               background=[("selected", COL["accent"])],
               foreground=[("selected", COL["bg"])])
        s.map("Dark.Treeview.Heading",
               background=[("active", COL["card2"])])

    # ─── sidebar ───
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, fg_color=COL["sidebar"], width=200, corner_radius=0)
        sb.grid(row=0, column=0, sticky="ns")
        sb.grid_propagate(False)

        ctk.CTkLabel(sb, text="💸 Chi Tiêu", font=("Segoe UI", 20, "bold"),
                     text_color=COL["accent"]).pack(pady=(20, 2))

        # Month navigator
        month_nav = ctk.CTkFrame(sb, fg_color="transparent")
        month_nav.pack(pady=(6, 12))
        ctk.CTkButton(month_nav, text="◀", command=self._prev_month,
                      font=("Segoe UI", 14, "bold"), fg_color="transparent",
                      text_color=COL["accent"], hover_color=COL["hover"],
                      width=30, height=28, corner_radius=6).pack(side="left", padx=2)
        self.lbl_month = ctk.CTkLabel(month_nav,
                                       text=f"Tháng {self.view_month:02d}/{self.view_year}",
                                       font=("Segoe UI", 13, "bold"), text_color=COL["fg"])
        self.lbl_month.pack(side="left", padx=6)
        ctk.CTkButton(month_nav, text="▶", command=self._next_month,
                      font=("Segoe UI", 14, "bold"), fg_color="transparent",
                      text_color=COL["accent"], hover_color=COL["hover"],
                      width=30, height=28, corner_radius=6).pack(side="left", padx=2)

        nav = [
            ("📊  Thống kê",       self.show_thong_ke),
            ("📋  Chi tiêu",        self.show_lich_su),
            ("🍜  Dư / Âm ngày",   self.show_du_am),
            ("⚙️  Quản lý danh mục", self.show_danh_muc),
        ]
        for text, cmd in nav:
            SidebarBtn(sb, text=text, command=cmd).pack(fill="x", padx=12, pady=2)

        ctk.CTkFrame(sb, fg_color="transparent").pack(expand=True)

        self.lbl_budget = ctk.CTkLabel(sb, text=f"💰 {fmt(self.total_budget)}",
                                        font=("Segoe UI", 14, "bold"),
                                        text_color=COL["green"])
        self.lbl_budget.pack(pady=(0, 4))
        ctk.CTkLabel(sb, text="Ngân sách tháng", font=("Segoe UI", 11),
                     text_color=COL["dim"]).pack(pady=(0, 16))

    # ─── month navigation ───
    def _prev_month(self):
        if self.view_month == 1 and self.view_year <= 2026:
            return  # don't go before Jan 2026
        if self.view_month == 1:
            self.view_month = 12
            self.view_year -= 1
        else:
            self.view_month -= 1
        self._switch_month()

    def _next_month(self):
        now = datetime.now()
        if self.view_year > now.year or (self.view_year == now.year and self.view_month >= now.month):
            return  # don't go past current month
        if self.view_month == 12:
            self.view_month = 1
            self.view_year += 1
        else:
            self.view_month += 1
        self._switch_month()

    def _switch_month(self):
        self.filepath = get_csv_path(self.view_month, self.view_year)
        init_csv(self.filepath)
        self.lbl_month.configure(text=f"Tháng {self.view_month:02d}/{self.view_year}")
        # Refresh current page
        self.show_thong_ke()

    def _is_current_month(self):
        now = datetime.now()
        return self.view_month == now.month and self.view_year == now.year

    # ─── main ───
    def _build_main(self):
        self.main = ctk.CTkFrame(self, fg_color=COL["bg"], corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main.grid_rowconfigure(0, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

    def _clear(self):
        for w in self.main.winfo_children():
            w.destroy()

    def _make_scroll_area(self):
        scroll = ctk.CTkScrollableFrame(self.main, fg_color=COL["bg"],
                                         corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=16, pady=12)
        scroll.grid_columnconfigure(0, weight=1)
        # Tăng tốc scroll (mặc định chỉ 1 unit, đổi thành 6)
        def _fast_scroll(event):
            scroll._parent_canvas.yview_scroll(int(-1 * (event.delta / 120) * 40), "units")
        scroll._parent_canvas.bind_all("<MouseWheel>", _fast_scroll)
        return scroll

    def _draw_bar_chart(self, master, by_day, dim, bar_color, max_h=110):
        """Clean bar chart – rounded bars, Y-axis scale, hover tooltips."""
        PAD_T, PAD_B, PAD_L, PAD_R = 14, 24, 44, 10
        GRIDS = 3
        canvas_h = PAD_T + max_h + PAD_B
        c = Canvas(master, height=canvas_h,
                   bg=COL["card"], highlightthickness=0, bd=0)
        c.pack(fill="x", padx=10, pady=(8, 6))

        max_val = max(by_day.values()) if by_day else 1
        is_cur = self._is_current_month()
        today = datetime.now().day

        def _fmt_val(v):
            if v >= 1_000_000: return f"{v/1_000_000:.1f}M"
            if v >= 1_000:     return f"{v/1_000:.0f}K"
            return f"{v:.0f}"

        # ── Hover tooltip ──
        def _show_tip(evt, day, val):
            c.delete("tip")
            if val <= 0:
                return
            txt = f"Ngày {day}: {val:,.0f}đ"
            tid = c.create_text(evt.x, PAD_T - 2, text=txt, anchor="s",
                                fill=COL["fg"], font=("Segoe UI", 9, "bold"), tags="tip")
            bb = c.bbox(tid)
            if bb:
                c.create_rectangle(bb[0]-6, bb[1]-2, bb[2]+6, bb[3]+2,
                                   fill=COL["card2"], outline=COL["dim"], tags="tip")
                c.tag_raise(tid)

        def _hide_tip(evt=None):
            c.delete("tip")

        def _redraw(event=None):
            c.delete("all")
            cw = c.winfo_width()
            if cw < 60:
                return
            chart_w = cw - PAD_L - PAD_R
            gap = max(2, chart_w // (dim * 5))
            bar_w = max(4, (chart_w - gap * (dim + 1)) // dim)
            r = min(bar_w // 2, 4)        # corner radius
            y_base = PAD_T + max_h

            # ── Grid lines & Y labels ──
            for i in range(GRIDS + 1):
                y = PAD_T + int(max_h * i / GRIDS)
                gv = max_val * (GRIDS - i) / GRIDS
                c.create_line(PAD_L, y, cw - PAD_R, y,
                              fill=COL["input"], width=1)
                if i < GRIDS:             # skip 0 label (it sits on baseline)
                    c.create_text(PAD_L - 6, y, text=_fmt_val(gv), anchor="e",
                                  fill=COL["dim"], font=("Segoe UI", 7))

            # ── Bars ──
            for d in range(1, dim + 1):
                x = PAD_L + gap + (d - 1) * (bar_w + gap)
                val = by_day.get(d, 0)
                is_td = d == today and is_cur

                if val > 0:
                    bar_h = max(4, int(max_h * val / max_val))
                    yt = y_base - bar_h
                    fill = COL["mauve"] if is_td else bar_color
                    # rounded-top rectangle
                    if bar_h > r * 2:
                        c.create_rectangle(x, yt + r, x + bar_w, y_base,
                                           fill=fill, outline="")
                        c.create_oval(x, yt, x + bar_w, yt + r * 2,
                                      fill=fill, outline="")
                    else:
                        c.create_rectangle(x, yt, x + bar_w, y_base,
                                           fill=fill, outline="")
                else:
                    # tiny dot placeholder
                    c.create_oval(x + bar_w//2 - 1, y_base - 3,
                                  x + bar_w//2 + 1, y_base - 1,
                                  fill=COL["input"], outline="")

                # hit area for tooltip
                hit = c.create_rectangle(x - 1, PAD_T, x + bar_w + 1, y_base,
                                         fill="", outline="")
                c.tag_bind(hit, "<Enter>", lambda e, dd=d, vv=val: _show_tip(e, dd, vv))
                c.tag_bind(hit, "<Leave>", _hide_tip)

                # ── Day labels ── show every day but smaller, highlight today
                lbl_clr = COL["accent"] if is_td else COL["dim"]
                lbl_f = ("Segoe UI", 8, "bold") if is_td else ("Segoe UI", 7)
                c.create_text(x + bar_w // 2, y_base + 11,
                              text=str(d), fill=lbl_clr, font=lbl_f)

        c.bind("<Configure>", _redraw)
        return c

    def _draw_stacked_bar(self, master, segments, total, height=24):
        """Draw stacked horizontal bar using Canvas."""
        if total <= 0:
            return
        c = Canvas(master, height=height, bg=COL["input"], highlightthickness=0, bd=0)
        c.pack(fill="x", pady=(0, 8))
        # Defer drawing until canvas knows its width
        def _draw(event=None):
            cw = c.winfo_width()
            if cw < 2:
                return
            c.delete("bars")
            x = 0
            for color, value in segments:
                w = max(2, int(cw * value / total))
                c.create_rectangle(x, 0, x + w, height,
                                   fill=color, outline="", tags="bars")
                x += w
        c.bind("<Configure>", _draw)
        return c

    # ==================================================================
    #  📊  THỐNG KÊ
    # ==================================================================
    def show_thong_ke(self):
        self._clear()
        self._reload_config()
        area = self._make_scroll_area()
        rows = self._read_all_cached()
        month, year = self.view_month, self.view_year
        dim = days_in_month(month, year)

        spent = defaultdict(int)
        count_by_cat = defaultdict(int)
        by_day = defaultdict(int)
        by_cat_day = defaultdict(lambda: defaultdict(int))
        for r in rows:
            cat = r["Danh mục"]
            amt = r["Số tiền chi"]
            spent[cat] += amt
            count_by_cat[cat] += 1
            dt = parse_date(r["Ngày nhập"])
            by_day[dt.day] += amt
            by_cat_day[cat][dt.day] += amt
        total_spent = sum(spent.values())
        total_remain = self.total_budget - total_spent
        total_txn = len(rows)

        # ── Header ──
        ctk.CTkLabel(area, text=f"📊  Thống kê tháng {month:02d}/{year}",
                     font=("Segoe UI", 20, "bold"), text_color=COL["fg"]
                     ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        # ── Summary Cards (4 cards) ──
        cards = ctk.CTkFrame(area, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        cards.grid_columnconfigure((0, 1, 2, 3), weight=1)

        pct_used = total_spent / self.total_budget if self.total_budget else 0
        StatCard(cards, "Ngân sách", fmt(self.total_budget), COL["accent"]
                 ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        StatCard(cards, "Đã chi", fmt(total_spent), COL["yellow"], progress=pct_used
                 ).grid(row=0, column=1, sticky="ew", padx=3)
        remain_color = COL["green"] if total_remain >= 0 else COL["red"]
        StatCard(cards, "Còn lại", fmt(total_remain), remain_color
                 ).grid(row=0, column=2, sticky="ew", padx=3)
        avg_day = total_spent // max(1, len(by_day)) if by_day else 0
        StatCard(cards, "TB / ngày chi", fmt(avg_day), COL["peach"]
                 ).grid(row=0, column=3, sticky="ew", padx=(6, 0))

        # ── Quick Stats Row ──
        qs = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=10)
        qs.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        qs_inner = ctk.CTkFrame(qs, fg_color="transparent")
        qs_inner.pack(fill="x", padx=14, pady=10)

        days_with = len(by_day)
        days_without = dim - days_with
        max_day = max(by_day.values()) if by_day else 0
        max_day_num = max(by_day, key=by_day.get) if by_day else "-"
        top_cat = max(spent, key=spent.get) if spent else "-"

        quick_items = [
            ("📝", "Giao dịch", str(total_txn)),
            ("📅", "Ngày có chi", f"{days_with}/{dim}"),
            ("💤", "Ngày không chi", str(days_without)),
            ("🔥", "Chi nhiều nhất", f"{fmt(max_day)} (ngày {max_day_num})" if by_day else "-"),
            ("🏆", "Danh mục nhiều nhất", f"{top_cat}" if spent else "-"),
        ]
        for icon, label, val in quick_items:
            qf = ctk.CTkFrame(qs_inner, fg_color="transparent")
            qf.pack(side="left", expand=True)
            ctk.CTkLabel(qf, text=f"{icon} {label}", font=("Segoe UI", 11),
                         text_color=COL["dim"]).pack()
            ctk.CTkLabel(qf, text=val, font=("Segoe UI", 13, "bold"),
                         text_color=COL["fg"]).pack()

        # ── Tổng kết ──
        summary = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=12)
        summary.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        sf = ctk.CTkFrame(summary, fg_color="transparent")
        sf.pack(fill="x", padx=14, pady=10)
        ctk.CTkLabel(sf, text="TỔNG KẾT", font=("Segoe UI", 15, "bold"),
                     text_color=COL["fg"]).pack(side="left")
        total_color = COL["green"] if total_remain >= 0 else COL["red"]
        ctk.CTkLabel(sf, text=f"Còn lại: {fmt(total_remain)}",
                     font=("Segoe UI", 15, "bold"),
                     text_color=total_color).pack(side="right")

        # ── Tỉ lệ chi tiêu ──
        COLORS = [COL["accent"], COL["teal"], COL["peach"], COL["mauve"],
                  COL["yellow"], COL["green"], COL["red"]]

        ctk.CTkLabel(area, text="🍩  Tỉ lệ chi tiêu", font=("Segoe UI", 16, "bold"),
                     text_color=COL["fg"]).grid(row=4, column=0, sticky="w", pady=(4, 6))

        pct_frame = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=12)
        pct_frame.grid(row=5, column=0, sticky="ew")
        pct_inner = ctk.CTkFrame(pct_frame, fg_color="transparent")
        pct_inner.pack(fill="x", padx=16, pady=12)

        # Stacked horizontal bar (Canvas-based)
        if total_spent > 0:
            segments = []
            for i, cat in enumerate(self.active_cats):
                s = spent.get(cat, 0)
                if s > 0:
                    segments.append((COLORS[i % len(COLORS)], s))
            self._draw_stacked_bar(pct_inner, segments, total_spent)

        # Legend with percentages
        legend = ctk.CTkFrame(pct_inner, fg_color="transparent")
        legend.pack(fill="x")
        for i, cat in enumerate(self.active_cats):
            s = spent.get(cat, 0)
            p = (s / total_spent * 100) if total_spent else 0
            if s <= 0:
                continue
            color = COLORS[i % len(COLORS)]
            lf = ctk.CTkFrame(legend, fg_color="transparent")
            lf.pack(side="left", padx=(0, 16), pady=2)
            ctk.CTkFrame(lf, fg_color=color, width=10, height=10,
                         corner_radius=5).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(lf, text=f"{cat}: {p:.1f}%", font=("Segoe UI", 12),
                         text_color=COL["fg"]).pack(side="left")

        # ── Chi tiết danh mục ──
        ctk.CTkLabel(area, text="📋  Chi tiết danh mục", font=("Segoe UI", 16, "bold"),
                     text_color=COL["fg"]).grid(row=6, column=0, sticky="w", pady=(8, 6))

        cat_frame = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=12)
        cat_frame.grid(row=7, column=0, sticky="ew")

        for i, cat in enumerate(self.active_cats):
            b = self.active_budget[cat]
            s = spent.get(cat, 0)
            remain = b - s
            pct = s / b if b else 0
            txn_count = count_by_cat.get(cat, 0)
            days_active = len(by_cat_day.get(cat, {}))
            avg_per_txn = s // txn_count if txn_count else 0
            color = COLORS[i % len(COLORS)]

            row_f = ctk.CTkFrame(cat_frame, fg_color="transparent", cursor="hand2")
            row_f.pack(fill="x", padx=16, pady=(10 if i == 0 else 4,
                                                  10 if i == len(self.active_cats)-1 else 4))

            top_row = ctk.CTkFrame(row_f, fg_color="transparent")
            top_row.pack(fill="x")

            # Category name with color dot
            name_f = ctk.CTkFrame(top_row, fg_color="transparent")
            name_f.pack(side="left")
            ctk.CTkFrame(name_f, fg_color=color, width=10, height=10,
                         corner_radius=5).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(name_f, text=cat, font=("Segoe UI", 14, "bold"),
                         text_color=COL["fg"]).pack(side="left")

            # Click hint
            ctk.CTkLabel(top_row, text="▶", font=("Segoe UI", 12),
                         text_color=COL["dim"]).pack(side="left", padx=(8, 0))

            # Amount on right
            status_text = f"{fmt(s)} / {fmt(b)}"
            status_color = COL["dim"] if remain >= 0 else COL["red"]
            ctk.CTkLabel(top_row, text=status_text, font=("Segoe UI", 13, "bold"),
                         text_color=status_color).pack(side="right")

            # Progress bar
            bar_color = color if remain >= 0 else COL["red"]
            bar = ctk.CTkProgressBar(row_f, height=8, progress_color=bar_color,
                                      fg_color=COL["input"], corner_radius=6)
            bar.set(min(1.0, pct))
            bar.pack(fill="x", pady=(3, 0))

            # Detail stats row
            detail_f = ctk.CTkFrame(row_f, fg_color="transparent")
            detail_f.pack(fill="x", pady=(3, 0))
            detail_items = [
                f"Còn lại: {fmt(remain)}" if remain >= 0 else f"⚠ Vượt {fmt(abs(remain))}",
                f"{txn_count} giao dịch",
                f"{days_active} ngày",
                f"TB: {fmt(avg_per_txn)}/lần" if txn_count else "",
            ]
            remain_clr = COL["green"] if remain >= 0 else COL["red"]
            for j, txt in enumerate(detail_items):
                if not txt:
                    continue
                clr = remain_clr if j == 0 else COL["dim"]
                ctk.CTkLabel(detail_f, text=txt, font=("Segoe UI", 11),
                             text_color=clr).pack(side="left", padx=(0, 16))

            # Clickable: show transactions for this category
            def _bind_click(widget, c=cat, clr=color):
                widget.bind("<Button-1>", lambda e: self._show_cat_transactions(c, clr))
                for child in widget.winfo_children():
                    _bind_click(child, c, clr)
            _bind_click(row_f)

    # ─── Show full-page transactions for a category ───
    def _show_cat_transactions(self, cat, color):
        """Show a dedicated page with all transactions for a category."""
        self._clear()
        rows = self._read_all_cached()
        month, year = self.view_month, self.view_year
        budget = self.active_budget.get(cat, 0)

        cat_rows = [r for r in rows if r["Danh mục"] == cat]
        cat_rows.sort(key=lambda r: parse_date(r["Ngày nhập"]), reverse=True)
        total_cat = sum(r["Số tiền chi"] for r in cat_rows)
        remain = budget - total_cat

        area = self._make_scroll_area()

        # ── Header with back button ──
        hdr = ctk.CTkFrame(area, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkButton(hdr, text="◀  Quay lại", command=self.show_thong_ke,
                      font=("Segoe UI", 13, "bold"), fg_color=COL["card2"],
                      text_color=COL["fg"], hover_color=COL["hover"],
                      corner_radius=8, height=34, width=120
                      ).pack(side="left")

        hdr_title = ctk.CTkFrame(hdr, fg_color="transparent")
        hdr_title.pack(side="left", padx=(14, 0))
        ctk.CTkFrame(hdr_title, fg_color=color, width=14, height=14,
                     corner_radius=7).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(hdr_title, text=f"📝  {cat} — Tháng {month:02d}/{year}",
                     font=("Segoe UI", 20, "bold"), text_color=COL["fg"]
                     ).pack(side="left")

        # ── Summary cards ──
        cards = ctk.CTkFrame(area, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        cards.grid_columnconfigure((0, 1, 2, 3), weight=1)

        pct_used = total_cat / budget if budget else 0
        StatCard(cards, "Ngân sách", fmt(budget), COL["accent"]
                 ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        StatCard(cards, "Đã chi", fmt(total_cat), COL["yellow"], progress=pct_used
                 ).grid(row=0, column=1, sticky="ew", padx=3)
        remain_color = COL["green"] if remain >= 0 else COL["red"]
        StatCard(cards, "Còn lại", fmt(remain), remain_color
                 ).grid(row=0, column=2, sticky="ew", padx=3)
        avg = total_cat // len(cat_rows) if cat_rows else 0
        StatCard(cards, "TB / giao dịch", fmt(avg), COL["peach"]
                 ).grid(row=0, column=3, sticky="ew", padx=(6, 0))

        # ── Spending chart for this category ──
        dim = days_in_month(month, year)
        by_day = defaultdict(int)
        for r in cat_rows:
            dt = parse_date(r["Ngày nhập"])
            by_day[dt.day] += r["Số tiền chi"]

        ctk.CTkLabel(area, text=f"📈  Chi tiêu theo ngày — {cat}",
                     font=("Segoe UI", 16, "bold"), text_color=COL["fg"]
                     ).grid(row=2, column=0, sticky="w", pady=(4, 4))

        chart = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=12)
        chart.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self._draw_bar_chart(chart, by_day, dim, color, max_h=70)

        # ── Transaction list ──
        ctk.CTkLabel(area, text=f"📋  Lịch sử giao dịch ({len(cat_rows)})",
                     font=("Segoe UI", 16, "bold"), text_color=COL["fg"]
                     ).grid(row=4, column=0, sticky="w", pady=(8, 6))

        if not cat_rows:
            empty = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=12)
            empty.grid(row=5, column=0, sticky="ew")
            ctk.CTkLabel(empty, text="  Chưa có giao dịch nào", font=("Segoe UI", 14),
                         text_color=COL["dim"]).pack(padx=14, pady=16)
        else:
            by_date = OrderedDict()
            for r in cat_rows:
                by_date.setdefault(r["Ngày nhập"], []).append(r)

            list_card = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=12)
            list_card.grid(row=5, column=0, sticky="ew")

            for di, (date_str, day_rows) in enumerate(by_date.items()):
                day_total = sum(r["Số tiền chi"] for r in day_rows)

                # Date header
                dh = ctk.CTkFrame(list_card, fg_color=COL["card2"] if di % 2 == 0 else "transparent",
                                  corner_radius=8)
                dh.pack(fill="x", padx=10, pady=(8 if di == 0 else 4, 2))
                ctk.CTkLabel(dh, text=f"📅 {date_str}", font=("Segoe UI", 14, "bold"),
                             text_color=COL["accent"]).pack(side="left", padx=8, pady=4)
                ctk.CTkLabel(dh, text=f"{len(day_rows)} giao dịch  ·  {fmt(day_total)}",
                             font=("Segoe UI", 12, "bold"),
                             text_color=COL["dim"]).pack(side="right", padx=8, pady=4)

                for r in day_rows:
                    rf = ctk.CTkFrame(list_card, fg_color="transparent")
                    rf.pack(fill="x", padx=16, pady=3)

                    # Amount badge
                    amt_badge = ctk.CTkFrame(rf, fg_color=color, corner_radius=8)
                    amt_badge.pack(side="left")
                    ctk.CTkLabel(amt_badge, text=f" {fmt(r['Số tiền chi'])} ",
                                 font=("Segoe UI", 13, "bold"),
                                 text_color=COL["bg"]).pack(padx=8, pady=3)

                    # Note
                    note = r["Ghi chú"] if r["Ghi chú"] != "-" else ""
                    if note:
                        ctk.CTkLabel(rf, text=note, font=("Segoe UI", 13),
                                     text_color=COL["fg"]).pack(side="left", padx=(12, 0))

            ctk.CTkFrame(list_card, fg_color="transparent", height=10).pack()

    # ==================================================================
    #  📋  CHI TIÊU  (Calendar View)
    # ==================================================================
    def show_lich_su(self):
        self._clear()
        self._reload_config()
        rows = self._read_all_cached()
        now = datetime.now()
        month, year = self.view_month, self.view_year
        dim = days_in_month(month, year)

        # ── group by day number ──
        by_day = defaultdict(list)  # day_num -> [row, ...]
        total = 0
        for r in rows:
            dt = parse_date(r["Ngày nhập"])
            by_day[dt.day].append(r)
            total += r["Số tiền chi"]

        area = self._make_scroll_area()

        # ── Header ──
        hdr = ctk.CTkFrame(area, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(hdr, text=f"📋  Chi tiêu tháng {month:02d}/{year}",
                     font=("Segoe UI", 20, "bold"), text_color=COL["fg"]
                     ).pack(side="left")
        ctk.CTkLabel(hdr, text=f"{len(rows)} giao dịch",
                     font=("Segoe UI", 13), text_color=COL["dim"]
                     ).pack(side="left", padx=(12, 0))

        cal_grid_row = 1

        # ── Calendar grid ──
        cal_card = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=14)
        cal_card.grid(row=cal_grid_row, column=0, sticky="ew", pady=(0, 8))
        for c in range(7):
            cal_card.grid_columnconfigure(c, weight=1)

        # Day-of-week headers
        DOW = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        DOW_COLORS = [COL["fg"]]*5 + [COL["accent"], COL["red"]]
        for c, (name, clr) in enumerate(zip(DOW, DOW_COLORS)):
            ctk.CTkLabel(cal_card, text=name, font=("Segoe UI", 12, "bold"),
                         text_color=clr).grid(row=0, column=c, pady=(10, 4))

        # First day of month -> weekday (Mon=0)
        first_wd = calendar.weekday(year, month, 1)
        grid_row = 1
        col = first_wd

        CAT_COLORS = {cat: [COL["accent"], COL["teal"], COL["peach"], COL["mauve"],
                             COL["yellow"], COL["green"], COL["red"]][i % 7]
                      for i, cat in enumerate(self.active_cats)}

        self._cal_detail_widgets = []  # track detail panel for toggling

        for day in range(1, dim + 1):
            is_today = (day == now.day and self._is_current_month())
            has_data = day in by_day
            day_spent = sum(r["Số tiền chi"] for r in by_day.get(day, []))

            # ── Cell frame ──
            cell_fg = COL["card2"] if is_today else "transparent"
            cell = ctk.CTkFrame(cal_card, fg_color=cell_fg, corner_radius=8,
                                height=72, width=90)
            cell.grid(row=grid_row, column=col, padx=3, pady=3, sticky="nsew")
            cell.grid_propagate(False)

            # Build cell text: day number + amount + dots via single label
            day_color = COL["accent"] if is_today else (COL["fg"] if has_data else COL["dim"])
            day_font = ("Segoe UI", 13, "bold") if is_today else ("Segoe UI", 12)
            ctk.CTkLabel(cell, text=str(day), font=day_font,
                         text_color=day_color).pack(anchor="nw", padx=6, pady=(4, 0))

            if has_data:
                ctk.CTkLabel(cell, text=fmt(day_spent),
                             font=("Segoe UI", 11, "bold"),
                             text_color=COL["yellow"]).pack(anchor="nw", padx=6)

                # Colored dots via Canvas (fast, single widget)
                cats_today = list({r["Danh mục"] for r in by_day[day]})[:4]
                if cats_today:
                    dot_cv = Canvas(cell, width=len(cats_today)*11, height=8,
                                   bg=cell._fg_color if isinstance(cell._fg_color, str) and cell._fg_color != "transparent" else COL["bg"],
                                   highlightthickness=0, bd=0)
                    dot_cv.pack(anchor="nw", padx=6, pady=(1, 0))
                    for ci, cat in enumerate(cats_today):
                        dc = CAT_COLORS.get(cat, COL["dim"])
                        dot_cv.create_oval(ci*11, 0, ci*11+8, 8, fill=dc, outline="")

            # Click handler
            cell.bind("<Button-1>", lambda e, d=day: self._show_day_detail(d, by_day, rows, area))
            for child in cell.winfo_children():
                child.bind("<Button-1>", lambda e, d=day: self._show_day_detail(d, by_day, rows, area))
            cell.configure(cursor="hand2")

            # Advance grid position
            col += 1
            if col > 6:
                col = 0
                grid_row += 1

        # ── Legend ──
        legend_f = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=10)
        legend_f.grid(row=cal_grid_row + 1, column=0, sticky="ew", pady=(4, 4))
        leg_inner = ctk.CTkFrame(legend_f, fg_color="transparent")
        leg_inner.pack(padx=12, pady=8)
        for cat in self.active_cats:
            dc = CAT_COLORS.get(cat, COL["dim"])
            cf = ctk.CTkFrame(leg_inner, fg_color="transparent")
            cf.pack(side="left", padx=(0, 14))
            ctk.CTkFrame(cf, fg_color=dc, width=10, height=10,
                         corner_radius=5).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(cf, text=cat, font=("Segoe UI", 11),
                         text_color=COL["fg"]).pack(side="left")

        # ── Total bar ──
        total_bar = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=10)
        total_bar.grid(row=cal_grid_row + 2, column=0, sticky="ew", pady=(4, 4))
        ctk.CTkLabel(total_bar, text=f"💰  Tổng chi tháng:  {fmt(total)}",
                     font=("Segoe UI", 17, "bold"), text_color=COL["yellow"]
                     ).pack(padx=14, pady=10)

        # ── Detail panel placeholder ──
        self._detail_area = ctk.CTkFrame(area, fg_color="transparent")
        self._detail_area.grid(row=cal_grid_row + 3, column=0, sticky="ew")

    def _show_day_detail(self, day, by_day, all_rows, area):
        """Show detail panel for a specific day below the calendar."""
        # Clear previous detail
        for w in self._detail_area.winfo_children():
            w.destroy()

        month, year = self.view_month, self.view_year
        day_rows = by_day.get(day, [])

        panel = ctk.CTkFrame(self._detail_area, fg_color=COL["card"], corner_radius=12)
        panel.pack(fill="x", pady=(4, 0))

        # ── Panel header ──
        ph = ctk.CTkFrame(panel, fg_color="transparent")
        ph.pack(fill="x", padx=14, pady=(10, 4))
        day_total = sum(r["Số tiền chi"] for r in day_rows)
        ctk.CTkLabel(ph, text=f"📅  Ngày {day}/{month}/{year}",
                     font=("Segoe UI", 15, "bold"), text_color=COL["accent"]
                     ).pack(side="left")
        if day_total:
            ctk.CTkLabel(ph, text=f"Tổng: {fmt(day_total)}",
                         font=("Segoe UI", 14, "bold"), text_color=COL["yellow"]
                         ).pack(side="right")

        # ── Separator ──
        ctk.CTkFrame(panel, fg_color=COL["input"], height=1).pack(fill="x", padx=14, pady=2)

        # ══════════════════════════════════════════════
        #  ✏️  INPUT FORM  (beautiful inline form)
        # ══════════════════════════════════════════════
        form = ctk.CTkFrame(panel, fg_color=COL["card2"], corner_radius=10)
        form.pack(fill="x", padx=12, pady=(6, 4))

        # Title row
        ctk.CTkLabel(form, text="✏️  Nhập chi tiêu",
                     font=("Segoe UI", 13, "bold"), text_color=COL["accent"]
                     ).pack(anchor="w", padx=12, pady=(8, 4))

        # Label row (above inputs, aligned by matching widths)
        lbl_row = ctk.CTkFrame(form, fg_color="transparent")
        lbl_row.pack(fill="x", padx=12, pady=(0, 0))
        ctk.CTkLabel(lbl_row, text="Danh mục", font=("Segoe UI", 11),
                     text_color=COL["dim"], width=150, anchor="w"
                     ).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(lbl_row, text="Số tiền", font=("Segoe UI", 11),
                     text_color=COL["dim"], width=130, anchor="w"
                     ).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(lbl_row, text="Ghi chú", font=("Segoe UI", 11),
                     text_color=COL["dim"], anchor="w"
                     ).pack(side="left")

        # Input row: Danh mục + Số tiền + Ghi chú
        inp_row = ctk.CTkFrame(form, fg_color="transparent")
        inp_row.pack(fill="x", padx=12, pady=(0, 4))

        cat_var = ctk.StringVar(value=self.active_cats[0] if self.active_cats else "")
        ctk.CTkOptionMenu(inp_row, variable=cat_var, values=self.active_cats,
                          font=("Segoe UI", 13), fg_color=COL["input"],
                          corner_radius=8, height=34, width=150,
                          dropdown_fg_color=COL["card"],
                          dropdown_hover_color=COL["hover"],
                          dropdown_text_color=COL["fg"],
                          dropdown_font=("Segoe UI", 13),
                          button_color=COL["accent"],
                          button_hover_color=COL["hover"],
                          text_color=COL["fg"],
                          ).pack(side="left", padx=(0, 6))

        amt_var = ctk.StringVar()
        e_amt = ctk.CTkEntry(inp_row, textvariable=amt_var, font=("Segoe UI", 13),
                              fg_color=COL["input"], border_width=0, corner_radius=8,
                              height=34, width=130, placeholder_text="VD: 50000")
        e_amt.pack(side="left", padx=(0, 6))

        note_var = ctk.StringVar()
        ctk.CTkEntry(inp_row, textvariable=note_var, font=("Segoe UI", 13),
                     fg_color=COL["input"], border_width=0, corner_radius=8,
                     height=34, placeholder_text="VD: Cơm trưa, cafe..."
                     ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        # Button row: Lưu + feedback
        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        feedback = ctk.CTkLabel(btn_row, text="", font=("Segoe UI", 12),
                                 text_color=COL["green"])

        target_date_str = f"{day}/{month}/{year}"
        # Determine correct CSV path for the target month
        target_csv = get_csv_path(month, year)
        init_csv(target_csv)

        def do_save():
            try:
                amount = parse_amount(amt_var.get())
                if amount <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                messagebox.showerror("Lỗi", "Số tiền không hợp lệ!")
                return
            cat = cat_var.get()
            if not cat:
                messagebox.showerror("Lỗi", "Chưa chọn danh mục!")
                return
            note = note_var.get().strip() or "-"
            append_row(target_csv, target_date_str, cat, amount, note)
            self._invalidate_cache(target_csv)
            feedback.configure(text=f"✅ {cat} · {fmt(amount)}")
            amt_var.set("")
            note_var.set("")
            e_amt.focus_set()
            # Reload calendar after short delay
            self.after(500, self.show_lich_su)

        ctk.CTkButton(btn_row, text="💾 Lưu", command=do_save,
                      font=("Segoe UI", 13, "bold"), fg_color=COL["accent"],
                      text_color=COL["bg"], hover_color=COL["hover"],
                      corner_radius=8, height=34, width=90
                      ).pack(side="left", padx=(0, 8))
        feedback.pack(side="left")

        e_amt.focus_set()

        # ══════════════════════════════════════════════
        #  📝  TRANSACTION LIST
        # ══════════════════════════════════════════════
        if day_rows:
            ctk.CTkLabel(panel, text=f"📝  Giao dịch ({len(day_rows)})",
                         font=("Segoe UI", 13, "bold"), text_color=COL["dim"]
                         ).pack(anchor="w", padx=14, pady=(6, 2))

            CAT_COLORS = {cat: [COL["accent"], COL["teal"], COL["peach"], COL["mauve"],
                                 COL["yellow"], COL["green"], COL["red"]][i % 7]
                          for i, cat in enumerate(self.active_cats)}

            for i, r in enumerate(day_rows):
                rf = ctk.CTkFrame(panel, fg_color="transparent")
                rf.pack(fill="x", padx=14, pady=3)

                cat_color = CAT_COLORS.get(r["Danh mục"], COL["dim"])

                # Top row: badge + note + amount + delete
                top = ctk.CTkFrame(rf, fg_color="transparent")
                top.pack(fill="x")

                # Category badge
                badge = ctk.CTkFrame(top, fg_color=cat_color, corner_radius=8)
                badge.pack(side="left", fill="y")
                ctk.CTkLabel(badge, text=f" {r['Danh mục']} ", font=("Segoe UI", 13, "bold"),
                             text_color=COL["bg"]).pack(padx=6, pady=3, expand=True)

                # Note badge (same color, next to category, fill remaining width)
                note = r["Ghi chú"] if r["Ghi chú"] != "-" else ""
                if note:
                    note_badge = ctk.CTkFrame(top, fg_color=cat_color, corner_radius=8)
                    note_badge.pack(side="left", padx=(8, 0), fill="both", expand=True)
                    ctk.CTkLabel(note_badge, text=note, font=("Segoe UI", 13),
                                 text_color=COL["bg"], wraplength=450, justify="left", anchor="w"
                                 ).pack(padx=8, pady=3, fill="x")

                # Amount
                ctk.CTkLabel(top, text=fmt(r["Số tiền chi"]), font=("Segoe UI", 13, "bold"),
                             text_color=COL["fg"]).pack(side="right")

                # Delete button per row
                def make_del(row=r):
                    def do_del():
                        if messagebox.askyesno("Xác nhận xóa",
                                f"Xóa:\n{row['Ngày nhập']}  |  {row['Danh mục']}  |  "
                                f"{fmt(row['Số tiền chi'])}?"):
                            for j, orig in enumerate(all_rows):
                                if (orig["Ngày nhập"] == row["Ngày nhập"] and
                                    orig["Danh mục"] == row["Danh mục"] and
                                    orig["Số tiền chi"] == row["Số tiền chi"] and
                                    orig["Ghi chú"] == row["Ghi chú"]):
                                    all_rows.pop(j)
                                    break
                            rewrite_csv(self.filepath, all_rows)
                            self._invalidate_cache()
                            self.show_lich_su()
                    return do_del

                ctk.CTkButton(top, text="✕", command=make_del(r),
                              font=("Segoe UI", 12), fg_color="transparent",
                              text_color=COL["red"], hover_color=COL["card2"],
                              corner_radius=6, width=28, height=26
                              ).pack(side="right", padx=(0, 8))

        # Bottom pad
        ctk.CTkFrame(panel, fg_color="transparent", height=8).pack()

    # ==================================================================
    #  🍜  DƯ / ÂM HÀNG NGÀY
    # ==================================================================
    def show_du_am(self):
        self._clear()
        self._reload_config()
        area = self._make_scroll_area()
        month, year = self.view_month, self.view_year
        rows = self._read_all_cached()

        # Header + nút quản lý
        hdr = ctk.CTkFrame(area, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(hdr, text=f"🍜  Dư / Âm — Tháng {month:02d}/{year}",
                     font=("Segoe UI", 20, "bold"), text_color=COL["fg"]
                     ).pack(side="left")
        ctk.CTkButton(hdr, text="⚙  Chọn danh mục theo dõi",
                      font=("Segoe UI", 13), fg_color=COL["card2"],
                      text_color=COL["fg"], hover_color=COL["hover"],
                      corner_radius=8, height=34,
                      command=lambda: self._open_daily_track_dlg()
                      ).pack(side="right")

        dim = days_in_month(month, year)

        # Lấy danh mục được theo dõi
        tracked = {cat: info for cat, info in self.config.items()
                   if info.get("daily_track") and info.get("enabled")}

        if not tracked:
            ctk.CTkLabel(area, text="Chưa chọn danh mục nào để theo dõi.\n"
                         "Nhấn nút ⚙ để cài đặt.",
                         font=("Segoe UI", 14), text_color=COL["dim"]
                         ).grid(row=1, column=0, pady=30)
            return

        grid_row = 1
        grand_total = 0
        ICONS = ["🍜", "⛽", "💳", "🎪", "🛠", "🎁", "🏠"]
        # Nếu đang xem tháng hiện tại → today = ngày hiện tại, ngược lại = cuối tháng
        if self._is_current_month():
            today = datetime.now().day
        else:
            today = dim

        for idx, (cat, info) in enumerate(tracked.items()):
            budget = info["budget"]
            times = info.get("daily_times", 0)
            if times > 0:
                per_budget = budget // times if budget else 0
                unit_label = f"Định mức {fmt(per_budget)}/lần ({times} lần/tháng)"
            else:
                per_budget = budget // dim if budget else 0
                unit_label = f"Định mức {fmt(per_budget)}/ngày"
            icon = ICONS[idx % len(ICONS)]

            # Gather data by day
            by_day = defaultdict(int)
            total_spent_cat = 0
            for r in rows:
                if r["Danh mục"] == cat:
                    by_day[r["Ngày nhập"]] += r["Số tiền chi"]
                    total_spent_cat += r["Số tiền chi"]

            # Section header
            ctk.CTkLabel(area, text=f"{icon}  {cat} — {unit_label}",
                         font=("Segoe UI", 15, "bold"), text_color=COL["fg"]
                         ).grid(row=grid_row, column=0, sticky="w", pady=(0, 6))
            grid_row += 1

            card = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=12)
            card.grid(row=grid_row, column=0, sticky="ew", pady=(0, 6))
            grid_row += 1

            for day in sorted(by_day, key=parse_date):
                chi = by_day[day]
                du = per_budget - chi
                rf = ctk.CTkFrame(card, fg_color="transparent")
                rf.pack(fill="x", padx=14, pady=5)
                ctk.CTkLabel(rf, text=day, font=("Segoe UI", 13),
                             text_color=COL["fg"]).pack(side="left")
                ctk.CTkLabel(rf, text=f"Chi: -{fmt(chi)}", font=("Segoe UI", 13),
                             text_color=COL["dim"]).pack(side="left", padx=(18, 0))
                du_color = COL["green"] if du >= 0 else COL["red"]
                ctk.CTkLabel(rf, text=fmt(du), font=("Segoe UI", 14, "bold"),
                             text_color=du_color).pack(side="right")

            if not by_day:
                ctk.CTkLabel(card, text="  Chưa có dữ liệu", font=("Segoe UI", 13),
                             text_color=COL["dim"]).pack(padx=14, pady=10)

            # Tổng dư
            if times > 0:
                occurrences = len(by_day)
                total_cat = budget - total_spent_cat
                total_text = f"Còn lại {cat} ({occurrences}/{times} lần)"
            else:
                total_cat = today * per_budget - total_spent_cat
                total_text = f"Tổng dư {cat} ({today} ngày)"
            c = COL["red"] if total_cat < 0 else COL["green"]
            ctk.CTkLabel(area, text=f"{total_text}: {fmt(total_cat)}",
                         font=("Segoe UI", 14, "bold"), text_color=c
                         ).grid(row=grid_row, column=0, sticky="e", pady=(4, 10))
            grid_row += 1
            # Chỉ cộng vào tổng: danh mục theo ngày luôn cộng;
            # danh mục theo lần chỉ cộng khi hết tháng hoặc đã tiêu hết budget
            if times > 0:
                is_month_over = (today == dim)
                if is_month_over or total_spent_cat >= budget:
                    grand_total += total_cat
            else:
                grand_total += total_cat

        # ── Tổng ──
        tc = COL["red"] if grand_total < 0 else COL["green"]
        total_card = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=12)
        total_card.grid(row=grid_row, column=0, sticky="ew")
        ctk.CTkLabel(total_card, text=f"💰  TỔNG DƯ / ÂM THÁNG:  {fmt(grand_total)}",
                     font=("Segoe UI", 17, "bold"), text_color=tc
                     ).pack(padx=18, pady=14)

    # ─── Dialog chọn danh mục theo dõi ───
    def _open_daily_track_dlg(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Chọn danh mục theo dõi Dư/Âm")
        dlg.configure(fg_color=COL["card"])
        dlg.resizable(False, False)
        dlg.grab_set()
        dw, dh = 520, min(560, 90 + 50 * len(self.config) + 60)
        dx = self.winfo_x() + (self.winfo_width() - dw) // 2
        dy = self.winfo_y() + (self.winfo_height() - dh) // 2
        dlg.geometry(f"{dw}x{dh}+{dx}+{dy}")

        ctk.CTkLabel(dlg, text="Bật/tắt theo dõi & cài đặt số lần:",
                     font=("Segoe UI", 15, "bold"), text_color=COL["fg"]
                     ).pack(padx=16, pady=(14, 4))
        ctk.CTkLabel(dlg, text="Số lần = 0  →  tự chia theo ngày trong tháng",
                     font=("Segoe UI", 12), text_color=COL["dim"]
                     ).pack(padx=16, pady=(0, 8))

        scroll = ctk.CTkScrollableFrame(dlg, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        switches = {}
        time_entries = {}
        for cat, info in self.config.items():
            if not info.get("enabled"):
                continue
            rf = ctk.CTkFrame(scroll, fg_color="transparent")
            rf.pack(fill="x", pady=3)
            ctk.CTkLabel(rf, text=cat, font=("Segoe UI", 14),
                         text_color=COL["fg"]).pack(side="left", padx=(4, 0))
            ctk.CTkLabel(rf, text=f"({fmt(info['budget'])})",
                         font=("Segoe UI", 12), text_color=COL["dim"]
                         ).pack(side="left", padx=(8, 0))
            sw = ctk.CTkSwitch(rf, text="", width=40,
                               fg_color=COL["input"], progress_color=COL["accent"])
            if info.get("daily_track"):
                sw.select()
            sw.pack(side="right", padx=(0, 4))
            switches[cat] = sw
            # Ô nhập số lần
            ctk.CTkLabel(rf, text="lần", font=("Segoe UI", 12),
                         text_color=COL["dim"]).pack(side="right", padx=(0, 6))
            t_var = ctk.StringVar(value=str(info.get("daily_times", 0)))
            ctk.CTkEntry(rf, textvariable=t_var, font=("Segoe UI", 13),
                         fg_color=COL["input"], border_width=0, corner_radius=6,
                         height=30, width=50, justify="center"
                         ).pack(side="right", padx=(8, 0))
            time_entries[cat] = t_var

        def save_track():
            for cat, sw in switches.items():
                self.config[cat]["daily_track"] = bool(sw.get())
                try:
                    t = int(time_entries[cat].get())
                    if t < 0: t = 0
                except (ValueError, KeyError):
                    t = 0
                self.config[cat]["daily_times"] = t
            save_config(self.config)
            self._reload_config()
            dlg.destroy()
            self.show_du_am()

        ctk.CTkButton(dlg, text="💾  Lưu", command=save_track,
                      font=("Segoe UI", 14, "bold"), fg_color=COL["accent"],
                      text_color=COL["bg"], hover_color=COL["hover"],
                      corner_radius=10, height=38, width=140
                      ).pack(pady=(4, 12))

    # ==================================================================
    #  ⚙️  QUẢN LÝ DANH MỤC
    # ==================================================================
    def show_danh_muc(self):
        self._clear()
        self._reload_config()

        header_f = ctk.CTkFrame(self.main, fg_color="transparent")
        header_f.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(header_f, text="⚙️  Quản lý danh mục",
                     font=("Segoe UI", 20, "bold"), text_color=COL["fg"]
                     ).pack(side="left")

        # Treeview
        tree_frame = ctk.CTkFrame(self.main, fg_color=COL["card"], corner_radius=12)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        cols = ("Danh mục", "Ngân sách / tháng", "Trạng thái", "Dư/Âm")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                             height=max(8, len(self.config)), style="Dark.Treeview")
        for c in cols:
            tree.heading(c, text=c)
        tree.column("Danh mục", width=180, anchor="w")
        tree.column("Ngân sách / tháng", width=160, anchor="center")
        tree.column("Trạng thái", width=110, anchor="center")
        tree.column("Dư/Âm", width=100, anchor="center")

        cat_keys = []

        tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        sb_t = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb_t.set)
        sb_t.pack(side="right", fill="y", pady=8, padx=(0, 4))

        # Buttons
        btn_frame = ctk.CTkFrame(self.main, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=4)

        # Total label (must be created before refresh)
        lbl_total = ctk.CTkLabel(self.main,
                                  text="",
                                  font=("Segoe UI", 20, "bold"), text_color=COL["green"])
        lbl_total.pack(padx=16, pady=(4, 12), anchor="w")

        def refresh():
            nonlocal cat_keys
            cat_keys.clear()
            tree.delete(*tree.get_children())
            for cat, info in self.config.items():
                st = "🟢 Bật" if info["enabled"] else "🔴 Tắt"
                dt = "✅" if info.get("daily_track") else "—"
                tg = "on" if info["enabled"] else "off"
                tree.insert("", "end", values=(cat, fmt(info["budget"]), st, dt), tags=(tg,))
                cat_keys.append(cat)
            tree.tag_configure("on", foreground=COL["green"])
            tree.tag_configure("off", foreground=COL["dim"])
            lbl_total.configure(text=f"Tổng ngân sách (bật): {fmt(self.total_budget)}")

        refresh()

        def get_sel():
            s = tree.selection()
            if not s: return None
            i = tree.index(s[0])
            return cat_keys[i] if i < len(cat_keys) else None

        def do_toggle():
            c = get_sel()
            if not c:
                messagebox.showwarning("Chọn dòng", "Hãy chọn 1 danh mục!")
                return
            self.config[c]["enabled"] = not self.config[c]["enabled"]
            save_config(self.config)
            self._reload_config()
            refresh()

        def do_edit():
            c = get_sel()
            if not c:
                messagebox.showwarning("Chọn dòng", "Hãy chọn 1 danh mục!")
                return
            _open_dlg(c)

        def do_del():
            c = get_sel()
            if not c:
                messagebox.showwarning("Chọn dòng", "Hãy chọn 1 danh mục!")
                return
            if not messagebox.askyesno("Xác nhận", f"Xóa danh mục '{c}'?"):
                return
            del self.config[c]
            save_config(self.config)
            self._reload_config()
            refresh()

        for label, cmd, color, tcolor in [
            ("➕  Thêm mới",   lambda: _open_dlg(None), COL["accent"], COL["bg"]),
            ("✏️  Sửa",        do_edit,                  COL["yellow"], COL["bg"]),
            ("🔄  Bật / Tắt",  do_toggle,                COL["card2"],  COL["fg"]),
            ("🗑  Xóa",        do_del,                   COL["red"],    COL["bg"]),
        ]:
            ctk.CTkButton(btn_frame, text=label, command=cmd,
                          font=("Segoe UI", 16), fg_color=color,
                          text_color=tcolor,
                          hover_color=COL["hover"], corner_radius=8,
                          height=42, width=170).pack(side="left", padx=4)

        # Dialog
        def _open_dlg(edit_cat):
            dlg = ctk.CTkToplevel(self)
            dlg.title("Thêm danh mục" if not edit_cat else f"Sửa: {edit_cat}")
            dlg.configure(fg_color=COL["card"])
            dlg.resizable(False, False)
            dlg.grab_set()
            dw, dh = 460, 280
            dx = self.winfo_x() + (self.winfo_width() - dw) // 2
            dy = self.winfo_y() + (self.winfo_height() - dh) // 2
            dlg.geometry(f"{dw}x{dh}+{dx}+{dy}")

            ctk.CTkLabel(dlg, text="Tên danh mục:", font=("Segoe UI", 14),
                         text_color=COL["fg"]).grid(row=0, column=0, padx=18, pady=(18, 8), sticky="w")
            n_var = ctk.StringVar(value=edit_cat or "")
            ctk.CTkEntry(dlg, textvariable=n_var, font=("Segoe UI", 14),
                         fg_color=COL["input"], border_width=0, corner_radius=8, height=36
                         ).grid(row=0, column=1, padx=(0, 18), pady=(18, 8), sticky="ew")

            ctk.CTkLabel(dlg, text="Ngân sách/tháng:", font=("Segoe UI", 14),
                         text_color=COL["fg"]).grid(row=1, column=0, padx=18, pady=8, sticky="w")
            b_val = str(self.config[edit_cat]["budget"]) if edit_cat else ""
            b_var = ctk.StringVar(value=b_val)
            ctk.CTkEntry(dlg, textvariable=b_var, font=("Segoe UI", 14),
                         fg_color=COL["input"], border_width=0, corner_radius=8, height=36,
                         placeholder_text="500k, 3tr..."
                         ).grid(row=1, column=1, padx=(0, 18), pady=8, sticky="ew")

            dlg.grid_columnconfigure(1, weight=1)

            def save_cat():
                name = n_var.get().strip()
                if not name:
                    messagebox.showerror("Lỗi", "Tên trống!", parent=dlg)
                    return
                try:
                    b = parse_amount(b_var.get())
                    if b <= 0: raise ValueError
                except (ValueError, TypeError):
                    messagebox.showerror("Lỗi", "Ngân sách không hợp lệ!", parent=dlg)
                    return

                if edit_cat and name != edit_cat:
                    old = self.config.pop(edit_cat)
                    self.config[name] = {"budget": b, "enabled": old["enabled"]}
                elif edit_cat:
                    self.config[edit_cat]["budget"] = b
                else:
                    if name in self.config:
                        messagebox.showwarning("Trùng", f"'{name}' đã tồn tại!", parent=dlg)
                        return
                    self.config[name] = {"budget": b, "enabled": True}
                save_config(self.config)
                self._reload_config()
                refresh()
                dlg.destroy()

            ctk.CTkButton(dlg, text="💾  Lưu", command=save_cat,
                          font=("Segoe UI", 14, "bold"), fg_color=COL["accent"],
                          text_color=COL["bg"],
                          hover_color=COL["hover"], corner_radius=10,
                          height=38, width=160
                          ).grid(row=2, column=0, columnspan=2, pady=18)




# ======================================================================
# RUN
# ======================================================================
if __name__ == "__main__":
    app = ExpenseApp()
    app.mainloop()
