import logging
import os
import tempfile
from Elevation import check_and_elevate

logger = logging.getLogger("TinoWizard")
logger.setLevel(logging.INFO)
logger.propagate = False 

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app_log_path = os.path.join(os.path.dirname(__file__), "tinowizard.log")
try:
    app_handler = logging.FileHandler(app_log_path)
    app_handler.setFormatter(formatter)
    logger.addHandler(app_handler)
except PermissionError:
    try:
        check_and_elevate()
    except Exception:
        pass

    temp_log_path = os.path.join(tempfile.gettempdir(), "tinowizard.log")
    try:
        app_handler = logging.FileHandler(temp_log_path)
        app_handler.setFormatter(formatter)
        logger.addHandler(app_handler)
    except Exception:
        pass

_project_handler = None
_current_project_log_path = None

def setup_project_logger(project_file_path: str, app_name: str = ""):
    """Adds a FileHandler to log to the project directory.

    Removes the previous project handler if it exists.

    Args:
        project_file_path: Absolute path to the .tino project file.
        app_name: The name of the application to format the log file name.
    """
    global _project_handler
    global _current_project_log_path
    
    if not project_file_path:
        return
        
    project_dir = os.path.dirname(os.path.abspath(project_file_path))
    
    safe_app_name = "".join(c if c.isalnum() else "_" for c in app_name).strip("_") if app_name else ""
    log_filename = f"{safe_app_name}_wizard.log" if safe_app_name else "wizard_project.log"
    project_log_path = os.path.join(project_dir, log_filename)
    
    if project_log_path == _current_project_log_path:
        return

    if os.path.abspath(project_log_path) == os.path.abspath(app_log_path):
        return
        
    if _project_handler:
        logger.removeHandler(_project_handler)
        _project_handler.close()
        _project_handler = None
        
    try:
        _project_handler = logging.FileHandler(project_log_path)
        _project_handler.setFormatter(formatter)
        logger.addHandler(_project_handler)
        _current_project_log_path = project_log_path
        logger.info(f"Project logger initialized at {project_log_path}")
    except Exception as e:
        logger.error(f"Failed to set up project logger at {project_log_path}: {e}")
        _current_project_log_path = None

def get_logger() -> logging.Logger:
    """Retrieves the application wide logger instance.

    Returns:
        The configured logging.Logger instance for TinoWizard.
    """
    return logger

def get_project_log_path() -> str | None:
    """Gets the path of the current active project log file.

    Returns:
        Path to the project log file or None if not set.
    """
    return _current_project_log_path
