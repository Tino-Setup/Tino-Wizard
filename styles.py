"""
Module for configuring the application's look and feel using tkinter.ttk styles.
"""
from tkinter.ttk import Style

MAIN_COLOR = "#9a89b0"
ACCENT_COLOR = "#8b79a1"


def get_style():
    """
    Creates and configures a ttk Style object for the application.

    Returns:
        Style: The configured ttk Style object.
    """
    style = Style()
    style.theme_use("clam")

    style.configure("Content.TFrame", background="white")
    style.configure("Content.TLabel", background="white", foreground="black", font=("Sans", 11))
    style.configure("Title.TLabel", background="white", foreground=MAIN_COLOR, font=("Sans", 16, "bold"))
    style.configure("Content.TButton", background="white", foreground="black", font=("Sans", 11, "bold"))
    style.configure("Accent.TButton", background=MAIN_COLOR, foreground="white", font=("Sans", 11, "bold"))
    style.map("Accent.TButton", background=[("active", ACCENT_COLOR)])

    style.configure("Content.TRadiobutton", background="white", foreground="black", font=("Sans", 11))
    style.map("Content.TRadiobutton",
              background=[("active", "white")],
              foreground=[("active", MAIN_COLOR)])

    style.configure("TNotebook", background="white", borderwidth=0)
    style.configure("TNotebook.Tab",
                    background="#f5f5f5",
                    foreground="#333333",
                    padding=[15, 8],
                    font=("Sans", 10, "bold"))
    style.map("TNotebook.Tab",
              background=[("selected", MAIN_COLOR)],
              foreground=[("selected", "white")])

    return style