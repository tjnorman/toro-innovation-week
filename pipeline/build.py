"""Build every chart, the README, and the website from data/model.yaml.

Run:  python -m pipeline.build
Nothing here is typed twice: costs, hours, and gaps are computed from the rates in the model.
"""
from __future__ import annotations

import html
import json
import textwrap
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CHARTS = ROOT / "docs" / "media" / "charts"
SITE = ROOT / "site"

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
THEMES = {
    "light": dict(ink="#1f2328", soft="#59636e", grid="#d8dee4", card="#f6f8fa", line="#8c959f",
                  accent="#860038", gold="#b88a00", surface="#ffffff"),
    "dark": dict(ink="#f0f6fc", soft="#9198a1", grid="#3d444d", card="#151b23", line="#656c76",
                 accent="#e0608c", gold="#e3b341", surface="#0d1117"),
}
KIND_TAG = {"college": "COLLEGE BLOCK", "catapult": "CATAPULT", "group": "STUDENT GROUP",
            "speaker": "SPEAKERS", "partner": "SUCCESS PARTNER", "program": "PROGRAM"}


def load() -> dict:
    return yaml.safe_load((ROOT / "data" / "model.yaml").read_text(encoding="utf-8"))


def money(x: float) -> str:
    return f"${x:,.0f}"


def clock(h: float) -> str:
    hh = int(h)
    mm = round((h - hh) * 60)
    h12 = hh if hh <= 12 else hh - 12
    return f"{h12}:{mm:02d}"


def compute(m: dict) -> dict:
    r = m["rates"]
    lead_wtu_sem = 3 * len(m["days"])
    students = r["student_hours_week"] * r["student_weeks_year"] * r["student_wage"]
    out = {"students": students, "supplies": r["supplies"], "base": r["base_budget"],
           "lead_cost_sem": 3 * r["wtu_cost"], "lead_hours_sem": 3 * r["hours_per_wtu"],
           "lead_hours_week": 3 * r["hours_per_wtu"] / r["weeks_per_semester"],
           "pool_hours_day": r["student_hours_week"] / len(m["days"]),
           "college_days_sem": r["weeks_per_semester"] * len(m["days"]),
           "work_hours": r["work_hours_semester"],
           "today_hours": r["director_wtu_today"] * r["hours_per_wtu"],
           "base_without_ed": r["base_budget"] - r["base_exec_director_line"]}
    opts = {}
    for key, name, wtu_sem in (("B", "Five college leads", lead_wtu_sem),
                               ("A", "Five college leads + Faculty Director", lead_wtu_sem + 6)):
        faculty = wtu_sem * 2 * r["wtu_cost"]
        total = faculty + students + r["supplies"]
        opts[key] = {"name": name, "wtu_sem": wtu_sem, "wtu_year": wtu_sem * 2, "faculty": faculty,
                     "total": total, "gap": total - r["base_budget"],
                     "gap_without_ed": total - out["base_without_ed"],
                     "hours_sem": wtu_sem * r["hours_per_wtu"]}
    out["options"] = opts
    return out


# ---------------------------------------------------------------- SVG helpers
def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def svg_open(w: int, h: int, label: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{esc(label)}" font-family="{FONT}">')


def text(x, y, s, size=13, fill="#000", weight=400, anchor="start", extra="") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}" {extra}>{esc(s)}</text>')


def on_fill(color: str) -> str:
    return "#0b0b0b" if color.lower() in ("#eda100", "#c98500") else "#ffffff"


# ---------------------------------------------------------------- charts
def chart_week(m: dict, theme: str) -> str:
    t = THEMES[theme]
    W, top, left, colw, gap, ph = 1040, 96, 62, 186, 8, 56
    t0, t1 = 7.5, 17.0
    H = int(top + (t1 - t0) * ph + 46)
    o = [svg_open(W, H, "Proposed weekly calendar: each college hosts one day in the Innovation Incubator")]
    o.append(text(left, 30, "One college, one day: the proposed Incubator week", 19, t["ink"], 600))
    o.append(text(left, 52, "Starting proposal for spring 2027. Days and hours are open for the deans to trade.", 12.5, t["soft"]))
    for hr in range(8, 18):
        y = top + (hr - t0) * ph
        o.append(f'<line x1="{left}" x2="{W - 12}" y1="{y:.1f}" y2="{y:.1f}" stroke="{t["grid"]}" stroke-width="1"/>')
        lab = f"{hr if hr <= 12 else hr - 12} {'am' if hr < 12 else 'pm'}"
        o.append(text(left - 10, y + 4, lab, 11, t["soft"], anchor="end"))
    for i, d in enumerate(m["days"]):
        x = left + 6 + i * (colw + gap)
        col = d["color_dark" if theme == "dark" else "color"]
        o.append(f'<rect x="{x}" y="64" width="{colw}" height="24" rx="4" fill="{col}"/>')
        o.append(text(x + colw / 2, 81, f'{d["day"]} · {d["short"]}', 12.5, on_fill(d["color"]), 600, "middle"))
        for b in m["schedule"][d["key"]]:
            y = top + (b["start"] - t0) * ph + 1
            hgt = (b["end"] - b["start"]) * ph - 3
            if b["kind"] == "college":
                fill, ink, tagc, stroke = col, on_fill(d["color"]), on_fill(d["color"]), "none"
            else:
                fill, ink, tagc, stroke = t["card"], t["ink"], t["soft"], t["line"]
            dash = ' stroke-dasharray="4 3"' if b["kind"] == "program" else ""
            o.append(f'<rect x="{x}" y="{y:.1f}" width="{colw}" height="{hgt:.1f}" rx="4" fill="{fill}" '
                     f'stroke="{stroke}" stroke-width="1"{dash}/>')
            o.append(text(x + 8, y + 14, f'{KIND_TAG[b["kind"]]} · {clock(b["start"])}–{clock(b["end"])}', 8.6, tagc, 600,
                          extra='letter-spacing="0.3"'))
            for j, line in enumerate(textwrap.wrap(b["label"], 28)[:2]):
                o.append(text(x + 8, y + 29 + j * 14, line, 11.6, ink, 600 if b["kind"] == "college" else 500))
    o.append(text(left, H - 14, "Evenings and Saturdays stay open for Continuing and Professional Education, EPUC LA, and partner programs.",
                  11.5, t["soft"]))
    o.append("</svg>")
    return "".join(o)


def bar_chart(title, sub, rows, theme, fmt, ref=None, note=None) -> str:
    """rows: (label, value, emphasis). ref: (value, label)."""
    t = THEMES[theme]
    W, left, right, top, bh, bg = 860, 300, 110, 78, 30, 20
    H = top + len(rows) * (bh + bg) + (44 if note else 18)
    vmax = max([v for _, v, _ in rows] + ([ref[0]] if ref else [])) * 1.02
    pw = W - left - right
    o = [svg_open(W, H, title), text(24, 30, title, 18, t["ink"], 600), text(24, 52, sub, 12.5, t["soft"])]
    labels = []
    for i, (lab, v, emph) in enumerate(rows):
        y = top + i * (bh + bg)
        w = max(2, v / vmax * pw)
        fill = t["accent"] if emph else t["line"]
        o.append(text(left - 14, y + bh / 2 + 4.5, lab, 13, t["ink"], 600 if emph else 400, "end"))
        o.append(f'<path d="M{left} {y} h{w - 4:.1f} a4 4 0 0 1 4 4 v{bh - 8} a4 4 0 0 1 -4 4 h-{w - 4:.1f} z" fill="{fill}"/>')
        labels.append(text(left + w + 8, y + bh / 2 + 4.5, fmt(v), 13, t["ink"], 600,
                           extra=f'paint-order="stroke" stroke="{t["surface"]}" stroke-width="5" stroke-linejoin="round"'))
    if ref:
        x = left + ref[0] / vmax * pw
        y1 = top + len(rows) * (bh + bg) - bg + 6
        o.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top - 8}" y2="{y1}" stroke="{t["gold"]}" stroke-width="2" stroke-dasharray="5 4"/>')
        o.append(text(x, top - 13, ref[1], 11.5, t["ink"], 600, "middle"))
    o.append(f'<line x1="{left}" x2="{left}" y1="{top - 6}" y2="{top + len(rows) * (bh + bg) - bg + 6}" stroke="{t["line"]}" stroke-width="1"/>')
    o.extend(labels)
    if note:
        o.append(text(24, H - 14, note, 11.5, t["soft"]))
    o.append("</svg>")
    return "".join(o)


def chart_cost(m, c, theme) -> str:
    A, B = c["options"]["A"], c["options"]["B"]
    rows = [("FY 2026–27 base budget", c["base"], False),
            ("Option B: five college leads", B["total"], True),
            ("Option A: five leads + Faculty Director", A["total"], True)]
    return bar_chart("What each option costs a year", "Faculty time, the shared student pool, and supplies",
                     rows, theme, money,
                     note=f"Option B is {money(B['gap'])} above the base budget; Option A is {money(A['gap'])} above. "
                          f"Rate: ${m['rates']['wtu_cost']:,.2f} per WTU.")


def chart_hours(m, c, theme) -> str:
    A, B = c["options"]["A"], c["options"]["B"]
    rows = [("Today: one director, 6 WTU", c["today_hours"], False),
            ("Option B: five leads, 15 WTU", B["hours_sem"], True),
            ("Option A: leads + Director, 21 WTU", A["hours_sem"], True)]
    return bar_chart("Faculty hours a semester", "Hours funded, at 45 hours per WTU",
                     rows, theme, lambda v: f"{v:,.0f} hours",
                     ref=(c["work_hours"], f"{c['work_hours']} hours of program work"),
                     note="The dashed line is the October 2026 estimate of faculty hours the current programs need each semester.")


def chart_roadmap(m, theme) -> str:
    t = THEMES[theme]
    ms = m["milestones"]
    W, rh, top = 860, 36, 74
    H = top + len(ms) * rh + 44
    colors = {"gate": t["accent"], "step": t["ink"], "date": t["line"], "games": t["gold"]}
    names = {"gate": "Decision", "step": "Launch", "date": "Deadline", "games": "LA28"}
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    o = [svg_open(W, H, "Roadmap from December 2026 to the 2028 Games"),
         text(24, 30, "From decision to the Games", 18, t["ink"], 600),
         text(24, 52, "A spring 2027 pilot gives the model three semesters before LA28", 12.5, t["soft"]),
         f'<line x1="170" x2="170" y1="{top + 4}" y2="{top + (len(ms) - 1) * rh + 12}" stroke="{t["grid"]}" stroke-width="2"/>']
    for i, x in enumerate(ms):
        y = top + i * rh + 8
        p = x["date"].split("-")
        when = f"{months[int(p[1]) - 1]} {int(p[2])}, {p[0]}" if len(p) == 3 else f"{months[int(p[1]) - 1]} {p[0]}"
        col = colors[x["kind"]]
        o.append(text(150, y + 4.5, when, 12.5, t["soft"], anchor="end"))
        if x["kind"] == "gate":
            o.append(f'<path d="M170 {y - 8} l8 8 l-8 8 l-8 -8 z" fill="{col}" stroke="{t["surface"]}" stroke-width="2"/>')
        else:
            o.append(f'<circle cx="170" cy="{y}" r="6.5" fill="{col}" stroke="{t["surface"]}" stroke-width="2"/>')
        o.append(text(192, y + 4.5, x["label"], 13.5, t["ink"], 600 if x["kind"] in ("gate", "games") else 400))
        o.append(text(W - 24, y + 4.5, names[x["kind"]], 11, t["soft"], anchor="end"))
    o.append(text(24, H - 14, "Diamonds are decisions the President and deans make. Everything else follows from them.", 11.5, t["soft"]))
    o.append("</svg>")
    return "".join(o)


def chart_day(m, c, theme) -> str:
    t = THEMES[theme]
    W, H = 860, 330
    o = [svg_open(W, H, "How one college day works: four inputs feed a college day that produces three results"),
         text(24, 30, "How one college day works", 18, t["ink"], 600),
         text(24, 52, "The same four ingredients, five days a week", 12.5, t["soft"])]
    ins = [("Faculty lead", f"3 WTU · about {c['lead_hours_week']:.0f} hours a week"),
           ("Shared student pool", f"{c['pool_hours_day']:.0f} student hours for the day"),
           ("Catapult studio", "Community Engaged Learning + a course"),
           ("Success partners", "Writing, tutoring, new-student programs")]
    outs = [("LA28-focused projects", "for local businesses and nonprofits"),
            ("Students building things", "across every college, not one"),
            ("Results the campus can count", "one impact report each June")]
    for i, (a, b) in enumerate(ins):
        y = 76 + i * 60
        o.append(f'<rect x="24" y="{y}" width="262" height="48" rx="6" fill="{t["card"]}" stroke="{t["line"]}"/>')
        o.append(text(38, y + 20, a, 13, t["ink"], 600) + text(38, y + 37, b, 11.5, t["soft"]))
        o.append(f'<path d="M290 {y + 24} C 320 {y + 24}, 320 190, 348 190" fill="none" stroke="{t["line"]}" stroke-width="1.5"/>')
    o.append(f'<rect x="350" y="140" width="170" height="100" rx="8" fill="{t["accent"]}"/>')
    o.append(text(435, 182, "One college,", 15, "#ffffff", 600, "middle") + text(435, 202, "one day", 15, "#ffffff", 600, "middle"))
    o.append(text(435, 224, "LA28 focus", 11.5, "#ffffff", 400, "middle"))
    for i, (a, b) in enumerate(outs):
        y = 96 + i * 68
        o.append(f'<path d="M522 190 C 548 190, 548 {y + 24}, 572 {y + 24}" fill="none" stroke="{t["line"]}" stroke-width="1.5"/>')
        o.append(f'<path d="M572 {y + 24} l-7 -4 v8 z" fill="{t["line"]}"/>')
        o.append(f'<rect x="576" y="{y}" width="260" height="48" rx="6" fill="{t["card"]}" stroke="{t["line"]}"/>')
        o.append(text(590, y + 20, a, 13, t["ink"], 600) + text(590, y + 37, b, 11.5, t["soft"]))
    o.append("</svg>")
    return "".join(o)


def chart_hero(m, theme) -> str:
    t = THEMES[theme]
    W, H = 1040, 300
    o = [svg_open(W, H, "Toro Innovation Week: five colleges, five days, one Innovation Incubator"),
         text(W / 2, 70, "Toro Innovation Week", 46, t["ink"], 700, "middle"),
         text(W / 2, 108, m["meta"]["tagline"], 19, t["soft"], 400, "middle")]
    bw, gap = 180, 14
    x0 = (W - 5 * bw - 4 * gap) / 2
    for i, d in enumerate(m["days"]):
        x = x0 + i * (bw + gap)
        col = d["color_dark" if theme == "dark" else "color"]
        ink = on_fill(d["color"])
        o.append(f'<rect x="{x:.1f}" y="146" width="{bw}" height="112" rx="10" fill="{col}"/>')
        o.append(text(x + bw / 2, 176, d["day"].upper(), 12, ink, 700, "middle", 'letter-spacing="1.5"'))
        o.append(text(x + bw / 2, 206, d["short"], 24, ink, 700, "middle"))
        for j, line in enumerate(textwrap.wrap(d["focus"], 26)[:2]):
            o.append(text(x + bw / 2, 228 + j * 14, line, 10.8, ink, 500, "middle"))
    o.append(text(W / 2, 286, "A faculty proposal for the CSUDH Innovation Incubator · LA28 focus · not a university decision", 12, t["soft"], 400, "middle"))
    o.append("</svg>")
    return "".join(o)


# ---------------------------------------------------------------- README
def pic(name: str, alt: str) -> str:
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="docs/media/charts/{name}-dark.svg" />'
            f'<img src="docs/media/charts/{name}-light.svg" alt="{esc(alt)}" width="100%" /></picture>')


def tiles(items, per_row=3) -> str:
    rows = []
    for i in range(0, len(items), per_row):
        cells = "".join(f'<td align="center" width="{100 // per_row}%"><h2>{esc(x["value"])}</h2>{esc(x["label"])}'
                        + (f'<br/><sub>{esc(x["note"])}</sub>' if x.get("note") else "") + "</td>"
                        for x in items[i:i + per_row])
        rows.append(f"<tr>\n{cells}\n</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


SOURCES = [
    ("Academic Affairs, Office of the Provost. (2026, November 9). FY 2026–27 Innovation Incubator budget, balances, and WTU rate [campus record].", None),
    ("CSUDH Innovation Incubator. (2026, October 23). Spring 2027 faculty-time estimate by program [campus record].", None),
    ("CSUDH Innovation Incubator. (2026, November 11). Assessment and participation data, fall 2026 [campus record].", None),
    ("California State University, Dominguez Hills. (2026). Division of Academic Affairs. Academic Catalog 2026–2027.",
     "https://catalog.csudh.edu/general-information/division-academic-affairs/"),
    ("Dignity Health Sports Park. (n.d.). About us.", "https://www.dignityhealthsportspark.com/about/about-us"),
    ("LA28. (2026, April 8). LA28 details procurement strategy to boost regional economy.",
     "https://la28.org/en/newsroom/la28-details-procurement-strategy-to-boost-regional-economy.html"),
    ("LA28. (2026, October 20). LA28 opens its brand to local businesses through new Made for Two-Eight license program.",
     "https://la28.org/en/newsroom/la28-opens-its-brand-to-local-businesses-through-new-made-for-two-eight-license-program.html"),
    ("Los Angeles County Department of Economic Opportunity. (n.d.). Path to 2028.", "https://opportunity.lacounty.gov/pathto2028/"),
    ("Fresno State, Lyles Center for Innovation and Entrepreneurship. (n.d.). Johanson Entrepreneurship Faculty Fellows.",
     "https://craig.fresnostate.edu/lyles/johansonworkshops.html"),
]


def readme(m, c) -> str:
    A, B = c["options"]["A"], c["options"]["B"]
    r = m["rates"]
    head = [{"value": "5", "label": "colleges, one day each"},
            {"value": "3 WTU", "label": "for each college's faculty lead"},
            {"value": f"{c['college_days_sem']}", "label": "college days a semester"},
            {"value": "2", "label": "speaker series, Tuesday and Thursday"},
            {"value": "5", "label": "student groups meeting weekly"},
            {"value": f"{r['student_hours_week']}", "label": "student hours a week, shared by all five"}]
    days_tbl = "\n".join(
        f'| **{d["day"]}** | {d["college"]} | {d["focus"]} | {d["group"]} |' for d in m["days"])
    ideas = "\n".join(
        f'<tr><td width="24%" valign="top"><b>{d["day"]}</b><br/>{esc(d["college"])}</td><td valign="top">'
        + "<br/>".join("• " + esc(i) for i in d["ideas"]) + "</td></tr>" for d in m["days"])
    partners = "\n".join(f'| **{p["name"]}** | {p["role"]} | {p["goal"]} |' for p in m["partners"])
    src = "\n".join(f"- {s}" + (f" {u}" if u else "") for s, u in SOURCES)
    return f"""<div align="center">

{pic("hero", "Toro Innovation Week: five colleges, five days, one Innovation Incubator")}

<p>A proposal to run the CSUDH Innovation Incubator as a shared campus space:<br/>
each college hosts one day a week, a faculty lead gets 3 WTU to program it around innovation with an LA28 focus,<br/>
and all five share one pool of student staff.</p>

<p><b>Status: a faculty proposal by {m["meta"]["author"]}. It is a recommendation, not a university decision.</b></p>

{tiles(head)}

[The week](#-the-week) · [How a day works](#-how-one-college-day-works) · [Two options](#-two-ways-to-staff-it) · [Results so far](#-results-so-far) · [Targets](#-what-success-looks-like) · [Partners](#-student-success-partners) · [LA28](#-why-now-la28) · [Roadmap](#-roadmap) · [Sources](#-sources)

</div>

---

## 🧭 The idea in one minute

<table>
<tr>
<td width="33%" valign="top">

### 📅 One college, one day
Each of the five colleges takes a weekday in the Incubator. The college decides the programming, and its students and faculty fill the room.

</td>
<td width="33%" valign="top">

### 👩‍🏫 3 WTU for a faculty lead
Each college names one faculty lead. Three WTU is {c["lead_hours_sem"]:.0f} hours a semester, about {c["lead_hours_week"]:.0f} hours a week: one day.

</td>
<td width="33%" valign="top">

### 🤝 One shared student team
The student assistants are one pool of {r["student_hours_week"]} hours a week, so every college day has {c["pool_hours_day"]:.0f} hours of student help without hiring its own staff.

</td>
</tr>
</table>

Today the Incubator runs on one faculty director with 6 WTU, part-time student assistants, and no staff. The October 2026 estimate puts the current programs at about {c["work_hours"]} faculty hours a semester, against {c["today_hours"]:.0f} hours funded. This proposal spreads the work across the colleges that benefit from it.

## 📅 The week

{pic("week", "Proposed weekly calendar with a college block, Catapult studio, student group, and partner hour each day")}

| Day | College | LA28 focus | Student group that day |
|---|---|---|---|
{days_tbl}

**What repeats every day**

- **A college innovation block.** The faculty lead runs it: workshops, guest sessions, project time, or a class meeting in the space.
- **A Catapult studio.** Community Engaged Learning pairs with that day's college so student teams do real client projects inside courses. Catapult belongs to all five days.
- **A student group.** Five groups get a weekly home: IEEE Computer Society, Rotaract, the Latine Business Student Association, Toro Guardian Scholars, and HRMA.

**Two speaker series, on different days**

- **Tuesday, 11:30–1:00:** the existing lunch series with Rotaract.
- **Thursday, 11:30–1:00:** a new *LA28 Ready* series on winning Games work, for students and local business owners.

<details>
<summary><b>Starting ideas for each college's LA28 focus</b></summary>
<br/>
<table>
{ideas}
</table>

These are conversation starters. Each college sets its own program.
</details>

## ⚙️ How one college day works

{pic("day", "Four inputs feed one college day, which produces LA28 projects, engaged students, and countable results")}

## ⚖️ Two ways to staff it

{pic("cost", "Annual cost of the base budget, Option B, and Option A")}

| | Option B: five college leads | Option A: five leads + Faculty Director |
|---|---|---|
| Faculty time a semester | {B["wtu_sem"]} WTU ({B["hours_sem"]:,.0f} hours) | {A["wtu_sem"]} WTU ({A["hours_sem"]:,.0f} hours) |
| Faculty time a year | {money(B["faculty"])} | {money(A["faculty"])} |
| Shared student pool | {money(c["students"])} | {money(c["students"])} |
| Supplies and printing | {money(c["supplies"])} | {money(c["supplies"])} |
| **Total a year** | **{money(B["total"])}** | **{money(A["total"])}** |
| Above the {money(c["base"])} base budget | {money(B["gap"])} | {money(A["gap"])} |
| Who coordinates | The five leads, with one chairing each semester | A Faculty Director (6 WTU a semester) |
| Best when | Money is tight and Undergraduate Studies can hold the budget | The campus wants one accountable leader for sponsors and LA28 |

{pic("hours", "Faculty hours funded each semester today and under each option, against the hours the programs need")}

Option B funds {B["hours_sem"]:,.0f} hours against an estimated {c["work_hours"]}, so it works only if Community Engaged Learning carries Catapult and the colleges add their own time. Option A covers the full estimate with room for open hours.

<sub>Costs use Academic Affairs' rate of ${r["wtu_cost"]:,.2f} per WTU and {r["hours_per_wtu"]} hours per WTU a semester. The student pool is {r["student_hours_week"]} hours a week for {r["student_weeks_year"]} weeks at ${r["student_wage"]} an hour. The base budget includes a vacant half-time Executive Director line of {money(r["base_exec_director_line"])}; both gaps assume that line stays and funds faculty time. Without it, the gaps are {money(B["gap_without_ed"])} (B) and {money(A["gap_without_ed"])} (A).</sub>

## 📈 Results so far

The Incubator already produces results with one part-time director. These are from campus records for 2026.

{tiles(m["results"])}

## 🎯 What success looks like

Proposed targets for the first full year. Each would be set with the deans and reported every June.

{tiles(m["targets"])}

## 🧑‍🎓 Student success partners

The space should also serve students who have never thought of themselves as founders. Three campus units and Community Engaged Learning each get a regular hour and a goal.

| Partner | Role in the week | Starting goal |
|---|---|---|
{partners}

<sub>Goals are starting points to confirm with each unit.</sub>

## 🏟 Why now: LA28

- The stadium complex on the CSUDH campus is set to host five Olympic and three Paralympic sports in 2028.
- LA28's procurement plan aims 25% of its addressable spending at small businesses and 75% at the Los Angeles region.
- LA County's *Path to 2028* runs business readiness workshops that campuses and cities can co-host.
- LA28's *Made for Two-Eight* licensing program for small local makers takes applications into February 2027.

An LA28 focus gives every college a reason to use the space and gives Carson, Compton, and South Bay businesses a campus partner while the contracts are still open.

## 🗺 Roadmap

{pic("roadmap", "Milestones from a December 2026 decision to the 2028 Games")}

**What it takes to start in spring 2027**

1. The President endorses the college-day direction and chooses Option A or B.
2. Each dean names a faculty lead and confirms a day.
3. Undergraduate Studies and Community Engaged Learning agree on how Catapult runs across the five days.
4. The Writing Center, First-Year and Transfer Experience, and the Toro Learning & Testing Center confirm their hours and goals.

## 🛠 Run it yourself

```bash
pip install pyyaml pytest
python -m pipeline.build     # redraws every chart, this README, and site/index.html
pytest -q                    # checks the arithmetic and the calendar
```

Change a rate, a day, or a block in [`data/model.yaml`](data/model.yaml) and everything else follows.

## 📚 Sources

{src}

Campus records are not posted online. Dollar figures and counts come from them as of the dates shown; program results are as reported by the Incubator and have not been independently audited.

## ℹ️ About

Prepared by {m["meta"]["author"]}, Professor of Management and Interim Faculty Director of the CSUDH Innovation Incubator, {m["meta"]["as_of"]}. This is an independent faculty proposal. It is not an official publication of California State University, Dominguez Hills, and nothing in it has been approved by the university. Days, hours, leads, and goals are proposals until the colleges and units named here agree to them. See [NOTICE.md](NOTICE.md).
"""


# ---------------------------------------------------------------- website
def site(m, c) -> str:
    A, B = c["options"]["A"], c["options"]["B"]
    r = m["rates"]
    t0, t1, ph = 7.5, 17.0, 58
    cols, lists = [], []
    for d in m["days"]:
        blocks = []
        items = []
        for b in m["schedule"][d["key"]]:
            top = (b["start"] - t0) * ph
            hgt = (b["end"] - b["start"]) * ph - 4
            span = f'{clock(b["start"])}–{clock(b["end"])}'
            blocks.append(f'<div class="blk k-{b["kind"]}" style="top:{top:.0f}px;height:{hgt:.0f}px" '
                          f'title="{esc(b["label"])}, {span}"><span class="tag">{KIND_TAG[b["kind"]]} · {span}</span>'
                          f'<span class="lab">{esc(b["label"])}</span></div>')
            items.append(f'<li class="k-{b["kind"]}"><span class="tag">{span} · {KIND_TAG[b["kind"]]}</span>{esc(b["label"])}</li>')
        cols.append(f'<button class="col" data-day="{d["key"]}" style="--c:{d["color"]};--cd:{d["color_dark"]};--on:{on_fill(d["color"])}" '
                    f'aria-label="{d["day"]}: {esc(d["college"])}"><span class="colhead">{d["day"]}<b>{d["short"]}</b></span>'
                    f'<span class="track" style="height:{(t1 - t0) * ph:.0f}px">{"".join(blocks)}</span></button>')
        lists.append(f'<article class="daycard" id="day-{d["key"]}" style="--c:{d["color"]};--cd:{d["color_dark"]};--on:{on_fill(d["color"])}">'
                     f'<header><span class="pill">{d["day"]}</span><h3>{esc(d["college"])}</h3></header>'
                     f'<p class="focus"><b>LA28 focus:</b> {esc(d["focus"])}</p>'
                     f'<ul class="sched">{"".join(items)}</ul>'
                     f'<p class="sub"><b>Starting ideas</b></p><ul>{"".join("<li>" + esc(i) + "</li>" for i in d["ideas"])}</ul>'
                     f'<p class="meta"><b>Student group:</b> {esc(d["group"])} · <b>Partner hour:</b> {esc(d["partner"])}</p></article>')
    hours = "".join(f'<span style="top:{(h - t0) * ph:.0f}px">{h if h <= 12 else h - 12} {"am" if h < 12 else "pm"}</span>' for h in range(8, 18))

    def tile(x):
        return (f'<div class="tile"><b>{esc(x["value"])}</b><span>{esc(x["label"])}</span>'
                + (f'<small>{esc(x["note"])}</small>' if x.get("note") else "") + "</div>")

    head = [{"value": "5", "label": "colleges, one day each"}, {"value": "3 WTU", "label": "per college faculty lead"},
            {"value": str(c["college_days_sem"]), "label": "college days a semester"},
            {"value": "2", "label": "speaker series a week"}, {"value": "5", "label": "student groups at home here"},
            {"value": str(r["student_hours_week"]), "label": "shared student hours a week"}]
    partners = "".join(f'<div class="pcard"><h3>{esc(p["name"])}</h3><p>{esc(p["role"])}</p><p class="goal"><b>Goal:</b> {esc(p["goal"])}</p></div>'
                       for p in m["partners"])
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def when(dv):
        p = dv.split("-")
        return f"{months[int(p[1]) - 1]} {int(p[2])}, {p[0]}" if len(p) == 3 else f"{months[int(p[1]) - 1]} {p[0]}"
    road = "".join(f'<li class="m-{x["kind"]}"><time>{when(x["date"])}</time><span>{esc(x["label"])}</span></li>' for x in m["milestones"])
    src = "".join("<li>" + esc(s) + (f' <a href="{u}">{u.split("/")[2]}</a>' if u else "") + "</li>" for s, u in SOURCES)
    data = {"base": c["base"], "work": c["work_hours"], "today": c["today_hours"],
            "students": c["students"], "supplies": c["supplies"],
            "A": {k: A[k] for k in ("total", "gap", "faculty", "wtu_sem", "hours_sem")},
            "B": {k: B[k] for k in ("total", "gap", "faculty", "wtu_sem", "hours_sem")}}
    return TEMPLATE.format(
        title=m["meta"]["title"], tagline=m["meta"]["tagline"], author=m["meta"]["author"], as_of=m["meta"]["as_of"],
        head="".join(tile(x) for x in head), hours=hours, cols="".join(cols), lists="".join(lists),
        results="".join(tile(x) for x in m["results"]), targets="".join(tile(x) for x in m["targets"]),
        partners=partners, road=road, src=src, data=json.dumps(data),
        lead_hours=f'{c["lead_hours_sem"]:.0f}', lead_week=f'{c["lead_hours_week"]:.0f}', pool_day=f'{c["pool_hours_day"]:.0f}',
        pool_week=r["student_hours_week"], work=c["work_hours"], today=f'{c["today_hours"]:.0f}',
        rate=f'{r["wtu_cost"]:,.2f}', base=money(c["base"]), ed=money(r["base_exec_director_line"]),
        gapB2=money(B["gap_without_ed"]), gapA2=money(A["gap_without_ed"]), track_h=f"{(t1 - t0) * ph:.0f}")


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}: one college, one day</title>
<meta name="description" content="A faculty proposal to run the CSUDH Innovation Incubator as a shared campus space: each college hosts one day a week with an LA28 focus.">
<style>
:root{{--bg:#ffffff;--card:#f6f5f1;--ink:#1c1b19;--soft:#5d5b54;--line:#dedcd3;--accent:#860038;--gold:#b88a00;--on-accent:#fff;color-scheme:light dark}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151413;--card:#201f1d;--ink:#f0efec;--soft:#b5b3a8;--line:#35332f;--accent:#e0608c;--gold:#e3b341;--on-accent:#1c1b19}}}}
*{{box-sizing:border-box}}
body{{margin:0;overflow-x:hidden;background:var(--bg);color:var(--ink);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}}
main{{max-width:1120px;margin:0 auto;padding:0 20px 80px}}
h1{{font-size:clamp(2.2rem,6vw,4rem);line-height:1.05;margin:0 0 .3em;letter-spacing:-.02em}}
h2{{font-size:1.7rem;margin:2.6em 0 .3em;letter-spacing:-.01em}}
h3{{margin:.2em 0;font-size:1.05rem}}
p.lede{{font-size:1.2rem;color:var(--soft);max-width:60ch;margin:.2em 0 1em}}
p.sec{{color:var(--soft);max-width:68ch;margin:0 0 1.2em}}
.status{{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:4px 14px;font-size:.85rem;color:var(--soft);margin-bottom:22px}}
.status b{{color:var(--accent)}}
header.hero{{padding:64px 0 10px}}
nav{{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:.92rem;margin:18px 0 0}}
nav a{{color:var(--soft);text-decoration:none;border-bottom:1px solid var(--line)}}
nav a:hover{{color:var(--accent)}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:22px 0}}
.tile{{background:var(--card);border-radius:12px;padding:16px 18px;display:flex;flex-direction:column;gap:2px}}
.tile b{{font-size:2rem;line-height:1.1;letter-spacing:-.02em}}
.tile span{{font-size:.93rem}}
.tile small{{color:var(--soft);font-size:.8rem}}
.three{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}}
.three div,.pcard{{background:var(--card);border-radius:12px;padding:18px}}
.three p,.pcard p{{margin:.3em 0;color:var(--soft);font-size:.95rem}}
.pcard .goal{{color:var(--ink)}}
/* calendar */
.cal{{display:grid;grid-template-columns:48px repeat(5,1fr);gap:8px;margin-top:8px}}
.axis{{position:relative;margin-top:44px;height:{track_h}px}}
.axis span{{position:absolute;right:4px;transform:translateY(-50%);font-size:.72rem;color:var(--soft);white-space:nowrap}}
.col{{all:unset;display:block;cursor:pointer;border-radius:10px;--col:var(--c)}}
@media (prefers-color-scheme:dark){{.col,.daycard{{--col:var(--cd)}}}}
.daycard{{--col:var(--c)}}
.col:focus-visible{{outline:2px solid var(--accent);outline-offset:3px}}
.colhead{{display:flex;justify-content:space-between;align-items:center;height:36px;padding:0 10px;border-radius:8px;background:var(--col);color:var(--on);font-size:.82rem;font-weight:600;margin-bottom:8px}}
.colhead b{{font-size:.95rem}}
.track{{display:block;position:relative;background:repeating-linear-gradient(to bottom,var(--line) 0 1px,transparent 1px 58px);background-position:0 29px;border-radius:6px}}
.blk{{position:absolute;left:0;right:0;border-radius:6px;padding:5px 8px;overflow:hidden;background:var(--card);border:1px solid var(--line);display:flex;flex-direction:column;gap:1px}}
.blk .tag,.sched .tag{{font-size:.6rem;letter-spacing:.04em;font-weight:700;color:var(--soft)}}
.blk .lab{{font-size:.78rem;font-weight:600;line-height:1.2}}
.blk.k-college{{background:var(--col);border-color:transparent;color:var(--on)}}
.blk.k-college .tag{{color:var(--on);opacity:.85}}
.blk.k-program{{border-style:dashed}}
.col:hover .blk,.col[aria-pressed=true] .blk{{border-color:var(--col)}}
.col[aria-pressed=true] .colhead{{box-shadow:0 0 0 3px var(--bg),0 0 0 5px var(--col)}}
.hint{{font-size:.85rem;color:var(--soft);margin:10px 0 0}}
.daycards{{margin-top:16px}}
.daycard{{display:none;background:var(--card);border-radius:12px;padding:20px;border-left:6px solid var(--col)}}
.daycard.on{{display:block}}
.daycard header{{display:flex;gap:12px;align-items:center;flex-wrap:wrap}}
.pill{{background:var(--col);color:var(--on);border-radius:999px;padding:2px 12px;font-size:.8rem;font-weight:700}}
.daycard ul{{margin:.3em 0 .6em;padding-left:1.2em}}
.daycard .sched{{display:none;list-style:none;padding:0}}
.sched li{{padding:7px 0;border-bottom:1px solid var(--line);display:flex;flex-direction:column}}
.daycard .meta,.daycard .sub{{font-size:.92rem;margin:.4em 0}}
@media (max-width:860px){{.cal{{display:none}}.daycard{{display:block;margin-bottom:14px}}.daycard .sched{{display:block}}.hint{{display:none}}}}
/* options */
.seg{{display:inline-flex;border:1px solid var(--line);border-radius:999px;padding:3px;margin:6px 0 16px}}
.seg button{{all:unset;cursor:pointer;padding:7px 18px;border-radius:999px;font-size:.92rem}}
.seg button[aria-pressed=true]{{background:var(--accent);color:var(--on-accent);font-weight:600}}
.seg button:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
.bars{{display:grid;gap:14px;margin:8px 0 6px}}
.bar{{display:grid;grid-template-columns:minmax(110px,200px) 1fr;gap:12px;align-items:center;font-size:.93rem}}
.bar .rail{{position:relative;height:28px}}
.bar .fill{{height:100%;border-radius:0 4px 4px 0;background:var(--soft);opacity:.55;transition:width .35s;min-width:2px}}
.bar.em .fill{{background:var(--accent);opacity:1}}
.bar .val{{position:absolute;top:50%;transform:translateY(-50%);padding-left:8px;font-weight:600;white-space:nowrap;transition:left .35s}}
.bar .ref{{position:absolute;top:-5px;bottom:-5px;border-left:2px dashed var(--gold)}}
.twocol{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(320px,100%),1fr));gap:26px}}
.panel{{background:var(--card);border-radius:12px;padding:20px}}
.panel h3{{margin-bottom:10px}}
.note{{font-size:.85rem;color:var(--soft)}}
.verdict{{margin:16px 0 0;padding:14px 16px;border-left:4px solid var(--accent);background:var(--card);border-radius:0 10px 10px 0}}
ul.plain{{padding-left:1.2em}}
ol.road{{list-style:none;padding:0;margin:0;border-left:2px solid var(--line);margin-left:8px}}
ol.road li{{position:relative;padding:8px 0 8px 22px;display:flex;gap:14px;flex-wrap:wrap}}
ol.road li::before{{content:"";position:absolute;left:-8px;top:14px;width:12px;height:12px;border-radius:50%;background:var(--soft);border:2px solid var(--bg)}}
ol.road li.m-gate::before{{background:var(--accent);border-radius:2px;transform:rotate(45deg)}}
ol.road li.m-games::before{{background:var(--gold)}}
ol.road time{{color:var(--soft);min-width:108px;font-size:.92rem}}
ol.road li.m-gate span,ol.road li.m-games span{{font-weight:600}}
footer{{margin-top:60px;padding-top:20px;border-top:1px solid var(--line);font-size:.85rem;color:var(--soft)}}
footer li{{margin:.3em 0}}
a{{color:var(--accent)}}
</style>
</head>
<body>
<main>
<header class="hero">
  <span class="status"><b>Faculty proposal</b> · not a university decision · {as_of}</span>
  <h1>{title}</h1>
  <p class="lede">{tagline} Each college hosts one day a week in the CSUDH Innovation Incubator, led by a faculty member with 3 WTU, built around innovation with an LA28 focus.</p>
  <nav><a href="#week">The week</a><a href="#options">Two options</a><a href="#results">Results so far</a><a href="#targets">Targets</a><a href="#partners">Partners</a><a href="#la28">Why LA28</a><a href="#roadmap">Roadmap</a><a href="#sources">Sources</a><a href="planner.html">Block planner</a></nav>
  <div class="tiles">{head}</div>
</header>

<section>
  <h2>The idea in one minute</h2>
  <div class="three">
    <div><h3>One college, one day</h3><p>Each of the five colleges takes a weekday. The college sets the programming, and its students and faculty fill the room.</p></div>
    <div><h3>3 WTU for a faculty lead</h3><p>Three WTU is {lead_hours} hours a semester, about {lead_week} hours a week: one day. Each dean names the lead.</p></div>
    <div><h3>One shared student team</h3><p>Student assistants are one pool of {pool_week} hours a week, so every college day gets {pool_day} hours of help without hiring its own staff.</p></div>
  </div>
  <p class="sec" style="margin-top:16px">Today the Incubator runs on one faculty director with 6 WTU and no staff. Current programs need about {work} faculty hours a semester; {today} are funded. This proposal spreads the work across the colleges that benefit from it.</p>
</section>

<section id="week">
  <h2>The week</h2>
  <p class="sec">Every day has a college block, a Catapult studio run with Community Engaged Learning, and a student group. Tuesday and Thursday add a lunch speaker series.</p>
  <div class="cal" role="group" aria-label="Proposed weekly calendar">
    <div class="axis">{hours}</div>
    {cols}
  </div>
  <p class="hint">Select a day to see its LA28 focus and starting ideas. Days and hours are a starting proposal, open for the deans to trade.</p>
  <div class="daycards">{lists}</div>
</section>

<section id="options">
  <h2>Two ways to staff it</h2>
  <p class="sec">Both options give each college 3 WTU and share one student pool. The difference is whether a Faculty Director sits on top.</p>
  <div class="seg" role="group" aria-label="Choose an option">
    <button data-opt="B" aria-pressed="true">Option B: five college leads</button>
    <button data-opt="A" aria-pressed="false">Option A: add a Faculty Director</button>
  </div>
  <div class="twocol">
    <div class="panel"><h3>Cost a year</h3>
      <div class="bars" id="cost"></div>
      <p class="note" id="costnote"></p></div>
    <div class="panel"><h3>Faculty hours a semester</h3>
      <div class="bars" id="hours"></div>
      <p class="note">The dashed line marks the {work} hours the current programs need each semester (October 2026 estimate).</p></div>
  </div>
  <p class="verdict" id="verdict"></p>
  <p class="note">Costs use Academic Affairs' rate of ${rate} per WTU and 45 hours per WTU a semester. The {base} base budget includes a vacant half-time Executive Director line of {ed}; both gaps assume it stays and funds faculty time. Without it, the gaps are {gapB2} (B) and {gapA2} (A).</p>
</section>

<section id="results">
  <h2>Results so far</h2>
  <p class="sec">The Incubator already produces results with one part-time director. These come from campus records for 2026.</p>
  <div class="tiles">{results}</div>
</section>

<section id="targets">
  <h2>What success looks like</h2>
  <p class="sec">Proposed targets for the first full year, to be set with the deans and reported every June.</p>
  <div class="tiles">{targets}</div>
</section>

<section id="partners">
  <h2>Student success partners</h2>
  <p class="sec">The space should also serve students who have never thought of themselves as founders. Each partner gets a regular hour and a goal to confirm together.</p>
  <div class="three">{partners}</div>
</section>

<section id="la28">
  <h2>Why now: LA28</h2>
  <ul class="plain">
    <li>The stadium complex on the CSUDH campus is set to host five Olympic and three Paralympic sports in 2028.</li>
    <li>LA28's procurement plan aims 25% of its addressable spending at small businesses and 75% at the Los Angeles region.</li>
    <li>LA County's Path to 2028 runs business readiness workshops that campuses and cities can co-host.</li>
    <li>LA28's Made for Two-Eight licensing program for small local makers takes applications into February 2027.</li>
  </ul>
  <p class="sec">An LA28 focus gives every college a reason to use the space, and gives Carson, Compton, and South Bay businesses a campus partner while contracts are still open.</p>
</section>

<section id="roadmap">
  <h2>Roadmap</h2>
  <p class="sec">A spring 2027 pilot gives the model three semesters before the Games. Diamonds are decisions.</p>
  <ol class="road">{road}</ol>
</section>

<footer id="sources">
  <p><b>Sources</b></p>
  <ul>{src}</ul>
  <p>Campus records are not posted online. Program results are as reported by the Incubator and have not been independently audited. Days, hours, leads, and goals are proposals until the colleges and units named here agree to them.</p>
  <p>Prepared by {author}, Professor of Management and Interim Faculty Director of the CSUDH Innovation Incubator. This is an independent faculty proposal. It is not an official publication of California State University, Dominguez Hills.</p>
</footer>
</main>
<script>
const D={data};
const $=s=>document.querySelector(s), fmt=n=>'$'+Math.round(n).toLocaleString('en-US');
function bars(el,rows,max,f,ref){{
  el.innerHTML=rows.map(r=>{{const w=r.v/max*62;return `<div class="bar ${{r.em?'em':''}}" title="${{r.l}}: ${{f(r.v)}}"><span>${{r.l}}</span><div class="rail">${{ref?`<i class="ref" style="left:${{ref/max*62}}%"></i>`:''}}<div class="fill" style="width:${{w}}%"></div><span class="val" style="left:${{w}}%">${{f(r.v)}}</span></div></div>`}}).join('');
}}
function show(k){{
  const o=D[k], other=k==='A'?'B':'A';
  document.querySelectorAll('.seg button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.opt===k));
  bars($('#cost'),[{{l:'Base budget today',v:D.base}},{{l:'Option '+k,v:o.total,em:1}}],D.A.total,fmt);
  bars($('#hours'),[{{l:'Today: 6 WTU',v:D.today}},{{l:'Option '+k+': '+o.wtu_sem+' WTU',v:o.hours_sem,em:1}}],D.A.hours_sem,n=>n.toLocaleString('en-US')+' hours',D.work);
  $('#costnote').textContent=`Faculty time ${{fmt(o.faculty)}}, student pool ${{fmt(D.students)}}, supplies ${{fmt(D.supplies)}}. That is ${{fmt(o.gap)}} above the base budget.`;
  $('#verdict').innerHTML=k==='B'
   ?`<b>Option B</b> costs ${{fmt(o.total)}} a year, ${{fmt(o.gap)}} above today's base. It funds ${{o.hours_sem}} hours against ${{D.work}} needed, so it works only if Community Engaged Learning carries Catapult and the colleges add their own time. One lead chairs each semester.`
   :`<b>Option A</b> costs ${{fmt(o.total)}} a year, ${{fmt(o.gap)}} above today's base. It funds ${{o.hours_sem}} hours, which covers the full ${{D.work}}-hour estimate, and gives sponsors and the LA28 effort one accountable leader.`;
}}
document.querySelectorAll('.seg button').forEach(b=>b.addEventListener('click',()=>show(b.dataset.opt)));
show('B');
function pick(k){{
  document.querySelectorAll('.col').forEach(c=>c.setAttribute('aria-pressed',c.dataset.day===k));
  document.querySelectorAll('.daycard').forEach(c=>c.classList.toggle('on',c.id==='day-'+k));
}}
document.querySelectorAll('.col').forEach(c=>c.addEventListener('click',()=>pick(c.dataset.day)));
pick('mon');
</script>
</body>
</html>
"""


def main() -> None:
    m = load()
    c = compute(m)
    CHARTS.mkdir(parents=True, exist_ok=True)
    SITE.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        for name, fn in (("hero", lambda t: chart_hero(m, t)), ("week", lambda t: chart_week(m, t)),
                         ("cost", lambda t: chart_cost(m, c, t)), ("hours", lambda t: chart_hours(m, c, t)),
                         ("roadmap", lambda t: chart_roadmap(m, t)), ("day", lambda t: chart_day(m, c, t))):
            (CHARTS / f"{name}-{theme}.svg").write_text(fn(theme), encoding="utf-8")
    (ROOT / "README.md").write_text(readme(m, c), encoding="utf-8")
    (SITE / "index.html").write_text(site(m, c), encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    A, B = c["options"]["A"], c["options"]["B"]
    print(f"Option A {money(A['total'])} (gap {money(A['gap'])}); Option B {money(B['total'])} (gap {money(B['gap'])})")


if __name__ == "__main__":
    main()
