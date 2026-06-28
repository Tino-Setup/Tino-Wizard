#!/bin/bash

set -e

VENV_DIR="tinowizard"
REQ_FILE="./_internal/requirements.txt"

if command -v apt-get >/dev/null 2>&1; then
    PM="apt"
    REFRESH_CMD="sudo apt-get update"
    INSTALL_CMD="sudo apt-get install -y"
    PYTHON_PACKAGE="python3"
    VENV_PACKAGE="python3-venv"
    TK_PACKAGE="python3-tk"

elif command -v dnf >/dev/null 2>&1; then
    PM="dnf"
    REFRESH_CMD="true"
    INSTALL_CMD="sudo dnf install -y"
    PYTHON_PACKAGE="python3"
    VENV_PACKAGE=""
    TK_PACKAGE="python3-tkinter"

elif command -v yum >/dev/null 2>&1; then
    PM="yum"
    REFRESH_CMD="true"
    INSTALL_CMD="sudo yum install -y"
    PYTHON_PACKAGE="python3"
    VENV_PACKAGE=""
    TK_PACKAGE="python3-tkinter"

elif command -v pacman >/dev/null 2>&1; then
    PM="pacman"
    REFRESH_CMD="sudo pacman -Sy"
    INSTALL_CMD="sudo pacman -S --noconfirm"
    PYTHON_PACKAGE="python"
    VENV_PACKAGE=""
    TK_PACKAGE="tk"

elif command -v zypper >/dev/null 2>&1; then
    PM="zypper"
    REFRESH_CMD="sudo zypper refresh"
    INSTALL_CMD="sudo zypper --non-interactive install"
    PYTHON_PACKAGE="python3"
    VENV_PACKAGE="python3-virtualenv"
    TK_PACKAGE="python3-tk"

else
    echo "Error: No supported package manager found (apt, dnf, yum, pacman, zypper)." >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    $REFRESH_CMD
    $INSTALL_CMD "$PYTHON_PACKAGE"
fi

if ! python3 -c "import venv" >/dev/null 2>&1; then
    if [ -n "$VENV_PACKAGE" ]; then
        $REFRESH_CMD
        $INSTALL_CMD "$VENV_PACKAGE"
    fi
fi

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    $REFRESH_CMD
    $INSTALL_CMD "$TK_PACKAGE"
fi

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

. "./$VENV_DIR/bin/activate"

pip install --no-input --upgrade pip 2>&1 || true

if [ -f "$REQ_FILE" ]; then
    pip install --no-input -r "$REQ_FILE"
fi

if [ -n "$SUDO_USER" ]; then
    REAL_USER="$SUDO_USER"
elif [ -n "$PKEXEC_UID" ]; then
    REAL_USER=$(getent passwd "$PKEXEC_UID" | cut -d: -f1)
else
    REAL_USER="$USER"
fi

REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

if [ -z "$REAL_HOME" ]; then
    REAL_HOME="$HOME"
fi

if [ -d "./_internal/Examples" ]; then
    mv ./_internal/Examples "$REAL_HOME/Tino Examples"
    chown -R "$REAL_USER":"$REAL_USER" "$REAL_HOME/Tino Examples"
fi
