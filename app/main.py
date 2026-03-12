"""
Lớp chính ExpenseApp — khung ứng dụng, sidebar, điều hướng tháng,
vùng cuộn, và các phương thức vẽ biểu đồ dùng chung.
"""

import os
from datetime import datetime
from tkinter import ttk, Canvas

import customtkinter as ctk

from .core import (APP_DIR, COL, CONFIG_PATH,
                   load_config, fmt, get_csv_path, init_csv, read_all,
                   days_in_month, SidebarBtn)


class ExpenseApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("💸 Quản lý Chi tiêu")
        self.configure(fg_color=COL["bg"])

        # Window / taskbar icon
        icon_path = os.path.join(APP_DIR, "app_icon.ico")
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
        self._csv_cache: dict = {}
        self._config_mtime = 0
        self._reload_config()

        self._setup_tree_style()
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()
        self.show_thong_ke()

    # ─── Helpers ───────────────────────────────────────────────

    def _read_all_cached(self, fp=None):
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
        fp = fp or self.filepath
        self._csv_cache.pop(fp, None)

    def _reload_config(self):
        try:
            mt = os.path.getmtime(CONFIG_PATH)
        except OSError:
            mt = 0
        if mt != self._config_mtime or not hasattr(self, "_cfg"):
            self._cfg = load_config()
            self._config_mtime = mt
        self.active_budget = {c: i["budget"] for c, i in self._cfg.items() if i["enabled"]}
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

    # ─── Sidebar ──────────────────────────────────────────────

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
            ("📊  Thống kê",        self.show_thong_ke),
            ("📋  Chi tiêu",        self.show_lich_su),
            ("🍜  Dư / Âm ngày",    self.show_du_am),
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

    # ─── Month navigation ────────────────────────────────────

    def _prev_month(self):
        if self.view_month == 1 and self.view_year <= 2026:
            return
        if self.view_month == 1:
            self.view_month = 12
            self.view_year -= 1
        else:
            self.view_month -= 1
        self._switch_month()

    def _next_month(self):
        now = datetime.now()
        if self.view_year > now.year or (self.view_year == now.year and self.view_month >= now.month):
            return
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
        self.show_thong_ke()

    def _is_current_month(self):
        now = datetime.now()
        return self.view_month == now.month and self.view_year == now.year

    # ─── Main area ────────────────────────────────────────────

    def _build_main(self):
        self.main = ctk.CTkFrame(self, fg_color=COL["bg"], corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main.grid_rowconfigure(0, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

    def _clear(self):
        for w in self.main.winfo_children():
            w.destroy()

    def _make_scroll_area(self):
        scroll = ctk.CTkScrollableFrame(self.main, fg_color=COL["bg"], corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=16, pady=12)
        scroll.grid_columnconfigure(0, weight=1)

        def _fast_scroll(event):
            scroll._parent_canvas.yview_scroll(int(-1 * (event.delta / 120) * 80), "units")
        scroll._parent_canvas.bind_all("<MouseWheel>", _fast_scroll)
        return scroll

    # ─── Shared chart methods ─────────────────────────────────

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
            if v >= 1_000_000:
                return f"{v / 1_000_000:.1f}M"
            if v >= 1_000:
                return f"{v / 1_000:.0f}K"
            return f"{v:.0f}"

        def _show_tip(evt, day, val):
            c.delete("tip")
            if val <= 0:
                return
            txt = f"Ngày {day}: {val:,.0f}đ"
            tid = c.create_text(evt.x, PAD_T - 2, text=txt, anchor="s",
                                fill=COL["fg"], font=("Segoe UI", 9, "bold"), tags="tip")
            bb = c.bbox(tid)
            if bb:
                c.create_rectangle(bb[0] - 6, bb[1] - 2, bb[2] + 6, bb[3] + 2,
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
            r = min(bar_w // 2, 4)
            y_base = PAD_T + max_h

            for i in range(GRIDS + 1):
                y = PAD_T + int(max_h * i / GRIDS)
                gv = max_val * (GRIDS - i) / GRIDS
                c.create_line(PAD_L, y, cw - PAD_R, y,
                              fill=COL["input"], width=1)
                if i < GRIDS:
                    c.create_text(PAD_L - 6, y, text=_fmt_val(gv), anchor="e",
                                  fill=COL["dim"], font=("Segoe UI", 7))

            for d in range(1, dim + 1):
                x = PAD_L + gap + (d - 1) * (bar_w + gap)
                val = by_day.get(d, 0)
                is_td = d == today and is_cur

                if val > 0:
                    bar_h = max(4, int(max_h * val / max_val))
                    yt = y_base - bar_h
                    fill = COL["mauve"] if is_td else bar_color
                    if bar_h > r * 2:
                        c.create_rectangle(x, yt + r, x + bar_w, y_base,
                                           fill=fill, outline="")
                        c.create_oval(x, yt, x + bar_w, yt + r * 2,
                                      fill=fill, outline="")
                    else:
                        c.create_rectangle(x, yt, x + bar_w, y_base,
                                           fill=fill, outline="")
                else:
                    c.create_oval(x + bar_w // 2 - 1, y_base - 3,
                                  x + bar_w // 2 + 1, y_base - 1,
                                  fill=COL["input"], outline="")

                hit = c.create_rectangle(x - 1, PAD_T, x + bar_w + 1, y_base,
                                         fill="", outline="")
                c.tag_bind(hit, "<Enter>", lambda e, dd=d, vv=val: _show_tip(e, dd, vv))
                c.tag_bind(hit, "<Leave>", _hide_tip)

                lbl_clr = COL["accent"] if is_td else COL["dim"]
                lbl_f = ("Segoe UI", 8, "bold") if is_td else ("Segoe UI", 7)
                c.create_text(x + bar_w // 2, y_base + 11,
                              text=str(d), fill=lbl_clr, font=lbl_f)

        c.bind("<Configure>", _redraw)
        return c

    def _draw_stacked_bar(self, master, segments, total, height=24):
        if total <= 0:
            return
        c = Canvas(master, height=height, bg=COL["input"], highlightthickness=0, bd=0)
        c.pack(fill="x", pady=(0, 8))

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

    # ─── Page dispatchers (lazy-import để khởi động nhanh) ────

    def show_thong_ke(self):
        from .page_thong_ke import show_thong_ke as _fn
        _fn(self)

    def show_lich_su(self):
        from .page_lich_su import show_lich_su as _fn
        _fn(self)

    def show_du_am(self):
        from .page_du_am import show_du_am as _fn
        _fn(self)

    def show_danh_muc(self):
        from .page_danh_muc import show_danh_muc as _fn
        _fn(self)
