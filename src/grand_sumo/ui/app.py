"""Grand Sumo Manager — tkinter desktop GUI."""

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from grand_sumo import config
from grand_sumo.exporters.images import download_rikishi_images
from grand_sumo.exporters.obsidian import (
    compile_makuuchi_data,
    export_banzuke_page,
    export_basho_summary,
    export_heya_pages,
    export_rikishi_pages,
    export_torikumi_pages,
    run_full_pipeline,
)
from grand_sumo.scrapers.profile import scrape_all_profiles


class App(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()

        self.title("Grand Sumo Manager")
        self.geometry("800x600")
        self.resizable(width=True, height=False)

        self._running = False
        self._op_buttons: list[tk.Widget] = []

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # ── Root layout: left panel + right panel ─────────────────────
        root_frame = ttk.Frame(self)
        root_frame.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(root_frame, width=200)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 4), pady=8)
        left.pack_propagate(False)

        right = ttk.Frame(root_frame)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 8), pady=8)

        self._build_left(left)
        self._build_right(right)

        # ── Status bar ────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            self, textvariable=self._status_var,
            relief=tk.SUNKEN, anchor=tk.W, padding=(6, 2)
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_left(self, parent: ttk.Frame) -> None:
        """Operations panel."""

        # FULL RUN
        full_frame = ttk.LabelFrame(parent, text="Full Run")
        full_frame.pack(fill=tk.X, pady=(0, 6))
        self._add_op_button(full_frame, "Run All", self._run_all)

        # RIKISHI
        rik_frame = ttk.LabelFrame(parent, text="Rikishi")
        rik_frame.pack(fill=tk.X, pady=(0, 6))
        self._add_op_button(rik_frame, "All Pages", self._run_rikishi_pages)
        self._add_op_button(rik_frame, "Images", self._run_images)
        self._add_op_button(rik_frame, "Scrape", self._run_scrape)

        # BASHO
        basho_frame = ttk.LabelFrame(parent, text="Basho")
        basho_frame.pack(fill=tk.X, pady=(0, 6))
        self._add_op_button(basho_frame, "Banzuke", self._run_banzuke)
        self._add_op_button(basho_frame, "Summary", self._run_basho_summary)
        self._add_op_button(basho_frame, "Torikumi", self._run_torikumi)

        # STABLES
        heya_frame = ttk.LabelFrame(parent, text="Stables")
        heya_frame.pack(fill=tk.X, pady=(0, 6))
        self._add_op_button(heya_frame, "Heya Pages", self._run_heya_pages)

    def _add_op_button(self, parent: ttk.LabelFrame, text: str, command) -> None:
        btn = ttk.Button(parent, text=text, command=command)
        btn.pack(fill=tk.X, padx=4, pady=2)
        self._op_buttons.append(btn)

    def _build_right(self, parent: ttk.Frame) -> None:
        """Settings + log panel."""

        # ── Settings ──────────────────────────────────────────────────
        settings_frame = ttk.LabelFrame(parent, text="Settings")
        settings_frame.pack(fill=tk.X, pady=(0, 6))

        # Basho ID
        ttk.Label(settings_frame, text="Basho ID:").grid(
            row=0, column=0, sticky=tk.W, padx=6, pady=4
        )
        self._basho_var = tk.StringVar(value=str(config.CURRENT_BASHO))
        basho_entry = ttk.Entry(settings_frame, textvariable=self._basho_var, width=12)
        basho_entry.grid(row=0, column=1, sticky=tk.W, padx=4, pady=4)

        # Vault path
        ttk.Label(settings_frame, text="Vault:").grid(
            row=1, column=0, sticky=tk.W, padx=6, pady=4
        )
        self._vault_var = tk.StringVar(value=str(config.DEFAULT_VAULT_PATH))
        vault_entry = ttk.Entry(settings_frame, textvariable=self._vault_var, width=42)
        vault_entry.grid(row=1, column=1, sticky=tk.EW, padx=4, pady=4)
        browse_btn = ttk.Button(settings_frame, text="Browse", command=self._browse_vault)
        browse_btn.grid(row=1, column=2, padx=4, pady=4)
        settings_frame.columnconfigure(1, weight=1)

        # ── Output log ────────────────────────────────────────────────
        log_frame = ttk.LabelFrame(parent, text="Output")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self._log_text = tk.Text(
            log_frame, state=tk.DISABLED, wrap=tk.WORD,
            font=("Consolas", 9), relief=tk.FLAT,
            background="#1e1e1e", foreground="#d4d4d4",
            insertbackground="#d4d4d4",
        )
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Tag colours
        self._log_text.tag_configure("success", foreground="#4ec9b0")
        self._log_text.tag_configure("error",   foreground="#f44747")
        self._log_text.tag_configure("normal",  foreground="#d4d4d4")

        # Clear button
        clear_btn = ttk.Button(parent, text="Clear Log", command=self._clear_log)
        clear_btn.pack(anchor=tk.E, pady=(4, 0))

    # ------------------------------------------------------------------
    # Settings helpers
    # ------------------------------------------------------------------

    def _browse_vault(self) -> None:
        path = filedialog.askdirectory(
            title="Select Obsidian Vault Folder",
            initialdir=self._vault_var.get(),
        )
        if path:
            self._vault_var.set(path)

    def _get_basho_id(self) -> int:
        try:
            return int(self._basho_var.get().strip())
        except ValueError:
            raise ValueError(f"Invalid Basho ID: {self._basho_var.get()!r}")

    def _get_vault_path(self) -> Path:
        return Path(self._vault_var.get().strip())

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def _append_log(self, message: str) -> None:
        """Thread-safe log append — always called via after()."""
        from datetime import datetime as _dt
        ts = _dt.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}\n"

        tag = "normal"
        if "✓" in message:
            tag = "success"
        elif "✗" in message or "Error" in message or "error" in message:
            tag = "error"

        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert(tk.END, line, tag)
        self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)

    def _log(self, message: str) -> None:
        """Schedule a log append on the main thread (safe from worker threads)."""
        self.after(0, self._append_log, message)

    def _clear_log(self) -> None:
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.delete("1.0", tk.END)
        self._log_text.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Thread management
    # ------------------------------------------------------------------

    def _set_running(self, running: bool, status: str = "") -> None:
        self._running = running
        state = tk.DISABLED if running else tk.NORMAL
        for btn in self._op_buttons:
            btn.configure(state=state)
        self._status_var.set(status if status else ("Running..." if running else "Ready"))

    def _run_in_thread(self, fn, *args, **kwargs) -> None:
        """Execute fn(*args, **kwargs) in a background thread."""
        if self._running:
            return

        def _worker():
            self.after(0, self._set_running, True, "Running...")
            try:
                fn(*args, **kwargs)
                self.after(0, self._set_running, False, "Done ✓")
            except Exception as exc:
                self._log(f"Error: {exc}")
                self.after(0, self._set_running, False, "Error ✗")

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _progress_cb(self, step: str, message: str) -> None:
        self._log(f"[{step}] {message}")

    # ------------------------------------------------------------------
    # Operation handlers
    # ------------------------------------------------------------------

    def _run_all(self) -> None:
        def _work():
            basho_id   = self._get_basho_id()
            vault_path = self._get_vault_path()
            self._log(f"Starting full pipeline for basho {basho_id} → {vault_path}")
            run_full_pipeline(basho_id, vault_path, progress_callback=self._progress_cb)
        self._run_in_thread(_work)

    def _run_rikishi_pages(self) -> None:
        def _work():
            basho_id   = self._get_basho_id()
            vault_path = self._get_vault_path()
            self._log(f"Compiling Makuuchi data for basho {basho_id}...")
            data = compile_makuuchi_data(basho_id, progress_callback=self._progress_cb)
            self._log("Exporting rikishi pages...")
            export_rikishi_pages(data, vault_path=vault_path, progress_callback=self._progress_cb)
        self._run_in_thread(_work)

    def _run_images(self) -> None:
        def _work():
            vault_path = self._get_vault_path()
            out_dir    = vault_path / "rikishi_images"
            self._log(f"Downloading rikishi images → {out_dir}")
            download_rikishi_images(
                output_dir=out_dir,
                progress_callback=lambda name, status: self._log(f"[images] {name}: {status}"),
            )
        self._run_in_thread(_work)

    def _run_scrape(self) -> None:
        def _work():
            vault_path = self._get_vault_path()
            vault_dir  = vault_path / "Rikishi"
            images_dir = vault_path / "rikishi_images"
            self._log(f"Scraping profiles → {vault_dir}")
            scrape_all_profiles(
                vault_dir=vault_dir,
                images_dir=images_dir,
                progress_callback=lambda name, status: self._log(f"[scrape] {name}: {status}"),
            )
        self._run_in_thread(_work)

    def _run_banzuke(self) -> None:
        def _work():
            basho_id   = self._get_basho_id()
            vault_path = self._get_vault_path()
            self._log(f"Compiling Makuuchi data for basho {basho_id}...")
            data = compile_makuuchi_data(basho_id, progress_callback=self._progress_cb)
            self._log("Exporting banzuke page...")
            export_banzuke_page(data, basho_id, vault_path=vault_path, progress_callback=self._progress_cb)
        self._run_in_thread(_work)

    def _run_basho_summary(self) -> None:
        def _work():
            basho_id   = self._get_basho_id()
            vault_path = self._get_vault_path()
            self._log(f"Exporting basho summary for {basho_id}...")
            export_basho_summary(basho_id, vault_path=vault_path, progress_callback=self._progress_cb)
        self._run_in_thread(_work)

    def _run_torikumi(self) -> None:
        def _work():
            basho_id   = self._get_basho_id()
            vault_path = self._get_vault_path()
            self._log(f"Exporting torikumi pages for basho {basho_id}...")
            export_torikumi_pages(basho_id, vault_path=vault_path, progress_callback=self._progress_cb)
        self._run_in_thread(_work)

    def _run_heya_pages(self) -> None:
        def _work():
            basho_id   = self._get_basho_id()
            vault_path = self._get_vault_path()
            self._log(f"Compiling Makuuchi data for basho {basho_id}...")
            data = compile_makuuchi_data(basho_id, progress_callback=self._progress_cb)
            self._log("Exporting heya pages...")
            export_heya_pages(data, vault_path=vault_path, progress_callback=self._progress_cb)
        self._run_in_thread(_work)


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
