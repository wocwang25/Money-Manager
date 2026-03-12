"""
Trang Dư / Âm hàng ngày + dialog chọn danh mục theo dõi.
"""

from collections import defaultdict
from datetime import datetime

import customtkinter as ctk

from .core import COL, save_config, fmt, days_in_month, parse_date


def show_du_am(app):
    app._clear()
    app._reload_config()
    area = app._make_scroll_area()
    month, year = app.view_month, app.view_year
    rows = app._read_all_cached()

    # Header
    hdr = ctk.CTkFrame(area, fg_color="transparent")
    hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    ctk.CTkLabel(hdr, text=f"🍜  Dư / Âm — Tháng {month:02d}/{year}",
                 font=("Segoe UI", 20, "bold"), text_color=COL["fg"]
                 ).pack(side="left")
    ctk.CTkButton(hdr, text="⚙  Chọn danh mục theo dõi",
                  font=("Segoe UI", 13), fg_color=COL["card2"],
                  text_color=COL["fg"], hover_color=COL["hover"],
                  corner_radius=8, height=34,
                  command=lambda: _open_daily_track_dlg(app)
                  ).pack(side="right")

    dim = days_in_month(month, year)

    tracked = {cat: info for cat, info in app._cfg.items()
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

    if app._is_current_month():
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

        by_day = defaultdict(int)
        total_spent_cat = 0
        for r in rows:
            if r["Danh mục"] == cat:
                by_day[r["Ngày nhập"]] += r["Số tiền chi"]
                total_spent_cat += r["Số tiền chi"]

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

        if times > 0:
            is_month_over = (today == dim)
            if is_month_over or total_spent_cat >= budget:
                grand_total += total_cat
        else:
            grand_total += total_cat

    # Tổng
    tc = COL["red"] if grand_total < 0 else COL["green"]
    total_card = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=12)
    total_card.grid(row=grid_row, column=0, sticky="ew")
    ctk.CTkLabel(total_card, text=f"💰  TỔNG DƯ / ÂM THÁNG:  {fmt(grand_total)}",
                 font=("Segoe UI", 17, "bold"), text_color=tc
                 ).pack(padx=18, pady=14)


# ── Dialog chọn danh mục theo dõi ──

def _open_daily_track_dlg(app):
    dlg = ctk.CTkToplevel(app)
    dlg.title("Chọn danh mục theo dõi Dư/Âm")
    dlg.configure(fg_color=COL["card"])
    dlg.resizable(False, False)
    dlg.grab_set()
    dw, dh = 520, min(560, 90 + 50 * len(app._cfg) + 60)
    dx = app.winfo_x() + (app.winfo_width() - dw) // 2
    dy = app.winfo_y() + (app.winfo_height() - dh) // 2
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
    for cat, info in app._cfg.items():
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
            app._cfg[cat]["daily_track"] = bool(sw.get())
            try:
                t = int(time_entries[cat].get())
                if t < 0:
                    t = 0
            except (ValueError, KeyError):
                t = 0
            app._cfg[cat]["daily_times"] = t
        save_config(app._cfg)
        app._reload_config()
        dlg.destroy()
        app.show_du_am()

    ctk.CTkButton(dlg, text="💾  Lưu", command=save_track,
                  font=("Segoe UI", 14, "bold"), fg_color=COL["accent"],
                  text_color=COL["bg"], hover_color=COL["hover"],
                  corner_radius=10, height=38, width=140
                  ).pack(pady=(4, 12))
