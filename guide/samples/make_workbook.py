#!/usr/bin/env python3
"""Write Haltestellen_Busbetrieb_Nord.xlsx: the FICTIONAL, deliberately messy workbook of a regional
bus company (the guide's messy-source sample). Real stop names, UIC numbers and municipality names from the
snapshot (so results can be checked); everything else (lines, platforms, local codes, fare zones) is
invented. Needs openpyxl (the backend's venv has it)."""

import datetime as dt
import json
import random
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
stops = json.loads((HERE / "data" / "reference" / "stops.json").read_text())
munis = {
    m["id"]: m
    for m in json.loads((HERE / "data" / "reference" / "municipalities.json").read_text())
}
ops = {o["id"]: o for o in json.loads((HERE / "data" / "reference" / "operators.json").read_text())}
rng = random.Random(2026)

# The fictional company runs the town buses of Chur and its neighbours: real Bus und Service (Chur) stops.
mine = [
    s
    for s in stops
    if s["operator"]
    and ops[s["operator"]]["code"] == "BuS/cb"
    and s["validTo"] is None
    and munis[s["parent"]]["name"]
    in ("Chur", "Haldenstein", "Trimmis", "Domat/Ems", "Felsberg", "Untervaz")
]
mine = sorted(mine, key=lambda s: (munis[s["parent"]]["name"], s["name"]))
per, picked = {}, []
for s in mine:  # up to 36 in Chur, 6 in each neighbour
    n = munis[s["parent"]]["name"]
    if per.get(n, 0) < (36 if n == "Chur" else 6):
        per[n] = per.get(n, 0) + 1
        picked.append(s)
mine = sorted(picked, key=lambda s: (s["name"].split(",")[0], s["name"]))
# Make sure the register's own name for the main station appears: "Chur, Bahnhof" style names are the norm.
CHUR_NAMES = {"Chur": ["Chur", "Coira", "Cuira"]}

wb = Workbook()
ws = wb.active
ws.title = "Haltestellen"
ws["A1"] = (
    "Busbetrieb Nord - Haltestellenliste (FIKTIVE Firma, erfundene Linien und Codes; Namen und Nummern aus dem Didok-Register)"
)
ws["A1"].font = Font(bold=True, size=13)
ws["A2"] = "Stand: Herbstfahrplan, intern - nicht verteilen"
heads = [
    "Haltestelle",
    "Gemeinde",
    "Linien",
    "UIC-Nr",
    "gültig ab",
    "Barrierefrei J/N",
    "Perron A",
    "Perron B",
    "Perron C",
    "Bemerkung",
]
for c, h in enumerate(heads, 1):
    cell = ws.cell(row=3, column=c, value=h)
    cell.font = Font(bold=True)
    cell.fill = PatternFill("solid", fgColor="DDDDDD")

names_rows = []
for i, s in enumerate(mine):
    r = 4 + i
    muni = munis[s["parent"]]["name"]
    name = s["name"]
    # ten rows differ from the register by punctuation: "Chur, Bahnhof" -> "Chur Bahnhof"
    if i % 4 == 0 and ", " in name and len(names_rows) < 10:
        name = name.replace(", ", " ", 1)
        names_rows.append(r)
    if muni == "Chur":
        muni = CHUR_NAMES["Chur"][i % 3]  # name drift: Chur / Coira / Cuira
    lines = rng.choice(["1", "2", "1, 2", "1, 2, 4", "4", "n/a", "?", "2, 4, 6"])
    uic = f"{s['number']} " if i % 3 else str(s["number"])  # text, often with a trailing space
    since = (
        dt.date.fromisoformat(s["validFrom"]).strftime("%d.%m.%Y")
        if i % 11
        else rng.choice(["-", "?", "n/a"])
    )
    barrier = rng.choice(["J", "N", "J", "J", "n/a", "?", "-"])
    flags = [("x" if rng.random() < p else None) for p in (0.7, 0.5, 0.15)]
    note = rng.choice(
        [
            None,
            None,
            None,
            "Wartehäuschen",
            "Fahrplan erneuert",
            "Standort prüfen",
            "siehe Skizze",
        ]
    )
    row = [name, muni, lines, uic, since, barrier, *flags, note]
    for c, v in enumerate(row, 1):
        cell = ws.cell(row=r, column=c, value=v)
        if c == 4:
            cell.number_format = "@"  # text
for c, w in enumerate([34, 14, 12, 12, 12, 16, 9, 9, 9, 22], 1):
    ws.column_dimensions[get_column_letter(c)].width = w

wn = wb.create_sheet("Namen")
wn.append(["Gemeinde (Namen in den Landessprachen)"])
wn["A1"].font = Font(bold=True)
wn.append([])
wn.append(["DE", "FR", "IT", "RM"])
for c in range(1, 5):
    wn.cell(row=3, column=c).font = Font(bold=True)
seen = []
near = [
    m
    for m in munis.values()
    if m["name"]
    in (
        "Chur",
        "Haldenstein",
        "Trimmis",
        "Domat/Ems",
        "Felsberg",
        "Untervaz",
        "Zizers",
        "Landquart",
        "Arosa",
        "Churwalden",
        "Bonaduz",
        "Rhäzüns",
        "Tamins",
        "Maienfeld",
    )
]
for m in sorted(near, key=lambda m: m["name"]):
    seen.append(m["name"])
    t = m["translations"]
    row = [t.get("de"), t.get("fr"), t.get("it"), t.get("rm")]
    if len(seen) % 2 == 0:
        row[3] = None  # partly empty: no Romansh
    if len(seen) % 3 == 0:
        row[1] = None
    wn.append(row)

wl = wb.create_sheet("Lokale Codes")
wl["A1"] = "Eigene Haltestellencodes (FIKTIV)"
wl["F1"] = "Tarifzonen (FIKTIV)"
wl["A1"].font = wl["F1"].font = Font(bold=True)
for c, h in enumerate(["Haltestelle", "UIC", "Code Busbetrieb"], 1):
    wl.cell(row=3, column=c, value=h).font = Font(bold=True)
for c, h in enumerate(["Zone", "Haltestelle", "Tarifverbund"], 6):
    wl.cell(row=3, column=c, value=h).font = Font(bold=True)
for i, s in enumerate(mine[:25]):
    wl.cell(row=4 + i, column=1, value=s["name"])
    wl.cell(row=4 + i, column=2, value=str(s["number"]))
    wl.cell(row=4 + i, column=3, value=f"BN-{100 + i * 3}")
    wl.cell(row=4 + i, column=6, value=f"Z{1 + i // 9}")
    wl.cell(row=4 + i, column=7, value=s["name"])
    wl.cell(row=4 + i, column=8, value="Tarifverbund Nord (fiktiv)")
out = HERE / "Haltestellen_Busbetrieb_Nord.xlsx"
wb.save(out)
print(out, len(mine), "stop rows,", len(names_rows), "rows renamed by punctuation")
