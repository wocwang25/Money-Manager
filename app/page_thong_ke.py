"""
Trang Thống kê + Chi tiết danh mục.
"""

from collections import defaultdict, OrderedDict
from datetime import datetime
from tkinter import Canvas

import customtkinter as ctk

from .core import COL, fmt, days_in_month, parse_date, StatCard

# Bảng màu danh mục (vòng lặp)
COLORS = [COL["accent"], COL["teal"], COL["peach"], COL["mauve"],
          COL["yellow"], COL["green"], COL["red"]]


def show_thong_ke(app):
    """Render trang thống kê chính."""
    app._clear()
    app._reload_config()
    area = app._make_scroll_area()
    rows = app._read_all_cached()
    month, year = app.view_month, app.view_year
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
    total_remain = app.total_budget - total_spent
    total_txn = len(rows)

    # ── Header ──
    ctk.CTkLabel(area, text=f"📊  Thống kê tháng {month:02d}/{year}",
                 font=("Segoe UI", 20, "bold"), text_color=COL["fg"]
                 ).grid(row=0, column=0, sticky="w", pady=(0, 12))

    # ── Summary Cards ──
    cards = ctk.CTkFrame(area, fg_color="transparent")
    cards.grid(row=1, column=0, sticky="ew", pady=(0, 10))
    cards.grid_columnconfigure((0, 1, 2, 3), weight=1)

    pct_used = total_spent / app.total_budget if app.total_budget else 0
    StatCard(cards, "Ngân sách", fmt(app.total_budget), COL["accent"]
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
    ctk.CTkLabel(area, text="🍩  Tỉ lệ chi tiêu", font=("Segoe UI", 16, "bold"),
                 text_color=COL["fg"]).grid(row=4, column=0, sticky="w", pady=(4, 6))

    pct_frame = ctk.CTkFrame(area, fg_color=COL["card"], corner_radius=12)
    pct_frame.grid(row=5, column=0, sticky="ew")
    pct_inner = ctk.CTkFrame(pct_frame, fg_color="transparent")
    pct_inner.pack(fill="x", padx=16, pady=12)

    if total_spent > 0:
        segments = []
        for i, cat in enumerate(app.active_cats):
            s = spent.get(cat, 0)
            if s > 0:
                segments.append((COLORS[i % len(COLORS)], s))
        app._draw_stacked_bar(pct_inner, segments, total_spent)

    legend = ctk.CTkFrame(pct_inner, fg_color="transparent")
    legend.pack(fill="x")
    for i, cat in enumerate(app.active_cats):
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

    for i, cat in enumerate(app.active_cats):
        b = app.active_budget[cat]
        s = spent.get(cat, 0)
        remain = b - s
        pct = s / b if b else 0
        txn_count = count_by_cat.get(cat, 0)
        days_active = len(by_cat_day.get(cat, {}))
        avg_per_txn = s // txn_count if txn_count else 0
        color = COLORS[i % len(COLORS)]

        row_f = ctk.CTkFrame(cat_frame, fg_color="transparent", cursor="hand2")
        row_f.pack(fill="x", padx=16, pady=(10 if i == 0 else 4,
                                              10 if i == len(app.active_cats) - 1 else 4))

        top_row = ctk.CTkFrame(row_f, fg_color="transparent")
        top_row.pack(fill="x")

        name_f = ctk.CTkFrame(top_row, fg_color="transparent")
        name_f.pack(side="left")
        ctk.CTkFrame(name_f, fg_color=color, width=10, height=10,
                     corner_radius=5).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(name_f, text=cat, font=("Segoe UI", 14, "bold"),
                     text_color=COL["fg"]).pack(side="left")

        ctk.CTkLabel(top_row, text="▶", font=("Segoe UI", 12),
                     text_color=COL["dim"]).pack(side="left", padx=(8, 0))

        status_text = f"{fmt(s)} / {fmt(b)}"
        status_color = COL["dim"] if remain >= 0 else COL["red"]
        ctk.CTkLabel(top_row, text=status_text, font=("Segoe UI", 13, "bold"),
                     text_color=status_color).pack(side="right")

        bar_color = color if remain >= 0 else COL["red"]
        bar = ctk.CTkProgressBar(row_f, height=8, progress_color=bar_color,
                                  fg_color=COL["input"], corner_radius=6)
        bar.set(min(1.0, pct))
        bar.pack(fill="x", pady=(3, 0))

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

        def _bind_click(widget, c=cat, clr=color):
            widget.bind("<Button-1>", lambda e: show_cat_transactions(app, c, clr))
            for child in widget.winfo_children():
                _bind_click(child, c, clr)
        _bind_click(row_f)


# ─── Chi tiết giao dịch theo danh mục ───

def show_cat_transactions(app, cat: str, color: str):
    """Trang riêng hiển thị giao dịch của 1 danh mục."""
    app._clear()
    rows = app._read_all_cached()
    month, year = app.view_month, app.view_year
    budget = app.active_budget.get(cat, 0)

    cat_rows = [r for r in rows if r["Danh mục"] == cat]
    cat_rows.sort(key=lambda r: parse_date(r["Ngày nhập"]), reverse=True)
    total_cat = sum(r["Số tiền chi"] for r in cat_rows)
    remain = budget - total_cat

    area = app._make_scroll_area()

    # Header
    hdr = ctk.CTkFrame(area, fg_color="transparent")
    hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))

    ctk.CTkButton(hdr, text="◀  Quay lại", command=app.show_thong_ke,
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

    # Cards
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

    # Chart
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
    app._draw_bar_chart(chart, by_day, dim, color, max_h=70)

    # Transaction list
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

            dh = ctk.CTkFrame(list_card,
                              fg_color=COL["card2"] if di % 2 == 0 else "transparent",
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

                amt_badge = ctk.CTkFrame(rf, fg_color=color, corner_radius=8)
                amt_badge.pack(side="left")
                ctk.CTkLabel(amt_badge, text=f" {fmt(r['Số tiền chi'])} ",
                             font=("Segoe UI", 13, "bold"),
                             text_color=COL["bg"]).pack(padx=8, pady=3)

                note = r["Ghi chú"] if r["Ghi chú"] != "-" else ""
                if note:
                    ctk.CTkLabel(rf, text=note, font=("Segoe UI", 13),
                                 text_color=COL["fg"]).pack(side="left", padx=(12, 0))

        ctk.CTkFrame(list_card, fg_color="transparent", height=10).pack()
