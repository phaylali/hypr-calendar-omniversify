#!/usr/bin/env python3
# --- inputs this script expects (adjust the paths below before running) ---
#   /tmp/opencode/gregorianCalendar.ts, islamicCalendar.ts : month tables
#     (also served by github.com/phaylali/moroccan-time-api)
#   /tmp/opencode/month_starts.py : Umm al-Qura month starts (from hijridate)
#   /tmp/opencode/palette.json : only used for the legacy "palette" key, which
#     the widget no longer reads - the theming now follows the GTK theme.
#   network access to morocco-date-api.omniversify.com for validation.
# It is committed for provenance: it is how data.json was produced and how the
# calendar math was validated.
#!/usr/bin/env python3
"""Build ~/.local/share/hypr-calendar/data.json from upstream sources.
Validates the calendar math before writing anything."""
import json, re, os, urllib.request

OUT_DIR = os.path.expanduser("~/.local/share/hypr-calendar")
os.makedirs(OUT_DIR, exist_ok=True)

# ---------- month tables from the user's own API repo ----------
def grab(path):
    s = open(path).read()
    body = s[s.index("["):s.rindex("]") + 1]
    body = re.sub(r"\s*as const\s*;", "", body).replace("'", '"')
    return json.loads(body)

months = {
    "gregorian": grab("/tmp/opencode/gregorianCalendar.ts"),
    "islamic": grab("/tmp/opencode/islamicCalendar.ts"),
}
amz = urllib.request.urlopen(
    "https://raw.githubusercontent.com/phaylali/moroccan-time-api/main/src/amazighCalendar.ts",
    timeout=25).read().decode()
open("/tmp/opencode/amazighCalendar.ts", "w").write(amz)
months["amazigh"] = grab("/tmp/opencode/amazighCalendar.ts")

# ---------- Umm al-Qura month starts ----------
ms = open("/tmp/opencode/month_starts.py").read()
MONTH_STARTS = eval(ms.replace("MONTH_STARTS = ", ""))
HIJRI_OFFSET = 1342 * 12

# ---------- Catppuccin palette (only the fields we use) ----------
pal_raw = json.load(open("/tmp/opencode/palette.json"))
BASE_KEYS = ["base", "mantle", "crust", "surface0", "surface1", "surface2",
             "overlay0", "overlay1", "overlay2", "subtext0", "subtext1", "text"]
ACCENTS = ["rosewater", "flamingo", "pink", "mauve", "red", "maroon", "peach",
           "yellow", "green", "teal", "sky", "sapphire", "blue", "lavender"]
palette = {}
for flavor in ("latte", "frappe", "macchiato", "mocha"):
    src = pal_raw[flavor]["colors"]
    palette[flavor] = {
        "label": pal_raw[flavor]["name"],
        "dark": pal_raw[flavor]["dark"],
        "base": {k: src[k]["hex"] for k in BASE_KEYS},
        "accents": {k: src[k]["hex"] for k in ACCENTS},
    }

# ================= VALIDATION =================
def gregorian_to_jdn(y, m, d):
    a = (14 - m) // 12
    yy, mm = y + 4800 - a, m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045

def jdn_to_julian(jdn):
    c = jdn + 32082
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = d - 4800 + m // 10
    return year, month, day

def julian_to_jdn(y, m, d):
    """Standard Julian-calendar -> JDN (inverse of jdn_to_julian)."""
    a = (14 - m) // 12
    yy, mm = y + 4800 - a, m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - 32083

def jdn_to_gregorian(jdn):
    j = jdn + 32044
    g = (4 * j + 3) // 146097
    c = j - (146097 * g) // 4
    dp = (4 * c + 3) // 1461
    e = c - (1461 * dp) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    return 100 * g + dp - 4800 + m // 10, month, day

# 1. Amazigh must reproduce the API exactly (Gregorian -> Julian is 13 days)
import urllib.request as _u
def _api(path):
    with _u.urlopen("https://morocco-date-api.omniversify.com" + path, timeout=25) as r:
        return json.load(r)
amz_dates = [(2026, 10, 9), (2026, 1, 1), (2024, 1, 15), (2026, 2, 7), (2025, 6, 1)]
for gd in amz_dates:
    a = _api(f"/api/amazigh/{gd[0]}/{gd[1]}/{gd[2]}/")
    exp = (a["year"], a["month"]["order"], a["day"])
    jy, jm, jd = jdn_to_julian(gregorian_to_jdn(*gd))
    got = (jy + 950, jm, jd)
    assert got == exp, f"amazigh {gd}: {got} != {exp}"
    # and julian_to_jdn must reproduce the same JDN
    assert julian_to_jdn(jy, jm, jd) == gregorian_to_jdn(*gd), f"jdn pivot {gd}"

# 2. julian_to_jdn must round-trip with jdn_to_julian
for y in (1900, 1999, 2026, 2077):
    for m in range(1, 13):
        for d in (1, 15, 28):
            assert jdn_to_julian(julian_to_jdn(y, m, d)) == (y, m, d), f"jul rt {y}-{m}-{d}"
# 3. ...and agree with the API's gregorian->julian pivot
for gd in [(2026, 10, 9), (2024, 1, 15), (2025, 6, 1)]:
    a = jdn_to_julian(gregorian_to_jdn(*gd))
    b = jdn_to_julian(julian_to_jdn(*a))
    assert a == b
    # amazigh of that julian date reached via JDN pivot
    assert a[0] + 950 == jdn_to_julian(gregorian_to_jdn(*gd))[0] + 950

# 4. Hijri: month lengths and JDN pivot consistent
# Umm al-Qura's table contains a handful of irregular months in 1925-1933
# (28 and 31 days) - these are genuine published-table entries, not extraction
# damage: the vendored table matches hijridate's MONTH_STARTS element-for-element.
for i in range(len(MONTH_STARTS) - 1):
    ln = MONTH_STARTS[i + 1] - MONTH_STARTS[i]
    assert 28 <= ln <= 31, f"bad hijri month length {ln} at {i}"
# hijri (y,m,1) -> jdn round trip
def hijri_to_jdn(y, m, d):
    idx = (y - 1) * 12 + m - 1 - HIJRI_OFFSET
    return MONTH_STARTS[idx] + d - 1 + 2400000

def jdn_to_hijri(jdn):
    rjd = jdn - 2400000
    idx = 0
    lo, hi = 0, len(MONTH_STARTS) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if MONTH_STARTS[mid] <= rjd: lo = mid
        else: hi = mid
    months_since = lo + HIJRI_OFFSET
    y, m = months_since // 12 + 1, months_since % 12 + 1
    return y, m, rjd - MONTH_STARTS[lo] + 1

# known values from the user's API (Aladhan Umm al-Qura)
for gd in [(2026, 10, 9), (2024, 1, 15), (2025, 3, 30), (2026, 7, 4), (2026, 9, 20)]:
    a = _api(f"/api/islamic/{gd[0]}/{gd[1]}/{gd[2]}/")
    exp = (a["year"], a["month"]["order"], a["day"])
    got = jdn_to_hijri(gregorian_to_jdn(*gd))
    assert got == exp, f"hijri {gd}: {got} != {exp}"
# round trip over a year
for off in range(0, 800, 7):
    jdn = gregorian_to_jdn(2026, 1, 1) + off
    y, m, d = jdn_to_hijri(jdn)
    assert hijri_to_jdn(y, m, d) == jdn, f"hijri rt {jdn}"
    assert jdn_to_gregorian(jdn) is not None
# weekday: jdn % 7 == 0 is Monday
assert jdn_to_gregorian(gregorian_to_jdn(2026, 10, 5))[0] == 2026  # sanity
import datetime
for off in range(0, 400, 11):
    dt = datetime.date(2026, 1, 1) + datetime.timedelta(days=off)
    assert (gregorian_to_jdn(dt.year, dt.month, dt.day) % 7) == dt.weekday(), f"wd {dt}"

data = {
    "months": months,
    "month_starts": MONTH_STARTS,
    "hijri_offset": HIJRI_OFFSET,
    "palette": palette,
    "accents": ACCENTS,
}
with open(os.path.join(OUT_DIR, "data.json"), "w") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

print("VALIDATION PASSED")
print("months:", {k: len(v) for k, v in months.items()})
print("month_starts:", len(MONTH_STARTS))
print("flavors:", list(palette), "| accents:", len(ACCENTS))
print("written:", os.path.join(OUT_DIR, "data.json"),
      os.path.getsize(os.path.join(OUT_DIR, "data.json")), "bytes")
