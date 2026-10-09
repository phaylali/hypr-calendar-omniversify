#!/bin/bash
# hypr-calendar -> opens as a centred floating overlay, like SUPER+R's walker.
#
# Why this script does the floating itself: Hyprland 0.56.2 accepts window
# rules without complaint (configerrors stays empty) but never applies them -
# see the note next to the calendar rule in ~/.config/hypr/hyprland.lua.
# So the window is floated explicitly instead:
#   1. spawn through an exec rule  -> the window maps already floating
#   2. resize + centre it through hl.dsp.window.*
# Clicking the waybar clock while it is open closes it (launcher behaviour).

set -u

CAL_CLASS="app.omniversify.hyprcalendar"
OVERLAY_W=704
OVERLAY_H=648

lua_quote() { # escape a string for use inside a Lua double-quoted literal
    printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

find_overlay() { # print the address of the calendar window, if any
    hyprctl clients -j 2>/dev/null | /usr/bin/python3 -c "
import sys, json
for c in json.load(sys.stdin):
    if c.get('class') == '$CAL_CLASS':
        print(c['address'])
" 2>/dev/null
}

ADDR=$(find_overlay)

# Already open -> toggle it away, the way a launcher overlay behaves.
if [ -n "$ADDR" ]; then
    hyprctl repl "hl.dispatch(hl.dsp.window.close({ window = 'address:$ADDR' })); return 'ok'" \
        >/dev/null 2>&1
    exit 0
fi

# Find the widget: an override, then the manual install, then whatever is on
# PATH (which is where the AUR package puts it: /usr/bin/hypr-calendar).
CAL="${HYPR_CALENDAR:-}"
if [ -z "$CAL" ] && [ -x "$HOME/.local/bin/hypr-calendar" ]; then
    CAL="$HOME/.local/bin/hypr-calendar"
fi
if [ -z "$CAL" ]; then
    CAL="$(command -v hypr-calendar 2>/dev/null || true)"
fi

if [ -z "$CAL" ] || [ ! -x "$CAL" ]; then
    notify-error "hypr-calendar not found" 2>/dev/null
    exit 1
fi

# Step 1: spawn it with an exec rule so it never gets a tile in the first place.
hyprctl repl "hl.dispatch(hl.dsp.exec_cmd(\"$(lua_quote "$CAL")\", { float = true })); return 'ok'" \
    >/dev/null 2>&1

# Step 2: wait for the window to map, then size it and centre it.
for _ in $(seq 1 40); do
    ADDR=$(find_overlay)
    [ -n "$ADDR" ] && break
    sleep 0.25
done

[ -z "$ADDR" ] && exit 0

hyprctl repl "hl.dispatch(hl.dsp.window.float({ window = 'address:$ADDR', action = 'on' })); hl.dispatch(hl.dsp.window.resize({ x = $OVERLAY_W, y = $OVERLAY_H, relative = false, window = 'address:$ADDR' })); hl.dispatch(hl.dsp.window.center({ window = 'address:$ADDR' })); return 'ok'" \
    >/dev/null 2>&1
