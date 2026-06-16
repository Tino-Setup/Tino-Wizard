import os
import shutil
from pathlib import Path
import subprocess
from logger_config import get_logger

logger = get_logger()


class DesktopFile:
    """Represents and manages a Linux .desktop launcher file."""

    def __init__(self, path: str = "", name: str = "", exePath: str = "", mainArgs: str = ""):
        """Initializes a DesktopFile instance.

        Args:
            path: Directory path where the .desktop file should be saved.
            name: Human-readable name of the application.
            exePath: Path to the executable binary or script.
            mainArgs: Arguments to append to the Exec command.
        """
        self.name = name
        self.exePath = exePath
        self.mainArgs = mainArgs
        self.path = os.path.join(path or ".", f"{name}.desktop")

        self.attributes = {}
        self.actions = []
        self.custom_entries = []

    def setComment(self, comment):
        """Sets the Comment attribute of the desktop entry.

        Args:
            comment: Description text.
        """
        self.attributes["Comment"] = comment

    def setIcon(self, pathToIcon):
        """Sets the Icon attribute of the desktop entry.

        Args:
            pathToIcon: Path or name of the icon file.
        """
        self.attributes["Icon"] = pathToIcon

    def setCategories(self, categories):
        """Sets the Categories attribute of the desktop entry.

        Args:
            categories: Semicolon-separated category list.
        """
        self.attributes["Categories"] = categories

    def setCustom(self, key, value):
        """Sets a custom attribute of the desktop entry.

        Args:
            key: Desktop entry key name.
            value: Value of the key.
        """
        if key and value:
            self.attributes[key] = value

    def addCustomEntry(self, short_action_name: str):
        """Adds an additional action entry (Desktop Action) to the file.

        Args:
            short_action_name: Simple action name identifier.
        """
        if not short_action_name:
            return
        clean_name = "".join(c if c.isalnum() or c == '-' else '-' for c in short_action_name.replace(" ", "-"))
        if clean_name and clean_name not in self.actions:
            self.actions.append(clean_name)
            self.custom_entries.append({"name": clean_name, "attributes": {}})

    def setCustomEntryAttribute(self, entry_index: int, key: str, value: str):
        """Sets an attribute on a specific custom action entry.

        Args:
            entry_index: Index of the custom entry.
            key: Desktop Action attribute key.
            value: Attribute value.
        """
        if 0 <= entry_index < len(self.custom_entries):
            self.custom_entries[entry_index]["attributes"][key] = value

    def save(self) -> bool:
        """Saves the desktop file configuration and runs desktop-file-validate.

        Returns:
            True if saving and validation succeeded, otherwise False.
        """
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write("[Desktop Entry]\n")
                f.write("Type=Application\n")
                f.write(f"Name={self.name}\n")
                
                full_exec = self.exePath
                if self.mainArgs:
                    full_exec += f" {self.mainArgs}"
                f.write(f"Exec={full_exec}\n")

                for key, value in self.attributes.items():
                    if value:
                        f.write(f"{key}={value}\n")

                if self.actions:
                    f.write("Actions=" + ";".join(self.actions) + ";\n")

                for entry in self.custom_entries:
                    f.write(f"\n[Desktop Action {entry['name']}]\n")
                    for key, value in entry["attributes"].items():
                        if value:
                            if key == "Exec":
                                f.write(f"{key}={self.exePath} {value}\n")
                            else:
                                f.write(f"{key}={value}\n")

            os.chmod(self.path, 0o644)
            logger.info(f"Successfully saved desktop file at {self.path}")
        except OSError as e:
            logger.error(f"OSError while saving desktop file: {e}", exc_info=True)
            return False

        if not shutil.which("desktop-file-validate"):
             logger.warning("desktop-file-validate not found, skipping validation.")
             return True

        try:
            logger.info(f"Validating desktop file: {self.path}")
            subprocess.run(
                ["desktop-file-validate", self.path],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("Desktop file validation successful.")
            return True
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else e.stdout.strip()
            logger.error(f"Desktop file validation failed:\n{error_msg}")
            Path(self.path).unlink(missing_ok=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error during desktop file validation: {e}")
            Path(self.path).unlink(missing_ok=True)
            return False