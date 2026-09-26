"""Pick which apps/sites count as distracting (shown on first launch)."""
import copy
import tkinter as tk

import config
from ui.widget import rounded_rect

T, UI = config.TEXTS, config.UI
F = config.UI_FONT
WIDTH = 520


class AppsWindow(tk.Toplevel):
    def __init__(self, master, settings, on_save, on_close=None):
        super().__init__(master, bg=UI["bg"])
        self.settings = copy.deepcopy(settings)
        self.on_save = on_save
        self.title(T["apps_title"])
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", on_close or self._save)

        f = tk.Frame(self, bg=UI["bg"], padx=28, pady=22)
        f.pack(fill="both", expand=True)
        tk.Label(f, text=T["apps_title"], bg=UI["bg"], fg=UI["text"], font=(F, 18, "bold")).pack(anchor="w")
        tk.Label(f, text=T["apps_subtitle"], bg=UI["bg"], fg=UI["muted"], font=(F, 10),
                 wraplength=WIDTH - 56, justify="left").pack(anchor="w", pady=(4, 12))

        # catalogue: groups in two columns
        grid = tk.Frame(f, bg=UI["bg"])
        grid.pack(fill="x")
        self.vars = {}
        columns = [tk.Frame(grid, bg=UI["bg"]) for _ in range(2)]
        for i, col in enumerate(columns):
            col.grid(row=0, column=i, sticky="nw", padx=(0, 24))
        for gi, group in enumerate(config.CATALOG_GROUPS):
            col = columns[0] if gi % 2 == 0 else columns[1]
            tk.Label(col, text=group.upper(), bg=UI["bg"], fg=UI["muted"],
                     font=(F, 8, "bold")).pack(anchor="w", pady=(8, 2))
            for item in (i for i in config.DISTRACTION_CATALOG if i["group"] == group):
                var = tk.BooleanVar(value=self.settings["enabled"].get(item["id"], item["default"]))
                self.vars[item["id"]] = var
                tk.Checkbutton(col, text=item["name"], variable=var, bg=UI["bg"], fg=UI["text"],
                               selectcolor=UI["field"], activebackground=UI["bg"], activeforeground=UI["text"],
                               highlightthickness=0, bd=0, font=(F, 10), anchor="w").pack(anchor="w")

        # custom entries
        tk.Label(f, text=T["apps_custom_label"], bg=UI["bg"], fg=UI["text"], font=(F, 10, "bold"),
                 wraplength=WIDTH - 56, justify="left").pack(anchor="w", pady=(16, 4))
        row = tk.Frame(f, bg=UI["bg"])
        row.pack(fill="x")
        self.new_item = tk.StringVar()
        entry = tk.Entry(row, textvariable=self.new_item, bg=UI["field"], fg=UI["text"],
                         insertbackground=UI["text"], relief="flat", highlightthickness=1,
                         highlightbackground=UI["border"], highlightcolor=UI["accent"], font=(F, 11))
        entry.pack(side="left", fill="x", expand=True, ipady=5)
        entry.bind("<Return>", lambda _e: self._add())
        tk.Button(row, text=T["apps_add"], command=self._add, bg=UI["field"], fg=UI["text"],
                  activebackground=UI["hover"], activeforeground=UI["text"], relief="flat", bd=0,
                  padx=14, pady=5, font=(F, 10)).pack(side="left", padx=(8, 0))
        self.chips = tk.Frame(f, bg=UI["bg"])
        self.chips.pack(fill="x", pady=(8, 0))
        self._render_chips()

        # save button
        self.btn = tk.Canvas(f, width=WIDTH - 56, height=44, bg=UI["bg"], highlightthickness=0, cursor="hand2")
        self.btn_bg = rounded_rect(self.btn, 1, 1, WIDTH - 57, 43, 12, fill=UI["accent"], outline="")
        self.btn.create_text((WIDTH - 56) / 2, 22, text=T["apps_save"], fill="white", font=(F, 12, "bold"))
        self.btn.pack(pady=(16, 0))
        self.btn.bind("<Enter>", lambda _e: self.btn.itemconfig(self.btn_bg, fill=UI["accent_hover"]))
        self.btn.bind("<Leave>", lambda _e: self.btn.itemconfig(self.btn_bg, fill=UI["accent"]))
        self.btn.bind("<ButtonRelease-1>", lambda _e: self._save())

        self.update_idletasks()
        self.geometry(f"{WIDTH}x{self.winfo_reqheight()}+{(self.winfo_screenwidth() - WIDTH) // 2}+"
                      f"{max(0, (self.winfo_screenheight() - self.winfo_reqheight()) // 3)}")
        self.focus_force()

    def _add(self):
        name = self.new_item.get().strip()
        if name and name.lower() not in (c.lower() for c in self.settings["custom"]):
            self.settings["custom"].append(name)
            self._render_chips()
        self.new_item.set("")

    def _remove(self, name):
        self.settings["custom"].remove(name)
        self._render_chips()

    def _render_chips(self):
        for w in self.chips.winfo_children():
            w.destroy()
        for name in self.settings["custom"]:
            chip = tk.Frame(self.chips, bg=UI["field"])
            chip.pack(side="left", padx=(0, 6), pady=2)
            tk.Label(chip, text=name, bg=UI["field"], fg=UI["text"], font=(F, 9)).pack(side="left", padx=(8, 2), pady=3)
            x = tk.Label(chip, text="×", bg=UI["field"], fg=UI["muted"], font=(F, 9), cursor="hand2")
            x.pack(side="left", padx=(2, 6))
            x.bind("<Button-1>", lambda _e, n=name: self._remove(n))
        self.update_idletasks()
        if self.winfo_ismapped():
            self.geometry(f"{WIDTH}x{self.winfo_reqheight()}")

    def _save(self):
        self.settings["enabled"] = {k: bool(v.get()) for k, v in self.vars.items()}
        self.destroy()
        self.on_save(self.settings)
