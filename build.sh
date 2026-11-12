#!/bin/sh
# Assemble shotrover.py from the source parts in src/ and byte-compile it as a syntax check.
# Usage: ./build.sh            (writes ./shotrover.py)
set -e
cd "$(dirname "$0")"
PARTS="p1 p1b p1c p1d p1e p2 p2b p2c p2d p2e p3b p3c p3d p3e p3f p3g p3 p4 p5"
: > shotrover.py.new
for p in $PARTS; do cat "src/$p.py" >> shotrover.py.new; done
PY=$(command -v python3.11 || command -v python3)
"$PY" -m py_compile shotrover.py.new
mv shotrover.py.new shotrover.py
chmod +x shotrover.py
echo "built shotrover.py ($(wc -l < shotrover.py) lines) with $PY"
