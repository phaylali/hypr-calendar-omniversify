# DEV_NOTES — hypr-calendar

Architecture, the decisions behind it, and every sharp edge found while
building it. Read this before changing anything.

---

## Shape of the thing

One Python file (`src/hypr-calendar`, PyGObject / GTK 4) plus one JSON table
(`src/data.json`). No build step, no code generation at runtime.

```
main()
 └─ App(Gtk.Application, id="app.omniversify.hyprcalendar")
     └─ Calendar(Gtk.ApplicationWindow)
         ├─ _build_header()  prev/next/title-year/switcher
         ├─ _build_title()   month + year button
         ├─ _build_info()    the same "today" in all three systems
         └─ rebuild()        clears the Gtk.Grid, dispatches on self.mode:
                             ├─ days   -> _build_days()
                             ├─ months -> _build_months()
                             └─ years  -> _build_years()
```

`self.mode ∈ {days, months, years}` and `self.view = (year, month)` are the
only state. `self.sel_jdn` / `self.today_jdn` are Julian day numbers — the one
date representation all three systems share.

### Drill-down

| action | effect |
|---|---|
| click year in title | `days → years` |
| click a year | `years → months` |
| click a month | `months → days` |
| `Escape` | climb one level; close only from `years` |
| prev/next | steps a **month** in `days`, a **year** in the pickers |

The reverse ladder is why `Escape` runs `months → years → days → close` rather
than closing outright: a picker is a temporary state, and leaving it should
never throw the user out of the widget.

---

## Why a normal XDG toplevel

There was a layer-shell version first. It was wrong.

Layer-shell windows in Hyprland get no keyboard focus of their own, cannot be
dragged by their header, and — the actual deal-breaker — the tiled windows
underneath stop being interactive. What was wanted was the behaviour of the
old kitty-wrapped `lvsk-calendar`: a window that floats in, takes focus, drags,
and leaves everything behind it alone.

So: `Gtk.ApplicationWindow`, and the *launcher* (`scripts/calendar.sh`) does
the floating — spawn through an `exec` rule so the window never gets a tile in
the first place, then resize and centre it.

---

## Theming: follow the system, do not reinvent it

There is **no theme switcher and no palette in the code**, deliberately.

GTK loads stylesheets in priority order: the theme's `gtk.css` at `THEME`
(200), `~/.config/gtk-4.0/gtk.css` at `USER` (800). Our own sheet is added at
**900**, and `~/.config/hypr-calendar/style.css` is appended **after** that, so
user CSS always wins.

The widget binds only *named* colours the theme is expected to define:

- `@theme_fg_color` — text, hover tints via `alpha(...)`
- `@theme_selected_bg_color` / `@theme_selected_fg_color` — today/selected
- `@borders` — separators

A hand-rolled Catppuccin palette was tried first and thrown away: it went stale
the moment the system theme changed. Following the theme means switching
GTK flavour or accent restyles this widget for free.

Two traps:

- GTK CSS accepts **`/* */` comments only** — `//` and `#` are parse errors.
- A broken `~/.config/gtk-4.0/gtk.css` (this machine had it symlinked to
  Breeze-Dark) silently wins over the real theme. It was removed.

---

## Bidi: solved structurally, not with marks

`ه` (or `هـ`) next to a number inside **one** text run makes Pango flip the
whole paragraph to RTL and print `28 ه` when you wanted `ه 28`. An `LRM` mark
at the front was tried; it does not fix it for Arabic-first strings.

What works: **never build a mixed-script string.** `_pair_box(tag, text)`
returns a `Gtk.Box` holding two separate `Gtk.Label`s — tag in one, number in
the other — with a fixed `gap` between them. The runs never meet, so neither
can re-order the other, and the spacing is exact regardless of script.

This is also why the switcher labels carry `.lang-ar` / `.lang-tfng` CSS
classes: the font family is chosen per element, not per string.

---

## Day-cell layout

`_build_days()` builds each cell as a **`Gtk.Overlay`**:

- **child** — the day number, `halign`/`valign` = `CENTER` → dead centre of
  the square.
- **overlay** — a horizontal box pinned to `valign = END` with the two
  secondary dates.

A plain vertical box cannot do this: the corner row consumes height and pushes
the number *up*, so it ends up centred only in the leftover space.

Which corner gets which system is fixed, not positional:

```python
left_cal  = "amazigh" if "amazigh" in others else "gregorian"
right_cal = next(c for c in others if c != left_cal)
```

so Amazigh is always bottom-left, Hijri always bottom-right, and Gregorian
fills whichever corner is free — each system keeps its corner in all three
modes instead of shuffling when you switch.

The corner row's `margin_*` (4) + `spacing` (2) are deliberately kept equal to
the 9px gap the old single-row layout used. Widening it would widen the grid,
and the grid sets the popup's natural width — which already exceeds the 704px
the launcher asks for (7 day columns × 82px `min-width`).

---

## Calendar math

Everything is reduced to a Julian day number and converted out:

- **Gregorian** — `g2j` / `j2g`, standard Fliegel–Van Flandern.
- **Amazigh** — Julian, with `julian_to_jdn` offset by `-32083`, and
  `amazighYear = julianYear + 950`.
- **Hijri** — a **vendored Umm al-Qura table** (`MONTH_STARTS` in `data.json`)
  offset by `HIJRI_OFFSET = 1342 * 12`, giving a stable index into the table.
  Astronomical calculation was rejected: it disagrees with Saudi official
  dates near the ends of months, which is exactly where users notice.

Validated before use against `morocco-date-api` (Amazigh) and Aladhan (Hijri).
Out-of-range Hijri dates are reported in the grid rather than crashing.

`tools/gen_data.py` rebuilds `data.json`. It pulls month tables from the
`phaylali/moroccan-time-api` repo and a local `month_starts.py`; see the
header of that file for the inputs it needs.

---

## Hyprland 0.56.2 (Lua config) — the things that lie

1. **`windowrulev2` is accepted and ignored.** `configerrors` stays empty, the
   rule never fires. Hence `calendar.sh` floats the window itself. Three dead
   `hyprctl keyword windowrule …` calls were removed for this reason.

2. **Address strings are a silent no-op.**
   `hl.dsp.focus({window='0x…'})` returns a healthy `HL.Dispatcher`, dispatch
   reports success, and focus never moves. Only real `HL.Window` objects from
   `hl.get_windows()` work. (`close`/`resize`/`float` do honour addresses, but
   going through `hl.get_windows()` is safer than remembering which is which.)

3. **`hl.dsp.…` only *builds* a dispatcher.** It must be passed to
   `hl.dispatch(…)`. Calling the dispatcher is not dispatching it.

4. **Resize takes `x`/`y`, not `w`/`h`**, with `relative = false`, and honours
   `window`.

5. `hl.dsp.window.focus` does not exist (`hl.dsp.focus` does); `hl.clients`
   does not exist (`hl.get_windows()` does).

6. **`hl.dsp.focus` switches workspace.** Any test harness that focuses the
   window yanks you off what you were doing — see below.

---

## Testing harness (not shipped)

`/tmp/opencode/drive.py` loads the widget as a module (`SourceFileLoader` on
`hypr-calendar`), opens its own window, and walks the drill-down under
`PHASE=years|months|days`, printing one line per transition so the shell side
can assert on it rather than sleeping blind.

Two rules learned the hard way:

- **Never spawn over the game.** Workspace 2 / DP-3 is where ETS2 runs;
  repeated spawns on top of it crashed it. The harness moves its window to
  **workspace 8 / HDMI-A-1** within 50ms of mapping and never focuses it.
  `ws8.sh` refuses to screenshot unless the window reports `workspace == 8`.
- `pkill -f` / `pgrep -f` matching the script's own name kills the shell
  running it. Use a `stop.sh` that names PIDs explicitly.

---

## Packaging

- **AUR**: `omniversify-hypr-calendar`, built from a `git` source pinned to
  `v$pkgver`, `sha256sums=('SKIP')`.
- **`arch=('any')`** — no compiled code.
- **License**: The Unlicense (`LICENSE.md`) — public domain dedication,
  `license=('Unlicense')` in the PKGBUILD. Dual licensing was considered and
  deliberately dropped: every line here is original (the month tables came
  from this author's own MIT `moroccan-time-api`), so adding GPL-2.0 as a
  second option *would* have been legitimate — but the Unlicense already
  lets anyone do anything with the code, so the GPL option added no
  leverage. Note that no GPL-2.0 code was ever involved; the licence is a
  grant, not a compliance obligation.
- **depends**: `python`, `python-gobject` (the `gi` module), `gtk4` (ships
  `Gtk-4.0.typelib`), `hyprland` (for `hyprctl` in the launcher).
  There is no `python-gtk4` package on Arch — that was the first wrong guess.
- **`optdepends`**: `noto-fonts` (Arabic + Tifinagh glyphs), `waybar`.
- **Nothing is installed into `$HOME`.** The tables go to
  `/usr/share/hypr-calendar/data.json`; `DATA_PATH` checks the user copy first
  and falls back to the system copy. A package writing to `$HOME` would break
  multi-user installs and system upgrades.
- The AUR clone lives in `packaging/<pkgname>/` and is **gitignored** — it is
  a separate repository, not part of this project.

---

## TODO

- [ ] `tools/gen_data.py` still points at `/tmp/opencode/*` scratch files;
      take them as arguments.
- [ ] The window's natural size (≈799px) exceeds the 704×648 the launcher
      requests; either drop a day column's `min-width` or ask for the real
      size.
