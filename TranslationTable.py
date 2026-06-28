import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from config import LocalizationEntry
from logger_config import get_logger

logger = get_logger()


class TranslationTable(tk.Toplevel):
    """
    A tkinter window for managing localization entries in the project.
    Allows adding, removing, and editing translations for various application fields.
    """
    def __init__(self, parent, project_data):
        """
        Initialize the TranslationTable window.
        
        Args:
            parent: The parent tkinter window.
            project_data: The TinoProject configuration data containing localizations.
        """
        super().__init__(parent)
        self.app = parent
        logger.info("Opening Translation Management Table")

        self.title("Manage Translations")
        self.geometry("1000x600")
        self.data = project_data
        self.selected_lang = None
        
        self.base_keys = [
            ("app_name", "Application Name", "text"),
            ("description", "Application Description", "text"),
            ("license_file", "License File", "file"),
            ("pre_install_information_file", "Pre-Install Info", "file"),
            ("post_install_information_file", "Post-Install Info", "file")
        ]
        self.translation_keys = []
        self.cached_langs = []
        self.cached_cols = []

        self.configure(background="white")
        
        self.main_frame = ttk.Frame(self, padding=20, style="Content.TFrame")
        self.main_frame.pack(fill="both", expand=True)

        ttk.Label(self.main_frame, text="Localizations", style="Title.TLabel").pack(anchor="w", pady=(0, 20))

        toolbar = ttk.Frame(self.main_frame, style="Content.TFrame")
        toolbar.pack(fill="x", pady=(0, 10))
        
        ttk.Label(toolbar, text=" (Right-click column header to manage a language | Click '+' to add)", style="Content.TLabel", foreground="#666").pack(side="left", padx=10)

        table_container = ttk.Frame(self.main_frame, style="Content.TFrame")
        table_container.pack(fill="both", expand=True)

        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_container, selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")

        v_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=v_scrollbar.set)

        h_scrollbar = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview)
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=h_scrollbar.set)

        style = ttk.Style()
        style.configure("Treeview", font=("Sans", 10), rowheight=30)
        style.configure("Treeview.Heading", font=("Sans", 10, "bold"))
        
        self.refresh_table()
        
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-1>", self.on_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def refresh_table(self):
        """Rebuild the translation table UI with the current localization data."""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.cached_langs = [l for l in self.data.localizations.keys() if l != "en_US"]
        self.cached_cols = ["Field"] + self.cached_langs
        langs = self.cached_langs

        if "en_US" not in self.data.localizations and self.data.app_name:
            en_entry = LocalizationEntry(
                language_label="English",
                app_name=self.data.app_name,
                description=self.data.description,
                license_file=self.data.license_file or "",
                pre_install_information_file=self.data.pre_install_information_file or "",
                post_install_information_file=self.data.post_install_information_file or ""
            )
            custom_prof = self.data.installer_profiles.get("custom")
            if custom_prof:
                en_entry.additional_tasks = {t.key: t.key for t in custom_prof.additional_tasks}
            self.data.localizations["en_US"] = en_entry

        self.tree["columns"] = ["Field"] + langs + ["ADD_LANG"]
        self.tree.heading("#0", text="", anchor="w")
        self.tree.column("#0", width=0, stretch=False)
        
        self.tree.heading("Field", text="Default (English)")
        self.tree.column("Field", width=300, anchor="w", stretch=False)
        
        for lang in langs:
            label = self.data.localizations[lang].language_label or lang
            self.tree.heading(lang, text=label)
            self.tree.column(lang, width=250, anchor="w", stretch=False)

        self.tree.heading("ADD_LANG", text="+")
        self.tree.column("ADD_LANG", width=40, anchor="center", stretch=False)

        self.translation_keys = list(self.base_keys)
        custom_prof = self.data.installer_profiles.get("custom")
        if custom_prof:
            for task in custom_prof.additional_tasks:
                if task.key:
                    self.translation_keys.append((f"task_{task.key}", "Additional Task", "text"))

        for key, label, ftype in self.translation_keys:
            values = self._get_row_values(key, label, ftype, langs)
            self.tree.insert("", "end", iid=key, values=values)

    def _get_row_values(self, key, label, ftype, langs):
        """
        Retrieve the cell values for a specific row across all selected languages.
        
        Args:
            key: The attribute key for the translation item.
            label: The display label for the item.
            ftype: The field type ('text' or 'file').
            langs: List of language codes to populate columns for.
            
        Returns:
            A list of values corresponding to the columns in the table row.
        """
        is_task = key.startswith("task_")
        task_key = key[5:] if is_task else None

        en_loc = self.data.localizations.get("en_US")
        if is_task:
            en_val = task_key
        else:
            en_val = getattr(en_loc, key) if en_loc else getattr(self.data, key, "")
        
        if not en_val and key == "app_name":
            en_val = self.data.app_name
        
        placeholder = "(not set)"
        display_label = f"{label} ({os.path.basename(en_val) if ftype == 'file' and en_val else (en_val or 'not set')})"
        values = [display_label]

        for lang in langs:
            loc = self.data.localizations[lang]
            if is_task:
                val = loc.additional_tasks.get(task_key, "")
            else:
                val = getattr(loc, key)
            
            if not val:
                val = placeholder
            elif ftype == "file":
                val = os.path.basename(val)
                
            values.append(val)

        values.append("")
        return values

    def on_click(self, event):
        """Handle single-click events on the table, primarily for language selection and adding new languages."""
        region = self.tree.identify_region(event.x, event.y)
        column = self.tree.identify_column(event.x)
        if not column: return
        
        if region == "heading":
            column_id = self.tree.column(column, option="id")
            if column_id == "ADD_LANG":
                self.add_language()
                return
            
            col_idx = int(column.replace("#", "")) - 1
            if 0 < col_idx < len(self.cached_cols):
                self.selected_lang = self.cached_cols[col_idx]
            else:
                self.selected_lang = None
        elif region == "cell":
            col_idx = int(column.replace("#", "")) - 1
            if 0 < col_idx < len(self.cached_cols):
                self.selected_lang = self.cached_cols[col_idx]
            else:
                self.selected_lang = None

    def save_project(self):
        """Silently save the project to disk."""
        if hasattr(self.app, "project"):
            self.app.project.save(silent=True)

    def show_context_menu(self, event):
        """Display a right-click context menu for column headers to manage languages."""
        region = self.tree.identify_region(event.x, event.y)
        if region != "heading": return
        
        column = self.tree.identify_column(event.x)
        if not column: return
        
        column_id = self.tree.column(column, option="id")
        if column_id in ("Field", "ADD_LANG", "en_US", ""): return

        self.selected_lang = column_id
        
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=f"Change Code for '{column_id}'", command=self.change_lang_code)
        menu.add_command(label=f"Change Name for '{column_id}'", command=self.change_lang_name)
        menu.add_separator()
        menu.add_command(label=f"Remove Language '{column_id}'", command=self.remove_language)
        menu.tk_popup(event.x_root, event.y_root)

    def change_lang_code(self):
        """Prompt the user to change the internal language code for the selected column."""
        if not self.selected_lang: return
        new_code = simpledialog.askstring("Change Code", f"Enter new code for '{self.selected_lang}':", initialvalue=self.selected_lang)
        if new_code and new_code != self.selected_lang:
            if new_code in self.data.localizations:
                logger.warning(f"Failed to change language code: {new_code} already exists")
                messagebox.showerror("Error", "Code already exists!")
                return
            logger.info(f"Changing language code from '{self.selected_lang}' to '{new_code}'")
            val = self.data.localizations.pop(self.selected_lang)

            self.data.localizations[new_code] = val
            self.selected_lang = new_code
            self.refresh_table()
            self.save_project()

    def change_lang_name(self):
        """Prompt the user to change the display name of the selected language."""
        if not self.selected_lang: return
        current_name = self.data.localizations[self.selected_lang].language_label
        new_name = simpledialog.askstring("Change Name", f"Enter new display name for '{self.selected_lang}':", initialvalue=current_name)
        if new_name is not None:
            logger.info(f"Changing language name for '{self.selected_lang}' to '{new_name}'")
            self.data.localizations[self.selected_lang].language_label = new_name

            self.refresh_table()
            self.save_project()

    def add_language(self):
        """Prompt the user for a new language code and name, then add it to the table."""
        code = simpledialog.askstring("Add Language", "Enter language code:")
        if not code: return
        
        name = simpledialog.askstring("Add Language", f"Enter display name for '{code}':")
        if not name: return
        
        if code in self.data.localizations:
            logger.warning(f"Failed to add language: {code} already exists")
            messagebox.showerror("Error", "Language already exists!")
            return
            
        logger.info(f"Adding new language: {code} ({name})")
        self.data.localizations[code] = LocalizationEntry(language_label=name)

        self.refresh_table()
        self.save_project()

    def remove_language(self):
        """Prompt for confirmation and remove the selected language from the localizations."""
        if not self.selected_lang:
            messagebox.showwarning("Warning", "Select a language column by clicking a cell.")
            return
        
        if messagebox.askyesno("Confirm", f"Remove language '{self.selected_lang}'?"):
            if self.selected_lang in self.data.localizations:
                logger.info(f"Removing language: {self.selected_lang}")
                del self.data.localizations[self.selected_lang]

                self.selected_lang = None
                self.refresh_table()
                self.save_project()

    def update_task_key(self, old_key, new_key):
        """
        Update an additional task's internal key across all localizations and profiles.
        
        Args:
            old_key: The current task key.
            new_key: The new task key to apply.
        """
        if not new_key or old_key == new_key: return

        custom_prof = self.data.installer_profiles.get("custom")
        if custom_prof:
            for task in custom_prof.additional_tasks:
                if task.key == old_key:
                    task.key = new_key
                    break

        for loc in self.data.localizations.values():
            if old_key in loc.additional_tasks:
                logger.info(f"Updating additional task key from '{old_key}' to '{new_key}' in localization '{loc.language_label}'")
                val = loc.additional_tasks.pop(old_key)
                loc.additional_tasks[new_key] = val

        self.save_project()

    def on_double_click(self, event):
        """Handle double-click events on table cells to edit their translation value or select a file."""
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell": return
        
        column = self.tree.identify_column(event.x)
        item_id = self.tree.identify_row(event.y)
        
        col_idx = int(column.replace("#", "")) - 1
        
        if col_idx <= 0 or col_idx >= len(self.cached_cols): return
        
        lang_code = self.cached_cols[col_idx]
        field_key = item_id
        
        is_task = field_key.startswith("task_")
        task_key = field_key[5:] if is_task else None
        
        field_type = "text"
        for k, label, t in self.translation_keys:
            if k == field_key:
                field_type = t
                break
        
        loc = self.data.localizations[lang_code]
        if is_task:
            if lang_code == "en_US":
                new_key = simpledialog.askstring("Edit Task Key", "Enter new internal key for this task:", initialvalue=task_key)
                if new_key and new_key != task_key:
                    self.update_task_key(task_key, new_key)
                    self.refresh_table()
                return
            else:
                current_val = loc.additional_tasks.get(task_key, "")
        else:
            current_val = getattr(loc, field_key) or ""
        
        new_val = None
        if field_type == "file":
            new_val = filedialog.askopenfilename(
                title=f"Select file for {field_key} ({lang_code})",
                initialdir=os.path.dirname(current_val) if current_val and os.path.exists(os.path.dirname(current_val)) else None
            )
            if new_val:
                logger.info(f"Selected file for {field_key} ({lang_code}): {new_val}")
        else:
            new_val = simpledialog.askstring("Edit Translation", f"Enter translation for {field_key} ({lang_code}):", initialvalue=current_val)
            if new_val is not None:
                logger.info(f"Updated translation for {field_key} ({lang_code})")

        
        if new_val is not None:
            if is_task:
                loc.additional_tasks[task_key] = new_val
            else:
                setattr(loc, field_key, new_val)

            label = ""
            ftype = "text"
            for k, l, t in self.translation_keys:
                if k == field_key:
                    label, ftype = l, t
                    break
            
            new_row_values = self._get_row_values(field_key, label, ftype, self.cached_langs)
            self.tree.item(field_key, values=new_row_values)
            self.save_project()
