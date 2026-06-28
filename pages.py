import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from logger_config import get_logger
from config import DesktopConfig, DesktopExtraKey, DesktopExtraEntry, InstallerTask

logger = get_logger()


class BasePage(ttk.Frame):
    """Base class for all wizard pages."""
    def __init__(self, parent, app):
        """Initialize the BasePage."""
        super().__init__(parent, style="Content.TFrame")
        self.app = app

    def refresh(self):
        """Called when this page becomes visible. Override in subclasses."""
        pass

    def on_next(self):
        """Called when global Next button is clicked. Override in subclasses."""
        try:
            idx = self.app.PAGE_ORDER.index(self.app.current_page_name)
            if idx < len(self.app.PAGE_ORDER) - 1:
                self.app.show_page(self.app.PAGE_ORDER[idx + 1])
        except ValueError:
            pass

    def _create_file_selector(self, parent, var, browse_command):
        """Helper to create a file selection UI component."""
        frame = ttk.Frame(parent, style="Content.TFrame")
        
        display_var = tk.StringVar()
        
        def update_display(*args):
            path = var.get()
            if path and path != "No file selected":
                display_var.set(os.path.basename(path))
            else:
                display_var.set("No file selected")
                
        var.trace_add("write", update_display)
        update_display()
        
        lbl = ttk.Label(frame, textvariable=display_var, wraplength=350, style="Content.TLabel", foreground="#555")
        lbl.pack(side="left", fill="x", expand=True)
        
        btn = ttk.Button(frame, text="Browse", style="Content.TButton", command=browse_command)
        btn.pack(side="right", padx=(10, 0))
        
        clear_btn = ttk.Button(frame, text="Remove", style="Content.TButton", 
                               command=lambda: var.set(""))
        clear_btn.pack(side="right", padx=(5, 0))
        
        return frame


class ScrollableFrame(ttk.Frame):
    """A custom tkinter frame that adds a vertical scrollbar to its contents."""
    def __init__(self, parent, **kwargs):
        """Initialize the ScrollableFrame."""
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, background="white")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        inner_style = kwargs.get("style")
        if inner_style:
            self.scrollable_frame = ttk.Frame(self.canvas, style=inner_style)
        else:
            self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self._window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", tags="inner_frame")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.pack(side="left", fill="both", expand=True)

        self._bind_ids = [
            ("<Button-4>", self.canvas.bind_all("<Button-4>", self._on_mousewheel, add="+")),
            ("<Button-5>", self.canvas.bind_all("<Button-5>", self._on_mousewheel, add="+")),
            ("<MouseWheel>", self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")),
        ]

    def _on_frame_configure(self, event):
        """Update canvas scroll region when the inner frame changes size."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_scrollbar()

    def _on_canvas_configure(self, event):
        """Resize the inner frame to match the canvas width."""
        self.canvas.itemconfigure(self._window, width=event.width)
        self._update_scrollbar()

    def _update_scrollbar(self):
        """Schedule a scrollbar visibility update."""
        if hasattr(self, '_scrollbar_after_id'):
            self.after_cancel(self._scrollbar_after_id)
        self._scrollbar_after_id = self.after(50, self._do_update_scrollbar)

    def _do_update_scrollbar(self):
        """Perform the scrollbar visibility check."""
        self.update_idletasks()
        bbox = self.canvas.bbox("all")
        if bbox:
            content_height = bbox[3]
            canvas_height = self.canvas.winfo_height()
            if content_height <= canvas_height:
                self.scrollbar.pack_forget()
            else:
                self.scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(self, event):
        """Handle mouse scroll wheel events to scroll the canvas."""
        if not self.winfo_ismapped():
            return
            
        try:
            w_class = event.widget.winfo_class()
            if w_class in ("TCombobox", "TSpinbox", "Spinbox", "Listbox", "Text") or "Combo" in w_class:
                return
        except Exception:
            pass

        try:
            x, y = event.x_root, event.y_root
            x0 = self.canvas.winfo_rootx()
            y0 = self.canvas.winfo_rooty()
            x1 = x0 + self.canvas.winfo_width()
            y1 = y0 + self.canvas.winfo_height()
            
            if x0 <= x <= x1 and y0 <= y <= y1:
                bbox = self.canvas.bbox("all")
                if not bbox or bbox[3] <= self.canvas.winfo_height():
                    return

                if getattr(event, "num", 0) == 4:
                    delta = -1
                elif getattr(event, "num", 0) == 5:
                    delta = 1
                else:
                    delta = int(-1 * (event.delta / 120))
                self.canvas.yview_scroll(delta, "units")
        except Exception:
            pass

    def destroy(self):
        """Clean up bindings before destroying the widget."""
        if hasattr(self, '_scrollbar_after_id'):
            self.after_cancel(self._scrollbar_after_id)
        for event_str, bind_id in self._bind_ids:
            try:
                self.canvas.unbind_all(event_str)
            except Exception:
                pass
        super().destroy()


class WelcomePage(BasePage):
    """The initial welcome page of the wizard."""
    def __init__(self, parent, app):
        """Initialize the WelcomePage."""
        super().__init__(parent, app)
        logger.info("Initializing WelcomePage")

        ttk.Label(self, text="Welcome to Tino Wizard!", style="Title.TLabel").pack(pady=(40, 10))
        ttk.Label(self, text="This wizard will help you create installer for Linux.",
              style="Content.TLabel", wraplength=600).pack(pady=20)

        btn_frame = ttk.Frame(self, style="Content.TFrame")
        btn_frame.pack(pady=30)

        ttk.Button(btn_frame, text="Create new project", style="Content.TButton",
               command=self.new_installer).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Import existing project", style="Content.TButton",
               command=self.import_config).pack(side="left", padx=10)

    def new_installer(self):
        """Prompt user for a new project location and create it."""
        filepath = filedialog.asksaveasfilename(defaultextension=".tino",
                                                filetypes=[("Tino Project", "*.tino")],
                                                title="Save new project")
        if not filepath:
            return
        logger.info(f"Creating new project at {filepath}")
        self.app.project.save(filepath)

        self.app.show_page("ProjectInfoPage")

    def import_config(self):
        """Prompt user to open an existing .tino project file."""
        filepath = filedialog.askopenfilename(title="Open project",
                                              filetypes=[("Tino Project", "*.tino")],
                                              defaultextension=".tino")
        if filepath:
            logger.info(f"Importing project from {filepath}")
            if self.app.project.load(filepath):
                self.app.show_page("ProjectInfoPage")


class ProjectInfoPage(BasePage):
    """Page for entering general project and application details."""
    def __init__(self, parent, app):
        """Initialize the ProjectInfoPage."""
        super().__init__(parent, app)
        logger.info("Initializing ProjectInfoPage")

        ttk.Label(self, text="Project or Application Information", style="Title.TLabel").pack(anchor="w", pady=(0, 12))

        self.app_var = tk.StringVar()
        self.ver_var = tk.StringVar()
        self.desc_var = tk.StringVar()
        self.home_var = tk.StringVar()
        self.author_var = tk.StringVar()
        self.installer_icon_var = tk.StringVar()
        self.uninstaller_icon_var = tk.StringVar()
        self.license_file_var = tk.StringVar()
        self.preii_file_var = tk.StringVar()
        self.postii_file_var = tk.StringVar()
        self.comp_type_var = tk.StringVar(value="gzip")
        self.comp_level_var = tk.IntVar(value=6)

        fields = [
            ("Name", self.app_var),
            ("Version", self.ver_var),
            ("Description", self.desc_var),
            ("Homepage URL", self.home_var),
            ("Author", self.author_var),
            ("Installer Icon", self.installer_icon_var),
            ("Uninstaller Icon", self.uninstaller_icon_var),
            ("Pre Install Information File", self.preii_file_var),
            ("License File", self.license_file_var),
            ("Post Install Information File", self.postii_file_var),
        ]

        for label, var in fields:
            f = ttk.Frame(self, style="Content.TFrame")
            f.pack(fill="x", pady=4, padx=20)
            ttk.Label(f, text=label, style="Content.TLabel", width=28, anchor="w").pack(side="left")
            if label == "License File":
                self._create_file_selector(f, var, lambda: self._browse_file("Select License File", [("License file", "*.txt *.rtf")], "license_file", self.license_file_var)).pack(side="left", fill="x", expand=True)
            elif label == "Pre Install Information File":
                self._create_file_selector(f, var, lambda: self._browse_file("Select Pre Install Information File", [("pre install information file", "*.txt *.rtf")], "pre_install_information_file", self.preii_file_var)).pack(side="left", fill="x", expand=True)
            elif label == "Post Install Information File":
                self._create_file_selector(f, var, lambda: self._browse_file("Select Post Install Information File", [("post install information file", "*.txt *.rtf")], "post_install_information_file", self.postii_file_var)).pack(side="left", fill="x", expand=True)
            elif label == "Installer Icon":
                self._create_file_selector(f, var, lambda: self._browse_file("Select Installer Icon", [("Icon files", "*.png *.xpm")], "installer_icon", self.installer_icon_var)).pack(side="left", fill="x", expand=True)
            elif label == "Uninstaller Icon":
                self._create_file_selector(f, var, lambda: self._browse_file("Select Uninstaller Icon", [("Icon files", "*.png *.xpm")], "uninstaller_icon", self.uninstaller_icon_var)).pack(side="left", fill="x", expand=True)
            else:
                ttk.Entry(f, textvariable=var).pack(side="left", fill="x", expand=True)

        comp_frame = ttk.Frame(self, style="Content.TFrame")
        comp_frame.pack(fill="x", pady=4, padx=20)

        ttk.Label(comp_frame, text="Compression Type", style="Content.TLabel", width=28, anchor="w").pack(side="left")
        self.comp_type_combo = ttk.Combobox(comp_frame, textvariable=self.comp_type_var, values=["bz2", "gzip", "lzma"], state="readonly")
        self.comp_type_combo.pack(side="left", fill="x", expand=True)

        comp_level_frame = ttk.Frame(self, style="Content.TFrame")
        comp_level_frame.pack(fill="x", pady=4, padx=20)

        self.comp_level_label = ttk.Label(comp_level_frame, text="Compression Level", style="Content.TLabel", width=28, anchor="w")
        self.comp_level_label.pack(side="left")
        self.comp_level_spin = ttk.Spinbox(comp_level_frame, from_=0, to=9, textvariable=self.comp_level_var, width=5)
        self.comp_level_spin.pack(side="left")

        self.comp_type_var.trace_add("write", lambda *args: self.update_compression_bounds())

        for var in (self.app_var, self.ver_var, self.author_var):
            var.trace_add("write", lambda *args, v=var: self.update_continue_button())

        self.refresh()

    def update_compression_bounds(self):
        """Adjust the allowed compression level bounds based on the selected algorithm."""
        ctype = self.comp_type_var.get()
        if ctype == "bz2":
            min_val, max_val = 1, 9
        else:
            min_val, max_val = 0, 9
            
        self.comp_level_spin.config(from_=min_val, to=max_val)
        self.comp_level_label.config(text=f"Compression Level ({min_val} to {max_val})")

        try:
            current = self.comp_level_var.get()
            if current < min_val:
                self.comp_level_var.set(min_val)
            elif current > max_val:
                self.comp_level_var.set(max_val)
        except tk.TclError:
            self.comp_level_var.set(min_val)

    def update_continue_button(self):
        """Enable or disable the 'Next' button based on required fields."""
        app_name = self.app_var.get().strip()
        version = self.ver_var.get().strip()
        author = self.author_var.get().strip()

        if app_name and version and author:
            self.app.btn_next.config(state="normal")
        else:
            self.app.btn_next.config(state="disabled")

    def _browse_file(self, title, filetypes, data_attr, var):
        """Helper to browse for a specific file and update the project data."""
        file = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if file:
            file = os.path.normpath(file)
            setattr(self.app.project.data, data_attr, file)
            var.set(file)
    
    def refresh(self):
        """Refresh the page UI with data from the project model."""
        data = self.app.project.data
        self.app_var.set(data.app_name)
        self.ver_var.set(data.version)
        self.desc_var.set(data.description)
        self.home_var.set(data.homepage)
        self.author_var.set(data.author)

        self.installer_icon_var.set(data.installer_icon or "No file selected")
        self.uninstaller_icon_var.set(data.uninstaller_icon or "No file selected")
        self.license_file_var.set(data.license_file or "No file selected")
        self.preii_file_var.set(data.pre_install_information_file or "No file selected")
        self.postii_file_var.set(data.post_install_information_file or "No file selected")

        self.comp_type_var.set(data.compression_type)
        self.comp_level_var.set(data.compression_level)
        self.update_compression_bounds()

        self.update_continue_button()

    def on_next(self):
        """Save current inputs to the project model and advance."""
        data = self.app.project.data
        data.app_name = self.app_var.get()
        data.version = self.ver_var.get()
        data.description = self.desc_var.get()
        data.homepage = self.home_var.get()
        data.author = self.author_var.get()
        data.compression_type = self.comp_type_var.get()
        data.compression_level = self.comp_level_var.get()

        def clean_val(v):
            val = v.get().strip()
            return val if val and val != "No file selected" else None

        data.installer_icon = clean_val(self.installer_icon_var)
        data.uninstaller_icon = clean_val(self.uninstaller_icon_var)
        data.license_file = clean_val(self.license_file_var)
        data.pre_install_information_file = clean_val(self.preii_file_var)
        data.post_install_information_file = clean_val(self.postii_file_var)

        en_loc = data.localizations.get("en_US")
        if en_loc:
            en_loc.app_name = data.app_name
            en_loc.description = data.description
            en_loc.license_file = data.license_file or ""
            en_loc.pre_install_information_file = data.pre_install_information_file or ""
            en_loc.post_install_information_file = data.post_install_information_file or ""

        self.app.project.save(silent=True)
        self.app.show_page("FilesPage")


class FilesPage(BasePage):
    """Page for adding and removing files and folders to include in the installer."""
    def __init__(self, parent, app):
        """Initialize the FilesPage."""
        super().__init__(parent, app)
        logger.info("Initializing FilesPage")

        ttk.Label(self, text="Files & Folders", style="Title.TLabel").pack(anchor="w", pady=(0, 10))

        btn_frame = ttk.Frame(self, style="Content.TFrame")
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Add Files", style="Content.TButton",
               command=self.add_files).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Add Folder", style="Content.TButton",
               command=self.add_folder).pack(side="left", padx=5)
        self.btn_remove = ttk.Button(btn_frame, text="Remove Selected", style="Content.TButton",
               command=self.remove_selected)
        self.btn_remove.pack(side="left", padx=5)
        self.btn_remove.config(state="disabled")

        self.listbox = tk.Listbox(self, height=14, font=("Sans", 11), selectmode=tk.EXTENDED)
        self.listbox.pack(fill="both", expand=True, padx=40, pady=10)
        self.listbox.bind("<<ListboxSelect>>", self.on_listbox_select)


        self.refresh()

    def update_continue_button(self):
        """Enable or disable the 'Next' button based on whether files or folders exist."""
        data = self.app.project.data
        has_assets = bool(data.files or data.folders)
        if has_assets:
            self.app.btn_next.config(state="normal")
        else:
            self.app.btn_next.config(state="disabled")

    def on_listbox_select(self, event=None):
        """Enable or disable the 'Remove' button based on listbox selection."""
        if self.listbox.curselection():
            self.btn_remove.config(state="normal")
        else:
            self.btn_remove.config(state="disabled")

    def refresh(self):
        """Repopulate the listbox with current project files and folders."""
        self.listbox.delete(0, tk.END)
        data = self.app.project.data
        for f in data.files:
            self.listbox.insert(tk.END, f"[File]  {f}")
        for f in data.folders:
            self.listbox.insert(tk.END, f"[Folder]  {f}")
        self.update_continue_button()
        self.on_listbox_select()

    def add_files(self):
        """Open a file dialog to add files to the project."""
        files = filedialog.askopenfilenames(title="Select files to include")
        for f in files:
            f = os.path.normpath(f)
            if f not in self.app.project.data.files:
                self.app.project.data.files.append(f)
                logger.info(f"Added file to project: {f}")
        self.app.project.save(silent=True)
        self.refresh()

    def add_folder(self):
        """Open a directory dialog to add a folder to the project."""
        folder = filedialog.askdirectory(title="Select folder to include")
        if folder:
            folder = os.path.normpath(folder)
            if folder not in self.app.project.data.folders:
                self.app.project.data.folders.append(folder)
                logger.info(f"Added folder to project: {folder}")
        self.app.project.save(silent=True)
        self.refresh()

    def remove_selected(self):
        """Remove the currently selected items from the project after confirmation."""
        sel = self.listbox.curselection()
        if not sel:
            return
            
        if not messagebox.askyesno("Remove Selected", "Are you sure you want to remove the selected items?"):
            return

        data = self.app.project.data
        for i in sorted(sel, reverse=True):
            item = self.listbox.get(i)
            if item.startswith("[File]"):
                path = item[len("[File]"):].strip()
                if path in data.files:
                    data.files.remove(path)
                    logger.info(f"Removed file from project: {path}")
            elif item.startswith("[Folder]"):
                path = item[len("[Folder]"):].strip()
                if path in data.folders:
                    data.folders.remove(path)
                    logger.info(f"Removed folder from project: {path}")
            self.listbox.delete(i)
        self.app.project.save(silent=True)
        self.refresh()

    def on_next(self):
        """Save current state and navigate to the InstallerOptionsPage."""
        self.app.project.save(silent=True)
        self.app.show_page("InstallerOptionsPage")


class InstallerOptionsPage(BasePage):
    """Page for configuring installer options, desktop file settings, scripts, and tasks."""
    def __init__(self, parent, app):
        """Initialize the InstallerOptionsPage."""
        super().__init__(parent, app)
        logger.info("Initializing InstallerOptionsPage")

        ttk.Label(self, text="Installer Options", style="Title.TLabel").pack(anchor="w", pady=(0, 10))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=10)

        self.app_type_var = tk.StringVar(value="GUI")
        self.executable_var = tk.StringVar(value="")
        self.icon_var = tk.StringVar(value="")
        self.install_dir_var = tk.StringVar(value="")
        self.exe_path_var = tk.StringVar(value="/usr/local/bin")
        self.icon_path_var = tk.StringVar(value="/usr/share/icons")
        self.desktop_path_var = tk.StringVar(value="/usr/share/applications")

        self.desktop_var = tk.BooleanVar(value=True)
        self.desktop_options_frame = None
        self.extra_container = None
        self.custom_entry_container = None

        self.extra_desktop_pairs = []
        self.custom_entries = []
        self.additional_tasks = []

        self.executable_args_var = tk.StringVar(value="")
        self.comment_var = tk.StringVar(value="")
        self.categories_var = tk.StringVar(value="")

        self.custom_preinstall = tk.StringVar()
        self.custom_postinstall = tk.StringVar()
        self.custom_preuninstall = tk.StringVar()
        self.custom_postuninstall = tk.StringVar()
        self.last_prefilled_name = ""

    def build_desktop_options(self):
        """Build the UI for .desktop file configuration options."""
        if self.desktop_options_frame is None:
            return
        for widget in self.desktop_options_frame.winfo_children():
            widget.destroy()

        self.extra_desktop_pairs.clear()
        self.custom_entries.clear()

        ttk.Label(self.desktop_options_frame, text="Desktop File Path:", style="Content.TLabel").pack(anchor="w", padx=20, pady=(15, 0))
        ttk.Entry(self.desktop_options_frame, textvariable=self.desktop_path_var).pack(fill="x", padx=20, pady=5)

        ttk.Label(self.desktop_options_frame, text="Executable Arguments:", style="Content.TLabel").pack(
            anchor="w", padx=20, pady=(15, 0))
        ttk.Entry(self.desktop_options_frame, textvariable=self.executable_args_var).pack(fill="x", padx=20, pady=5)

        fields = [
            ("Comment:", self.comment_var),
            ("Categories:", self.categories_var),
        ]
        for label_text, var in fields:
            ttk.Label(self.desktop_options_frame, text=label_text, style="Content.TLabel").pack(
                anchor="w", padx=20, pady=(15, 0))
            ttk.Entry(self.desktop_options_frame, textvariable=var).pack(fill="x", padx=20, pady=5)

        ttk.Label(self.desktop_options_frame, text="Additional Key-Value Pairs (main section):",
              style="Content.TLabel").pack(anchor="w", padx=20, pady=(25, 5))

        self.extra_container = ttk.Frame(self.desktop_options_frame, style="Content.TFrame")
        self.extra_container.pack(fill="x", padx=20, pady=5)

        ttk.Button(self.extra_container, text="Add Key-Value Pair", style="Content.TButton",
               command=self.add_extra_desktop_pair).pack(anchor="w", pady=8)

        ttk.Label(self.desktop_options_frame, text="Additional Entries and its Key-Value Pairs:",
              style="Content.TLabel").pack(anchor="w", padx=20, pady=(30, 5))

        self.custom_entry_container = ttk.Frame(self.desktop_options_frame, style="Content.TFrame")
        self.custom_entry_container.pack(fill="x", padx=20, pady=5)

        ttk.Button(self.custom_entry_container, text="Add New Entry",
               style="Content.TButton", command=self.add_custom_entry).pack(anchor="w", pady=8)

    def add_extra_desktop_pair(self, key="", value=""):
        """Add a key-value pair row for the desktop file's main section."""
        row = ttk.Frame(self.extra_container, style="Content.TFrame")
        row.pack(fill="x", pady=3)

        key_var = tk.StringVar(value=key)
        value_var = tk.StringVar(value=value)

        ttk.Entry(row, textvariable=key_var, width=25).pack(side="left", padx=(0, 5))
        ttk.Label(row, text="=", style="Content.TLabel").pack(side="left")
        ttk.Entry(row, textvariable=value_var).pack(side="left", padx=5, fill="x", expand=True)

        ttk.Button(row, text="Remove", style="Content.TButton",
               command=lambda r=row: self.remove_extra_pair(r)).pack(side="right", padx=5)

        self.extra_desktop_pairs.append({"frame": row, "key_var": key_var, "value_var": value_var})

    def add_custom_entry(self, entry_name=""):
        """Add a custom Desktop Action entry with its own key-value pairs."""
        entry_frame = ttk.Frame(self.custom_entry_container, style="Content.TFrame")
        entry_frame.pack(fill="x", pady=10, padx=10)

        name_frame = ttk.Frame(entry_frame, style="Content.TFrame")
        name_frame.pack(fill="x")
        ttk.Label(name_frame, text="Entry Name:", style="Content.TLabel").pack(side="left", padx=(0, 10))
        entry_name_var = tk.StringVar(value=entry_name)
        ttk.Entry(name_frame, textvariable=entry_name_var, width=35).pack(side="left", fill="x", expand=True)

        ttk.Button(name_frame, text="Remove Entry", style="Content.TButton",
               command=lambda: self.remove_custom_entry(entry_frame)).pack(side="right", padx=5)

        pairs_container = ttk.Frame(entry_frame, style="Content.TFrame")
        pairs_container.pack(fill="x", pady=8, padx=20)

        ttk.Button(pairs_container, text="Add Key-Value Pair", style="Content.TButton",
               command=lambda e=entry_name_var: self.add_pair_to_custom_entry(pairs_container, e)).pack(anchor="w")

        entry_obj = {
            "frame": entry_frame,
            "name_var": entry_name_var,
            "pairs_container": pairs_container,
            "pairs": []
        }
        self.custom_entries.append(entry_obj)
        return entry_obj

    def add_pair_to_custom_entry(self, container, entry_name_var, key="", value=""):
        """Add a key-value pair row to a specific custom Desktop Action entry."""
        row = ttk.Frame(container, style="Content.TFrame")
        row.pack(fill="x", pady=3)

        keypair = tk.StringVar(value=key)
        valuepair = tk.StringVar(value=value)

        ttk.Entry(row, textvariable=keypair, width=22).pack(side="left", padx=(0, 5))
        ttk.Label(row, text="=", style="Content.TLabel").pack(side="left")
        ttk.Entry(row, textvariable=valuepair).pack(side="left", padx=5, fill="x", expand=True)

        ttk.Button(row, text="Remove", style="Content.TButton",
               command=lambda: self.remove_pair_from_custom_entry(row, entry_name_var, keypair)).pack(side="right", padx=5)

        for entry in self.custom_entries:
            if entry["name_var"] is entry_name_var:
                entry["pairs"].append({"key_var": keypair, "value_var": valuepair})
                break
        

    def remove_extra_pair(self, row):
        """Remove a key-value pair row from the desktop file's main section."""
        row.destroy()
        self.extra_desktop_pairs = [p for p in self.extra_desktop_pairs if p["frame"] is not row]
    
    def remove_pair_from_custom_entry(self, row, entry_name_var, key):
        """Remove a key-value pair row from a specific custom Desktop Action entry."""
        row.destroy()

        for entry in self.custom_entries:
            if entry["name_var"] is entry_name_var:
                entry["pairs"] = [p for p in entry["pairs"] if p["key_var"] is not key]
                break

    def remove_custom_entry(self, frame):
        """Remove an entire custom Desktop Action entry."""
        frame.destroy()
        self.custom_entries = [e for e in self.custom_entries if e["frame"] is not frame]

    def load_desktop_data(self, desktop_data):
        """Populate the desktop options UI from existing desktop configuration data."""
        self.executable_args_var.set(desktop_data.executable_args)
        self.comment_var.set(desktop_data.comment)
        self.categories_var.set(desktop_data.categories)

        for pair in desktop_data.extra_keys:
            self.add_extra_desktop_pair(pair.key, pair.value)

        for entry in desktop_data.extra_entries:
            entry_obj = self.add_custom_entry(entry.name)
            for attr in entry.attributes:
                self.add_pair_to_custom_entry(entry_obj["pairs_container"], entry_obj["name_var"], attr.key, attr.value)
    
    
    def add_additional_task(self, key="", value=""):
        """Add an additional task row with a key and file selector."""
        row = ttk.Frame(self.tab_extra_container, style="Content.TFrame")
        row.pack(fill="x", pady=3)

        key_var = tk.StringVar(value=key)
        value_var = tk.StringVar(value=value)

        ttk.Entry(row, textvariable=key_var, width=25).pack(side="left", padx=(0, 5))
        self._create_file_selector(row, value_var, lambda: self.file_for_additional_task(value_var)).pack(side="left", padx=5, fill="x", expand=True)

        ttk.Button(row, text="X", style="Content.TButton", width=5,
               command=lambda r=row: self.remove_additional_tasks(r)).pack(side="right", padx=5)

        self.additional_tasks.append({"frame": row, "key_var": key_var, "value_var": value_var})
    
    def file_for_additional_task(self, value_var):
        """Open a file dialog to select a script for an additional task."""
        file = filedialog.askopenfilename(filetypes=[("Shell Script", "*.*")])
        if file:
            file = os.path.normpath(file)
            for task in self.additional_tasks:
                if task["value_var"] is value_var:
                    task["value_var"].set(file)
                    break
    
    def remove_additional_tasks(self, row):
        """Remove an additional task row."""
        row.destroy()
        self.additional_tasks = [p for p in self.additional_tasks if p["frame"] is not row]


    def refresh_tabs(self):
        """Save current state, reset the snapshot, and rebuild tabs."""
        self.on_next(continue_next=False)
        self._last_snapshot = None
        self.refresh()

    def _data_snapshot(self):
        """Return a hashable snapshot of data that drives tab layout."""
        data = self.app.project.data
        return (
            data.app_type,
            tuple(sorted((k, v.enabled) for k, v in data.installer_profiles.items())),
            hash(tuple(data.files)),
            hash(tuple(data.folders)),
            data.app_name,
            data.install_dir,
        )

    def refresh(self):
        """Rebuild all tabs from the project data if the data has changed."""
        snapshot = self._data_snapshot()
        if hasattr(self, '_last_snapshot') and self._last_snapshot is not None and snapshot == self._last_snapshot:
            return

        self.additional_tasks.clear()
        self.extra_desktop_pairs.clear()
        self.custom_entries.clear()
        self.extra_container = None
        self.custom_entry_container = None
        for tab_id in list(self.notebook.tabs()):
            tab_widget = self.nametowidget(tab_id)
            self.notebook.forget(tab_id)
            tab_widget.destroy()

        data = self.app.project.data
        has_installers = any(p.enabled for p in data.installer_profiles.values())
        has_assets = bool(data.files or data.folders)

        if has_installers and has_assets:
            self.app.btn_next.config(state="normal")
        else:
            self.app.btn_next.config(state="disabled")
            self._last_snapshot = snapshot
            return

        app_slug = re.sub(r'[^\w\-.]', '_', data.app_name) if data.app_name else "app"
        if not data.install_dir:
            data.install_dir = f"/opt/{app_slug}"
        if not data.exe_path:
            data.exe_path = f"/usr/local/bin/{app_slug}"
        if not data.icon_path:
            data.icon_path = f"/usr/share/icons/{app_slug}.png"
        self.last_prefilled_name = data.app_name
        
        self.install_dir_var.set(data.install_dir)
        self.exe_path_var.set(data.exe_path)
        self.icon_path_var.set(data.icon_path)
        self.desktop_path_var.set(data.desktop_path)

        self.general_tab = ScrollableFrame(self.notebook, style="Content.TFrame")
        self.notebook.add(self.general_tab, text="Settings")
        
        self.app_type_var.set(data.app_type)
        self.executable_var.set(data.executable)
        self.icon_var.set(data.icon)
        
        ttk.Label(self.general_tab.scrollable_frame, text="App Type:", style="Content.TLabel").pack(anchor="w", padx=20, pady=(15, 0))
        app_type_frame = ttk.Frame(self.general_tab.scrollable_frame, style="Content.TFrame")
        app_type_frame.pack(fill="x", padx=20, pady=5)
        
        ttk.Radiobutton(app_type_frame, text="GUI Application", variable=self.app_type_var, value="GUI", command=self.refresh_tabs, style="Content.TRadiobutton").pack(side="left", padx=10)
        ttk.Radiobutton(app_type_frame, text="CLI Tool", variable=self.app_type_var, value="CLI", command=self.refresh_tabs, style="Content.TRadiobutton").pack(side="left", padx=10)

        ttk.Label(self.general_tab.scrollable_frame, text="Destination:", style="Content.TLabel").pack(anchor="w", padx=20, pady=(15, 0))
        ttk.Entry(self.general_tab.scrollable_frame, textvariable=self.install_dir_var).pack(fill="x", padx=20, pady=5)

        ttk.Label(self.general_tab.scrollable_frame, text="Executable Settings:", style="Content.TLabel").pack(anchor="w", padx=20, pady=(15, 0))
        
        f_exe = ttk.Frame(self.general_tab.scrollable_frame, style="Content.TFrame")
        f_exe.pack(fill="x", padx=20, pady=5)
        
        ttk.Label(f_exe, text="Source:", style="Content.TLabel").pack(side="left")
        ttk.Combobox(f_exe, textvariable=self.executable_var, values=data.files, state="readonly").pack(side="left", fill="x", expand=True, padx=5)
        
        ttk.Label(f_exe, text="Target:", style="Content.TLabel").pack(side="left", padx=(10, 0))
        ttk.Entry(f_exe, textvariable=self.exe_path_var).pack(side="left", fill="x", expand=True, padx=5)
        
        if data.app_type == "GUI":
            ttk.Label(self.general_tab.scrollable_frame, text="Icon Settings:", style="Content.TLabel").pack(anchor="w", padx=20, pady=(15, 0))
            
            f_icon = ttk.Frame(self.general_tab.scrollable_frame, style="Content.TFrame")
            f_icon.pack(fill="x", padx=20, pady=5)
            
            ttk.Label(f_icon, text="Source:", style="Content.TLabel").pack(side="left")
            icon_values = [""] + data.files
            ttk.Combobox(f_icon, textvariable=self.icon_var, values=icon_values, state="readonly").pack(side="left", fill="x", expand=True, padx=5)
            
            ttk.Label(f_icon, text="Target:", style="Content.TLabel").pack(side="left", padx=(10, 0))
            ttk.Entry(f_icon, textvariable=self.icon_path_var).pack(side="left", fill="x", expand=True, padx=5)

            self.integration_tab = ScrollableFrame(self.notebook, style="Content.TFrame")
            self.notebook.add(self.integration_tab, text=".desktop File")

            desktop_data = data.desktop
            self.desktop_var.set(True)

            self.desktop_options_frame = ttk.Frame(self.integration_tab.scrollable_frame, style="Content.TFrame")
            self.desktop_options_frame.pack(fill="x", padx=40, pady=10)
            self.build_desktop_options()

            self.load_desktop_data(desktop_data)
        else:
            self.desktop_var.set(False)

        for key, profile in data.installer_profiles.items():
            if not profile.enabled:
                continue
            if key == "custom":
                tab = ScrollableFrame(self.notebook, style="Content.TFrame")
                self.notebook.add(tab, text="Scripts and Tasks")

                ttk.Label(tab.scrollable_frame, text="Pre install script path:", style="Content.TLabel").pack(anchor="w", padx=20, pady=(15, 0))
                self._create_file_selector(tab.scrollable_frame, self.custom_preinstall, lambda: self._browse_script(self.custom_preinstall)).pack(fill="x", padx=20, pady=5)

                ttk.Label(tab.scrollable_frame, text="Post install script path:", style="Content.TLabel").pack(anchor="w", padx=20, pady=(15, 0))
                self._create_file_selector(tab.scrollable_frame, self.custom_postinstall, lambda: self._browse_script(self.custom_postinstall)).pack(fill="x", padx=20, pady=5)

                ttk.Label(tab.scrollable_frame, text="Pre uninstall script path:", style="Content.TLabel").pack(anchor="w", padx=20, pady=(10, 0))
                self._create_file_selector(tab.scrollable_frame, self.custom_preuninstall, lambda: self._browse_script(self.custom_preuninstall)).pack(fill="x", padx=20, pady=5)

                ttk.Label(tab.scrollable_frame, text="Post uninstall script path:", style="Content.TLabel").pack(anchor="w", padx=20, pady=(10, 0))
                self._create_file_selector(tab.scrollable_frame, self.custom_postuninstall, lambda: self._browse_script(self.custom_postuninstall)).pack(fill="x", padx=20, pady=5)


                ttk.Label(tab.scrollable_frame, text="Additional Tasks:",
              style="Content.TLabel").pack(anchor="w", padx=20, pady=(25, 5))
                self.tab_extra_container = ttk.Frame(tab.scrollable_frame, style="Content.TFrame")
                self.tab_extra_container.pack(fill="x", padx=20, pady=5)
                ttk.Button(self.tab_extra_container, text="Add additional task", style="Content.TButton", command=self.add_additional_task).pack(anchor="w", pady=8)

                self.load_custom_data(profile)

        self._last_snapshot = snapshot

    def load_custom_data(self, profile):
        """Populate script path variables and additional tasks from an installer profile."""
        self.custom_preinstall.set(profile.pre_install_script)
        self.custom_postinstall.set(profile.post_install_script)
        self.custom_preuninstall.set(profile.pre_uninstall_script)
        self.custom_postuninstall.set(profile.post_uninstall_script)

        for task in profile.additional_tasks:
            self.add_additional_task(task.key, task.value)
        
    def _browse_script(self, target_var: tk.StringVar):
        """Open a file dialog to browse for a script file."""
        file = filedialog.askopenfilename(filetypes=[("Shell Script", "*.*")])
        if file:
            target_var.set(os.path.normpath(file))


    def on_next(self, continue_next=True):
        """Collect all form data, save to the project model, and optionally advance."""
        data = self.app.project.data

        extra_keys = [
            {"key": p["key_var"].get().strip(), "value": p["value_var"].get().strip()}
            for p in self.extra_desktop_pairs if p["key_var"].get().strip()
        ]

        extra_entries = []
        for entry in self.custom_entries:
            entry_name = entry["name_var"].get().strip()
            if not entry_name:
                continue
            pairs = [
                {"key": p["key_var"].get().strip(), "value": p["value_var"].get().strip()}
                for p in entry["pairs"] if p["key_var"].get().strip()
            ]
            extra_entries.append({"name": entry_name, "attributes": pairs})

        data.app_type = self.app_type_var.get()
        data.executable = self.executable_var.get()
        data.icon = self.icon_var.get()
        data.install_dir = self.install_dir_var.get()
        data.exe_path = self.exe_path_var.get()
        data.icon_path = self.icon_path_var.get()
        data.desktop_path = self.desktop_path_var.get()

        data.desktop = DesktopConfig(
            enabled=self.desktop_var.get(),
            executable_args=self.executable_args_var.get(),
            comment=self.comment_var.get(),
            categories=self.categories_var.get(),
            extra_keys=[DesktopExtraKey(**k) for k in extra_keys],
            extra_entries=[DesktopExtraEntry(
                name=str(e["name"]),
                attributes=[DesktopExtraKey(**a) for a in e["attributes"]]
            ) for e in extra_entries],
        )

        custom = data.installer_profiles.get("custom")
        if custom:
            custom.pre_install_script = self.custom_preinstall.get()
            custom.post_install_script = self.custom_postinstall.get()
            custom.pre_uninstall_script = self.custom_preuninstall.get()
            custom.post_uninstall_script = self.custom_postuninstall.get()
            custom.additional_tasks = [
                InstallerTask(key=t["key_var"].get().strip(), value=t["value_var"].get().strip())
                for t in self.additional_tasks
            ]

        self.app.project.save(silent=True)
        if continue_next:
            self.app.show_page("SummaryPage")


class SummaryPage(BasePage):
    """Page showing a summary of the project configuration before building."""
    def __init__(self, parent, app):
        """Initialize the SummaryPage."""
        super().__init__(parent, app)
        logger.info("Initializing SummaryPage")


        ttk.Label(self, text="Review & Generate", style="Title.TLabel").pack(anchor="w", pady=(0, 25))

        self.app_label = ttk.Label(self, text="", style="Content.TLabel")
        self.app_label.pack(anchor="w", pady=5)
        self.dest_label = ttk.Label(self, text="", style="Content.TLabel")
        self.dest_label.pack(anchor="w", pady=5)
        self.bin_label = ttk.Label(self, text="", style="Content.TLabel")
        self.bin_label.pack(anchor="w", pady=5)
        self.desktop_label = ttk.Label(self, text="", style="Content.TLabel")
        self.desktop_label.pack(anchor="w", pady=5)
        self.icon_label = ttk.Label(self, text="", style="Content.TLabel")
        self.icon_label.pack(anchor="w", pady=5)
        self.installer_icon_summary_label = ttk.Label(self, text="", style="Content.TLabel")
        self.installer_icon_summary_label.pack(anchor="w", pady=5)
        self.uninstaller_icon_summary_label = ttk.Label(self, text="", style="Content.TLabel")
        self.uninstaller_icon_summary_label.pack(anchor="w", pady=5)
        self.license_label = ttk.Label(self, text="", style="Content.TLabel")
        self.license_label.pack(anchor="w", pady=5)
        self.comp_label = ttk.Label(self, text="", style="Content.TLabel")
        self.comp_label.pack(anchor="w", pady=5)
        self.extra_label = ttk.Label(self, text="", style="Content.TLabel")
        self.extra_label.pack(anchor="w", pady=5)

    def refresh(self):
        """Update all summary labels with the latest project data."""
        data = self.app.project.data
        self.app_label.config(text=f"App: {data.app_name} {data.version}")
        self.dest_label.config(text=f"Destination: {data.install_dir}")
        self.bin_label.config(text=f"Executable: {data.exe_path}")
        self.desktop_label.config(text=f"Desktop File: {data.desktop_path if data.app_type == 'GUI' else 'None'}")
        self.icon_label.config(text=f"Icon: {data.icon_path if data.app_type == 'GUI' else 'None'}")
        self.installer_icon_summary_label.config(text=f"Installer Icon: {os.path.basename(data.installer_icon) if data.installer_icon else 'None selected'}")
        self.uninstaller_icon_summary_label.config(text=f"Uninstaller Icon: {os.path.basename(data.uninstaller_icon) if data.uninstaller_icon else 'None selected'}")
        self.license_label.config(text=f"License: {data.license_file or 'None selected'}")
        self.comp_label.config(text=f"Compression: {data.compression_type} (Level {data.compression_level})")
        
        langs_count = len(data.localizations)
        files_count = len(data.files)
        folders_count = len(data.folders)
        custom = data.installer_profiles.get("custom")
        tasks_count = len(custom.additional_tasks) if custom else 0
        scripts_count = 0
        if custom:
            if custom.pre_install_script: scripts_count += 1
            if custom.post_install_script: scripts_count += 1
            if custom.pre_uninstall_script: scripts_count += 1
            if custom.post_uninstall_script: scripts_count += 1

        self.extra_label.config(text=f"Includes: {files_count} files, {folders_count} folders, {langs_count} languages, {tasks_count} tasks, {scripts_count} scripts")


class BuildOutputPage(BasePage):
    """Page that displays live build output during installer generation."""
    def __init__(self, parent, app):
        """Initialize the BuildOutputPage."""
        super().__init__(parent, app)
        logger.info("Initializing BuildOutputPage")

        ttk.Label(self, text="Generating Installer", style="Title.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(self, text="Please wait while PyInstaller processes the files...", style="Content.TLabel").pack(anchor="w", pady=(0, 10))
        
        self.stage_label = ttk.Label(self, text="▶ Preparing...", style="Content.TLabel", font=("Sans", 10, "bold"))
        self.stage_label.pack(anchor="w", pady=(0, 10))

        container = ttk.Frame(self, style="Content.TFrame")
        container.pack(fill="both", expand=True)

        self.text_box = tk.Text(container, height=20, wrap="word", font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4", relief="flat")
        self.scroll = ttk.Scrollbar(container, orient="vertical", command=self.text_box.yview)
        self.text_box.configure(yscrollcommand=self.scroll.set)

        self.scroll.pack(side="right", fill="y")
        self.text_box.pack(side="left", fill="both", expand=True)
        self.text_box.configure(state="disabled")

    def append_output(self, text: str):
        """Append text to the build output display."""
        self.text_box.configure(state="normal")
        self.text_box.insert("end", text)
        self.text_box.see("end")
        self.text_box.configure(state="disabled")
        
    def set_stage(self, text: str):
        """Update the build stage label text."""
        self.stage_label.configure(text=text)
        
    def clear(self):
        """Clear the build output display."""
        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", "end")
        self.text_box.configure(state="disabled")