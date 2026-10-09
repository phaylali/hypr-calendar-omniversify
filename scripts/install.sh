#!/bin/bash
# Manual install into $HOME, for people not using the AUR package.
# Idempotent: config/style.css/waybar launcher are only written if missing,
# so rerunning never clobbers a personal setup.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN_DIR="$HOME/.local/bin"
DATA_DIR="$HOME/.local/share/hypr-calendar"
CONF_DIR="$HOME/.config/hypr-calendar"
WAYBAR_DIR="$HOME/.config/waybar/scripts"

install -Dm755 "$HERE/src/hypr-calendar" "$BIN_DIR/hypr-calendar"
install -Dm644 "$HERE/src/data.json" "$DATA_DIR/data.json"

mkdir -p "$CONF_DIR"
if [ ! -e "$CONF_DIR/style.css" ]; then
    install -Dm644 "$HERE/config/style.css" "$CONF_DIR/style.css"
fi

if [ ! -e "$WAYBAR_DIR/calendar.sh" ]; then
    install -Dm755 "$HERE/scripts/calendar.sh" "$WAYBAR_DIR/calendar.sh"
    echo "installed launcher -> $WAYBAR_DIR/calendar.sh"
fi

echo "installed widget    -> $BIN_DIR/hypr-calendar"
echo "installed tables    -> $DATA_DIR/data.json"
echo
echo "Point your waybar clock at it:"
echo "  \"on-click\": \"$WAYBAR_DIR/calendar.sh\""
