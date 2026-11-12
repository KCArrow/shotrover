#!/bin/sh
# Install Shotrover for the current user: ~/.local/bin/shotrover plus an application-menu entry.
# Usage: ./install.sh        ./install.sh --uninstall
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
BIN="$HOME/.local/bin"; APPS="$HOME/.local/share/applications"; ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"
if [ "$1" = "--uninstall" ]; then
  rm -f "$BIN/shotrover" "$APPS/shotrover.desktop" "$ICONS/shotrover.svg"
  update-desktop-database "$APPS" 2>/dev/null || true
  echo "Removed. Settings/cache left in ~/.config/shotrover and ~/.cache/shotrover."
  exit 0
fi
if ! python3 -c "import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk" 2>/dev/null; then
  echo "PyGObject/GTK 3 missing."
  echo "  Rocky/RHEL/Fedora:  sudo dnf install python3-gobject gtk3"
  echo "  Debian/Ubuntu:      sudo apt install python3-gi gir1.2-gtk-3.0"
  echo "  Arch/CachyOS:       sudo pacman -S python-gobject gtk3"
  exit 1
fi
mkdir -p "$BIN" "$APPS" "$ICONS"
cp "$HERE/packaging/shotrover.svg" "$ICONS/shotrover.svg"
gtk-update-icon-cache -q -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
cp "$HERE/shotrover.py" "$BIN/shotrover"; chmod +x "$BIN/shotrover"
sed "s|^Exec=.*|Exec=$BIN/shotrover %U|" "$HERE/packaging/shotrover.desktop" > "$APPS/shotrover.desktop"
# the app was called Kestrel before: replace that install rather than leaving two menu entries
if [ -f "$APPS/kestrel.desktop" ] || [ -f "$BIN/kestrel" ]; then
  [ "$(xdg-mime query default inode/directory 2>/dev/null)" = "kestrel.desktop" ] && xdg-mime default shotrover.desktop inode/directory 2>/dev/null || true
  rm -f "$BIN/kestrel" "$APPS/kestrel.desktop"
  echo "Replaced the old Kestrel install (settings carry over on first start)."
fi
update-desktop-database "$APPS" 2>/dev/null || true
echo "Installed: shotrover [folder]   (app menu: 'Shotrover')"
echo "Default folder handler:  xdg-mime default shotrover.desktop inode/directory"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "Note: $BIN is not on your PATH yet.";; esac
