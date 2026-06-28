import os
import json
import re
import threading
import shutil
import sys
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from desktopfile import DesktopFile
from pages import WelcomePage, ProjectInfoPage, FilesPage, InstallerOptionsPage, SummaryPage, BuildOutputPage
from styles import get_style
from config import ConfigManager, LocalizationEntry
from compression import compress_project
from logger_config import get_logger, get_project_log_path
from TranslationTable import TranslationTable


logger = get_logger()


class App(tk.Tk):
    """
    Main application class for the Tino Wizard installer generator.
    Handles the main window, navigation between pages, and the overall build process.
    """
    PAGE_ORDER = [
        "WelcomePage",
        "ProjectInfoPage",
        "FilesPage",
        "InstallerOptionsPage",
        "SummaryPage",
    ]

    def __init__(self):
        """Initialize the main application window and set up UI components."""
        super().__init__(className="Tinowizard")
        self._style = get_style()

        self.title("Tino Wizard")
        self.geometry("920x620")
        self.resizable(False, False)

        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)
        
        self.project = ConfigManager()

        icon_path = os.path.join(os.path.dirname(__file__), "Tino Wizard.png")
        if os.path.isfile(icon_path):
            try:
                self.wm_iconphoto(True, tk.PhotoImage(file=icon_path))
            except tk.TclError:
                pass

        self.main_area = ttk.Frame(self, style="Content.TFrame")
        self.main_area.pack(side="right", fill="both", expand=True)

        self.nav_frame = ttk.Frame(self.main_area, style="Content.TFrame")
        self.nav_frame.pack(side="bottom", fill="x", padx=30, pady=15)

        self.content = ttk.Frame(self.main_area, style="Content.TFrame")
        self.content.pack(fill="both", expand=True, padx=30, pady=20)

        self.btn_back = ttk.Button(
            self.nav_frame, text="Back",
            command=self.previous_page, style="Content.TButton"
        )
        self.btn_generate = ttk.Button(
            self.nav_frame, text="Generate Installer",
            command=self.generate_installer, style="Accent.TButton"
        )
        self.btn_next = ttk.Button(
            self.nav_frame, text="Next",
            command=self.next_page, style="Content.TButton"
        )

        self.current_page_name = ""
        self.current_page = None

        self._create_pages()
        self.show_page("WelcomePage")

    def _create_pages(self):
        """Instantiate all the wizard pages and store them in a dictionary."""
        self.pages = {
            "WelcomePage": WelcomePage(self.content, self),
            "ProjectInfoPage": ProjectInfoPage(self.content, self),
            "FilesPage": FilesPage(self.content, self),
            "InstallerOptionsPage": InstallerOptionsPage(self.content, self),
            "SummaryPage": SummaryPage(self.content, self),
            "BuildOutputPage": BuildOutputPage(self.content, self),
        }

    def open_translations(self):
        """Open the translation management window."""
        logger.info("User requested translation management")
        TranslationTable(self, self.project.data)


    def update_menu(self):
        """Update the menu bar based on the current page and project state."""
        try:
            self.menu_bar.index("Localization")
            menu_exists = True
        except tk.TclError:
            menu_exists = False

        should_show = (
            self.project.current_path and 
            self.current_page_name not in ("WelcomePage", "SummaryPage", "BuildOutputPage")
        )

        if menu_exists and not should_show:
            self.menu_bar.delete("Localization")
        elif not menu_exists and should_show:
            self.menu_bar.add_command(label="Localization", command=self.open_translations)

    def show_page(self, page_name: str):
        """
        Navigate to and display the specified page.
        
        Args:
            page_name: The name of the page to show.
        """
        if self.current_page:
            self.current_page.pack_forget()
        logger.info(f"Navigating to page: {page_name}")
        self.current_page_name = page_name
        self.current_page = self.pages[page_name]
        self.current_page.pack(fill="both", expand=True)

        self.current_page.refresh()
        self._update_navigation_buttons()
        self.update_menu()

    def _update_navigation_buttons(self):
        """Update the visibility of navigation buttons (Back, Next, Generate) based on the current page."""
        self.btn_back.pack_forget()
        self.btn_generate.pack_forget()
        self.btn_next.pack_forget()
        
        if self.current_page_name == "WelcomePage":
            return
            
        self.btn_back.pack(side="left", padx=5)
        
        if self.current_page_name == "SummaryPage":
            self.btn_generate.pack(side="right", padx=5)
        else:
            self.btn_next.pack(side="right", padx=5)

    def previous_page(self):
        """Navigate to the previous page in the wizard."""
        try:
            idx = self.PAGE_ORDER.index(self.current_page_name)
            if idx > 0:
                self.show_page(self.PAGE_ORDER[idx - 1])
        except ValueError:
            pass

    def next_page(self):
        """Navigate to the next page in the wizard by triggering the current page's on_next method."""
        if self.current_page:
            self.current_page.on_next()

    def generate_installer(self):
        """Validate project data, generate desktop files, configure uninstaller, and start the build thread."""
        data = self.project.data
        profiles = data.installer_profiles
        tar_icon_path = None

        if not self.project.current_path:
             logger.warning("Attempted to generate installer without saving project first.")
             messagebox.showerror("Generation Error", "Please save your project first before generating an installer.")
             return

        if not data.executable:
             messagebox.showerror("Generation Error", "No executable source selected. Please select one in the 'Installer Options' page.")
             return

        missing = []
        for f in data.files:
            if not os.path.exists(f):
                missing.append(f"File: {f}")
        for d in data.folders:
            if not os.path.isdir(d):
                missing.append(f"Folder: {d}")

        file_checks = [
            ("Executable source", data.executable),
            ("License", data.license_file),
            ("Pre-install info", data.pre_install_information_file),
            ("Post-install info", data.post_install_information_file),
            ("Installer icon", data.installer_icon),
            ("Uninstaller icon", data.uninstaller_icon)
        ]

        custom_prof_check = data.installer_profiles.get("custom")
        if custom_prof_check:
            file_checks.extend([
                ("Pre-install script", custom_prof_check.pre_install_script),
                ("Post-install script", custom_prof_check.post_install_script),
                ("Pre-uninstall script", custom_prof_check.pre_uninstall_script),
                ("Post-uninstall script", custom_prof_check.post_uninstall_script)
            ])

        for loc in data.localizations.values():
            file_checks.extend([
                ("Localized license", loc.license_file),
                ("Localized pre-install info", loc.pre_install_information_file),
                ("Localized post-install info", loc.post_install_information_file)
            ])

        for label, path in file_checks:
            if path and not os.path.isfile(path):
                missing.append(f"{label}: {path}")

        if missing:
            detail = "\n".join(missing)
            logger.error(f"Pre-build validation failed. Missing files:\n{detail}")
            messagebox.showerror("Missing Files", f"The following files or folders could not be found:\n\n{detail}")
            return

        project_dir = os.path.dirname(self.project.current_path)
        logger.info(f"Generating installer for project at {project_dir}")



        desktop = data.desktop
        desktop_enabled = data.desktop.enabled

        app_slug = re.sub(r'[^\w\-.]', '_', data.app_name)

        if desktop_enabled:
            df = DesktopFile(project_dir, data.app_name, data.exe_path, desktop.executable_args)
            df.path = os.path.join(project_dir, f"{app_slug}.desktop")

            df.setIcon(data.icon_path)
            df.setComment(desktop.comment)
            df.setCategories(desktop.categories)

            for pair in desktop.extra_keys:
                if pair.key:
                    df.setCustom(pair.key, pair.value)

            for entry in desktop.extra_entries:
                action_name = entry.name.strip()
                if action_name:
                    df.addCustomEntry(action_name)
                    for attr in entry.attributes:
                        if attr.key and attr.value:
                            df.setCustomEntryAttribute(
                                len(df.custom_entries) - 1,
                                attr.key,
                                attr.value,
                            )

            if not df.save():
                logger.error("Failed to create or validate the .desktop file.")
                messagebox.showerror(
                    "Desktop File Error",
                    "Please consult the log file produced in the project directory."
                )
                return
            logger.info("Successfully created and validated .desktop file.")

        extra_files = []
        if desktop_enabled:
            extra_files.append(Path(df.path))

        custom_prof = data.installer_profiles.get("custom")
        is_gui = data.app_type == "GUI"
        
        uninstaller_icon_src = data.uninstaller_icon if data.uninstaller_icon else os.path.join(os.path.dirname(__file__), "Uninstaller", "Tino Uninstaller.png")
        
        uninstaller_icon_deployed_path = ""
        if data.icon_path:
            base_icon, _ = os.path.splitext(data.icon_path)
            _, ext = os.path.splitext(uninstaller_icon_src)
            uninstaller_icon_deployed_path = f"{base_icon}-uninstaller{ext}"
        
        uninstaller_bin_dir = os.path.dirname(data.exe_path)
        uninstaller_exec_path = os.path.join(uninstaller_bin_dir, f"{app_slug}-uninstaller")
        
        uninstaller_config = {
            "Application Version": data.version,
            "Application Author": data.author,
            "Application Website": data.homepage,
            "Application Icon": os.path.basename(data.uninstaller_icon) if data.uninstaller_icon else "Tino Uninstaller.png",
            "Application Installation Path": data.install_dir,
            "Application Executable Path": data.exe_path,
            "Application Icon Path": data.icon_path if is_gui else "",
            "Application Desktop Path": f"{data.desktop_path}/{app_slug}.desktop" if is_gui else "",
            "Application Pre Uninstallation Script": os.path.basename(custom_prof.pre_uninstall_script) if custom_prof and custom_prof.pre_uninstall_script else "",
            "Application Post Uninstallation Script": os.path.basename(custom_prof.post_uninstall_script) if custom_prof and custom_prof.post_uninstall_script else "",
            "Application Name Slug": app_slug,
            "Application Uninstaller Desktop Path": f"{data.desktop_path}/{app_slug}-uninstaller.desktop",
            "Application Uninstaller Icon Path": uninstaller_icon_deployed_path,
            "Localization": {}
        }
        
        for lang_code, loc in data.localizations.items():
            loc_dict = loc if isinstance(loc, dict) else loc.model_dump()
            uninstaller_config["Localization"][lang_code] = {
                "Language Label": loc_dict.get("language_label") or lang_code,
                "Application Name": loc_dict.get("app_name") or data.app_name,
                "Application Description": loc_dict.get("description") or data.description
            }
            
        uninstaller_tino_path = os.path.join(project_dir, "uninstaller.tino")
        try:
            with open(uninstaller_tino_path, "w", encoding="utf-8") as f:
                json.dump(uninstaller_config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving uninstaller config: {e}", exc_info=True)

        uninstaller_df = DesktopFile(project_dir, f"{data.app_name} Uninstaller", uninstaller_exec_path, "")
        uninstaller_df.path = os.path.join(project_dir, f"{app_slug}-uninstaller.desktop")
        uninstaller_df.setCustom("StartupWMClass", "uninstaller")
        
        if uninstaller_icon_deployed_path:
            uninstaller_df.setIcon(uninstaller_icon_deployed_path)
        else:
            uninstaller_df.setIcon(uninstaller_icon_src)
            
        if os.path.exists(uninstaller_icon_src):
            _, ext = os.path.splitext(uninstaller_icon_src)
            tar_icon_path = os.path.join(project_dir, f"{app_slug}-uninstaller{ext}")
            try:
                shutil.copy2(uninstaller_icon_src, tar_icon_path)
                extra_files.append(Path(tar_icon_path))
            except Exception as e:
                logger.error(f"Failed to copy uninstaller icon for packaging: {e}")
            
        uninstaller_df.setComment(f"Uninstall {data.app_name}")
        if uninstaller_df.save():
            extra_files.append(Path(uninstaller_df.path))
        else:
            logger.error("Failed to create uninstaller .desktop file.")

        self.show_page("BuildOutputPage")
        self.btn_back.pack_forget()
        self.btn_generate.pack_forget()
        self.btn_next.pack_forget()
        self.update_idletasks()
        
        build_page = self.pages["BuildOutputPage"]
        assert isinstance(build_page, BuildOutputPage)
        build_page.clear()
        
        def run_build():
            original_stdout = sys.stdout
            original_stderr = sys.stderr

            build_log_path = get_project_log_path()
            build_log_file = open(build_log_path, "a", encoding="utf-8") if build_log_path else None
            
            class OutputRedirector:
                def write(self, string):
                    if string.strip('\r\n'):
                        try:
                            build_page.app.after(0, build_page.append_output, string)
                        except RuntimeError:
                            pass
                        if build_log_file:
                            build_log_file.write(string)
                            build_log_file.flush()
                def flush(self):
                    if build_log_file:
                        build_log_file.flush()
                
            redirector = OutputRedirector()
            sys.stdout = redirector
            sys.stderr = redirector
            
            df_path = df.path if desktop_enabled else None
            uninstaller_df_path = uninstaller_df.path

            try:
                self._run_build_thread(project_dir, data, uninstaller_icon_deployed_path, app_slug, extra_files, uninstaller_tino_path, df_path, uninstaller_df_path, custom_prof, is_gui, tar_icon_path=tar_icon_path)
            except Exception as e:
                logger.error(f"Build thread failed: {e}", exc_info=True)
                self.after(0, lambda err=str(e): messagebox.showerror("Build Error", f"An unexpected error occurred:\n{err}"))
            finally:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                if build_log_file:
                    build_log_file.close()
                self.after(0, self._on_build_finished)
                
        t = threading.Thread(target=run_build, daemon=True)
        t.start()

    def _on_build_finished(self):
        """Callback executed when the build process completes, navigating to the summary page."""
        self.show_page("SummaryPage")
        
    def _run_build_thread(self, project_dir, data, uninstaller_icon_deployed_path, app_slug, extra_files, uninstaller_tino_path, df_path, uninstaller_df_path, custom_prof, is_gui, tar_icon_path=None):
        """
        Execute the complete build process in a separate thread.
        
        This involves building the uninstaller, creating the project archive, preparing installer configuration,
        and finally building the installer executable.
        """
        build_page = self.pages["BuildOutputPage"]
        assert isinstance(build_page, BuildOutputPage)
        
        self.after(0, build_page.set_stage, "Stage 1/4: Building Uninstaller...")
        uninstaller_binary_path = os.path.join(project_dir, f"{app_slug}-uninstaller")
        build_success = self._build_uninstaller(project_dir, data, uninstaller_tino_path, custom_prof, app_slug)

        if build_success and os.path.exists(uninstaller_binary_path):
            extra_files.append(Path(uninstaller_binary_path))
        if not build_success:
            return
        
        ext_map = {
            "gzip": ".tar.gz",
            "bz2": ".tar.bz2",
            "lzma": ".tar.xz"
        }
        extension = ext_map.get(data.compression_type, ".tar.gz")
        archive_name = f"installer{extension}"
        output_path = os.path.join(project_dir, archive_name)

        try:
            self.after(0, build_page.set_stage, "Stage 2/4: Creating Archive...")
            logger.info(f"Starting compression to {output_path}")
            compress_project(data, output_path, extra_files=extra_files)
            if df_path:
                Path(df_path).unlink(missing_ok=True)
            if uninstaller_df_path:
                Path(uninstaller_df_path).unlink(missing_ok=True)
            Path(uninstaller_tino_path).unlink(missing_ok=True)
            Path(uninstaller_binary_path).unlink(missing_ok=True)
            if tar_icon_path:
                Path(tar_icon_path).unlink(missing_ok=True)
            logger.info("Compression completed successfully.")
        except Exception as e:
            logger.error("Failed to compress files", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Compression Error", f"Please consult the log file produced in the project directory."))
            return

        self.after(0, build_page.set_stage, "Stage 3/4: Preparing Installer Configuration...")
        installer_config = {
            "Application Version": data.version,
            "Application Author": data.author,
            "Application Website": data.homepage,
            "Application Icon": os.path.basename(data.installer_icon) if data.installer_icon else "Tino Installer.png",
            "Application Installation Path": data.install_dir,
            "Application Executable Path": data.exe_path,
            "Application Icon Path": data.icon_path if is_gui else "",
            "Application Desktop Path": data.desktop_path,
            "Application Executable Source": os.path.basename(data.executable),
            "Application Icon Source": os.path.basename(data.icon) if data.icon else "",
            "Application Desktop Source": f"{app_slug}.desktop" if is_gui else "",
            "Application Compression Type": data.compression_type,
            "Application Name Slug": app_slug,
            "Application Uninstaller Icon Path": uninstaller_icon_deployed_path,
            "Application Pre Installation Script": os.path.basename(custom_prof.pre_install_script) if custom_prof and custom_prof.pre_install_script else "",
            "Application Post Installation Script": os.path.basename(custom_prof.post_install_script) if custom_prof and custom_prof.post_install_script else "",
            "Localization": {}
        }

        if not data.localizations:
            data.localizations["en_US"] = LocalizationEntry(
                language_label="English (United States)",
                app_name=data.app_name,
                description=data.description,
                license_file=os.path.basename(data.license_file) if data.license_file else "",
                pre_install_information_file=os.path.basename(data.pre_install_information_file) if data.pre_install_information_file else "",
                post_install_information_file=os.path.basename(data.post_install_information_file) if data.post_install_information_file else "",
                additional_tasks={t.key: t.key for t in custom_prof.additional_tasks} if custom_prof else {}
            )

        for lang_code, loc in data.localizations.items():
            loc_dict = loc if isinstance(loc, dict) else loc.model_dump()
            
            installer_config["Localization"][lang_code] = {
                "Language Label": loc_dict.get("language_label") or lang_code,
                "Application Name": loc_dict.get("app_name") or data.app_name,
                "Application Description": loc_dict.get("description") or data.description,
                "Application Pre Install Information": os.path.basename(loc_dict.get("pre_install_information_file")) if loc_dict.get("pre_install_information_file") else os.path.basename(data.pre_install_information_file) if data.pre_install_information_file else "",
                "Application License": os.path.basename(loc_dict.get("license_file")) if loc_dict.get("license_file") else os.path.basename(data.license_file) if data.license_file else "",
                "Application Post Install Information": os.path.basename(loc_dict.get("post_install_information_file")) if loc_dict.get("post_install_information_file") else os.path.basename(data.post_install_information_file) if data.post_install_information_file else "",
                "Application Additional Tasks": [
                    {"Name": loc_dict.get("additional_tasks", {}).get(t.key, t.key), "Command": os.path.basename(t.value) if t.value else ""}
                    for t in (custom_prof.additional_tasks if custom_prof else [])
                ]
            }

        try:
            config_filename = "installer.tino"
            installer_config_path = os.path.join(project_dir, config_filename)
            logger.info(f"Saving installer config to {installer_config_path}")
            with open(installer_config_path, "w", encoding="utf-8") as f:
                json.dump(installer_config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving installer config: {e}", exc_info=True)
            return
            
        self.after(0, build_page.set_stage, "Stage 4/4: Building Installer...")
        success = self._build_installer(project_dir, data, archive_name, installer_config_path)
        if not success:
            return

        self.after(0, build_page.set_stage, "Build completed successfully!")



        def show_success():
            messagebox.showinfo(
                "Success!",
                "Installer Generated! \n\n"
                f"Executable: {data.app_name} setup\n"
            )
        self.after(0, show_success)
        logger.info("Installer generated successfully!")



    def _get_pyinstaller_cmd(self):
        """Returns the base PyInstaller command as a list."""
        if getattr(sys, 'frozen', False):
            venv_bin = os.path.join(os.path.dirname(sys.executable), "tinowizard", "bin", "pyinstaller")
            return [venv_bin] if os.path.isfile(venv_bin) else ["pyinstaller"]
        else:
            return [sys.executable, "-m", "PyInstaller"]

    def _check_pyinstaller_available(self):
        """Check if PyInstaller is available. Shows error and returns False if not."""
        cmd = self._get_pyinstaller_cmd()
        if getattr(sys, 'frozen', False) and cmd == ["pyinstaller"] and not shutil.which("pyinstaller"):
            self.after(0, lambda: messagebox.showerror("Generation Error", "PyInstaller command not found. Please ensure the 'tinowizard' venv exists next to the executable, or pyinstaller is in your PATH."))
            return False
        return True

    def _build_uninstaller(self, project_dir, data, uninstaller_tino_path, custom_prof, app_slug):
        """
        Build the uninstaller binary using PyInstaller.
        
        Args:
            project_dir: The project directory path.
            data: The project configuration data.
            uninstaller_tino_path: Path to the uninstaller configuration JSON.
            custom_prof: Custom installer profile data, if any.
            app_slug: Slugified application name.
            
        Returns:
            bool: True if build was successful, False otherwise.
        """
        if not self._check_pyinstaller_available():
            return False
        cmd = self._get_pyinstaller_cmd()

        logger.info("Building Uninstaller binary...")
        wizard_dir = os.path.dirname(__file__)
        uninstaller_src_dir = os.path.join(wizard_dir, "Uninstaller")
        
        build_dir = os.path.join(project_dir, "_build")

        uninstaller_args = [
            os.path.join(uninstaller_src_dir, "Wizard.py"),
            "--onefile",
            "--windowed",
            "--name", f"{app_slug}-uninstaller",
            "--distpath", project_dir,
            "--workpath", build_dir,
            "--specpath", build_dir,
            "--noconfirm",
            "--strip",
            "--noupx",
        ]
        
        uninstaller_args += ["--add-data", f"{uninstaller_tino_path}:."]
        uninstaller_args += ["--add-data", f"{os.path.join(uninstaller_src_dir, 'Tino Uninstaller License')}:."]
        
        if data.uninstaller_icon:
            uninstaller_args += ["--add-data", f"{data.uninstaller_icon}:."]
        else:
            uninstaller_args += ["--add-data", f"{os.path.join(uninstaller_src_dir, 'Tino Uninstaller.png')}:."]
            
        locale_path = os.path.join(uninstaller_src_dir, "locale")
        if os.path.exists(locale_path):
            uninstaller_args += ["--add-data", f"{locale_path}:locale"]
            
        if custom_prof:
            if custom_prof.pre_uninstall_script:
                uninstaller_args += ["--add-data", f"{custom_prof.pre_uninstall_script}:."]
            if custom_prof.post_uninstall_script:
                uninstaller_args += ["--add-data", f"{custom_prof.post_uninstall_script}:."]

        cmd.extend(uninstaller_args)

        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if process.stdout is not None:
                for line in process.stdout:
                    sys.stdout.write(line)
                process.wait()
            
            if process.returncode != 0:
                raise RuntimeError(f"PyInstaller failed with return code {process.returncode}")

            shutil.rmtree(build_dir, ignore_errors=True)
            spec_uninst = os.path.join(project_dir, f"{app_slug}-uninstaller.spec")
            if os.path.exists(spec_uninst): os.remove(spec_uninst)
            return True
        except Exception as e:
            logger.error(f"Uninstaller PyInstaller build failed: {e}", exc_info=True)
            self.after(0, lambda err=str(e): messagebox.showerror("Build Error", f"Failed to build uninstaller binary: {err}"))
            return False

    def _build_installer(self, project_dir, data, archive_name, installer_config_path):
        """
        Build the installer binary using PyInstaller.
        
        Args:
            project_dir: The project directory path.
            data: The project configuration data.
            archive_name: The name of the compressed project archive.
            installer_config_path: Path to the installer configuration JSON.
            
        Returns:
            bool: True if build was successful, False otherwise.
        """
        if not self._check_pyinstaller_available():
            return False
        cmd = self._get_pyinstaller_cmd()

        logger.info("Building Installer binary...")
        custom_prof = data.installer_profiles.get("custom")
        wizard_dir = os.path.dirname(__file__)
        installer_src_dir = os.path.join(wizard_dir, "Installer")

        build_dir = os.path.join(project_dir, "_build")

        installer_args = [
            os.path.join(installer_src_dir, "Wizard.py"),
            "--onefile",
            "--windowed",
            "--name", f"{data.app_name} setup",
            "--distpath", project_dir,
            "--workpath", build_dir,
            "--specpath", build_dir,
            "--noconfirm",
            "--strip",
            "--noupx",
        ]
        
        installer_args += ["--add-data", f"{os.path.join(project_dir, archive_name)}:."]
        installer_args += ["--add-data", f"{installer_config_path}:."]
        installer_args += ["--add-data", f"{os.path.join(installer_src_dir, 'Tino Installer License')}:."]
        
        if data.installer_icon:
            installer_args += ["--add-data", f"{data.installer_icon}:."]
        else:
            installer_args += ["--add-data", f"{os.path.join(installer_src_dir, 'Tino Installer.png')}:."]
            
        locale_path = os.path.join(installer_src_dir, "locale")
        if os.path.exists(locale_path):
            installer_args += ["--add-data", f"{locale_path}:locale"]
            
        if custom_prof:
            if custom_prof.pre_install_script:
                installer_args += ["--add-data", f"{custom_prof.pre_install_script}:."]
            if custom_prof.post_install_script:
                installer_args += ["--add-data", f"{custom_prof.post_install_script}:."]
        
        if data.license_file:
            installer_args += ["--add-data", f"{data.license_file}:."]
        if data.pre_install_information_file:
            installer_args += ["--add-data", f"{data.pre_install_information_file}:."]
        if data.post_install_information_file:
            installer_args += ["--add-data", f"{data.post_install_information_file}:."]
            
        for loc in data.localizations.values():
            if isinstance(loc, dict):
                lic_file = loc.get("license_file")
                pre_info = loc.get("pre_install_information_file")
                post_info = loc.get("post_install_information_file")
            else:
                lic_file = loc.license_file
                pre_info = loc.pre_install_information_file
                post_info = loc.post_install_information_file
            if lic_file: installer_args += ["--add-data", f"{lic_file}:."]
            if pre_info: installer_args += ["--add-data", f"{pre_info}:."]
            if post_info: installer_args += ["--add-data", f"{post_info}:."]
            
        cmd.extend(installer_args)
            
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if process.stdout is not None:
                for line in process.stdout:
                    sys.stdout.write(line)
                process.wait()
            
            if process.returncode != 0:
                raise RuntimeError(f"PyInstaller failed with return code {process.returncode}")
        except Exception as e:
            logger.error(f"Installer PyInstaller build failed: {e}", exc_info=True)
            self.after(0, lambda err=str(e): messagebox.showerror("Build Error", f"Failed to build installer binary: {err}"))
            return False

        try:
            shutil.rmtree(build_dir, ignore_errors=True)
            spec_inst = os.path.join(project_dir, f"{data.app_name} setup.spec")
            if os.path.exists(spec_inst): os.remove(spec_inst)
            
            installer_tino_path = os.path.join(project_dir, "installer.tino")
            if os.path.exists(installer_tino_path): os.remove(installer_tino_path)
            
            archive_path = os.path.join(project_dir, archive_name)
            if os.path.exists(archive_path): os.remove(archive_path)
        except Exception:
            pass

        return True


if __name__ == "__main__":
    logger.info("Starting Tino Wizard application.")

    if len(sys.argv) > 1 and os.path.isfile(sys.argv[-1]) and sys.argv[-1].endswith(".tino"):
        project_to_load = sys.argv[-1]
    else:
        project_to_load = None
        
    app = App()
    if project_to_load:
        app.project.load(project_to_load)
        app.update_menu()
    
    app.mainloop()
    logger.info("Exiting Tino Wizard application.")
