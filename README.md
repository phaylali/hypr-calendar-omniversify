# hypr-calendar — Omniversify

A three-calendar overlay for **Hyprland**: Gregorian, Hijri (Umm al-Qura) and
Amazigh (Tifinagh), shown side by side in every cell, in one small floating
window.

| | |
|---|---|
| Toolkit | GTK 4 (PyGObject) |
| Language | Python (single file, no build step) |
| Window type | normal XDG toplevel (not layer-shell) |
| Calendars | Gregorian · Hijri (Umm al-Qura) · Amazigh (Julian) |
| Data | vendored `src/data.json`, validated against morocco-date-api + Aladhan |
| License | GPL-2.0 |

---

## Why this exists

The waybar clock used to open `lvsk-calendar` through a kitty wrapper. It worked,
but it was a terminal emulator holding a script, and everything about it —
the theme, the help bar, the calendar system — was somebody else's decision.

`hypr-calendar` is the replacement: the same overlay behaviour people actually
liked (a window that floats in, takes focus, drags by its header, and leaves the
tiled windows behind it fully interactive) with the calendar logic rewritten.

The two things worth having are the ones a `waybar`/`eww` widget cannot give you:

- **A real window.** It takes keyboard focus, it is draggable, and `Escape`
  closes it. It does not join the tiling layout, so it never pushes your tiles
  around.
- **Three systems at once.** Every day cell shows the day number of the system
  you are browsing, plus the same date in the other two systems in the bottom
  corners — so you can read `28 هـ` next to `9` and `26 ⵣ` without switching.

---

## Features

- **Year → month → day drill-down.** Click the year in the title for the year
  picker, click a year for the month picker, click a month for the day grid.
  `Escape` climbs back one level at a time and only closes from the top.
- **Calendar switcher** in the header: `Gregorian`, `هجري`, `ⵉⵎⴰⵣⵉⴳⵏ`.
- **No help bar, no theme switcher.** The visual theme is the system GTK theme;
  this widget follows it instead of carrying a palette of its own.
- **Bidi-safe labels.** Arabic and Tifinagh tags never swallow the digits
  beside them, because each tag and each number is its own `Gtk.Label` (see
  `DEV_NOTES.md`).
- **Corner layout in the day cells.** The day number is centred in the square;
  Amazigh always sits bottom-left, Hijri always bottom-right, and Gregorian
  fills whichever corner is free.

---

## Install

### From AUR

```sh
yay -S omniversify-hypr-calendar
```

The package installs `/usr/bin/hypr-calendar` and
`/usr/bin/hypr-calendar-toggle`. Point your waybar clock at the toggle:

```jsonc
"clock": { "on-click": "hypr-calendar-toggle" }
```

### Manually

```sh
./scripts/install.sh
```

which puts:

| file | destination |
|---|---|
| `src/hypr-calendar` | `~/.local/bin/hypr-calendar` |
| `src/data.json` | `~/.local/share/hypr-calendar/data.json` |
| `config/style.css` | `~/.config/hypr-calendar/style.css` (only if absent) |
| `scripts/calendar.sh` | `~/.config/waybar/scripts/calendar.sh` (only if absent) |

`./scripts/uninstall.sh` reverses it (`--purge` also drops your config).

The widget creates `~/.config/hypr-calendar/config` on first run if it is
missing.

### Requirements

`python-gtk4` (PyGObject + GTK 4), `hyprland`, and any waybar setup that can
run a script on clock click. Fonts: `Noto Sans Arabic` for the Hijri tag,
`Noto Sans Tifinagh` for Amazigh.

---

## Usage

- **Waybar clock click** → toggles the overlay (open if closed, close if open).
- **Drag** the header bar to move it; it is a normal window, so it behaves like
  one.
- **`Escape`** → day grid → month picker → year picker → close.
- Click the **year in the title** to jump straight to the year picker.

Bind it to a key the same way you would any other launcher:

```lua
-- ~/.config/hypr/hyprland.lua
hl.bind({ mods = "SUPER", key = "C", desc = "calendar",
          cmd = "$HOME/.config/waybar/scripts/calendar.sh" })
```

---

## Configuration

`~/.config/hypr-calendar/config` — one key:

```
calendar = gregorian | hijri | amazigh   # which system to open on
```

`~/.config/hypr-calendar/style.css` — optional, loaded **after** the widget's
own stylesheet, so anything written there wins. It ships as comments only.

```css
.day            { border-radius: 4px; }
.day.today      { background-color: #f5c2e7; color: #1e1e2e; }
.cal-head       { background-color: #181825; }
```

GTK CSS accepts `/* */` comments only.

---

## Repository layout

```
src/hypr-calendar      the widget (single Python file)
src/data.json          vendored calendar tables
config/style.css       optional user override (comments only)
scripts/calendar.sh    waybar launcher: float, resize, centre, toggle
scripts/install.sh     manual install into $HOME
packaging/             PKGBUILD for the AUR package
DEV_NOTES.md           architecture, quirks, and the things that bit us
```

---

## Related

- [omniversify-usb-wireless-drivers](https://github.com/phaylali/omniversify-usb-wireless-drivers)
  — DKMS driver for the PIX-LINK LV-UW03 (ZTOP ZT9101), GPL-2.0.
