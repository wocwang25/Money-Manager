"""
Trang Chi tiêu (Calendar View) + chi tiết ngày + form nhập.
"""

import calendar
from collections import defaultdict
from datetime import datetime
from tkinter import Canvas, messagebox

import customtkinter as ctk

from .core import (COL, fmt, days_in_month, parse_date, parse_amount,
                   get_csv_path, init_csv, append_row, rewrite_csv)


def show_lich_su(app):
    app._clear()
    app._reload_config()
    rows = app._read_all_cached()
    now = datetime.now()
    month, year = app.view_month, app.view_year
    dim = days_in_month(month, year)

    by_day = defaultdict(list)
    total = 0
    for r in rows:
        dt = parse_date(r["Ngày nhập"])
        by_day[dt.day].append(r)
        total += r["Số tiền chi"]

    area = app._make_scroll_area()

    # Header
    hdr = ctk.CTkFrame(area, fg_color="transparent")
    hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    ctk.CTkLabel(hdr, text=f"📋  Chi tiêu tháng {month:02d}/{year}",
                 font=("Segoe UI", 20, "bold"), text_color=COL["fg"]
                 ).pack(side="left")
    ctk.CTkLabel(hdr, text=f"{len(rows)} giao dịch",
                 font=("Segoe UI", 13), text_color=COL["dim"]
                 ).pack(side="left", padx=(12, 0))

    cal_grid_row = 1

    # Calendar grid
    cal_card = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=14)
    cal_card.grid(row=cal_grid_row, column=0, sticky="ew", pady=(0, 8))
    for c in range(7):
        cal_card.grid_columnconfigure(c, weight=1)

    DOW = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    DOW_COLORS = [COL["fg"]] * 5 + [COL["accent"], COL["red"]]
    for c, (name, clr) in enumerate(zip(DOW, DOW_COLORS)):
        ctk.CTkLabel(cal_card, text=name, font=("Segoe UI", 12, "bold"),
                     text_color=clr).grid(row=0, column=c, pady=(10, 4))

    first_wd = calendar.weekday(year, month, 1)
    grid_row = 1
    col = first_wd

    CAT_COLORS = {cat: [COL["accent"], COL["teal"], COL["peach"], COL["mauve"],
                         COL["yellow"], COL["green"], COL["red"]][i % 7]
                  for i, cat in enumerate(app.active_cats)}

    app._cal_detail_widgets = []

    for day in range(1, dim + 1):
        is_today = (day == now.day and app._is_current_month())
        has_data = day in by_day
        day_spent = sum(r["Số tiền chi"] for r in by_day.get(day, []))

        cell_fg = COL["card2"] if is_today else "transparent"
        cell = ctk.CTkFrame(cal_card, fg_color=cell_fg, corner_radius=8,
                            height=72, width=90)
        cell.grid(row=grid_row, column=col, padx=3, pady=3, sticky="nsew")
        cell.grid_propagate(False)

        day_color = COL["accent"] if is_today else (COL["fg"] if has_data else COL["dim"])
        day_font = ("Segoe UI", 13, "bold") if is_today else ("Segoe UI", 12)
        ctk.CTkLabel(cell, text=str(day), font=day_font,
                     text_color=day_color).pack(anchor="nw", padx=6, pady=(4, 0))

        if has_data:
            ctk.CTkLabel(cell, text=fmt(day_spent),
                         font=("Segoe UI", 11, "bold"),
                         text_color=COL["yellow"]).pack(anchor="nw", padx=6)

            cats_today = list({r["Danh mục"] for r in by_day[day]})[:4]
            if cats_today:
                dot_cv = Canvas(cell, width=len(cats_today) * 11, height=8,
                                bg=(cell._fg_color
                                    if isinstance(cell._fg_color, str) and cell._fg_color != "transparent"
                                    else COL["bg"]),
                                highlightthickness=0, bd=0)
                dot_cv.pack(anchor="nw", padx=6, pady=(1, 0))
                for ci, cat in enumerate(cats_today):
                    dc = CAT_COLORS.get(cat, COL["dim"])
                    dot_cv.create_oval(ci * 11, 0, ci * 11 + 8, 8, fill=dc, outline="")

        cell.bind("<Button-1>",
                  lambda e, d=day: _show_day_detail(app, d, by_day, rows, area))
        for child in cell.winfo_children():
            child.bind("<Button-1>",
                       lambda e, d=day: _show_day_detail(app, d, by_day, rows, area))
        cell.configure(cursor="hand2")

        col += 1
        if col > 6:
            col = 0
            grid_row += 1

    # Legend
    legend_f = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=10)
    legend_f.grid(row=cal_grid_row + 1, column=0, sticky="ew", pady=(4, 4))
    leg_inner = ctk.CTkFrame(legend_f, fg_color="transparent")
    leg_inner.pack(padx=12, pady=8)
    for cat in app.active_cats:
        dc = CAT_COLORS.get(cat, COL["dim"])
        cf = ctk.CTkFrame(leg_inner, fg_color="transparent")
        cf.pack(side="left", padx=(0, 14))
        ctk.CTkFrame(cf, fg_color=dc, width=10, height=10,
                     corner_radius=5).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(cf, text=cat, font=("Segoe UI", 11),
                     text_color=COL["fg"]).pack(side="left")

    # Total bar
    total_bar = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=10)
    total_bar.grid(row=cal_grid_row + 2, column=0, sticky="ew", pady=(4, 4))
    ctk.CTkLabel(total_bar, text=f"💰  Tổng chi tháng:  {fmt(total)}",
                 font=("Segoe UI", 17, "bold"), text_color=COL["yellow"]
                 ).pack(padx=14, pady=10)

    # Detail placeholder
    app._detail_area = ctk.CTkFrame(area, fg_color="transparent")
    app._detail_area.grid(row=cal_grid_row + 3, column=0, sticky="ew")


def _show_day_detail(app, day, by_day, all_rows, area):
    """Panel chi tiết + form nhập cho 1 ngày."""
    for w in app._detail_area.winfo_children():
        w.destroy()

    month, year = app.view_month, app.view_year
    day_rows = by_day.get(day, [])

    panel = ctk.CTkFrame(app._detail_area, fg_color=COL["card"], corner_radius=12)
    panel.pack(fill="x", pady=(4, 0))

    # Header
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

    ctk.CTkFrame(panel, fg_color=COL["input"], height=1).pack(fill="x", padx=14, pady=2)

    # ── Input form ──
    form = ctk.CTkFrame(panel, fg_color=COL["card2"], corner_radius=10)
    form.pack(fill="x", padx=12, pady=(6, 4))

    ctk.CTkLabel(form, text="✏️  Nhập chi tiêu",
                 font=("Segoe UI", 13, "bold"), text_color=COL["accent"]
                 ).pack(anchor="w", padx=12, pady=(8, 4))

    lbl_row = ctk.CTkFrame(form, fg_color="transparent")
    lbl_row.pack(fill="x", padx=12)
    ctk.CTkLabel(lbl_row, text="Danh mục", font=("Segoe UI", 11),
                 text_color=COL["dim"], width=150, anchor="w").pack(side="left", padx=(0, 6))
    ctk.CTkLabel(lbl_row, text="Số tiền", font=("Segoe UI", 11),
                 text_color=COL["dim"], width=130, anchor="w").pack(side="left", padx=(0, 6))
    ctk.CTkLabel(lbl_row, text="Ghi chú", font=("Segoe UI", 11),
                 text_color=COL["dim"], anchor="w").pack(side="left")

    inp_row = ctk.CTkFrame(form, fg_color="transparent")
    inp_row.pack(fill="x", padx=12, pady=(0, 4))

    cat_var = ctk.StringVar(value=app.active_cats[0] if app.active_cats else "")
    ctk.CTkOptionMenu(
        inp_row, variable=cat_var, values=app.active_cats,
        font=("Segoe UI", 13), fg_color=COL["input"],
        corner_radius=8, height=34, width=150,
        dropdown_fg_color=COL["card"], dropdown_hover_color=COL["hover"],
        dropdown_text_color=COL["fg"], dropdown_font=("Segoe UI", 13),
        button_color=COL["accent"], button_hover_color=COL["hover"],
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

    btn_row = ctk.CTkFrame(form, fg_color="transparent")
    btn_row.pack(fill="x", padx=12, pady=(0, 10))

    feedback = ctk.CTkLabel(btn_row, text="", font=("Segoe UI", 12),
                             text_color=COL["green"])

    target_date_str = f"{day}/{month}/{year}"
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
        app._invalidate_cache(target_csv)
        feedback.configure(text=f"✅ {cat} · {fmt(amount)}")
        amt_var.set("")
        note_var.set("")
        e_amt.focus_set()
        app.after(500, app.show_lich_su)

    ctk.CTkButton(btn_row, text="💾 Lưu", command=do_save,
                  font=("Segoe UI", 13, "bold"), fg_color=COL["accent"],
                  text_color=COL["bg"], hover_color=COL["hover"],
                  corner_radius=8, height=34, width=90
                  ).pack(side="left", padx=(0, 8))
    feedback.pack(side="left")
    e_amt.focus_set()

    # ── Transaction list ──
    if day_rows:
        ctk.CTkLabel(panel, text=f"📝  Giao dịch ({len(day_rows)})",
                     font=("Segoe UI", 13, "bold"), text_color=COL["dim"]
                     ).pack(anchor="w", padx=14, pady=(6, 2))

        CAT_COLORS = {cat: [COL["accent"], COL["teal"], COL["peach"], COL["mauve"],
                             COL["yellow"], COL["green"], COL["red"]][i % 7]
                      for i, cat in enumerate(app.active_cats)}

        for i, r in enumerate(day_rows):
            rf = ctk.CTkFrame(panel, fg_color="transparent")
            rf.pack(fill="x", padx=14, pady=3)

            cat_color = CAT_COLORS.get(r["Danh mục"], COL["dim"])
            top = ctk.CTkFrame(rf, fg_color="transparent")
            top.pack(fill="x")

            badge = ctk.CTkFrame(top, fg_color=cat_color, corner_radius=8)
            badge.pack(side="left", fill="y")
            ctk.CTkLabel(badge, text=f" {r['Danh mục']} ", font=("Segoe UI", 13, "bold"),
                         text_color=COL["bg"]).pack(padx=6, pady=3, expand=True)

            note = r["Ghi chú"] if r["Ghi chú"] != "-" else ""
            if note:
                note_badge = ctk.CTkFrame(top, fg_color=cat_color, corner_radius=8)
                note_badge.pack(side="left", padx=(8, 0), fill="both", expand=True)
                ctk.CTkLabel(note_badge, text=note, font=("Segoe UI", 13),
                             text_color=COL["bg"], wraplength=450, justify="left", anchor="w"
                             ).pack(padx=8, pady=3, fill="x")

            ctk.CTkLabel(top, text=fmt(r["Số tiền chi"]), font=("Segoe UI", 13, "bold"),
                         text_color=COL["fg"]).pack(side="right")

            def make_del(row=r):
                def do_del():
                    if messagebox.askyesno(
                        "Xác nhận xóa",
                        f"Xóa:\n{row['Ngày nhập']}  |  {row['Danh mục']}  |  "
                        f"{fmt(row['Số tiền chi'])}?",
                    ):
                        for j, orig in enumerate(all_rows):
                            if (orig["Ngày nhập"] == row["Ngày nhập"]
                                    and orig["Danh mục"] == row["Danh mục"]
                                    and orig["Số tiền chi"] == row["Số tiền chi"]
                                    and orig["Ghi chú"] == row["Ghi chú"]):
                                all_rows.pop(j)
                                break
                        from .utils import rewrite_csv as _rewrite
                        _rewrite(app.filepath, all_rows)
                        app._invalidate_cache()
                        app.show_lich_su()
                return do_del

            ctk.CTkButton(top, text="✕", command=make_del(r),
                          font=("Segoe UI", 12), fg_color="transparent",
                          text_color=COL["red"], hover_color=COL["card2"],
                          corner_radius=6, width=28, height=26
                          ).pack(side="right", padx=(0, 8))

    ctk.CTkFrame(panel, fg_color="transparent", height=8).pack()
