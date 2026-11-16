#!/bin/sh
# Assemble shotrover.py from the source parts in src/ and byte-compile it as a syntax check.
# Usage: ./build.sh            (writes ./shotrover.py)
set -e
cd "$(dirname "$0")"
# The order matters and is fixed here, not by the file names: the parts share one namespace, a class must be
# defined before one that inherits from it, and mainwindow.py ENDS INSIDE class MainWindow, which
# mainwindow_actions.py continues (it then holds the application class and main()).
PARTS="core decoders diagnostics fileindex crashreport toolkit dialogs batchrename reportdialog largefiles icons_theme widgets preview_3d_video importers scenes shaders sceneobjects folderview mainwindow mainwindow_actions"
: > shotrover.py.new
for p in $PARTS; do cat "src/$p.py" >> shotrover.py.new; done
PY=$(command -v python3.11 || command -v python3)
"$PY" -m py_compile shotrover.py.new
mv shotrover.py.new shotrover.py
chmod +x shotrover.py
echo "built shotrover.py ($(wc -l < shotrover.py) lines) with $PY"
