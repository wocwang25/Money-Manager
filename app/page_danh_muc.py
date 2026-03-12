"""
Trang quản lý danh mục (Treeview + CRUD dialogs).
"""

from tkinter import ttk, messagebox
import customtkinter as ctk

from .core import COL, save_config, fmt, parse_amount


def show_danh_muc(app):
    app._clear()
    app._reload_config()

    header_f = ctk.CTkFrame(app.main, fg_color="transparent")
    header_f.pack(fill="x", padx=16, pady=(12, 6))
    ctk.CTkLabel(header_f, text="⚙️  Quản lý danh mục",
                 font=("Segoe UI", 20, "bold"), text_color=COL["fg"]
                 ).pack(side="left")

    # Treeview
    tree_frame = ctk.CTkFrame(app.main, fg_color=COL["card"], corner_radius=12)
    tree_frame.pack(fill="both", expand=True, padx=16, pady=(0, 6))

    cols = ("Danh mục", "Ngân sách / tháng", "Trạng thái", "Dư/Âm")
    tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                         height=max(8, len(app._cfg)), style="Dark.Treeview")
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
    btn_frame = ctk.CTkFrame(app.main, fg_color="transparent")
    btn_frame.pack(fill="x", padx=16, pady=4)

    # Total label
    lbl_total = ctk.CTkLabel(app.main, text="",
                              font=("Segoe UI", 20, "bold"), text_color=COL["green"])
    lbl_total.pack(padx=16, pady=(4, 12), anchor="w")

    def refresh():
        nonlocal cat_keys
        cat_keys.clear()
        tree.delete(*tree.get_children())
        for cat, info in app._cfg.items():
            st = "🟢 Bật" if info["enabled"] else "🔴 Tắt"
            dt = "✅" if info.get("daily_track") else "—"
            tg = "on" if info["enabled"] else "off"
            tree.insert("", "end", values=(cat, fmt(info["budget"]), st, dt), tags=(tg,))
            cat_keys.append(cat)
        tree.tag_configure("on", foreground=COL["green"])
        tree.tag_configure("off", foreground=COL["dim"])
        lbl_total.configure(text=f"Tổng ngân sách (bật): {fmt(app.total_budget)}")

    refresh()

    def get_sel():
        s = tree.selection()
        if not s:
            return None
        i = tree.index(s[0])
        return cat_keys[i] if i < len(cat_keys) else None

    def do_toggle():
        c = get_sel()
        if not c:
            messagebox.showwarning("Chọn dòng", "Hãy chọn 1 danh mục!")
            return
        app._cfg[c]["enabled"] = not app._cfg[c]["enabled"]
        save_config(app._cfg)
        app._reload_config()
        refresh()

    def do_edit():
        c = get_sel()
        if not c:
            messagebox.showwarning("Chọn dòng", "Hãy chọn 1 danh mục!")
            return
        _open_dlg(app, c, refresh)

    def do_del():
        c = get_sel()
        if not c:
            messagebox.showwarning("Chọn dòng", "Hãy chọn 1 danh mục!")
            return
        if not messagebox.askyesno("Xác nhận", f"Xóa danh mục '{c}'?"):
            return
        del app._cfg[c]
        save_config(app._cfg)
        app._reload_config()
        refresh()

    for label, cmd, color, tcolor in [
        ("➕  Thêm mới",   lambda: _open_dlg(app, None, refresh), COL["accent"], COL["bg"]),
        ("✏️  Sửa",        do_edit,                                COL["yellow"], COL["bg"]),
        ("🔄  Bật / Tắt",  do_toggle,                              COL["card2"],  COL["fg"]),
        ("🗑  Xóa",        do_del,                                 COL["red"],    COL["bg"]),
    ]:
        ctk.CTkButton(btn_frame, text=label, command=cmd,
                      font=("Segoe UI", 16), fg_color=color,
                      text_color=tcolor,
                      hover_color=COL["hover"], corner_radius=8,
                      height=42, width=170).pack(side="left", padx=4)


def _open_dlg(app, edit_cat, refresh_cb):
    dlg = ctk.CTkToplevel(app)
    dlg.title("Thêm danh mục" if not edit_cat else f"Sửa: {edit_cat}")
    dlg.configure(fg_color=COL["card"])
    dlg.resizable(False, False)
    dlg.grab_set()
    dw, dh = 460, 280
    dx = app.winfo_x() + (app.winfo_width() - dw) // 2
    dy = app.winfo_y() + (app.winfo_height() - dh) // 2
    dlg.geometry(f"{dw}x{dh}+{dx}+{dy}")

    ctk.CTkLabel(dlg, text="Tên danh mục:", font=("Segoe UI", 14),
                 text_color=COL["fg"]).grid(row=0, column=0, padx=18, pady=(18, 8), sticky="w")
    n_var = ctk.StringVar(value=edit_cat or "")
    ctk.CTkEntry(dlg, textvariable=n_var, font=("Segoe UI", 14),
                 fg_color=COL["input"], border_width=0, corner_radius=8, height=36
                 ).grid(row=0, column=1, padx=(0, 18), pady=(18, 8), sticky="ew")

    ctk.CTkLabel(dlg, text="Ngân sách/tháng:", font=("Segoe UI", 14),
                 text_color=COL["fg"]).grid(row=1, column=0, padx=18, pady=8, sticky="w")
    b_val = str(app._cfg[edit_cat]["budget"]) if edit_cat else ""
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
            if b <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messagebox.showerror("Lỗi", "Ngân sách không hợp lệ!", parent=dlg)
            return

        if edit_cat and name != edit_cat:
            old = app._cfg.pop(edit_cat)
            app._cfg[name] = {"budget": b, "enabled": old["enabled"]}
        elif edit_cat:
            app._cfg[edit_cat]["budget"] = b
        else:
            if name in app._cfg:
                messagebox.showwarning("Trùng", f"'{name}' đã tồn tại!", parent=dlg)
                return
            app._cfg[name] = {"budget": b, "enabled": True}
        save_config(app._cfg)
        app._reload_config()
        refresh_cb()
        dlg.destroy()

    ctk.CTkButton(dlg, text="💾  Lưu", command=save_cat,
                  font=("Segoe UI", 14, "bold"), fg_color=COL["accent"],
                  text_color=COL["bg"],
                  hover_color=COL["hover"], corner_radius=10,
                  height=38, width=160
                  ).grid(row=2, column=0, columnspan=2, pady=18)
