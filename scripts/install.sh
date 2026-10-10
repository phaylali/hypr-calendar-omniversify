#!/bin/bash
# Manual install into $HOME, for people not using the AUR package.
# Idempotent: config is only written if missing, so rerunning never clobbers a
# personal setup. Nothing is written into a status bar's directory - the
# launcher goes on PATH under the same name the AUR package uses, so a manual
# install and a packaged install are interchangeable.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN_DIR="$HOME/.local/bin"
DATA_DIR="$HOME/.local/share/hypr-calendar"
CONF_DIR="$HOME/.config/hypr-calendar"

install -Dm755 "$HERE/src/hypr-calendar" "$BIN_DIR/hypr-calendar"
install -Dm755 "$HERE/scripts/calendar.sh" "$BIN_DIR/hypr-calendar-toggle"
install -Dm644 "$HERE/src/data.json" "$DATA_DIR/data.json"

mkdir -p "$CONF_DIR"
if [ ! -e "$CONF_DIR/style.css" ]; then
    install -Dm644 "$HERE/config/style.css" "$CONF_DIR/style.css"
fi

echo "installed widget   -> $BIN_DIR/hypr-calendar"
echo "installed launcher -> $BIN_DIR/hypr-calendar-toggle"
echo "installed tables   -> $DATA_DIR/data.json"
echo
echo "Bind the launcher, not the widget - it is what floats and toggles:"
echo "  hl.bind({ mods = \"SUPER\", key = \"C\", desc = \"calendar\","
echo "            cmd = \"hypr-calendar-toggle\" })"
echo
echo "Running waybar? Point a clock at the same command if you want it one"
echo "click away. It is a convenience, not a requirement."
