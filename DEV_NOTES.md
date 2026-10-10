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

## Cell layout — day, month and year

Every cell in the widget — a day, a month, a year — is built the same way, as
a **`Gtk.Overlay`** (`_build_days()`, `_build_months()`, `_build_years()`):

- **child** — the value being picked (`num`), `halign`/`valign` = `CENTER` →
  dead centre of the square.
- **overlay** — a horizontal box pinned to `valign = END` carrying the other
  two systems, built by `_corner_boxes()`.

A plain vertical box cannot do this: the corner row consumes height and pushes
the value *up*, so it ends up centred only in the leftover space. That is
precisely how the two pickers looked before this: the month name sat above a
Tifinagh subtitle instead of owning the cell, and the year's secondary years
were a single centred row instead of two corners. The day grid was right and
the pickers were not, because the overlay had only ever been written for days.

Which corner gets which system is fixed, not positional, and now lives in one
place — `_corner_boxes()`:

```python
left_cal  = "amazigh" if "amazigh" in cells else "gregorian"
right_cal = next(c for c in cells if c != left_cal)
```

so Amazigh is always bottom-left, Hijri always bottom-right, and Gregorian
fills whichever corner is free — each system keeps its corner in all three
modes instead of shuffling when you switch. The rule existed in three
variations: spelled out in the day cells, present only as a centred row in the
year picker, absent from the month picker. Factoring it out is what stops them
drifting apart again.

The corner row's `margin_*` (4) + `spacing` (2) are deliberately kept equal to
the 9px gap the old single-row layout used. Widening it would widen the grid,
and the grid sets the popup's natural width — which already exceeds the 704px
the launcher asks for (7 day columns × 82px `min-width`).

### What a corner holds

- **day cell** — the other two systems' day numbers (`28 هـ`, `26 ⵣ`).
- **month cell** — their month names, each in *its own* script, taken at the
  midpoint of the month (`_months_at()`). Midpoint, not the first day: a
  Gregorian January spans two Hijri months, so the middle names the one that
  holds most of it.
- **year cell** — their years at the midpoint of the year (`_years_at()`).

### Sizing: why nothing may be ellipsised

Corner month names are the longest string a corner ever carries ("Jumada
al-Akhira"), so the row can end up wider than the centred value above it. That
matters because of how `Gtk.Overlay` sizes itself: **it asks only its main
child**, and lays overlay children out *inside* whatever that gives it. A
corner row wider than the centre is therefore squeezed until it truncates —
and only the cells that are wide enough to hit the limit truncate, so the bug
reads as "November and December are cut off but January is fine".
The fix is a **CSS floor, not Python arithmetic**: the picker cells get a
`min-width` large enough that their centre can never be the narrow thing in
the row, so the overlay has no reason to squeeze it.

```css
.day.pick  { min-width: 90px; }    /* year picker  */
.day.month { min-width: 158px; }   /* month picker */
```

Both numbers are measured, not chosen — the worst corner row any of the three
systems produces, plus a pixel: **89px** for the year corner row (`G 2021`
+ `هـ 1442`), **157px** for the month corner row (`Jumada al-Akhira` at its
midpoint). The values are identical across Gregorian, Hijri and Amazigh, so
one number covers all three calendars and no cell ever measures wider than its
own allocation. The day grid needs none: `82px` (`.day`) already clears a day's
two short corner numbers, which is why it measures the same 799px before and
after the whole rework.

There is no size-request code in Python at all. An earlier version asked the
overlay for the corner row's width (`_attach_corners()`, with a `+24` fudge for
margins and letter-spacing that Pango applies at render time rather than at
measure time) and set it back on the cell. It worked and it was wrong: a cell
that grows itself past its stylesheet contradicts the stylesheet, and the next
person to read the CSS would be reading a lie. The floor lives where the rest
of the sizing lives.

Both numbers were taken from a probe that builds the widget, walks the mapped
tree and reports `get_preferred_size()` per cell — a scratch script, not part
of the repo, because the numbers it produced are already written into the CSS
and there is nothing left for it to check. The measurement that matters, run
once per change: **days 799px, months 759px, years 487px, identical for
Gregorian, Hijri and Amazigh, with no corner row anywhere wider than the cell
holding it.**

**No label in this app may set `ellipsize`.** It was first written with
`Pango.EllipsizeMode.END` on corner month names as a "guard that never fires",
and it fired on every window: a window is mapped once at a size it does not
keep (GTK has to lay out before it knows its real size, and the launcher asks
for 704px against a 951px natural width), so every corner label was allocated
narrow *once*. GTK4 labels latch from that point: the measured natural width
becomes the width of the already-ellipsised text and never recovers, even once
the window is 100px wider than it needs. `November` measured 65px as built and
55px after a single narrow allocation, and printed `G Novemb...` for the rest
of its life in a cell with 49px going spare. The tell that this — and not a
real width problem — was the cause: GTK's own allocation report said
`nat == alloc` for the truncated label, and the truncation appeared on short
names (`July`) but not long ones (`September`), because what matters is which
cell sized its column, not how long the string is. Full text with no ellipsis
mechanism is the only state with no such latch.

### Month names: native scripts, not transliteration

```python
NATIVE = {"gregorian": "latin", "hijri": "arabic", "amazigh": "tifinagh"}
month_native(cal, m)  # -> month_name(cal, m)[NATIVE[cal]]
```

`data.json` already carried all three spellings for every month, so this is a
decision about which one *is* the name — not new data. The other two appear as
the corners, in their own scripts, which is what makes the cell readable at a
glance: you recognise `المحرّم` as Arabic without first mapping a
transliteration onto it.

The rule is the same in three places, so no two can disagree — `_build_months()`
for the month cells, `_build_title()` for the title over the day grid,
`_build_info()` for the Today strip:

| system | month picker centre | title over the day grid | its Today strip |
| --- | --- | --- | --- |
| Gregorian | `January` | `October` | `G 10 October 2026` |
| Hijri | `المحرّم` | `شعبان` | `هـ 29 ربيع الآخر 1448` |
| Amazigh | `ⵉⵏⵏⴰⵢⵔ` | `ⵛⵓⵜⴰⵏⴱⵉⵔ` | `ⵣ 27 ⵛⵓⵜⴰⵏⴱⵉⵔ 2976` |

Two details that only look like decoration:

- **The title wears a font class for whatever script it holds** — `lang-ar` or
  `lang-tfng`, taken from the same `CAL_LABEL` table the switcher buttons use,
  so `شعبان` renders in Noto Sans Arabic rather than in whatever Pango would
  pick by fallback, and matches the `هجري` button next to it. It is removed on
  the way into the month and year titles, which are digits: `1447 – 1458` must
  not inherit an Arabic face from the screen you just left.
- **The second line under the title is the same month in another script** —
  Tifinagh, except on Amazigh where the title already *is* Tifinagh, where it
  drops to Latin (`Cutanbir`) instead of printing the same line twice.

Each part of a date in the strip is its own label. An Arabic run that holds
Western digits lets Pango reorder the paragraph, which is how you end up with
`4 1447 ربيع الآخر`; separate labels make that impossible because the bidi
algorithm never sees two scripts in one run. No label in the app sets
`ellipsize`, for the latch reason above.

### The year picker pages by whole pages

Twelve years on screen, `YEARS_PER_PAGE = 12`, and `YEAR_LEAD = 5` of them
above the current one — so a page reads `2021 – 2032` with 2026 in the middle
rather than at the top edge. Title and grid both take their years from that
same pair of constants, which is what stops them drifting apart.

`←`/`→` move by a **whole page** (`y ± YEARS_PER_PAGE`), `↑`/`↓` step one year
(`_year_step()`, which returns 12 in years mode and 1 in the day grid, so the
arrow keys mean "the thing you can see" in both). Pages never overlap: 2009 –
2020, then 2021 – 2032.

The outline (`.sel`) goes on the **browsed** year — `_build_years()` compares
against `y`, the view anchor, not the year you picked to get here. Because
`YEAR_LEAD` is fixed at 5 and pages advance by 12, that means the outline sits
on the 6th cell of every page and follows you as you page, rather than
disappearing when the picked year scrolls off the end of the list. It is a
position marker, not a "you chose this one" marker; the chosen year is only
recoverable from the day grid you came from.

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
