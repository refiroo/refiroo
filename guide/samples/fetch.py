#!/usr/bin/env python3
"""Download a dated snapshot of the real sources and turn it into the guide's two data sets.

    python3 fetch.py            # download into snapshot/, then write data/docs and data/reference
    python3 fetch.py --offline  # only transform the snapshot already in snapshot/

The reference set is every current service point of Graubuenden. The docs set is the part of it that
the guide's examples run on: the stops that a train serves, with everything they point at.

Sources (all read-only, no key needed):
  S1  Didok service points, Graubuenden, from the Explore API of data.sbb.ch
      (based on opentransportdata.swiss).
  S2  Wikidata (SPARQL): municipality labels by P771, items of stations by P722, the canton.
  S5  A FICTIONAL regional ticketing system, made up for the demonstration; marked as such in every
      name it produces.

Real data only; the one invented thing is S5, and it says so everywhere it appears.
Standard library only. The attribution lines are in SOURCES.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAP = HERE / "snapshot"
DATA = HERE / "data"

DIDOK_URL = (
    "https://data.sbb.ch/api/explore/v2.1/catalog/datasets/"
    "dienststellen-gemass-opentransportdataswiss/exports/json"
)
DIDOK_QUERY = {"where": 'cantonabbreviation="GR"', "timezone": "UTC"}
WIKIDATA_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "refiroo-guide-samples/1.0"
CANTON_QID = "Q11925"  # Canton of the Grisons

LANGS = [
    ("de", "German"),
    ("fr", "French"),
    ("it", "Italian"),
    ("rm", "Romansh"),
    ("en", "English"),
]

# Mode groups are our grouping; the codes are Didok's names for the means of transport.
MODES = [
    ("GRP_RAIL", "Rail-bound", None),
    ("TRAIN", "Train", "GRP_RAIL"),
    ("RACK_RAILWAY", "Rack railway", "GRP_RAIL"),
    ("CABLE_RAILWAY", "Funicular", "GRP_RAIL"),
    ("TRAM", "Tram", "GRP_RAIL"),
    ("METRO", "Metro", "GRP_RAIL"),
    ("GRP_ROAD", "Road", None),
    ("BUS", "Bus", "GRP_ROAD"),
    ("GRP_WATER", "Water", None),
    ("BOAT", "Boat", "GRP_WATER"),
    ("GRP_CABLEWAY", "Cableway", None),
    ("CABLE_CAR", "Cable car", "GRP_CABLEWAY"),
    ("CHAIRLIFT", "Chairlift", "GRP_CABLEWAY"),
    ("GRP_OTHER", "Other", None),
    ("ELEVATOR", "Elevator", "GRP_OTHER"),
]
# S5: FICTIONAL ticketing codes. (code, label, kind, targets) - targets are stop numbers (or municipality
# FSO numbers); an empty list is deliberately unmapped. Real stop numbers and names, made-up codes.
FICTIONAL_TICKETING = [
    ("T-0412", "Zone 1 stop: Chur Wiesental", "stop", [8509006]),
    ("T-0413", "Zone 1 stop: Haldenstein", "stop", [8509051]),
    ("T-0414", "Zone 2 stop: Zizers", "stop", [8509054]),
    ("T-0415", "Zone 2 stop: Igis", "stop", [8509055]),
    ("T-0416", "Zone 2 stop: Malans GR", "stop", [8509057]),
    ("T-0417", "Zone 3 stop: Grüsch", "stop", [8509059]),
    ("T-0418", "Zone 3 stop: Schiers", "stop", [8509060]),
    ("T-0419", "Zone 5 stop: St. Moritz", "stop", [8509253]),
    (
        "T-0300",
        "Zone 1 hub: Chur and Chur West (two stops, one code)",
        "stop",
        [8509000, 8509050],
    ),
    ("T-0500", "Zone 4 stop: Arosa", "stop", [8509157]),
    ("T-0501", "Zone 4 stop: Davos Platz", "stop", [8509073]),
    ("T-9999", "Special day pass (no stop; left unmapped on purpose)", "stop", []),
]
NS = uuid.UUID("6f1d2c1e-8f64-4a73-9a52-5b0c7d0a0e11")


def uid(kind: str, key: object) -> str:
    """A stable ID for a record, so a second load finds the same record."""
    # The API wants UUID version 4: take the name-based bytes and stamp them as v4 (still stable).
    return str(uuid.UUID(bytes=uuid.uuid5(NS, f"{kind}:{key}").bytes, version=4))


def http(url: str, data: bytes | None = None, accept: str = "application/json") -> bytes:
    req = urllib.request.Request(
        url, data=data, headers={"User-Agent": USER_AGENT, "Accept": accept}
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return resp.read()


def sparql(query: str) -> list[dict]:
    body = urllib.parse.urlencode({"query": query}).encode()
    raw = http(WIKIDATA_URL, body, "application/sparql-results+json")
    return json.loads(raw)["results"]["bindings"]


def download(snapshot_date: str) -> None:
    SNAP.mkdir(exist_ok=True)
    url = DIDOK_URL + "?" + urllib.parse.urlencode(DIDOK_QUERY)
    print("Didok ...", flush=True)
    didok = json.loads(http(url))
    (SNAP / "didok_graubuenden.json").write_text(json.dumps(didok, ensure_ascii=False, indent=0))

    fso = sorted({r["fsonumber"] for r in didok})
    print("Wikidata municipalities ...", flush=True)
    q = """SELECT ?item ?fso ?de ?fr ?it ?rm ?en WHERE {
 VALUES ?fso { %s } ?item wdt:P771 ?fso .
 OPTIONAL { ?item rdfs:label ?de FILTER(lang(?de)="de") }
 OPTIONAL { ?item rdfs:label ?fr FILTER(lang(?fr)="fr") }
 OPTIONAL { ?item rdfs:label ?it FILTER(lang(?it)="it") }
 OPTIONAL { ?item rdfs:label ?rm FILTER(lang(?rm)="rm") }
 OPTIONAL { ?item rdfs:label ?en FILTER(lang(?en)="en") } }""" % " ".join(f'"{f}"' for f in fso)
    muni = sparql(q)
    (SNAP / "wikidata_municipalities.json").write_text(
        json.dumps(muni, ensure_ascii=False, indent=0)
    )

    print("Wikidata stations ...", flush=True)
    uic = sorted({str(r["number"]) for r in didok})
    q = """SELECT ?item ?uic ?label WHERE {
 VALUES ?uic { %s } ?item wdt:P722 ?uic .
 OPTIONAL { ?item rdfs:label ?label FILTER(lang(?label)="de") } }""" % " ".join(
        f'"{u}"' for u in uic
    )
    stations = sparql(q)
    (SNAP / "wikidata_stations.json").write_text(json.dumps(stations, ensure_ascii=False, indent=0))

    print("Wikidata canton ...", flush=True)
    q = (
        """SELECT ?l ?lang WHERE { wd:%s rdfs:label ?l BIND(lang(?l) AS ?lang)
 FILTER(?lang IN ("de","fr","it","rm","en")) }"""
        % CANTON_QID
    )
    canton = sparql(q)
    (SNAP / "wikidata_canton.json").write_text(json.dumps(canton, ensure_ascii=False, indent=0))

    meta = {
        "snapshotDate": snapshot_date,
        "retrievedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "sources": [
            {
                "id": "S1",
                "name": "Service Points (Didok) based on opentransportdata.swiss",
                "url": url,
                "original": "https://opentransportdata.swiss",
                "terms": "https://opentransportdata.swiss/en/terms-of-use/",
                "attribution": f"Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB, snapshot {snapshot_date}",
                "records": len(didok),
            },
            {
                "id": "S2",
                "name": "Wikidata (SPARQL)",
                "url": WIKIDATA_URL,
                "terms": "https://www.wikidata.org/wiki/Wikidata:Licensing (CC0)",
                "attribution": "Wikidata, CC0",
                "municipalityRows": len(muni),
                "stationRows": len(stations),
                "cantonLabels": len(canton),
            },
            {
                "id": "S5",
                "name": "Regional ticketing system (FICTIONAL)",
                "url": None,
                "attribution": "Fictional: invented for this demonstration; codes mean nothing outside it",
            },
        ],
    }
    (SNAP / "SNAPSHOT.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))


def end_exclusive(validto: str) -> str | None:
    """Didok validto is the last valid day and 9999-12-31 means open; the engine's end is exclusive."""
    if validto.startswith("9999"):
        return None
    return (dt.date.fromisoformat(validto) + dt.timedelta(days=1)).isoformat()


def transform() -> None:
    meta = json.loads((SNAP / "SNAPSHOT.json").read_text())
    meta["sources"] = [s for s in meta["sources"] if s["id"] != "S3"]  # not used
    didok = json.loads((SNAP / "didok_graubuenden.json").read_text())
    muni_wd = json.loads((SNAP / "wikidata_municipalities.json").read_text())
    stations_wd = json.loads((SNAP / "wikidata_stations.json").read_text())
    canton_wd = json.loads((SNAP / "wikidata_canton.json").read_text())
    qid = lambda b: b["item"]["value"].rsplit("/", 1)[1]  # noqa: E731

    # --- geography
    canton_row = didok[0]
    canton = {
        "id": uid("canton", canton_row["cantonabbreviation"]),
        "name": canton_row["cantonname"],
        "abbreviation": canton_row["cantonabbreviation"],
        "fso": int(canton_row["cantonfsonumber"]),
        "translations": {b["lang"]["value"]: b["l"]["value"] for b in canton_wd},
    }
    districts, municipalities = {}, {}
    for r in didok:
        districts.setdefault(
            r["districtfsonumber"],
            {
                "id": uid("district", r["districtfsonumber"]),
                "name": r["districtname"],
                "fso": int(r["districtfsonumber"]),
                "parent": canton["id"],
            },
        )
        if r["fsonumber"] not in municipalities:
            municipalities[r["fsonumber"]] = {
                "id": uid("municipality", r["fsonumber"]),
                "name": r["municipalityname"],
                "fso": int(r["fsonumber"]),
                "parent": districts[r["districtfsonumber"]]["id"],
            }
    wd_by_fso = {b["fso"]["value"]: b for b in muni_wd}
    for fso, m in municipalities.items():
        b = wd_by_fso.get(fso)
        m["qid"] = qid(b) if b else None
        m["translations"] = {lang: b[lang]["value"] for lang, _ in LANGS if b and lang in b}

    # --- operators
    operators = {}
    for r in didok:
        sb = r["businessorganisation"]
        if sb and sb not in operators:
            operators[sb] = {
                "id": uid("operator", sb),
                "sboid": sb,
                "code": r["businessorganisationabbreviationde"],
                "name": r["businessorganisationdescriptionde"] or sb,
                "translations": {
                    k: v
                    for k, v in (
                        ("de", r["businessorganisationdescriptionde"]),
                        ("fr", r["businessorganisationdescriptionfr"]),
                    )
                    if v
                },
            }

    # --- modes
    modes = [
        {
            "id": uid("mode", c),
            "code": c,
            "name": n,
            "parent": uid("mode", p) if p else None,
            "group": p is None,
        }
        for c, n, p in MODES
    ]

    # --- stops: all current ones; the ones Didok ends in December 2026 are loaded open and
    # ended by the change set; later ends (2027) are loaded with their end.
    stops, change_ends = [], []
    for r in sorted(didok, key=lambda r: r["number"]):
        end = end_exclusive(r["validto"])
        december = r["validto"].startswith("2026-12")
        stop = {
            "id": uid("stop", r["number"]),
            "name": r["designationofficial"],
            "number": r["number"],
            "sloid": r["sloid"],
            "abbreviation": r["abbreviation"],
            "lat": r["geopos"]["lat"] if r["geopos"] else None,
            "lon": r["geopos"]["lon"] if r["geopos"] else None,
            "height": r["height"],
            "validFrom": r["validfrom"],
            "validTo": None if december else end,
            "parent": municipalities[r["fsonumber"]]["id"],
            "operator": operators[r["businessorganisation"]]["id"]
            if r["businessorganisation"]
            else None,
            "modes": [uid("mode", m) for m in (r["meansoftransport"] or "").split("|") if m],
        }
        stops.append(stop)
        if december:
            change_ends.append(
                {
                    "stop": stop["id"],
                    "number": r["number"],
                    "name": r["designationofficial"],
                    "validTo": end,
                    "didokValidTo": r["validto"],
                }
            )
    stop_ids = {s["number"]: s["id"] for s in stops}

    # --- systems and codes
    systems = [
        {
            "id": uid("system", "wikidata-municipalities"),
            "key": "wikidata-municipalities",
            "name": "Wikidata: municipalities",
            "description": "Item numbers (Q-ids) of the municipalities, found by their FSO number (P771). Real, CC0.",
        },
        {
            "id": uid("system", "wikidata-stations"),
            "key": "wikidata-stations",
            "name": "Wikidata: stations",
            "description": "Item numbers (Q-ids) of railway stations, found by their UIC station code (P722). Real, CC0.",
        },
        {
            "id": uid("system", "ticketing"),
            "key": "ticketing",
            "name": "Regional ticketing (FICTIONAL)",
            "description": "FICTIONAL: a made-up ticketing system with made-up codes, to show mapping.",
        },
    ]
    sysid = {s["key"]: s["id"] for s in systems}
    codes = []  # {id, system, code, name, targetType, targets: [(type, id)]}

    def add_code(system, code, name, ttype, targets):
        codes.append(
            {
                "id": uid("code", f"{system}:{code}"),
                "system": sysid[system],
                "code": code,
                "name": name,
                "targetType": ttype,
                "targets": targets,
            }
        )

    for fso, m in sorted(municipalities.items()):
        if m["qid"]:
            add_code(
                "wikidata-municipalities",
                m["qid"],
                f"{m['qid']} {m['name']}",
                "municipality",
                [m["id"]],
            )
    seen = set()
    for b in stations_wd:
        n = int(b["uic"]["value"])
        if n in stop_ids and qid(b) not in seen:
            seen.add(qid(b))
            nm = next(s["name"] for s in stops if s["number"] == n)
            add_code("wikidata-stations", qid(b), f"{qid(b)} {nm}", "stop", [stop_ids[n]])
    for code, label, kind, tg in FICTIONAL_TICKETING:
        ids = (
            [stop_ids[n] for n in tg]
            if kind == "stop"
            else [municipalities[str(n)]["id"] for n in tg]
        )
        add_code("ticketing", code, f"{code} FICTIONAL: {label}", kind, ids)

    # --- translations (language x object)
    languages = [{"id": uid("language", c), "code": c, "name": n} for c, n in LANGS]
    translations = []

    def add_tr(kind, obj_id, obj_name, lang, text):
        translations.append(
            {
                "id": uid("translation", f"{kind}:{obj_id}:{lang}"),
                "language": uid("language", lang),
                "object": obj_id,
                "name": f"{obj_name} ({lang})",
                "text": text,
            }
        )

    for lang, text in canton["translations"].items():
        add_tr("canton", canton["id"], canton["name"], lang, text)
    for m in municipalities.values():
        for lang, text in m["translations"].items():
            add_tr("municipality", m["id"], m["name"], lang, text)
    for o in operators.values():
        for lang, text in o["translations"].items():
            add_tr("operator", o["id"], o["name"], lang, text)

    out = {
        "canton": canton,
        "districts": list(districts.values()),
        "municipalities": list(municipalities.values()),
        "operators": list(operators.values()),
        "modes": modes,
        "languages": languages,
        "systems": systems,
        "codes": codes,
        "stops": stops,
        "translations": translations,
        "changeSet": {
            "name": "December 2026 timetable change",
            "ends": change_ends,
            "addIfMissing": {
                "number": 8509050,
                "name": "Chur West",
                "present": 8509050 in stop_ids,
            },
        },
        "snapshot": meta,
    }
    write_set("reference", out)
    write_set("docs", docs_subset(out))
    (DATA / "SNAPSHOT.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")


def docs_subset(full: dict) -> dict:
    """The docs set: the stops a train serves, and everything they point at (their municipalities,
    districts and canton, their operators, the code and name records of those), with all modes and
    languages. No change set: the guide's examples open their own."""
    train = uid("mode", "TRAIN")
    stops = [s for s in full["stops"] if train in s["modes"]]
    stop_ids = {s["id"] for s in stops}
    municipalities = [m for m in full["municipalities"] if m["id"] in {s["parent"] for s in stops}]
    municipality_ids = {m["id"] for m in municipalities}
    districts = [d for d in full["districts"] if d["id"] in {m["parent"] for m in municipalities}]
    operators = [o for o in full["operators"] if o["id"] in {s["operator"] for s in stops}]
    present = stop_ids | municipality_ids
    codes = []
    for c in full["codes"]:
        targets = [t for t in c["targets"] if t in present]
        if targets or not c["targets"]:
            codes.append({**c, "targets": targets})
    system_ids = {c["system"] for c in codes}
    owners = {full["canton"]["id"]} | municipality_ids | {o["id"] for o in operators}
    return {
        **full,
        "districts": districts,
        "municipalities": municipalities,
        "operators": operators,
        "systems": [s for s in full["systems"] if s["id"] in system_ids],
        "codes": codes,
        "stops": stops,
        "translations": [t for t in full["translations"] if t["object"] in owners],
        "changeSet": {**full["changeSet"], "ends": []},
    }


def write_set(name: str, data: dict) -> None:
    folder = DATA / name
    folder.mkdir(parents=True, exist_ok=True)
    for k, v in data.items():
        if k != "snapshot":
            (folder / f"{k}.json").write_text(json.dumps(v, ensure_ascii=False) + "\n")
    counts = {k: (len(v) if isinstance(v, list) else 1) for k, v in data.items() if k != "snapshot"}
    counts["stopModeRelations"] = sum(len(s["modes"]) for s in data["stops"])
    counts["codeMappings"] = sum(len(c["targets"]) for c in data["codes"])
    counts["unmappedCodes"] = sum(1 for c in data["codes"] if not c["targets"])
    counts["records"] = (
        sum(
            counts[k]
            for k in (
                "districts municipalities operators modes languages systems codes stops translations"
            ).split()
        )
        + 1
    )
    print(name, json.dumps(counts))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args()
    if not a.offline:
        download(a.date)
    transform()
    return 0


if __name__ == "__main__":
    sys.exit(main())
