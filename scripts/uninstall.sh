#!/bin/bash
# Removes what install.sh put in $HOME. Never touches anything outside the
# paths below, and leaves ~/.config/hypr-calendar alone unless --purge is
# passed, so your config survives an upgrade.
set -euo pipefail

rm -f "$HOME/.local/bin/hypr-calendar"
rm -f "$HOME/.local/share/hypr-calendar/data.json"
rmdir --ignore-fail-on-non-empty "$HOME/.local/share/hypr-calendar" 2>/dev/null || true
rm -f "$HOME/.config/waybar/scripts/calendar.sh"

if [ "${1:-}" = "--purge" ]; then
    rm -f "$HOME/.config/hypr-calendar/config" \
          "$HOME/.config/hypr-calendar/style.css"
    rmdir "$HOME/.config/hypr-calendar" 2>/dev/null || true
    echo "purged config"
fi

echo "uninstalled"
