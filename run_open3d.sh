#!/bin/bash
# Pfad zu deiner Miniconda/Anaconda-Installation
source ~/miniconda3/etc/profile.d/conda.sh

# Aktiviert deine Umgebung
conda activate open3d_env

# Zwingt das gesamte Terminal und alle Unterprozesse in den X11/XWayland-Modus
export GLFW_PLATFORM=x11
export QT_QPA_PLATFORM=xcb

# Startet das Python-Skript (Ersetze simeono falls nötig)
python /home/simeono/Open3D/open3d_script.py

