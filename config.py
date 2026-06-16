import os
import json
from typing import Optional
from tkinter import messagebox, filedialog

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from logger_config import get_logger, setup_project_logger

logger = get_logger()


class DesktopExtraKey(BaseModel):
    """A single custom key-value pair in the [Desktop Entry] section."""
    model_config = ConfigDict(strict=True, extra="forbid")
    key: str = ""
    value: str = ""


class DesktopExtraEntry(BaseModel):
    """A custom Desktop Action (e.g. 'New Window')."""
    model_config = ConfigDict(strict=True, extra="forbid")
    name: str = ""
    attributes: list[DesktopExtraKey] = Field(default_factory=list)


class DesktopConfig(BaseModel):
    """Configuration for the generated .desktop file."""
    model_config = ConfigDict(strict=True, extra="forbid")
    enabled: bool = True
    comment: str = ""
    categories: str = ""
    extra_keys: list[DesktopExtraKey] = Field(default_factory=list)
    extra_entries: list[DesktopExtraEntry] = Field(default_factory=list)
    executable_args: str = ""


class InstallerTask(BaseModel):
    """An additional task selectable during installation."""
    model_config = ConfigDict(strict=True, extra="forbid")
    key: str = ""
    value: str = ""


class InstallerProfile(BaseModel):
    """A single installer profile (e.g. 'custom')."""
    model_config = ConfigDict(strict=True, extra="forbid")
    enabled: bool = True
    type: str = "custom"
    additional_tasks: list[InstallerTask] = Field(default_factory=list)
    pre_install_script: str = ""
    post_install_script: str = ""
    pre_uninstall_script: str = ""
    post_uninstall_script: str = ""


class LocalizationEntry(BaseModel):
    """Localized strings and files for a specific language."""
    model_config = ConfigDict(strict=True, extra="forbid")
    language_label: str = ""
    app_name: str = ""
    description: str = ""
    license_file: str = ""
    pre_install_information_file: str = ""
    post_install_information_file: str = ""
    additional_tasks: dict[str, str] = Field(default_factory=dict)


class TinoProject(BaseModel):
    """
    Root model that represents a complete .tino project file.

    All fields have sensible defaults so a blank project can be
    created with ``TinoProject()``.
    """
    model_config = ConfigDict(strict=True, extra="forbid")
    tino_version: str = "1.0"
    app_name: str = ""
    app_type: str = "GUI"
    executable: str = ""
    icon: str = ""
    install_dir: str = ""
    exe_path: str = "/usr/local/bin"
    icon_path: str = "/usr/share/icons"
    desktop_path: str = "/usr/share/applications"
    version: str = ""
    description: str = ""
    homepage: str = ""
    author: str = ""
    license_file: Optional[str] = None
    pre_install_information_file: Optional[str] = None
    post_install_information_file: Optional[str] = None
    installer_icon: Optional[str] = None
    uninstaller_icon: Optional[str] = None
    files: list[str] = Field(default_factory=list)
    folders: list[str] = Field(default_factory=list)
    desktop: DesktopConfig = Field(default_factory=DesktopConfig)
    installer_profiles: dict[str, InstallerProfile] = Field(
        default_factory=lambda: {"custom": InstallerProfile()}
    )
    compression_type: str = "gzip"
    compression_level: int = 6
    localizations: dict[str, LocalizationEntry] = Field(default_factory=dict)


class ConfigManager:
    """Manages loading, saving, path normalization, and state of Tino projects."""

    def __init__(self):
        """Initializes a new ConfigManager with a default project configuration."""
        self.data = TinoProject()
        self.current_path: Optional[str] = None

    def load(self, filepath: str) -> bool:
        """Loads and validates a .tino project file from disk.

        Args:
            filepath: Path to the .tino JSON file.

        Returns:
            True if load and validation succeeded, otherwise False.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in file", exc_info=True)
            messagebox.showerror("JSON Error", "Please consult the log file produced in the project directory.")
            return False
        except Exception:
            logger.error("Could not read file", exc_info=True)
            messagebox.showerror("JSON Error", "Please consult the log file produced in the project directory.")
            return False

        try:
            project = TinoProject.model_validate(raw)
        except ValidationError as e:
            errors = []
            for err in e.errors():
                loc = " → ".join(str(part) for part in err["loc"])
                errors.append(f"  • {loc}: {err['msg']}")
            detail = "\n".join(errors)
            logger.error(f"Validation Error: {detail}")
            messagebox.showerror(
                "Validation Error",
                f"Please consult the log file produced in the project directory."
            )
            return False

        self.data = project
        self.current_path = filepath

        self._normalize_paths(filepath, to_absolute=True)
        
        setup_project_logger(filepath, self.data.app_name)
        logger.info(f"Project loaded successfully from {filepath}")
        messagebox.showinfo("Import project", "Project imported successfully!")
        return True

    def _normalize_paths(self, project_path: str, to_absolute: bool):
        """Normalizes path fields in the project model to be relative or absolute.

        Args:
            project_path: Path of the project file, used as base directory.
            to_absolute: If True, makes paths absolute. Otherwise, relative.
        """
        base_dir = os.path.dirname(os.path.abspath(project_path))
        
        def transform(path: str | None) -> str | None:
            if path is None or path == "No file selected":
                return path
            if not path:
                return ""
            try:
                if to_absolute:
                    if not os.path.isabs(path):
                        return os.path.normpath(os.path.join(base_dir, path))
                else:
                    if os.path.isabs(path):
                        return os.path.relpath(path, base_dir)
            except Exception:
                pass
            return path

        d = self.data
        d.executable = transform(d.executable) or ""
        d.icon = transform(d.icon) or ""
        d.license_file = transform(d.license_file)
        d.pre_install_information_file = transform(d.pre_install_information_file)
        d.post_install_information_file = transform(d.post_install_information_file)
        d.installer_icon = transform(d.installer_icon)
        d.uninstaller_icon = transform(d.uninstaller_icon)
        
        d.files = [transform(f) or "" for f in d.files]
        d.folders = [transform(f) or "" for f in d.folders]
        
        for prof in d.installer_profiles.values():
            prof.pre_install_script = transform(prof.pre_install_script) or ""
            prof.post_install_script = transform(prof.post_install_script) or ""
            prof.pre_uninstall_script = transform(prof.pre_uninstall_script) or ""
            prof.post_uninstall_script = transform(prof.post_uninstall_script) or ""
            for task in prof.additional_tasks:
                task.value = transform(task.value) or ""
                
        for loc in d.localizations.values():
            loc.license_file = transform(loc.license_file) or ""
            loc.pre_install_information_file = transform(loc.pre_install_information_file) or ""
            loc.post_install_information_file = transform(loc.post_install_information_file) or ""

    def save(self, filepath: str | None = None, silent: bool = False) -> bool:
        """Saves the project data to disk as a JSON file.

        Args:
            filepath: Optional path to save to. If omitted, uses current_path or prompts.
            silent: If True, avoids showing success popups.

        Returns:
            True if saving succeeded, otherwise False.
        """
        if not filepath and self.current_path:
            filepath = self.current_path
        if not filepath:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".tino",
                filetypes=[("Tino Project", "*.tino")],
                title="Save Tino project"
            )
            if not filepath:
                return False

        try:
            self._normalize_paths(filepath, to_absolute=False)
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(self.data.model_dump(mode="json"), f, indent=4)
            finally:
                self._normalize_paths(filepath, to_absolute=True)

            if self.current_path != filepath:
                setup_project_logger(filepath, self.data.app_name)
            self.current_path = filepath
            logger.info(f"Project saved successfully to {filepath}")
            if not silent:
                messagebox.showinfo("Project saved", "Project saved successfully!")
            return True
        except Exception:
            logger.error("Could not save file", exc_info=True)
            messagebox.showerror("Save Error", "Please consult the log file produced in the project directory.")
            return False